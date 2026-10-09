# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 Venius24
# Extracted from BuyShark: https://github.com/Venius24/kaspi-price-feed
# Preserve attribution notices; see LICENSE and NOTICE.

import datetime
import json
from kaspi_price_feed import CatalogSnapshot, Integrations, use_integrations
from kaspi_price_feed.xml_feed import generate_xml_feed
from kaspi_price_feed.feed_uploader import UploadVerdict
from kaspi_price_feed.feed_settle import settle_file
from kaspi_price_feed import feed_state


def _case(tmp_path):
    offers = [{"merchantSku": f"DEMO-{i}", "price_num": 1000, "stock": 10,
               "available": True, "name": "Demo", "brand": "demo"} for i in range(10)]
    now = datetime.datetime.now()
    path = tmp_path / "feed.xml"
    path.write_bytes(generate_xml_feed("10000001", offers))
    path.with_suffix(".xml.meta.json").write_text(json.dumps({
        "active_before": 10, "archived_before": ["OLD-ARCHIVE"],
        "snapshot_at": now.isoformat(),
    }))
    snapshot = CatalogSnapshot("demo", "10000001", offers, now, archived_skus=["OLD-ARCHIVE"])
    verdict = UploadVerdict("file-id", "feed.xml", "FLUSHED", distinct=10, processed=10)
    return path, snapshot, verdict


def test_matching_catalog_acknowledges_via_host_adapter(tmp_path):
    path, snapshot, verdict = _case(tmp_path)
    calls = []
    def acknowledge(store_id, declared, snapshot_at):
        calls.append((store_id, declared, snapshot_at))
        return 3, 2
    with use_integrations(Integrations(acknowledge_intents=acknowledge)):
        report = settle_file("demo", path, verdict, snapshot=snapshot)
    assert not report.needs_attention
    assert (report.settled, report.kept_queued) == (3, 2)
    assert calls[0][0] == "demo" and len(calls[0][1]) == 10


def test_catalog_loss_disables_feed_before_acknowledgement(tmp_path):
    path, snapshot, verdict = _case(tmp_path)
    snapshot.offers = snapshot.offers[:5]
    calls = []
    with use_integrations(Integrations(acknowledge_intents=lambda *args: calls.append(args))):
        feed_state.enable("demo")
        report = settle_file("demo", path, verdict, snapshot=snapshot)
        assert not feed_state.is_enabled("demo")
    assert report.alarms and not calls


def test_concurrent_price_change_is_explained_by_host_adapter(tmp_path):
    path, snapshot, verdict = _case(tmp_path)
    snapshot.offers[0]["price_num"] = 950
    with use_integrations(Integrations(moved_after_snapshot=lambda *args: {"DEMO-0"})):
        report = settle_file("demo", path, verdict, snapshot=snapshot)
    assert not report.mismatches
    assert report.mismatches_explained[0]["sku"] == "DEMO-0"


def test_first_unexpected_archive_is_detected_with_empty_prior_archive(tmp_path):
    path, snapshot, verdict = _case(tmp_path)
    meta_path = path.with_suffix(".xml.meta.json")
    meta = json.loads(meta_path.read_text())
    meta["archived_before"] = []
    meta_path.write_text(json.dumps(meta))
    snapshot.offers = snapshot.offers[1:]
    snapshot.archived_skus = ["DEMO-0"]
    report = settle_file("demo", path, verdict, snapshot=snapshot)
    assert report.unexpected_archived == ["DEMO-0"]
    assert report.alarms
