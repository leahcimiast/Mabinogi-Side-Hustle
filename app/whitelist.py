"""Read-only reference loading. Exact names and source order are preserved."""
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class Quest:
    quest: str
    material: str
    quantity: int


def validate(rows):
    result, seen = [], set()
    for index, row in enumerate(rows, 2):
        if len(row) != 3:
            raise ValueError(f"Row {index}: expected three columns")
        name, material, count = row
        if not isinstance(name, str) or not name or name != name.strip():
            raise ValueError(f"Row {index}: invalid quest name")
        if not isinstance(material, str) or not material or material != material.strip():
            raise ValueError(f"Row {index}: invalid material name")
        if name in seen:
            raise ValueError(f"Row {index}: duplicate quest: {name}")
        if isinstance(count, bool) or not isinstance(count, (int, float)) or count <= 0 or count != int(count):
            raise ValueError(f"Row {index}: quantity must be a positive integer")
        seen.add(name)
        result.append(Quest(name, material, int(count)))
    if not result:
        raise ValueError("Whitelist is empty")
    return result


def load(path):
    path = Path(path)
    if path.suffix.lower() == '.json':
        data = json.loads(path.read_text(encoding='utf-8'))
        return validate([(x['quest'], x['material'], x['quantity']) for x in data])
    from openpyxl import load_workbook
    book = load_workbook(path, read_only=True, data_only=False, keep_links=False)
    try:
        if len(book.worksheets) != 1:
            raise ValueError("Expected one reference worksheet")
        rows = iter(book.worksheets[0].values)
        if tuple(next(rows, ())) != ('Quest Name', 'Material', 'Qty Per Completetion'):
            raise ValueError("Expected headers: Quest Name / Material / Qty Per Completetion")
        return validate([row for row in rows if any(v is not None for v in row)])
    finally:
        book.close()
