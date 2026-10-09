# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 Venius24
# Extracted from BuyShark: https://github.com/Venius24/kaspi-price-feed
# Preserve attribution notices; see LICENSE and NOTICE.

"""Kaspi XML price feeds extracted from BuyShark."""
from .integrations import AssortmentTruncated, Integrations, use_integrations
from .xml_feed import FeedSerializationError, generate_xml_feed
from .feed_snapshot import CatalogSnapshot, FeedSnapshotRefused, build_catalog_snapshot
from .feed_plan import FeedPlan, FeedPlanRefused, build_feed_plan, render_plan_report
from .feed_uploader import FeedUploadFailed, FeedUploadRefused, send_plan
from .feed_settle import SettleReport, settle_file

__all__ = [
    "AssortmentTruncated", "Integrations", "use_integrations",
    "FeedSerializationError", "generate_xml_feed", "CatalogSnapshot",
    "FeedSnapshotRefused", "build_catalog_snapshot", "FeedPlan", "FeedPlanRefused",
    "build_feed_plan", "render_plan_report", "FeedUploadFailed", "FeedUploadRefused",
    "send_plan", "SettleReport", "settle_file",
]
