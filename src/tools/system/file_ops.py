"""Файловые инструменты: file_read, file_write, file_edit."""
from __future__ import annotations

import os
import re
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

# ---------- file_read ----------

MAX_LINES_TO_READ = 2000
MAX_OUTPUT_SIZE = 256 * 1024  # 256 KB


class FileReadInput(BaseModel):
    file_path: str = Field(description="Абсолютный путь к файлу")
    offset: int = Field(default=1, ge=0, description="Номер строки начала (1-based)")
    limit: int = Field(default=MAX_LINES_TO_READ, gt=0, description="Сколько строк читать")


@tool(args_schema=FileReadInput)
def file_read(file_path: str, offset: int = 1, limit: int = MAX_LINES_TO_READ) -> str:
    """Читает файл с нумерацией строк (формат ``cat -n``: ``номер\\tстрока``).

    Бинарные файлы и файлы в неподдерживаемых кодировках возвращают сообщение об ошибке,
    а не байты.
    """
    path = Path(file_path)
    if not path.exists():
        return f"File does not exist. Note: your current working directory is {os.getcwd()}."
    if not path.is_file():
        return f"Error: Not a file: {file_path}"

    try:
        data = path.read_bytes()
    except Exception as e:
        return f"Error reading file: {e}"

    has_utf16_bom = data[:2] == b"\xff\xfe"
    if (
        b"\x00" in data[:8192]
        and not has_utf16_bom
        and not file_path.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp"))
    ):
        return "This tool cannot read binary files."

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = data.decode("utf-16-le")
        except UnicodeDecodeError:
            return "Error: Unable to decode file (not UTF-8 or UTF-16LE)."

    lines = text.splitlines(keepends=True)
    if not lines:
        return "<system-reminder>Warning: the file exists but the contents are empty.</system-reminder>"

    start_idx = max(offset - 1, 0) if offset >= 1 else 0
    selected = lines[start_idx : start_idx + limit]
    return "\n".join(f"{start_idx + i + 1}\t{line.rstrip()}" for i, line in enumerate(selected))


# ---------- file_write ----------


class FileWriteInput(BaseModel):
    file_path: str = Field(description="Абсолютный путь к файлу")
    content: str = Field(description="Содержимое файла")


@tool(args_schema=FileWriteInput)
def file_write(file_path: str, content: str) -> str:
    """Создаёт или перезаписывает файл. Родительские директории создаются автоматически."""
    path = Path(file_path)
    existed = path.exists()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except Exception as e:
        return f"Error writing file: {e}"
    if existed:
        return f"The file {file_path} has been updated successfully."
    return f"File created successfully at: {file_path}"


# ---------- file_edit ----------

MAX_EDIT_FILE_SIZE = 1024 * 1024 * 1024  # 1 GiB

LEFT_SINGLE_CURLY = "‘"
RIGHT_SINGLE_CURLY = "’"
LEFT_DOUBLE_CURLY = "“"
RIGHT_DOUBLE_CURLY = "”"

_QUOTE_MAP = str.maketrans(
    {
        LEFT_SINGLE_CURLY: "'",
        RIGHT_SINGLE_CURLY: "'",
        LEFT_DOUBLE_CURLY: '"',
        RIGHT_DOUBLE_CURLY: '"',
    }
)


def _normalize_quotes(s: str) -> str:
    return s.translate(_QUOTE_MAP)


def _find_actual(content: str, search: str) -> str | None:
    if search in content:
        return search
    norm_search = _normalize_quotes(search)
    norm_content = _normalize_quotes(content)
    idx = norm_content.find(norm_search)
    if idx != -1:
        return content[idx : idx + len(search)]
    return None


def _curly_double(s: str) -> str:
    out, in_open = [], True
    for ch in s:
        if ch == '"':
            out.append(LEFT_DOUBLE_CURLY if in_open else RIGHT_DOUBLE_CURLY)
            in_open = not in_open
        else:
            out.append(ch)
    return "".join(out)


def _curly_single(s: str) -> str:
    out, in_open = [], True
    for ch in s:
        if ch == "'":
            out.append(LEFT_SINGLE_CURLY if in_open else RIGHT_SINGLE_CURLY)
            in_open = not in_open
        else:
            out.append(ch)
    return "".join(out)


