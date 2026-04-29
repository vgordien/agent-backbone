"""Поисковые инструменты: glob (по именам файлов), grep (по содержимому)."""
from __future__ import annotations

import glob as glob_module
import os
import re
import subprocess
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

# ---------- glob ----------

GLOB_MAX_RESULTS = 100


class GlobInput(BaseModel):
    pattern: str = Field(description="Glob-паттерн (например, '**/*.py')")
    path: str | None = Field(default=None, description="Директория поиска (по умолчанию — cwd)")


def _format_glob(files: list[str]) -> str:
    truncated = len(files) > GLOB_MAX_RESULTS
    files = files[:GLOB_MAX_RESULTS]
    if not files:
        return "No files matched the pattern."
    out = "\n".join(files)
    if truncated:
        out += "\n(Results are truncated. Consider using a more specific path or pattern.)"
    return out


@tool(args_schema=GlobInput)
def glob(pattern: str, path: str | None = None) -> str:
    """Ищет файлы по glob-паттерну. Возвращает относительные пути по mtime (старые первыми)."""
    search_dir = path or os.getcwd()

    try:
        result = subprocess.run(
            [
                "rg", "--files",
                "--glob", pattern,
                "--sort=modified",
                "--no-ignore",
                "--hidden",
            ],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=search_dir,
        )
        if result.returncode <= 1:
            files = [f for f in result.stdout.strip().split("\n") if f]
            return _format_glob(files)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    full_pattern = os.path.join(search_dir, pattern)
    matches = sorted(glob_module.glob(full_pattern, recursive=True))
    files = [m for m in matches if os.path.isfile(m)]
    files.sort(key=lambda f: os.path.getmtime(f))
    rel_files = [os.path.relpath(f, search_dir) for f in files]
    return _format_glob(rel_files)


# ---------- grep ----------

GREP_DEFAULT_HEAD_LIMIT = 250
VCS_DIRS = [".git", ".svn", ".hg", ".bzr", ".jj", ".sl"]


class GrepInput(BaseModel):
    pattern: str = Field(description="Regex-паттерн для поиска")
    path: str | None = Field(default=None, description="Файл или директория (по умолчанию — cwd)")
    glob: str | None = Field(default=None, description="Glob-фильтр файлов (например, '*.py')")
    type: str | None = Field(default=None, description="Тип файлов для ripgrep (например, 'py')")
    output_mode: str = Field(
        default="files_with_matches",
        description="files_with_matches | content | count",
    )
    case_insensitive: bool = Field(default=False)
    context: int | None = Field(default=None, description="Строки контекста (только для content)")
    head_limit: int = Field(default=GREP_DEFAULT_HEAD_LIMIT, description="0 = без ограничения")
    offset: int = Field(default=0)
    multiline: bool = Field(default=False)


def _sort_by_mtime_newest(files: list[str], search_dir: str) -> list[str]:
    timed = []
    for f in files:
        full = f if os.path.isabs(f) else os.path.join(search_dir, f)
        try:
            mtime = os.path.getmtime(full)
        except OSError:
            mtime = 0
        timed.append((f, mtime))
    timed.sort(key=lambda x: (-x[1], x[0]))
    return [f for f, _ in timed]


def _to_rel(p: str, base: str) -> str:
    return os.path.relpath(p, base) if os.path.isabs(p) else p


