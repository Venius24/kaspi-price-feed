# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 Venius24
# Extracted from BuyShark: https://github.com/Venius24/kaspi-price-feed
# Preserve attribution notices; see LICENSE and NOTICE.

"""Offline, synthetic catalog: run after `python -m pip install -e .`."""
from pathlib import Path
from kaspi_price_feed import Integrations, use_integrations, build_feed_plan, render_plan_report


def main():
    products = [
        {"merchantSku": f"DEMO-{i:03d}", "name": f"Demo product {i}",
         "brand": "demobrand", "price_num": 1000, "stock": 10.0,
         "available": True, "status": "Активен"}
        for i in range(10)
    ]
    identity = {p["merchantSku"]: {"name": p["name"], "brand": p["brand"]} for p in products}
    adapters = Integrations(
        catalog=lambda token, **kwargs: products,
        merchant_id=lambda token, **kwargs: "10000001",
    )
    with use_integrations(adapters):
        plan = build_feed_plan(
            "unused-demo-token", "demo-store", baseline_count=10,
            intents={"DEMO-003": {"price": 990, "reason": "demo"}},
            identity=identity, identity_source="synthetic demo (offline)",
            use_accepted_identity=False,
        )
        print(render_plan_report(plan))
        Path("demo-feed.xml").write_bytes(plan.xml)
        print("Saved demo-feed.xml. No network requests or uploads.")


if __name__ == "__main__":
    main()
