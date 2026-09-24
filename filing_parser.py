"""Extract source pages without using benchmark answers or gold evidence."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from lxml import etree, html
from pypdf import PdfReader

PARSER_VERSION = 3
MAX_BYTES = 50 * 1024 * 1024


@dataclass
class Page:
    index: int  # always one-based source order; not a benchmark PDF page index
    label: str | None
    text: str


@dataclass
class Filing:
    name: str
    digest: str
    kind: str
    pages: list[Page]
    elapsed: float
    warnings: list[str]

    def location(self, page: Page) -> str:
        if self.kind == "pdf":
            return f"PDF page {page.index}" + (f" · printed label {page.label}" if page.label and page.label != str(page.index) else "")
        return (f"Printed page {page.label} · " if page.label else "") + f"HTML segment {page.index}"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def printed_label(text: str) -> str | None:
    lines = [normalize(s) for s in text.splitlines() if normalize(s)]
    for line in reversed(lines[-5:]):
        if re.fullmatch(r"(?:Page\s+)?(?:[A-Z]-)?\d{1,3}", line, re.I):
            return re.sub(r"^Page\s+", "", line, flags=re.I)
    return None


def html_pages(raw: bytes) -> list[Page]:
    parser = html.HTMLParser(no_network=True, recover=True)
    root = html.fromstring(raw, parser=parser)
    for node in list(root.iter()):
        if not isinstance(node.tag, str):
            continue
        tag = node.tag.lower().split("}")[-1]
        style = re.sub(r"\s", "", node.get("style", "").lower())
        if tag in {"script", "style", "head", "noscript", "ix:header", "ix:hidden"} or "display:none" in style or "visibility:hidden" in style:
            if node.getparent() is not None:
                node.drop_tree()
    parts: list[str] = []
    pages: list[Page] = []

    def flush():
        text = "".join(parts).replace("\xa0", " ")
        text = "\n".join(re.sub(r"[ \t]+", " ", s).strip() for s in text.splitlines())
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text:
            pages.append(Page(len(pages) + 1, printed_label(text), text))
        parts.clear()

    # Event traversal preserves table cell boundaries, row boundaries and CSS page breaks.
    cell_depth = 0
    for event, node in etree.iterwalk(root, events=("start", "end")):
        if not isinstance(node.tag, str):
            continue
        tag = node.tag.lower().split("}")[-1]
        style = re.sub(r"\s", "", node.get("style", "").lower())
        if event == "start":
            if tag in {"td", "th"}:
                cell_depth += 1
            if re.search(r"(?:page-break-before:always|break-before:page)", style):
                flush()
            if tag in {"div", "p", "tr", "table", "h1", "h2", "h3", "li", "br", "hr"}:
                parts.append(" " if cell_depth else "\n")
            if node.text:
                parts.append(re.sub(r"\s+", " ", node.text))
        else:
            if tag in {"td", "th"}:
                cell_depth -= 1
                parts.append(" | ")
            elif tag in {"div", "p", "tr", "table", "h1", "h2", "h3", "li"}:
                parts.append(" " if cell_depth else "\n")
            if re.search(r"(?:page-break-after:always|break-after:page)", style):
                flush()
            if node.tail:
                parts.append(re.sub(r"\s+", " ", node.tail))
    flush()
    return pages


def ingest(raw: bytes, name: str, cache_dir: Path | None = None,
           progress: Callable[[float, str], None] | None = None) -> Filing:
    start = time.monotonic()
    tick = progress or (lambda *_: None)
    name = Path(name).name
    ext = Path(name).suffix.lower()
    if ext not in {".pdf", ".html", ".htm"}:
        raise ValueError("Please upload a PDF or an HTML filing.")
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("The filing must be non-empty and no larger than 50 MB.")
    digest = hashlib.sha256(raw).hexdigest()
    cached = cache_dir / f"v{PARSER_VERSION}-{digest}.json.gz" if cache_dir else None
    if cached and cached.exists():
        try:
            payload = json.loads(gzip.decompress(cached.read_bytes()))
            payload["pages"] = [Page(**p) for p in payload["pages"]]
            payload["name"] = name
            payload["elapsed"] = time.monotonic() - start
            tick(1, "Ready from local cache")
            return Filing(**payload)
        except (ValueError, KeyError, TypeError, OSError, EOFError):
            pass  # A damaged cache is safely rebuilt from the original.
    tick(0.05, "Reading filing and preserving page boundaries")
    warnings = []
    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(raw))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ValueError("This PDF is password-protected. Upload an unlocked copy.")
        if len(reader.pages) > 2000:
            raise ValueError("This PDF exceeds the 2,000-page processing limit.")
        labels = reader.page_labels
        pages = []
        for i, page in enumerate(reader.pages):
            if time.monotonic() - start > 570:
                raise TimeoutError("Processing approached 10 minutes. Try a smaller text-based filing.")
            txt = (page.extract_text(extraction_mode="layout") or "") if page.get("/Contents") is not None else ""
            pages.append(Page(i + 1, labels[i] if labels else printed_label(txt), txt.strip()))
            tick(0.1 + 0.8 * (i + 1) / len(reader.pages), f"Read page {i + 1} of {len(reader.pages)}")
        kind = "pdf"
        empty = sum(len(p.text.strip()) < 30 for p in pages)
        if empty:
            warnings.append(f"{empty} pages contain little or no extractable text. Scanned pages need OCR before upload.")
    else:
        pages = html_pages(raw)
        kind = "html"
        warnings.append("HTML segments follow source page breaks; they are not the reference PDF's page numbers. Printed page labels are shown when detected.")
    if sum(len(p.text) for p in pages) < 80:
        raise ValueError("No usable filing text was found. For scanned PDFs, run OCR first.")
    filing = Filing(name, digest, kind, pages, time.monotonic() - start, warnings)
    if cached:
        cached.parent.mkdir(parents=True, exist_ok=True)
        # Atomic replacement avoids incomplete cache reads in another session.
        import tempfile
        with tempfile.NamedTemporaryFile(dir=cached.parent, delete=False) as f:
            tmp = Path(f.name)
            f.write(gzip.compress(json.dumps(asdict(filing)).encode()))
        tmp.replace(cached)
    tick(1, f"Ready · {len(pages)} source pages/segments")
    return filing
