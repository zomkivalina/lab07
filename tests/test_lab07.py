import io
from decimal import Decimal
from functools import partial, reduce
from operator import attrgetter, itemgetter, methodcaller, mul
from pathlib import Path
from typing import Any

import pytest

from core import (
    adjust_total,
    loyalty_discount,
    normalize_order,
    only_paid,
    pipeline,
    rank_orders,
    remote_delivery,
    revenue,
    sort_rows_city_total_id,
    take,
    top_paid_orders,
    totals_by_city,
)
from loaders import load_orders
from models import Box, Order, OrderRank

D = Decimal

# ---------- pipeline / reduce ----------


def test_pipeline_runs_left_to_right() -> None:
    def inc(x: int) -> int:
        return x + 1

    def dbl(x: int) -> int:
        return x * 2

    assert pipeline(3, inc, dbl, inc) == 9  # ((3+1)*2)+1
    assert pipeline(3) == 3  # без функцій — саме значення


def test_reduce_with_initial_value() -> None:
    assert reduce(mul, [], 1) == 1
    assert revenue([]) == D("0.00")


# ---------- нормалізація ----------


def test_normalize_order_from_json_and_csv_types() -> None:
    o = normalize_order(
        {
            "id": "7",
            "customer": "  олена коваль ",
            "total": " 99.999 ",
            "status": " PAID",
            "city": "львів",
        }
    )
    assert o == Order(7, "Олена Коваль", D("100.00"), "paid", "Львів")


def test_normalize_order_rejects_bad_records() -> None:
    with pytest.raises(ValueError):
        normalize_order({"id": 1, "customer": "x"})  # немає полів
    with pytest.raises(ValueError):
        normalize_order(
            {"id": "x", "customer": "a", "total": 1, "status": "paid", "city": "b"}
        )


# ---------- partial ----------


def test_partial_policies() -> None:
    order = Order(1, "A", D("3000.00"), "paid", "Ужгород")
    assert loyalty_discount(order).total == D("2700.00")
    assert remote_delivery(order).total == D("3080.00")
    assert order.total == D("3000.00")  # оригінал не змінено
    below = Order(2, "B", D("1999.99"), "paid", "Київ")
    assert loyalty_discount(below) == below  # нижче порогу — без знижки
    assert isinstance(loyalty_discount, partial)
    assert loyalty_discount.keywords["discount_rate"] == D("0.10")


def test_custom_partial_policy_changes_ranking(rows: list[dict[str, Any]]) -> None:
    big_surcharge = partial(
        adjust_total, surcharge=D("2000"), surcharge_cities=frozenset({"Ужгород"})
    )
    top = top_paid_orders(rows, top=1, policies=(big_surcharge,))
    assert top[0].id == 4 and top[0].total == D("3500.00")


# ---------- основне завдання ----------


def test_top_paid_orders(rows: list[dict[str, Any]]) -> None:
    top = top_paid_orders(rows, top=3)
    # оплачені: 1 (2500→2250), 3 (2500→2250), 4 (1500+80=1580); 2 і 5 не оплачені
    assert [o.id for o in top] == [1, 3, 4]
    assert [o.total for o in top] == [D("2250.00"), D("2250.00"), D("1580.00")]


def test_top_n_edge_cases(rows: list[dict[str, Any]]) -> None:
    assert top_paid_orders(rows, top=0) == []
    assert len(top_paid_orders(rows, top=100)) == 3
    assert top_paid_orders([], top=3) == []
    with pytest.raises(ValueError):
        take(-1)


def test_input_rows_are_not_mutated(rows: list[dict[str, Any]]) -> None:
    snapshot = [dict(r) for r in rows]
    top_paid_orders(rows)
    assert rows == snapshot


# ---------- singledispatch ----------


