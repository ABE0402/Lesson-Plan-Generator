# -*- coding: utf-8 -*-
"""편집 워크스페이스 저장·파싱 (lessons/workspace)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from offline_images import extract_lesson_from_html, lesson_slug

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT / "lessons" / "workspace"


def ensure_workspace_root() -> None:
    WORKSPACE.mkdir(parents=True, exist_ok=True)


def slugify(title: str) -> str:
    return lesson_slug(title)


def unique_slug(title: str) -> str:
    base = slugify(title) or "lesson"
    if not (WORKSPACE / base).exists():
        return base
    n = 2
    while (WORKSPACE / f"{base}-{n}").exists():
        n += 1
    return f"{base}-{n}"


def lesson_dir(slug: str) -> Path:
    return WORKSPACE / slug


def lesson_json_path(slug: str) -> Path:
    return lesson_dir(slug) / "lesson.json"


def preview_path(slug: str) -> Path:
    return lesson_dir(slug) / "preview.html"


def assets_dir(slug: str) -> Path:
    return lesson_dir(slug) / "assets"


def safe_asset_name(filename: str) -> str:
    name = Path(filename or "asset").name
    name = re.sub(r"[^\w.\-가-힣]+", "_", name, flags=re.UNICODE).strip("._")
    return name or "asset.bin"


def normalize_lesson(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("lesson 데이터가 객체가 아닙니다.")
    out = json.loads(json.dumps(data))
    out.setdefault("title", "수업 교안")
    out.setdefault("level", "크레용스쿨")
    out.setdefault("sourceUrl", "")
    if not out.get("pages") and out.get("stages"):
        out["mode"] = out.get("mode") or "stages"
    elif out.get("pages"):
        out["mode"] = out.get("mode") or "blocks"
    return out


def parse_lesson_payload(raw: str, filename: str = "") -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        raise ValueError("내용이 비어 있습니다.")
    name = (filename or "").lower()
    if name.endswith(".json") or text.startswith("{"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            if name.endswith(".json"):
                raise ValueError(f"JSON 파싱 실패: {exc}") from exc
            data = None
        if isinstance(data, dict):
            return normalize_lesson(data)
    extracted = extract_lesson_from_html(text)
    if extracted:
        return normalize_lesson(extracted)
    raise ValueError("HTML/JSON에서 lessonData를 찾지 못했습니다.")


def save_lesson(
    slug: str,
    data: dict[str, Any],
    build_html: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    ensure_workspace_root()
    cleaned = normalize_lesson(data)
    folder = lesson_dir(slug)
    folder.mkdir(parents=True, exist_ok=True)
    assets_dir(slug).mkdir(parents=True, exist_ok=True)
    lesson_json_path(slug).write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    html = build_html(cleaned)
    preview_path(slug).write_text(html, encoding="utf-8")
    return cleaned


def load_lesson(slug: str) -> dict[str, Any] | None:
    path = lesson_json_path(slug)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return normalize_lesson(data) if isinstance(data, dict) else None


def list_lessons() -> list[dict[str, Any]]:
    ensure_workspace_root()
    items: list[dict[str, Any]] = []
    for path in sorted(WORKSPACE.iterdir()):
        if not path.is_dir():
            continue
        data = load_lesson(path.name)
        if not data:
            continue
        items.append(
            {
                "slug": path.name,
                "title": data.get("title") or path.name,
                "level": data.get("level") or "",
                "pageCount": len(data.get("pages") or []),
                "previewUrl": f"/w/{path.name}/preview",
            }
        )
    return items
