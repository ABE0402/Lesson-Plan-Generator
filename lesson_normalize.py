# -*- coding: utf-8 -*-
"""변환 산출물용 lesson JSON 정규화 (편집 워크스페이스와 무관)."""
from __future__ import annotations

import json
import re
from typing import Any

H5P_EMBED = (
    "https://crayonschool.co.kr/wp-admin/admin-ajax.php"
    "?action=h5p_embed&id={id}"
)


def slugify(title: str, fallback: str = "lesson") -> str:
    raw = (title or "").strip()
    s = re.sub(r"[^\w\-가-힣]+", "-", raw, flags=re.UNICODE)
    s = re.sub(r"-{2,}", "-", s).strip("-").lower()
    if not s:
        s = fallback
    return s[:60]


def normalize_h5p_src(value: str | int) -> str:
    s = str(value or "").strip()
    if not s:
        return ""
    if s.isdigit():
        return H5P_EMBED.format(id=s)
    m = re.search(r"[?&]id=(\d+)", s)
    if m and "h5p_embed" not in s:
        return H5P_EMBED.format(id=m.group(1))
    return s


def pages_from_stages(data: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in data.get("stages") or []:
        blocks: list[dict[str, Any]] = []
        if s.get("bubble"):
            blocks.append({"type": "text", "text": s["bubble"]})
        if s.get("image"):
            blocks.append({"type": "image", "src": s["image"]})
        for src in s.get("images") or []:
            blocks.append({"type": "image", "src": src})
        if s.get("videoUrl"):
            blocks.append(
                {
                    "type": "h5p",
                    "src": normalize_h5p_src(s["videoUrl"]),
                    "title": s.get("title") or "영상",
                }
            )
        for p in s.get("discussionPages") or []:
            if p.get("bubble"):
                blocks.append({"type": "text", "text": p["bubble"]})
            if p.get("image"):
                blocks.append({"type": "image", "src": p["image"]})
        for p in s.get("playPages") or []:
            if p.get("title"):
                blocks.append({"type": "heading", "text": p["title"]})
            if p.get("bubble"):
                blocks.append({"type": "text", "text": p["bubble"]})
            for t in p.get("steps") or []:
                blocks.append({"type": "text", "text": t})
            if p.get("image"):
                blocks.append({"type": "image", "src": p["image"]})
        for p in s.get("closingPages") or []:
            if p.get("bubble"):
                blocks.append({"type": "text", "text": p["bubble"]})
            quiz = p.get("quiz")
            if quiz:
                blocks.append(
                    {
                        "type": "quiz",
                        "question": quiz.get("question") or "질문",
                        "options": quiz.get("options") or [],
                    }
                )
        out.append(
            {
                "kicker": s.get("displayName") or s.get("label") or "",
                "title": s.get("title") or s.get("label") or "",
                "kind": s.get("type") or "topic",
                "blocks": blocks,
                "displayName": s.get("displayName") or s.get("label") or "",
            }
        )
    return out


def normalize_lesson(data: dict[str, Any]) -> dict[str, Any]:
    out = json.loads(json.dumps(data))
    out.pop("meta", None)
    for st in out.get("stages") or []:
        if isinstance(st, dict):
            st.pop("rawBlocks", None)

    pages = out.get("pages")
    if not pages:
        pages = pages_from_stages(out)
        out["pages"] = pages
    out.pop("stages", None)
    out["mode"] = "blocks"
    out.setdefault("title", "크레용 디지털 교안")
    out.setdefault("level", "")
    out.setdefault("sourceUrl", "")
    out.setdefault("goals", [])
    out.setdefault("materials", [])
    out.setdefault("characterImages", {"intro": "", "thinking": "", "guide": ""})
    out.setdefault("expression", "")

    for page in out.get("pages") or []:
        for block in page.get("blocks") or []:
            if block.get("type") == "h5p":
                block["src"] = normalize_h5p_src(block.get("src") or block.get("id") or "")
                block.setdefault("title", "인터랙티브")
    return out