def test_load_orders_same_for_all_sources(
    rows: list[dict[str, Any]], json_path: Path, csv_path: Path
) -> None:
    json_text = json_path.read_text(encoding="utf-8")
    expected = top_paid_orders(rows)
    with json_path.open(encoding="utf-8") as fh:
        from_file = top_paid_orders(fh)
    with csv_path.open(encoding="utf-8") as fh:
        from_csv_file = top_paid_orders(fh)
    for result in (
        top_paid_orders(json_text),
        top_paid_orders(str(json_path)),
        top_paid_orders(json_path),
        top_paid_orders(str(csv_path)),
        top_paid_orders(csv_path),
        top_paid_orders(io.StringIO(json_text)),
        from_file,
        from_csv_file,
        top_paid_orders(tuple(rows)),
    ):
        assert result == expected


def test_json_string_equals_path(json_path: Path) -> None:
    assert load_orders(json_path.read_text(encoding="utf-8")) == load_orders(json_path)


def test_load_orders_errors() -> None:
    with pytest.raises(TypeError):
        load_orders(42)
    with pytest.raises(ValueError):
        load_orders([1, 2, 3])
    with pytest.raises(FileNotFoundError):
        load_orders("no_such_file.json")


def test_registered_types() -> None:
    assert {str, Path, io.TextIOBase, list, tuple} <= set(load_orders.registry)


# ---------- operator ----------


def test_itemgetter_multi_key_sort() -> None:
    rows = [{"a": 1, "b": 2}, {"a": 1, "b": 1}, {"a": 0, "b": 9}]
    assert sorted(rows, key=itemgetter("a", "b")) == [
        {"a": 0, "b": 9},
        {"a": 1, "b": 1},
        {"a": 1, "b": 2},
    ]


def test_sort_rows_city_total_id() -> None:
    rows = [
        {"id": 3, "city": "Київ", "total": 10},
        {"id": 1, "city": "Київ", "total": 50},
        {"id": 2, "city": "Київ", "total": 50},
        {"id": 4, "city": "Дніпро", "total": 5},
    ]
    assert [r["id"] for r in sort_rows_city_total_id(rows)] == [4, 1, 2, 3]


def test_attrgetter_and_methodcaller() -> None:
    o = Order(1, "Анна", D("10.00"), "paid", "Львів")
    assert attrgetter("customer", "city")(o) == ("Анна", "Львів")
    assert methodcaller("replace", "a", "o")("banana") == "bonono"
    assert list(only_paid([o, Order(2, "Б", D("1"), "new", "К")])) == [o]


def test_reduce_aggregations(rows: list[dict[str, Any]]) -> None:
    orders = top_paid_orders(rows, top=10, policies=())
    assert revenue(orders) == D("6500.00")
    assert totals_by_city(orders) == {
        "Львів": D("2500.00"),
        "Київ": D("2500.00"),
        "Ужгород": D("1500.00"),
    }


# ---------- total_ordering ----------


def test_order_rank_all_comparisons() -> None:
    low, high = OrderRank(D("100"), 1), OrderRank(D("200"), 2)
    early, late = OrderRank(D("100"), 1), OrderRank(D("100"), 9)
    assert low < high and low <= high and high > low and high >= low
    assert early > late  # рівна сума: менший id — вищий ранг
    assert late < early and late <= early and early >= late
    assert low == OrderRank(D("100.00"), 1) and low != high
    assert hash(low) == hash(OrderRank(D("100"), 1))


def test_order_rank_not_implemented_for_other_types() -> None:
    rank = OrderRank(D("1"), 1)
    assert rank.__eq__(42) is NotImplemented
    assert rank.__lt__("x") is NotImplemented
    assert rank != 42
    with pytest.raises(TypeError):
        _ = rank < 42


def test_rank_orders_sorted_total_desc_id_asc() -> None:
    orders = [Order(i, "x", D(t), "paid", "c") for i, t in [(5, 10), (2, 30), (1, 10)]]
    assert [o.id for o in rank_orders(orders)] == [2, 1, 5]


def test_box_ordering() -> None:
    small, a, b, c = Box(1, 1, 1), Box(1, 4, 6), Box(2, 3, 4), Box(3, 2, 4)
    assert sorted([c, b, a, small]) == [small, a, b, c]  # об'єм → w*h → w
    assert a <= b and c >= b and b > a and not (b < a)
    assert Box(2, 3, 4) == Box(2, 3, 4)
    assert Box(1, 1, 1).__lt__("box") is NotImplemented
