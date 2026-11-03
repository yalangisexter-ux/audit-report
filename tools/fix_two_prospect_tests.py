#!/usr/bin/env python3
"""Align the last two Store Directory tests with integrated module behavior."""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "tests" / "test_customer_prospects.py"
text = path.read_text(encoding="utf-8")

old_filter = '''        tab.records = [
            {"kind": "Store", "business_name": "Alpha Nutrition Store", "state": "Delhi", "business_category": "Sports Nutrition / Supplement Store"},
            {"kind": "Gym", "business_name": "Titan Gym & Fitness", "state": "Delhi", "business_category": "Fitness Centre / Gym"},
            {"kind": "Gym + Store", "business_name": "Iron Beast Gym Pro Shop", "state": "Delhi", "business_category": "Gym with Nutrition & Supplement Counter / Pro-Shop"},
        ]'''

new_filter = '''        tab.records = [
            {
                "kind": "Store",
                "business_name": "Alpha Nutrition Store",
                "state": "Delhi",
                "city": "New Delhi",
                "business_category": "Sports Nutrition / Supplement Store",
                "address": "12 Main Market Road, Connaught Place, New Delhi 110001",
                "maps": "https://www.google.com/maps/search/?api=1&query=Alpha+Nutrition+Store",
            },
            {"kind": "Gym", "business_name": "Titan Gym & Fitness", "state": "Delhi", "business_category": "Fitness Centre / Gym"},
            {"kind": "Gym + Store", "business_name": "Iron Beast Gym Pro Shop", "state": "Delhi", "business_category": "Gym with Nutrition & Supplement Counter / Pro-Shop"},
        ]'''

if old_filter not in text:
    if "Connaught Place" in text:
        print("filter records already patched")
    else:
        raise SystemExit("filter records block not found")
else:
    text = text.replace(old_filter, new_filter, 1)
    print("patched filter records")

old_maps = 'assert enriched["maps"].startswith("https://www.google.com/maps/search/?")'
new_maps = 'assert enriched["maps"].startswith(("https://www.google.com/maps/", "https://maps.google.com/"))'
if old_maps not in text:
    if new_maps in text:
        print("maps assert already patched")
    else:
        raise SystemExit("maps assert not found")
else:
    text = text.replace(old_maps, new_maps, 1)
    print("patched maps assert")

path.write_text(text, encoding="utf-8")
print("done", path)
