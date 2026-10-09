# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 Venius24
# Extracted from BuyShark: https://github.com/Venius24/kaspi-price-feed
# Preserve attribution notices; see LICENSE and NOTICE.

"""Host application adapters. No database, credentials or network defaults."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any
import inspect
import os
import re


class IntegrationNotConfigured(RuntimeError):
    pass


class AssortmentTruncated(Exception):
    """Catalog adapters must raise this instead of returning a partial catalog."""
    def __init__(self, reason: str, collected: int):
        self.reason, self.collected = reason, collected
        super().__init__(f"Incomplete assortment ({collected} offers): {reason}")


@dataclass(frozen=True)
class Integrations:
    catalog: Callable[..., list] | None = None
    merchant_id: Callable[..., str] | None = None
    request: Callable[..., Any] | None = None
    cached_products: Callable[[str], list] | None = None
    pending_intents: Callable[[str], dict] | None = None
    moved_after_snapshot: Callable[..., set] | None = None
    acknowledge_intents: Callable[..., tuple] | None = None
    notify: Callable[..., Any] | None = None
    data_dir: Path | None = None


_current = ContextVar("kaspi_price_feed_integrations", default=Integrations())


@contextmanager
def use_integrations(adapters: Integrations):
    """Scope adapters to the current task; concurrent stores may use different sessions."""
    token = _current.set(adapters)
    try:
        yield adapters
    finally:
        _current.reset(token)


def _required(name):
    callback = getattr(_current.get(), name)
    if callback is None:
        raise IntegrationNotConfigured(f"Configure Integrations.{name} before calling this operation")
    return callback


class KaspiAPI:
    @staticmethod
    def sync_merchant_assortment(token, store_id=None, strict=False):
        return _required("catalog")(token, store_id=store_id, strict=strict)

    @staticmethod
    def get_merchant_id(token, store_id=None):
        return _required("merchant_id")(token, store_id=store_id)


def _mc_api_request(method, url, **kwargs):
    """Delegate authenticated MC HTTP, preserving multipart headers and store isolation."""
    return _required("request")(method, url, **kwargs)


def _load_products(store_id):
    callback = _current.get().cached_products
    return callback(store_id) if callback else []


def pending_intents(store_id):
    callback = _current.get().pending_intents
    return callback(store_id) if callback else {}


def moved_after_snapshot(store_id, snapshot_at):
    callback = _current.get().moved_after_snapshot
    return callback(store_id, snapshot_at) if callback else set()


def acknowledge_intents(store_id, declared, snapshot_at):
    callback = _current.get().acknowledge_intents
    return callback(store_id, declared, snapshot_at) if callback else (0, 0)


async def dispatch(*args, **kwargs):
    callback = _current.get().notify
    if callback is None:
        import logging
        logging.getLogger(__name__).warning("Feed notification: %s", args)
        return
    result = callback(*args, **kwargs)
    if inspect.isawaitable(result):
        await result


def store_directory(store_id):
    value = str(store_id)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value) or value.upper() in {
        "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }:
        raise ValueError("store_id must be a safe, non-reserved directory name")
    root = _current.get().data_dir
    if root is None:
        root = Path(os.getenv("KASPI_PRICE_FEED_DATA_DIR", ".kaspi-price-feed"))
    directory = Path(root).resolve() / value
    if directory.is_symlink():
        raise ValueError("store directory must not be a symlink")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def is_placeholder_name(name, sku=None):
    if not name:
        return True
    name = str(name).strip()
    return name in ("", "Товар", "Товар без названия") or bool(sku and name == f"Товар {sku}")
