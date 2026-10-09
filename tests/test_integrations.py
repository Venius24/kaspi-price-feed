# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 Venius24
# Extracted from BuyShark: https://github.com/Venius24/kaspi-price-feed
# Preserve attribution notices; see LICENSE and NOTICE.

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from kaspi_price_feed import Integrations, use_integrations, build_catalog_snapshot
from kaspi_price_feed.integrations import (
    IntegrationNotConfigured, KaspiAPI, store_directory, _mc_api_request,
)


def test_missing_adapter_fails_without_network():
    with pytest.raises(IntegrationNotConfigured):
        _mc_api_request("GET", "https://mc.shop.kaspi.kz/", store_id="demo")


def test_nested_adapters_restore_previous_context():
    with use_integrations(Integrations(merchant_id=lambda token, **kw: "outer")):
        with use_integrations(Integrations(merchant_id=lambda token, **kw: "inner")):
            assert KaspiAPI.get_merchant_id("unused") == "inner"
        assert KaspiAPI.get_merchant_id("unused") == "outer"
    with pytest.raises(IntegrationNotConfigured):
        KaspiAPI.get_merchant_id("unused")


def test_concurrent_adapters_do_not_share_store_identity():
    def read(merchant):
        with use_integrations(Integrations(merchant_id=lambda token, **kw: merchant)):
            return KaspiAPI.get_merchant_id("unused")
    with ThreadPoolExecutor() as pool:
        assert list(pool.map(read, ["first", "second"])) == ["first", "second"]


@pytest.mark.parametrize("store_id", ["../outside", "a/b", "a\\b", "", "C:", "CON", "NUL"])
def test_storage_rejects_unsafe_store_ids(store_id):
    with pytest.raises(ValueError):
        store_directory(store_id)


def test_storage_uses_host_application_directory(tmp_path):
    with use_integrations(Integrations(data_dir=tmp_path)):
        assert store_directory("my-store") == tmp_path / "my-store"


def test_catalog_adapter_receives_strict_and_store_identity():
    calls = []
    def catalog(token, **kwargs):
        calls.append(kwargs)
        return [{"merchantSku": f"DEMO-{i}", "price_num": 1000, "stock": 1,
                 "available": True} for i in range(5)]
    def merchant(token, **kwargs):
        assert kwargs["store_id"] == "my-store"
        return "10000001"
    with use_integrations(Integrations(catalog=catalog, merchant_id=merchant)):
        assert build_catalog_snapshot("unused", "my-store").size == 5
    assert calls == [{"store_id": "my-store", "strict": True}]
