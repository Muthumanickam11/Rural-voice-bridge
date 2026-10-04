import os
import re
import glob
import logging
from typing import List, Dict, Any

from utils.logger import logger

FRONTMATTER_REGEX = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
HEADING_PREFIX_REGEX = re.compile(r"^#{1,6}\s*")


def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    match = FRONTMATTER_REGEX.match(content)
    if not match:
        return {}, content

    fm_text = match.group(1)
    body = content[match.end():]
    metadata: Dict[str, Any] = {}

    current_key: str | None = None
    for raw_line in fm_text.splitlines():
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue

        # Block-style YAML list item: "  - value"
        list_item = re.match(r"^\s*-\s+(.*)$", raw_line)
        if list_item and current_key:
            value = list_item.group(1).strip().strip('"').strip("'")
            if not isinstance(metadata.get(current_key), list):
                metadata[current_key] = []
            metadata[current_key].append(value)
            continue

        if ":" not in raw_line:
            continue

        key, val = raw_line.split(":", 1)
        key = key.strip()
        val = val.strip()
        if not key:
            continue

        if val.startswith("[") and val.endswith("]"):
            metadata[key] = [
                item.strip().strip('"').strip("'")
                for item in val[1:-1].split(",")
                if item.strip()
            ]
        elif val == "":
            # Possible start of a block list; keep the key so following "- " lines attach to it.
            metadata[key] = []
            current_key = key
            continue
        else:
            metadata[key] = val.strip('"').strip("'")
            current_key = None

    return metadata, body


def clean_heading(raw: str) -> str:
    """Strip only the leading '#' run and surrounding whitespace."""
    return HEADING_PREFIX_REGEX.sub("", raw).strip()


def chunk_markdown_file(file_path: str) -> List[Dict[str, Any]]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning(f"Skipping unreadable knowledge base file {file_path}: {exc}")
        return []

    meta, body = parse_frontmatter(content)
    file_id = meta.get("id", os.path.basename(file_path).replace(".md", ""))

    # Split body into sections by headings
    sections = re.split(r'\n(?=##\s+)', body)
    chunks: List[Dict[str, Any]] = []

    for i, sec in enumerate(sections):
        sec = sec.strip()
        if not sec:
            continue

        lines = sec.splitlines()
        has_heading = bool(lines) and lines[0].lstrip().startswith("#")
        if has_heading:
            heading = clean_heading(lines[0]) or file_id
            text = "\n".join(lines[1:]).strip()
        else:
            heading = meta.get("title", file_id)
            text = sec

        if not text:
            continue

        chunk = {
            "chunk_id": f"{file_id}_{i:02d}",
            "file_id": file_id,
            "title": meta.get("title", file_id),
            "section": heading,
            "category": meta.get("category", "general"),
            "state": meta.get("state", "TN"),
            "source_name": meta.get("source_name", "Official Portal"),
            "source_url": meta.get("source_url", ""),
            "last_verified": meta.get("last_verified", "2026-09-20"),
            "status": meta.get("status", "active"),
            "aliases": meta.get("aliases", []) if isinstance(meta.get("aliases", []), list) else [],
            # `content` deliberately holds the prose ONLY. The heading is kept in
            # `section` so retrieval can match on it without it being read back
            # to the user as if it were the answer.
            "content": text
        }
        chunks.append(chunk)

    return chunks


def build_all_chunks(kb_dir: str) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    md_files = sorted(glob.glob(os.path.join(kb_dir, "**", "*.md"), recursive=True))
    for f in md_files:
        try:
            chunks.extend(chunk_markdown_file(f))
        except Exception as exc:
            # A single malformed document must never prevent the backend from starting.
            logger.error(f"Failed to chunk {f}: {exc}")
    return chunks
