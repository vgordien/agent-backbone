"""Инструмент notebook_edit — правка ячеек Jupyter (.ipynb)."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field


def _parse_cell_index(cell_id: str) -> int | None:
    """Распарсить fallback-формат 'cell-N' в индекс."""
    if cell_id.startswith("cell-"):
        try:
            return int(cell_id[5:])
        except ValueError:
            return None
    return None


def _find_cell(cells: list[dict], cell_id: str) -> int | None:
    for i, cell in enumerate(cells):
        if cell.get("id") == cell_id:
            return i
    idx = _parse_cell_index(cell_id)
    if idx is not None and 0 <= idx < len(cells):
        return idx
    return None


class NotebookEditInput(BaseModel):
    notebook_path: str = Field(description="Абсолютный путь к .ipynb")
    new_source: str = Field(description="Новый source ячейки")
    cell_id: str | None = Field(
        default=None,
        description=(
            "ID ячейки. Для insert: новая ячейка вставляется после указанной "
            "(если None — в начало). Поддерживается fallback-формат 'cell-N'."
        ),
    )
    cell_type: Literal["code", "markdown"] | None = Field(
        default=None,
        description="Тип ячейки (обязателен для insert, по умолчанию 'code')",
    )
    edit_mode: Literal["replace", "insert", "delete"] = Field(
        default="replace",
        description="Режим: replace (по умолчанию), insert, delete",
    )


@tool(args_schema=NotebookEditInput)
def notebook_edit(
    notebook_path: str,
    new_source: str,
    cell_id: str | None = None,
    cell_type: Literal["code", "markdown"] | None = None,
    edit_mode: Literal["replace", "insert", "delete"] = "replace",
) -> str:
    """Редактирует ячейку Jupyter-ноутбука. Режимы: replace / insert / delete.

    Для replace выполняется сброс ``execution_count`` и ``outputs`` (только для code-ячеек).
    Для insert новая ячейка вставляется после ``cell_id`` (или в начало, если ``cell_id`` не задан).
    Поиск ячейки идёт сначала по точному ID, затем по fallback-формату ``cell-N``.
    """
    path = Path(notebook_path)
    if not path.exists():
        return f"Error: Notebook not found: {notebook_path}"

    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return f"Error reading notebook: {e}"

    cells = nb.get("cells", [])

    if edit_mode == "insert":
        ct = cell_type or "code"
        new_id = str(uuid.uuid4())[:8]
        new_cell: dict = {
            "cell_type": ct,
            "source": new_source,
            "metadata": {},
            "id": new_id,
        }
        if ct == "code":
            new_cell["outputs"] = []
            new_cell["execution_count"] = None

        if cell_id:
            idx = _find_cell(cells, cell_id)
            if idx is None:
                return f"Cell with ID not found: {cell_id}"
            cells.insert(idx + 1, new_cell)
        else:
            cells.insert(0, new_cell)

        nb["cells"] = cells
        path.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
        return f"Inserted cell {new_id} with {new_source}"

    if edit_mode == "delete":
        if not cell_id:
            return "Error: cell_id is required for delete."
        idx = _find_cell(cells, cell_id)
        if idx is None:
            return f"Cell with ID not found: {cell_id}"
        cells.pop(idx)
        nb["cells"] = cells
        path.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
        return f"Deleted cell {cell_id}"

    # replace
    if not cell_id:
        return "Error: cell_id is required for replace."
    idx = _find_cell(cells, cell_id)
    if idx is None:
        return f"Cell with ID not found: {cell_id}"

    target = cells[idx]
    target["source"] = new_source
    if cell_type:
        target["cell_type"] = cell_type
    if target.get("cell_type") == "code":
        target["execution_count"] = None
        target["outputs"] = []

    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    return f"Updated cell {cell_id} with {new_source}"
