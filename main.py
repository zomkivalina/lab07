"""Демонстрація: конвеєр замовлень, singledispatch, operator, total_ordering."""

import io
from decimal import Decimal
from functools import partial
from operator import attrgetter, itemgetter
from pathlib import Path

from core import (
    adjust_total,
    normalize_all,
    only_paid,
    pipeline,
    revenue,
    sort_rows_city_total_id,
    top_paid_orders,
    totals_by_city,
)
from loaders import load_orders
from models import Box, Order, OrderRank

DATA = Path(__file__).parent


def show(orders: list[Order]) -> None:
    for place, o in enumerate(orders, start=1):
        print(
            f"  {place}. #{o.id} {o.customer:<16} {o.city:<9} {o.status:<10} "
            f"{o.total:>9} грн"
        )


def main() -> None:
    print(
        "=== TOP-5 ОПЛАЧЕНИХ (знижка 10% від 2000 грн, +80 грн у віддалені міста) ==="
    )
    show(top_paid_orders(DATA / "sample_data.json", top=5))

    print(
        "\n=== Той самий конвеєр, інша політика через partial: знижка 5% від 1000 ==="
    )
    small_discount = partial(
        adjust_total, discount_rate=Decimal("0.05"), discount_from=Decimal("1000")
    )
    show(top_paid_orders(DATA / "sample_data.json", top=3, policies=(small_discount,)))

    print("\n=== singledispatch: однаковий результат для різних джерел ===")
    json_text = (DATA / "sample_data.json").read_text(encoding="utf-8")
    sources: list[tuple[str, object]] = [
        ("JSON-рядок", json_text),
        ("шлях str (.json)", str(DATA / "sample_data.json")),
        ("Path (.csv)", DATA / "sample_data.csv"),
        ("відкритий файл", io.StringIO(json_text)),
        ("list[dict]", load_orders(json_text)),
    ]
    reference = top_paid_orders(json_text)
    for name, src in sources:
        result = top_paid_orders(src)
        ids = [o.id for o in result]
        verdict = "збігається" if result == reference else "ВІДРІЗНЯЄТЬСЯ"
        print(f"  {name:<17} -> Top-3 {ids} — {verdict}")

    paid = pipeline(
        DATA / "sample_data.json", load_orders, normalize_all, only_paid, list
    )
    print(f"\n=== reduce: оплачених {len(paid)}, виручка {revenue(paid)} грн ===")
    for city, total in sorted(
        totals_by_city(paid).items(), key=itemgetter(1), reverse=True
    ):
        print(f"  {city:<9} {total:>9} грн")

    print("\n=== operator: сортування словників за (city ↑, total ↓, id ↑) ===")
    rows = [{"id": o.id, "city": o.city, "total": o.total} for o in paid]
    for r in sort_rows_city_total_id(rows):
        print(f"  {r['city']:<9} {r['total']:>9}  #{r['id']}")
    names = list(map(attrgetter("customer", "city"), paid[:2]))
    print(f"  attrgetter('customer', 'city'): {names}")

    print("\n=== @total_ordering ===")
    a, b = OrderRank(Decimal("2205.00"), 101), OrderRank(Decimal("2205.00"), 106)
    print(f"  {a} > {b}: {a > b}   (рівна сума — вище менший id)")
    print(f"  {a} >= {b}: {a >= b},  <=: {a <= b},  ==: {a == b}")
    boxes = [Box(2, 3, 4), Box(1, 4, 6), Box(3, 2, 4), Box(1, 1, 1)]
    print(f"  sorted(boxes): {sorted(boxes)}")


if __name__ == "__main__":
    main()
