"""Поліморфний load_orders на @singledispatch: JSON/CSV з різних джерел."""

import csv
import io
import json
from collections.abc import Mapping
from functools import singledispatch
from pathlib import Path
from typing import Any

type RawOrder = dict[str, Any]


def _validate(rows: object) -> list[RawOrder]:
    if not isinstance(rows, list) or not all(isinstance(r, Mapping) for r in rows):
        raise ValueError("очікувався список словників із замовленнями")
    return [dict(r) for r in rows]  # копії: вхідні словники не змінюємо


def _parse_text(text: str, *, is_csv: bool) -> list[RawOrder]:
    if is_csv:
        return _validate(list(csv.DictReader(io.StringIO(text))))
    return _validate(json.loads(text))


def _looks_like_json(text: str) -> bool:
    return text.lstrip().startswith(("[", "{"))


@singledispatch
def load_orders(source: object) -> list[RawOrder]:
    """Єдина точка входу: JSON-рядок, шлях str, Path, відкритий файл, list."""
    raise TypeError(f"load_orders: непідтримуваний тип {type(source).__name__}")


@load_orders.register
def _(source: str) -> list[RawOrder]:
    if _looks_like_json(source):
        return _parse_text(source, is_csv=False)  # сам рядок — це JSON
    return load_orders(Path(source))  # інакше — шлях до файлу


@load_orders.register
def _(source: Path) -> list[RawOrder]:
    text = source.read_text(encoding="utf-8")
    return _parse_text(text, is_csv=source.suffix.lower() == ".csv")


@load_orders.register
def _(source: io.TextIOBase) -> list[RawOrder]:
    text = source.read()
    return _parse_text(text, is_csv=not _looks_like_json(text))


@load_orders.register
def _(source: list) -> list[RawOrder]:  # type: ignore[type-arg]
    return _validate(source)


@load_orders.register
def _(source: tuple) -> list[RawOrder]:  # type: ignore[type-arg]
    return _validate(list(source))