def _grep_rg(
    pattern: str,
    search_dir: str,
    glob_filter: str | None,
    file_type: str | None,
    output_mode: str,
    case_insensitive: bool,
    context: int | None,
    head_limit: int,
    offset: int,
    multiline: bool,
) -> str:
    cmd = ["rg", "--hidden", "--max-columns", "500"]
    for d in VCS_DIRS:
        cmd.extend(["--glob", f"!{d}"])

    if multiline:
        cmd.extend(["-U", "--multiline-dotall"])
    if case_insensitive:
        cmd.append("-i")

    if output_mode == "files_with_matches":
        cmd.append("-l")
    elif output_mode == "count":
        cmd.append("-c")
    else:
        cmd.append("-n")
        if context:
            cmd.extend(["-C", str(context)])

    if file_type:
        cmd.extend(["--type", file_type])
    if glob_filter:
        cmd.extend(["--glob", glob_filter])

    if pattern.startswith("-"):
        cmd.extend(["-e", pattern])
    else:
        cmd.append(pattern)
    cmd.append(search_dir)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    output = result.stdout.strip()
    if not output:
        return "No matches found."

    lines = output.split("\n")
    if output_mode == "files_with_matches":
        lines = _sort_by_mtime_newest(lines, search_dir)
        lines = [_to_rel(f, search_dir) for f in lines]
    elif output_mode == "count":
        converted = []
        for line in lines:
            if ":" in line:
                p, c = line.rsplit(":", 1)
                converted.append(f"{_to_rel(p, search_dir)}:{c}")
            else:
                converted.append(line)
        lines = converted

    lines = lines[offset:]
    truncated = False
    if head_limit > 0 and len(lines) > head_limit:
        lines = lines[:head_limit]
        truncated = True

    out = "\n".join(lines)
    if truncated or offset > 0:
        parts = []
        if truncated:
            parts.append(f"limit: {head_limit}")
        if offset > 0:
            parts.append(f"offset: {offset}")
        out += f"\n[{', '.join(parts)}]"
    return out


def _grep_python(
    pattern: str,
    search_dir: str,
    output_mode: str,
    case_insensitive: bool,
    head_limit: int,
    offset: int,
) -> str:
    flags = re.IGNORECASE if case_insensitive else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return f"Invalid regex: {e}"

    matches: list[str] = []
    for fp in Path(search_dir).rglob("*"):
        if not fp.is_file():
            continue
        if any(d in fp.parts for d in VCS_DIRS):
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
            if regex.search(text):
                rel = os.path.relpath(str(fp), search_dir)
                if output_mode == "count":
                    matches.append(f"{rel}:{len(regex.findall(text))}")
                elif output_mode == "content":
                    for i, line in enumerate(text.splitlines(), 1):
                        if regex.search(line):
                            matches.append(f"{rel}:{i}:{line}")
                else:
                    matches.append(rel)
        except Exception:
            continue
        if len(matches) >= (head_limit + offset) * 2:
            break

    matches = matches[offset:]
    truncated = False
    if head_limit > 0 and len(matches) > head_limit:
        matches = matches[:head_limit]
        truncated = True

    if not matches:
        return "No matches found."

    out = "\n".join(matches)
    if truncated or offset > 0:
        parts = []
        if truncated:
            parts.append(f"limit: {head_limit}")
        if offset > 0:
            parts.append(f"offset: {offset}")
        out += f"\n[{', '.join(parts)}]"
    return out


@tool(args_schema=GrepInput)
def grep(
    pattern: str,
    path: str | None = None,
    glob: str | None = None,
    type: str | None = None,
    output_mode: str = "files_with_matches",
    case_insensitive: bool = False,
    context: int | None = None,
    head_limit: int = GREP_DEFAULT_HEAD_LIMIT,
    offset: int = 0,
    multiline: bool = False,
) -> str:
    """Ищет regex-паттерн в файлах через ripgrep (с Python-фоллбеком, если ``rg`` не найден).

    Исключает .git/.svn/.hg/.bzr/.jj/.sl. По умолчанию режим ``files_with_matches``,
    отсортированный по mtime (новые первыми).
    """
    search_dir = path or os.getcwd()
    try:
        return _grep_rg(
            pattern, search_dir, glob, type, output_mode,
            case_insensitive, context, head_limit, offset, multiline,
        )
    except FileNotFoundError:
        return _grep_python(
            pattern, search_dir, output_mode, case_insensitive, head_limit, offset,
        )