def _preserve_quote_style(old: str, actual_old: str, new: str) -> str:
    if old == actual_old:
        return new
    has_double = LEFT_DOUBLE_CURLY in actual_old or RIGHT_DOUBLE_CURLY in actual_old
    has_single = LEFT_SINGLE_CURLY in actual_old or RIGHT_SINGLE_CURLY in actual_old
    if not has_double and not has_single:
        return new
    out = new
    if has_double:
        out = _curly_double(out)
    if has_single:
        out = _curly_single(out)
    return out


def _strip_trailing_ws(s: str) -> str:
    parts = re.split(r"(\r\n|\n|\r)", s)
    return "".join(p.rstrip() if i % 2 == 0 else p for i, p in enumerate(parts))


def _format_size(n: int) -> str:
    if n < 1024:
        return f"{n} bytes"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    if n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    return f"{n / (1024 * 1024 * 1024):.1f} GB"


class FileEditInput(BaseModel):
    file_path: str = Field(description="Абсолютный путь к файлу")
    old_string: str = Field(description="Точная строка для замены")
    new_string: str = Field(description="Новая строка (должна отличаться от old_string)")
    replace_all: bool = Field(default=False, description="Заменить все вхождения")


@tool(args_schema=FileEditInput)
def file_edit(
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> str:
    """Заменяет точное вхождение строки в файле.

    Если ``old_string`` встречается несколько раз и ``replace_all=False`` — ошибка.
    Поддерживает нормализацию curly/straight кавычек при поиске.
    Для ``.ipynb`` файлов используйте отдельный notebook-инструмент.
    """
    if old_string == new_string:
        return "No changes to make: old_string and new_string are exactly the same."
    if file_path.endswith(".ipynb"):
        return "File is a Jupyter Notebook. Use the notebook_edit tool to edit this file."

    path = Path(file_path)
    if not path.exists():
        if old_string == "":
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                is_md = re.search(r"\.(md|mdx)$", file_path, re.IGNORECASE)
                content = new_string if is_md else _strip_trailing_ws(new_string)
                path.write_text(content, encoding="utf-8")
                return f"File created successfully at: {file_path}"
            except Exception as e:
                return f"Error creating file: {e}"
        return f"File does not exist. Note: your current working directory is {os.getcwd()}."
    if not path.is_file():
        return f"Error: Not a file: {file_path}"

    try:
        size = path.stat().st_size
    except Exception as e:
        return f"Error reading file: {e}"
    if size > MAX_EDIT_FILE_SIZE:
        return (
            f"File is too large to edit ({_format_size(size)}). "
            f"Maximum editable file size is {_format_size(MAX_EDIT_FILE_SIZE)}."
        )

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = path.read_bytes().decode("utf-16-le")
        except Exception:
            return "Error: Unable to decode file."
    except Exception as e:
        return f"Error reading file: {e}"

    text = text.replace("\r\n", "\n")

    if old_string == "" and text.strip() != "":
        return "Cannot create new file - file already exists."

    actual_old = _find_actual(text, old_string)
    if actual_old is None:
        return f"String to replace not found in file.\nString: {old_string}"

    count = text.count(actual_old)
    if count > 1 and not replace_all:
        return (
            f"Found {count} matches of the string to replace, but replace_all is false. "
            "To replace all occurrences, set replace_all to true. "
            "To replace only one occurrence, please provide more context to uniquely identify the instance.\n"
            f"String: {old_string}"
        )

    actual_new = _preserve_quote_style(old_string, actual_old, new_string)
    if not re.search(r"\.(md|mdx)$", file_path, re.IGNORECASE):
        actual_new = _strip_trailing_ws(actual_new)

    new_text = text.replace(actual_old, actual_new) if replace_all else text.replace(actual_old, actual_new, 1)

    try:
        path.write_text(new_text, encoding="utf-8")
    except Exception as e:
        return f"Error writing file: {e}"

    if replace_all:
        return f"The file {file_path} has been updated. All occurrences were successfully replaced."
    return f"The file {file_path} has been updated successfully."
