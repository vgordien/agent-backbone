"""Системные инструменты в стиле Claude Code, обёрнутые как LangChain ``@tool``.

Использование::

    from src.tools.system import system_tools
    llm.bind_tools(system_tools)

Подмножества:
- ``READONLY_TOOLS`` — только чтение (file_read, glob, grep, web_fetch).
- ``FILE_OPS_TOOLS`` — все файловые операции без shell-доступа.
- ``CODING_TOOLS`` — bash + файлы + поиск.
"""
from src.tools.system.file_ops import file_edit, file_read, file_write
from src.tools.system.notebook import notebook_edit
from src.tools.system.search import glob, grep
from src.tools.system.shell import bash
from src.tools.system.web import web_fetch

system_tools = [bash, file_read, file_write, file_edit, glob, grep, web_fetch, notebook_edit]

READONLY_TOOLS = [file_read, glob, grep, web_fetch]
FILE_OPS_TOOLS = [file_read, file_write, file_edit, glob, grep, notebook_edit]
CODING_TOOLS = [bash, file_read, file_write, file_edit, glob, grep, notebook_edit]

__all__ = [
    "bash",
    "file_read",
    "file_write",
    "file_edit",
    "glob",
    "grep",
    "web_fetch",
    "notebook_edit",
    "system_tools",
    "READONLY_TOOLS",
    "FILE_OPS_TOOLS",
    "CODING_TOOLS",
]
