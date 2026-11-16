import json
from pathlib import Path
from typing import Any

import pytest

ROWS: list[dict[str, Any]] = [
    {"id": 1, "customer": " анна ", "total": 2500, "status": "PAID", "city": "львів"},
    {"id": 2, "customer": "Борис", "total": 900, "status": "new", "city": "Київ"},
    {"id": 3, "customer": "віра", "total": 2500, "status": "delivered", "city": "Київ"},
    {
        "id": 4,
        "customer": "Гліб",
        "total": 1500,
        "status": "shipped",
        "city": "Ужгород",
    },
    {
        "id": 5,
        "customer": "дана",
        "total": 3000,
        "status": "cancelled",
        "city": "Одеса",
    },
]


@pytest.fixture
def rows() -> list[dict[str, Any]]:
    return [dict(r) for r in ROWS]


@pytest.fixture
def json_path(tmp_path: Path) -> Path:
    p = tmp_path / "orders.json"
    p.write_text(json.dumps(ROWS, ensure_ascii=False), encoding="utf-8")
    return p


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    header = "id,customer,total,status,city"
    lines = [header] + [
        f"{r['id']},{r['customer']},{r['total']},{r['status']},{r['city']}"
        for r in ROWS
    ]
    p = tmp_path / "orders.csv"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p
