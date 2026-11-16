"""Предметні класи: Order, OrderRank (@total_ordering) і Box."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from functools import total_ordering

PAID_STATUSES = frozenset({"paid", "shipped", "delivered"})


@dataclass(frozen=True, slots=True)
class Order:
    id: int
    customer: str
    total: Decimal
    status: str
    city: str

    @property
    def is_paid(self) -> bool:
        return self.status in PAID_STATUSES


@total_ordering
class OrderRank:
    """Ранг замовлення: більша сума — вищий ранг; за рівної суми вище те,
    у кого менший id (раніше оформлене). Тому sorted(..., reverse=True)
    дає порядок: total ↓, id ↑.

    Реалізовано лише __eq__ і __lt__; <=, >, >= додає @total_ordering.
    """

    __slots__ = ("total", "id")

    def __init__(self, total: Decimal, id: int) -> None:
        self.total = total
        self.id = id

    @classmethod
    def of(cls, order: Order) -> OrderRank:
        return cls(order.total, order.id)

    def _key(self) -> tuple[Decimal, int]:
        return (self.total, -self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OrderRank):
            return NotImplemented
        return self._key() == other._key()

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, OrderRank):
            return NotImplemented
        return self._key() < other._key()

    def __hash__(self) -> int:
        return hash(self._key())

    def __repr__(self) -> str:
        return f"OrderRank(total={self.total}, id={self.id})"


@total_ordering
@dataclass(frozen=True, slots=True, eq=False)
class Box:
    """Порядок: об'єм, потім площа фронтальної грані (w*h), потім w."""

    w: float
    h: float
    d: float

    def _key(self) -> tuple[float, float, float]:
        return (self.w * self.h * self.d, self.w * self.h, self.w)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Box):
            return NotImplemented
        return self._key() == other._key()

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Box):
            return NotImplemented
        return self._key() < other._key()

    def __hash__(self) -> int:
        return hash(self._key())
