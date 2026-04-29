import json
from pathlib import Path

from src.tools.banking import calculate_loan_payment, fetch_policy_excerpt
from src.tools.system import (
    CODING_TOOLS,
    FILE_OPS_TOOLS,
    READONLY_TOOLS,
    bash,
    file_edit,
    file_read,
    file_write,
    glob,
    grep,
    notebook_edit,
    system_tools,
)


def test_loan_calc():
    res = calculate_loan_payment.invoke({"amount": 1_000_000, "months": 12})
    assert res["monthly_payment"] > 0
    assert res["currency"] == "RUB"

def test_policy_fallback():
    res = fetch_policy_excerpt.invoke({"topic": "несуществующее"})
    assert "не найдена" in res.lower()


def test_system_tools_registry():
    names = {t.name for t in system_tools}
    assert names == {
        "bash", "file_read", "file_write", "file_edit",
        "glob", "grep", "web_fetch", "notebook_edit",
    }
    assert {t.name for t in READONLY_TOOLS} == {"file_read", "glob", "grep", "web_fetch"}
    assert {t.name for t in FILE_OPS_TOOLS} == {
        "file_read", "file_write", "file_edit", "glob", "grep", "notebook_edit",
    }
    assert {t.name for t in CODING_TOOLS} == {
        "bash", "file_read", "file_write", "file_edit", "glob", "grep", "notebook_edit",
    }


def test_bash_echo():
    out = bash.invoke({"command": "echo hi"})
    assert out.strip() == "hi"


def test_bash_nonzero_exit():
    out = bash.invoke({"command": "false"})
    assert "Exit code 1" in out


def test_file_write_read_edit_roundtrip(tmp_path: Path):
    target = tmp_path / "sample.txt"
    create = file_write.invoke({"file_path": str(target), "content": "alpha\nbeta\n"})
    assert "created" in create.lower()

    contents = file_read.invoke({"file_path": str(target)})
    assert "1\talpha" in contents
    assert "2\tbeta" in contents

    edited = file_edit.invoke(
        {"file_path": str(target), "old_string": "beta", "new_string": "gamma"}
    )
    assert "updated" in edited.lower()
    assert target.read_text() == "alpha\ngamma\n"


def test_file_edit_rejects_identical():
    out = file_edit.invoke(
        {"file_path": "/tmp/whatever.txt", "old_string": "x", "new_string": "x"}
    )
    assert "No changes to make" in out


def test_glob_finds_files(tmp_path: Path):
    (tmp_path / "a.py").write_text("print(1)")
    (tmp_path / "b.txt").write_text("hi")
    out = glob.invoke({"pattern": "*.py", "path": str(tmp_path)})
    assert "a.py" in out
    assert "b.txt" not in out


def test_grep_finds_pattern(tmp_path: Path):
    (tmp_path / "code.py").write_text("def needle():\n    return 1\n")
    out = grep.invoke({"pattern": "needle", "path": str(tmp_path)})
    assert "code.py" in out


def _make_notebook(path: Path, cells: list[dict]) -> None:
    nb = {"cells": cells, "metadata": {}, "nbformat": 4, "nbformat_minor": 5}
    path.write_text(json.dumps(nb), encoding="utf-8")


def test_notebook_edit_replace(tmp_path: Path):
    nb_path = tmp_path / "nb.ipynb"
    _make_notebook(nb_path, [
        {"cell_type": "code", "source": "old", "metadata": {}, "id": "c1",
         "outputs": [{"text": "stale"}], "execution_count": 7},
    ])

    out = notebook_edit.invoke({
        "notebook_path": str(nb_path),
        "cell_id": "c1",
        "new_source": "print('hi')",
    })
    assert "Updated cell c1" in out
    nb = json.loads(nb_path.read_text())
    assert nb["cells"][0]["source"] == "print('hi')"
    assert nb["cells"][0]["outputs"] == []
    assert nb["cells"][0]["execution_count"] is None


def test_notebook_edit_insert_and_delete(tmp_path: Path):
    nb_path = tmp_path / "nb.ipynb"
    _make_notebook(nb_path, [
        {"cell_type": "code", "source": "first", "metadata": {}, "id": "c1"},
    ])

    out = notebook_edit.invoke({
        "notebook_path": str(nb_path),
        "cell_id": "c1",
        "new_source": "# title",
        "cell_type": "markdown",
        "edit_mode": "insert",
    })
    assert "Inserted cell" in out
    nb = json.loads(nb_path.read_text())
    assert len(nb["cells"]) == 2
    assert nb["cells"][1]["cell_type"] == "markdown"

    out = notebook_edit.invoke({
        "notebook_path": str(nb_path),
        "cell_id": "c1",
        "new_source": "",
        "edit_mode": "delete",
    })
    assert "Deleted cell c1" in out
    nb = json.loads(nb_path.read_text())
    assert len(nb["cells"]) == 1
    assert nb["cells"][0]["cell_type"] == "markdown"


def test_notebook_edit_cell_n_fallback(tmp_path: Path):
    nb_path = tmp_path / "nb.ipynb"
    _make_notebook(nb_path, [
        {"cell_type": "code", "source": "a", "metadata": {}, "id": "alpha"},
        {"cell_type": "code", "source": "b", "metadata": {}, "id": "beta"},
    ])

    out = notebook_edit.invoke({
        "notebook_path": str(nb_path),
        "cell_id": "cell-1",
        "new_source": "edited",
    })
    assert "Updated" in out
    nb = json.loads(nb_path.read_text())
    assert nb["cells"][1]["source"] == "edited"