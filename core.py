"""Конвеєр обробки замовлень: partial + reduce + operator.

Кроки конвеєра — функції «колекція → колекція». Параметри кроків
фіксуються через functools.partial, а сам конвеєр збирає pipeline() на reduce.
"""

from collections.abc import Callable, Iterable, Mapping
from decimal import ROUND_HALF_UP, Decimal
from functools import partial, reduce
from itertools import islice
from operator import add, attrgetter, itemgetter, methodcaller
from typing import Any

from loaders import load_orders
from models import Order, OrderRank

CENT = Decimal("0.01")

# ---------- pipeline ----------


def pipeline(value: Any, *funcs: Callable[[Any], Any]) -> Any:
    """pipeline(x, f, g, h) == h(g(f(x))) — reduce з початковим значенням x."""
    return reduce(lambda acc, f: f(acc), funcs, value)


# ---------- Нормалізація ----------

clean = methodcaller("strip")
title_case = methodcaller("title")
lower = methodcaller("lower")


def to_money(value: object) -> Decimal:
    return Decimal(str(value).strip()).quantize(CENT, rounding=ROUND_HALF_UP)


def normalize_order(raw: Mapping[str, Any]) -> Order:
    """Сирий словник (JSON або CSV, де все — рядки) → незмінний Order."""
    try:
        return Order(
            id=int(raw["id"]),
            customer=pipeline(str(raw["customer"]), clean, title_case),
            total=to_money(raw["total"]),
            status=pipeline(str(raw["status"]), clean, lower),
            city=pipeline(str(raw["city"]), clean, title_case),
        )
    except (KeyError, ValueError, ArithmeticError) as exc:
        raise ValueError(f"некоректне замовлення {dict(raw)!r}: {exc}") from exc


# ---------- Цінова політика (налаштовується через partial) ----------


def adjust_total(
    order: Order,
    *,
    discount_rate: Decimal = Decimal("0"),
    discount_from: Decimal = Decimal("0"),
    surcharge: Decimal = Decimal("0"),
    surcharge_cities: frozenset[str] = frozenset(),
) -> Order:
    """Нове замовлення зі скоригованою сумою: знижка від порогу та
    надбавка за доставку у вказані міста. Вхідний Order не змінюється."""
    total = order.total
    if total >= discount_from and discount_rate:
        total -= total * discount_rate
    if order.city in surcharge_cities:
        total += surcharge
    return Order(
        order.id, order.customer, total.quantize(CENT), order.status, order.city
    )


# Готові політики: часткове застосування замість окремих функцій
loyalty_discount = partial(
    adjust_total, discount_rate=Decimal("0.10"), discount_from=Decimal("2000")
)
remote_delivery = partial(
    adjust_total,
    surcharge=Decimal("80"),
    surcharge_cities=frozenset({"Ужгород", "Чернівці", "Луцьк"}),
)

# ---------- Кроки конвеєра ----------

normalize_all: Callable[[Iterable[Mapping[str, Any]]], Iterable[Order]] = partial(
    map, normalize_order
)
only_paid: Callable[[Iterable[Order]], Iterable[Order]] = partial(
    filter, attrgetter("is_paid")
)


def apply_policy(
    policy: Callable[[Order], Order],
) -> Callable[[Iterable[Order]], Iterable[Order]]:
    return partial(map, policy)


def rank_orders(orders: Iterable[Order]) -> list[Order]:
    """total ↓, id ↑ — за допомогою OrderRank з @total_ordering."""
    return sorted(orders, key=OrderRank.of, reverse=True)


def take[T](n: int) -> Callable[[Iterable[T]], list[T]]:
    if n < 0:
        raise ValueError("n має бути >= 0")
    return lambda items: list(islice(items, n))


def top_paid_orders(
    source: object,
    top: int = 3,
    policies: tuple[Callable[[Order], Order], ...] = (
        loyalty_discount,
        remote_delivery,
    ),
) -> list[Order]:
    """Основне завдання: завантажити → нормалізувати → оплачені →
    знижка/надбавка → сортування за total → Top-N."""
    return pipeline(  # type: ignore[no-any-return]
        source,
        load_orders,
        normalize_all,
        only_paid,
        *map(apply_policy, policies),
        rank_orders,
        take(top),
    )


# ---------- reduce-агрегації ----------


def revenue(orders: Iterable[Order]) -> Decimal:
    return reduce(add, map(attrgetter("total"), orders), Decimal("0.00"))


def totals_by_city(orders: Iterable[Order]) -> dict[str, Decimal]:
    """Сума по містах: reduce з новим словником на кожному кроці."""
    return reduce(
        lambda acc, o: {**acc, o.city: acc.get(o.city, Decimal("0.00")) + o.total},
        orders,
        {},
    )


# ---------- operator: багатокритеріальне сортування словників ----------


def sort_rows_city_total_id(
    rows: Iterable[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """(city ↑, total ↓, id ↑) лише через itemgetter: стабільне сортування
    в кілька проходів — від найменш важливого ключа до найважливішого."""
    by_id = sorted(rows, key=itemgetter("id"))
    by_total = sorted(by_id, key=itemgetter("total"), reverse=True)
    return sorted(by_total, key=itemgetter("city"))
