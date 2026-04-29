"""Инструмент bash — запуск shell-команд с merged stdout/stderr."""
from __future__ import annotations

import os
import subprocess

from langchain_core.tools import tool
from pydantic import BaseModel, Field

DEFAULT_TIMEOUT_MS = 120_000
MAX_TIMEOUT_MS = 600_000
MAX_OUTPUT_LENGTH = 30_000


def _max_output_length() -> int:
    val = os.environ.get("BASH_MAX_OUTPUT_LENGTH")
    if val:
        try:
            return min(max(int(val), 1), 150_000)
        except ValueError:
            pass
    return MAX_OUTPUT_LENGTH


def _truncate(content: str) -> str:
    max_len = _max_output_length()
    if len(content) <= max_len:
        return content
    removed_kb = round((len(content) - max_len) / 1024)
    return f"{content[:max_len]}\n... [output truncated - {removed_kb}KB removed]"


class BashInput(BaseModel):
    command: str = Field(description="Shell-команда для выполнения")
    timeout: int | None = Field(
        default=None,
        description="Таймаут в миллисекундах (макс 600000, по умолчанию 120000)",
    )


@tool(args_schema=BashInput)
def bash(command: str, timeout: int | None = None) -> str:
    """Выполняет shell-команду и возвращает объединённый stdout+stderr.

    Лимит вывода — 30000 символов; при превышении вывод усекается.
    На non-zero exit code добавляет строку ``Exit code N``.
    """
    timeout_ms = min(timeout, MAX_TIMEOUT_MS) if timeout is not None else DEFAULT_TIMEOUT_MS
    timeout_s = timeout_ms / 1000

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=os.getcwd(),
        )
        output = result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr
        if result.returncode != 0:
            output += f"\nExit code {result.returncode}"
        return _truncate(output)
    except subprocess.TimeoutExpired as e:
        partial = ""
        if e.stdout:
            partial = e.stdout if isinstance(e.stdout, str) else e.stdout.decode(errors="replace")
        msg = f"Command timed out after {timeout_s:.0f}s"
        if partial:
            msg = f"{msg}\n{partial}"
        return _truncate(msg)
    except Exception as e:
        return f"Error: {e}"
