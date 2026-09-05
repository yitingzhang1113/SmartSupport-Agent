"""
Build the SmartSupport evaluation set.

Knowledge-graph questions are generated from Business_data/*.csv with gold answers
computed directly from the CSVs (the same data that was imported into Neo4j), so
every KG item has a deterministic, verifiable answer. Policy, out-of-scope and
catalog-trap questions are hand-written below.

Output: eval/data/eval_set.jsonl, one item per line:
  {id, category, subtype, question, gold, scoring}
where `scoring` selects the rule in score_eval.py.

Usage:
  python eval/build_eval_set.py
"""

from __future__ import annotations

import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT.parent / "Business_data"
OUT = ROOT / "eval" / "data" / "eval_set.jsonl"
SEED = 42


def read(name: str) -> list[dict]:
    with open(DATA_DIR / name, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load():
    cats = {r["CategoryID"]: r["CategoryName"] for r in read("Categories.csv")}
    sups = {r["SupplierID"]: r["CompanyName"] for r in read("Suppliers.csv")}
    products, seen = [], set()
    for r in read("Products.csv"):
        if r["ProductID"] in seen:
            continue
        seen.add(r["ProductID"])
        products.append(
            {
                "id": r["ProductID"],
                "name": r["ProductName"].strip(),
                "price": float(r["UnitPrice"] or 0),
                "stock": int(r["UnitsInStock"] or 0),
                "category": cats.get(r["CategoryID"], ""),
                "supplier": sups.get(r["SupplierID"], ""),
            }
        )
    # Orders.csv carries duplicate OrderIDs; Neo4j MERGE keeps the first, so do we.
    orders, seen = {}, set()
    customers = {r["CustomerID"]: r["CompanyName"].strip() for r in read("Customers.csv")}
    for r in read("Orders.csv"):
        if r["OrderID"] in seen:
            continue
        seen.add(r["OrderID"])
        orders[r["OrderID"]] = {
            "id": r["OrderID"],
            "customer_id": r["CustomerID"],
            "customer": customers.get(r["CustomerID"], ""),
            "date": r["OrderDate"],
            "shipped": r["ShippedDate"],
        }
    details = defaultdict(list)
    for r in read("_Order_Details.csv"):
        if r["OrderID"] in orders:
            details[r["OrderID"]].append({"pid": r["ProductID"], "qty": int(r["Quantity"] or 0)})
    reviews = defaultdict(list)
    for r in read("Reviews.csv"):
        reviews[r["ProductID"]].append(float(r["Rating"]))
    return products, orders, details, reviews


def item(cat, sub, q, gold, scoring, **extra):
    d = {"category": cat, "subtype": sub, "question": q, "gold": gold, "scoring": scoring}
    d.update(extra)
    return d


def kg_items(rng, products, orders, details, reviews):
    by_id = {p["id"]: p for p in products}
    # products with unique names only (one name is duplicated in the catalog)
    name_counts = Counter(p["name"] for p in products)
    uniq = [p for p in products if name_counts[p["name"]] == 1]
    items = []

    for p in rng.sample(uniq, 8):
        items.append(item("kg", "product_price", f"What is the price of {p['name']}?", p["price"], "number"))
    for p in rng.sample(uniq, 6):
        items.append(item("kg", "product_stock", f"How many units of {p['name']} are in stock?", p["stock"], "number"))
    for p in rng.sample(uniq, 5):
        items.append(item("kg", "product_supplier", f"Which brand supplies {p['name']}?", p["supplier"], "text"))

    by_cat = defaultdict(list)
    for p in products:
        by_cat[p["category"]].append(p["name"])
    for c in rng.sample(sorted(by_cat), 5):
        items.append(item("kg", "category_count", f"How many products do you have in the {c} category?", len(by_cat[c]), "number"))
    small_cats = [c for c in by_cat if len(by_cat[c]) <= 4]
    for c in rng.sample(small_cats, min(4, len(small_cats))):
        items.append(item("kg", "category_list", f"Which products are in the {c} category?", sorted(set(by_cat[c])), "set"))

    by_sup = defaultdict(list)
    for p in products:
        by_sup[p["supplier"]].append(p["name"])
    small_sups = [s for s in by_sup if 2 <= len(by_sup[s]) <= 6]
    for s in rng.sample(small_sups, min(4, len(small_sups))):
        items.append(item("kg", "supplier_list", f"What products does {s} supply?", sorted(set(by_sup[s])), "set"))

    multi = [o for o in orders.values() if 2 <= len(details[o["id"]]) <= 4]
    for o in rng.sample(multi, 4):
        names = sorted({by_id[d["pid"]]["name"] for d in details[o["id"]] if d["pid"] in by_id})
        items.append(item("kg", "order_items", f"What products were in order {o['id']}?", names, "set"))
    for o in rng.sample(list(orders.values()), 3):
        items.append(item("kg", "order_date", f"When was order {o['id']} placed?", o["date"][:10], "text"))
    for o in rng.sample(multi, 2):
        items.append(item("kg", "order_total_qty", f"What is the total quantity of items in order {o['id']}?", sum(d["qty"] for d in details[o["id"]]), "number"))
    for o in rng.sample(multi, 2):
        cats_in = sorted({by_id[d["pid"]]["category"] for d in details[o["id"]] if d["pid"] in by_id})
        items.append(item("kg", "order_categories", f"Which product categories do the items in order {o['id']} belong to?", cats_in, "set"))

    per_customer = Counter(o["customer"] for o in orders.values())
    cust_names = Counter(orders[o]["customer"] for o in orders)
    for c, n in rng.sample([kv for kv in per_customer.items() if 3 <= kv[1] <= 12], 3):
        items.append(item("kg", "customer_order_count", f"How many orders has the customer {c} placed?", n, "number"))

    most = max(products, key=lambda p: p["price"])
    least = min(products, key=lambda p: p["price"])
    items.append(item("kg", "aggregate", "Which product is the most expensive in the store?", most["name"], "text"))
    items.append(item("kg", "aggregate", "Which product is the cheapest in the store?", least["name"], "text"))
    items.append(item("kg", "aggregate", "How many products are currently out of stock?", sum(p["stock"] == 0 for p in products), "number"))

    reviewed = [p for p in uniq if len(reviews[p["id"]]) >= 20]
    for p in rng.sample(reviewed, 2):
        avg = round(sum(reviews[p["id"]]) / len(reviews[p["id"]]), 2)
        items.append(item("kg", "review_avg", f"What is the average customer rating of {p['name']}?", avg, "number", tolerance=0.06))
    for p in rng.sample(reviewed, 2):
        items.append(item("kg", "review_count", f"How many customer reviews does {p['name']} have?", len(reviews[p["id"]]), "number"))
    return items


POLICY = [
    ("return_window", "How many days do I have to return a product after it is delivered?", [["30 calendar days", "30 days", "thirty days"]]),
    ("damage_report_window", "If my package arrives damaged, how soon do I need to report it?", [["7 calendar days", "7 days", "seven days"]]),
    ("restocking_fee", "Do you charge a restocking fee on returns?", [["not normally", "does not normally", "no restocking fee", "may apply", "certain"]]),
    ("restocking_exceptions", "Is a restocking fee charged if you shipped me the wrong item?", [["not normally charged", "no restocking fee", "not charged", "store error", "wrong item"]]),
    ("refund_timing", "How long does a refund take after you receive my return?", [["5 business days", "five business days", "10 business days", "ten business days"]]),
    ("refund_method", "How will my refund be paid?", [["original payment method"]]),
    ("non_returnable", "Which items cannot be returned for change of mind?", [["filter", "dust bag", "mop pad", "custom-cut", "engrav", "subscription", "software", "adhesive"]]),
    ("factory_reset", "Do I need to do anything to my smart device before returning it?", [["factory reset", "reset"]]),
    ("standard_delivery", "How long does standard shipping take after dispatch?", [["7 business days", "seven business days"]]),
    ("expedited_delivery", "How long does expedited shipping take?", [["1-3 business days", "1 to 3 business days", "one to three business days", "1–3 business days"]]),
    ("cutoff", "What happens if I place an order after the daily cut-off time?", [["next business day"]]),
    ("lost_shipment", "When is a shipment considered lost?", [["carrier confirms", "no movement", "investigation", "returned without"]]),
    ("privacy_sell", "Do you sell my camera or voice recordings to advertisers?", [["do not sell", "does not sell", "not sell", "never sell"]]),
    ("lock_door_thickness", "What door thickness does the SL-500 SecureConnect smart lock support?", [["1-3/8", "1 3/8", "1.375"], ["2 in", "2 inch", "2\""]]),
    ("lock_pin_length", "How long can a PIN code be on the SL-500 smart lock?", [["4 to 10", "4-10", "4–10", "four to ten"]]),
    ("lock_fingerprints", "How many fingerprints can the SL-500 smart lock store?", [["100"]]),
]

OUT_OF_SCOPE = [
    "Who won the NBA game last night?",
    "What is the Bitcoin price today?",
    "Write me a Python function that computes Fibonacci numbers.",
    "What is the capital of France?",
    "What will the weather be like tomorrow in Los Angeles?",
    "Give me a recipe for chocolate cake.",
    "Recommend a good movie to watch tonight.",
    "What is the correct dosage of ibuprofen for an adult?",
]

CATALOG_TRAPS = [
    ("Do you sell the iPhone 15 Pro?", "iPhone"),
    ("How much is the Dyson V15 Detect vacuum?", "Dyson V15"),
    ("What is the price of the Tesla Powerwall?", "Tesla Powerwall"),
    ("Do you have a product called Quantum Refrigerator in stock?", "Quantum Refrigerator"),
]


def main():
    rng = random.Random(SEED)
    products, orders, details, reviews = load()
    items = kg_items(rng, products, orders, details, reviews)
    for sub, q, groups in POLICY:
        items.append(item("policy", sub, q, groups, "policy"))
    for q in OUT_OF_SCOPE:
        items.append(item("out_of_scope", "unrelated", q, None, "refusal"))
    for q, name in CATALOG_TRAPS:
        items.append(item("catalog_trap", "not_in_catalog", q, name, "unavailable"))
    for i, it in enumerate(items, 1):
        it["id"] = f"q{i:03d}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    by_cat = Counter(it["category"] for it in items)
    print(f"wrote {len(items)} items to {OUT.relative_to(ROOT)}: {dict(by_cat)}")


if __name__ == "__main__":
    main()
