# Лабораторна робота №7. functools та operator

**Студентка:** Зьомків А. І., група ФЕП-21
**Варіант:** 6 — «Замовлення інтернет-магазину»

## Завдання варіанту
Замовлення: `id, customer, total, status, city`. Відібрати оплачені, застосувати
знижку/надбавку через `partial`, відсортувати за `total`.
`load_orders` через `singledispatch`; `OrderRank` порівнюється за `total` та `id`.

## Що реалізовано
- **`core.py`**
  - `pipeline(value, *funcs)` на `functools.reduce`;
  - нормалізація через `methodcaller("strip")`, `methodcaller("title")`, суми в `Decimal`;
  - `adjust_total` + готові політики через `partial`: `loyalty_discount`
    (−10 % від 2000 грн) і `remote_delivery` (+80 грн у віддалені міста);
  - кроки конвеєра `normalize_all = partial(map, normalize_order)`,
    `only_paid = partial(filter, attrgetter("is_paid"))`;
  - `top_paid_orders(source, top, policies)` — завантаження → нормалізація →
    оплачені → політики → сортування (total ↓, id ↑) → Top-N;
  - `revenue`, `totals_by_city` — агрегації через `reduce`;
  - `sort_rows_city_total_id` — сортування словників лише через `itemgetter`.
- **`loaders.py`** — `load_orders` на `@singledispatch`: JSON-рядок, шлях `str`,
  `Path` (`.json` / `.csv`), відкритий текстовий файл (JSON або CSV), `list`, `tuple`.
- **`models.py`** — `Order` (frozen dataclass), `OrderRank` і `Box` з
  `@total_ordering` (`__eq__` + `__lt__`, `NotImplemented` для чужих типів).
- **`main.py`** — демонстрація, **`tests/`** — pytest.

Оплаченими вважаються статуси `paid`, `shipped`, `delivered`.

## Запуск
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt

python main.py
pytest -v
mypy .
black --check .
ruff check .
```
Потрібен Python 3.12+.
