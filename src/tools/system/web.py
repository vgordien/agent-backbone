"""Веб-инструмент: web_fetch — скачать URL и вернуть текст (HTML → markdown/plain)."""
from __future__ import annotations

import urllib.error
import urllib.request
from html.parser import HTMLParser

from langchain_core.tools import tool
from pydantic import BaseModel, Field

MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
MAX_RESULT_LENGTH = 100_000
MAX_URL_LENGTH = 2000


class _TextExtractor(HTMLParser):
    """Простой extractor HTML → текст без внешних зависимостей."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False
        self._skip_tags = {"script", "style", "nav", "footer", "header"}

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip = True
        if tag in ("p", "br", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"):
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts).strip()


def _html_to_text(html: str) -> str:
    try:
        import markdownify
        return markdownify.markdownify(html, strip=["script", "style", "nav", "footer"])
    except ImportError:
        pass
    try:
        import html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        return h.handle(html)
    except ImportError:
        pass
    extractor = _TextExtractor()
    extractor.feed(html)
    return extractor.get_text()


class WebFetchInput(BaseModel):
    url: str = Field(description="URL для загрузки")
    prompt: str = Field(description="Подсказка для дальнейшей обработки контента")


@tool(args_schema=WebFetchInput)
def web_fetch(url: str, prompt: str) -> str:
    """Скачивает URL (HTTP GET) и возвращает текст. HTML конвертируется в markdown/plain.

    Лимит ответа — 10 МБ, итоговый текст усекается до 100k символов.
    Параметр ``prompt`` сейчас не применяется на стороне инструмента — он передаётся LLM
    вместе с контентом, чтобы агент знал, что именно извлекать.
    """
    if len(url) > MAX_URL_LENGTH:
        return f"Error: URL too long (max {MAX_URL_LENGTH} chars)."
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "agent-backbone/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content_type = resp.headers.get("Content-Type", "")
            data = resp.read(MAX_CONTENT_LENGTH)
            text = data.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return f"Error: HTTP {e.code} {e.reason}"
    except urllib.error.URLError as e:
        return f"Error: {e.reason}"
    except Exception as e:
        return f"Error fetching URL: {e}"

    if "html" in content_type.lower():
        text = _html_to_text(text)
    if len(text) > MAX_RESULT_LENGTH:
        text = text[:MAX_RESULT_LENGTH] + "\n... [truncated]"
    return f"[fetched {url}]\n\n{text}\n\n---\nInstruction for assistant: {prompt}"
