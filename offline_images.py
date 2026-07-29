# -*- coding: utf-8 -*-
"""lessonData / preview.html 이미지를 받아 GitHub Raw 절대 URL로 치환."""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import requests

ROOT = Path(__file__).resolve().parent

GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "ABE0402")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "Lesson-Plan-Generator")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")

IMG_URL_RE = re.compile(
    r"https?://[^\s\"'<>]+?\.(?:png|jpe?g|gif|webp|svg|bmp)(?:\?[^\s\"'<>]*)?",
    re.I,
)
LESSON_ASSIGN_RE = re.compile(r"(?:const|let|var)\s+lessonData\s*=\s*", re.I)

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "LessonPlanOfflineImages/1.0",
        "Accept": "image/*,*/*",
    }
)


def github_raw_url(repo_relative: str) -> str:
    rel = repo_relative.replace("\\", "/").lstrip("/")
    return (
        f"https://raw.githubusercontent.com/"
        f"{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{rel}"
    )


def lesson_slug(title: str, *, max_len: int = 60) -> str:
    """차시 제목 → 폴더/파일용 안전한 이름 (예: 3차시-고-구-그를-배워요)."""
    s = re.sub(r"[^\w\-가-힣]+", "-", (title or "lesson").strip(), flags=re.UNICODE)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return (s[:max_len] or "lesson")


def preview_html_name(title: str) -> str:
    """다운로드/GitHub에 보이는 HTML 파일명 (preview.html 대신 제목 사용)."""
    return f"{lesson_slug(title)}.html"


def extract_lesson_from_html(html: str) -> dict[str, Any] | None:
    m = LESSON_ASSIGN_RE.search(html)
    if not m:
        return None
    start = m.end()
    while start < len(html) and html[start].isspace():
        start += 1
    if start >= len(html) or html[start] != "{":
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(html[start:])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def collect_image_urls(lesson: dict[str, Any]) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def add(url: str) -> None:
        u = (url or "").strip()
        if not u or not u.startswith(("http://", "https://")):
            return
        # 이미 GitHub raw면 스킵(재처리 시)
        if "raw.githubusercontent.com" in u and GITHUB_REPO in u:
            return
        if u not in seen:
            seen.add(u)
            found.append(u)

    for page in lesson.get("pages") or []:
        for block in page.get("blocks") or []:
            t = block.get("type")
            if t == "image" and block.get("src"):
                add(block["src"])
            elif t == "gallery":
                for src in block.get("srcs") or []:
                    add(src)
            elif t == "banner" and block.get("src"):
                add(block["src"])

    # stages 경로(있을 때만)
    for st in lesson.get("stages") or []:
        if st.get("image"):
            add(st["image"])
        for src in st.get("images") or []:
            add(src)
        for p in st.get("discussionPages") or []:
            if p.get("image"):
                add(p["image"])
        for p in st.get("playPages") or []:
            if p.get("image"):
                add(p["image"])
        for p in st.get("closingPages") or []:
            if p.get("image"):
                add(p["image"])
        chars = lesson.get("characterImages") or {}
        for key in ("intro", "thinking", "guide"):
            if chars.get(key):
                add(chars[key])

    return found


def collect_urls_from_html_text(html: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for m in IMG_URL_RE.finditer(html):
        u = m.group(0).rstrip(".,);]")
        if "raw.githubusercontent.com" in u and GITHUB_REPO in u:
            continue
        if u not in seen:
            seen.add(u)
            found.append(u)
    return found


def _safe_name(url: str, index: int, content_type: str | None) -> str:
    path = unquote(urlparse(url).path)
    base = Path(path).name or f"image_{index}"
    base = re.sub(r"[^\w.\-가-힣]+", "_", base, flags=re.UNICODE)
    if len(base) > 80:
        stem = Path(base).stem[:60]
        suf = Path(base).suffix[:10]
        base = stem + suf
    if "." not in base:
        ext = mimetypes.guess_extension((content_type or "").split(";")[0].strip()) or ".img"
        if ext == ".jpe":
            ext = ".jpg"
        base = f"{base}{ext}"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return f"{index:03d}_{digest}_{base}"


def download_images(
    urls: list[str],
    images_dir: Path,
) -> dict[str, str]:
    """원래 URL → 로컬 파일명(파일명만) 매핑."""
    images_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    for i, url in enumerate(urls, start=1):
        try:
            r = SESSION.get(url, timeout=40)
            r.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {url} ({exc})")
            continue
        name = _safe_name(url, i, r.headers.get("Content-Type"))
        dest = images_dir / name
        dest.write_bytes(r.content)
        mapping[url] = name
        print(f"OK  {name} <- {url}")
    return mapping


def rewrite_lesson_urls(lesson: dict[str, Any], url_map: dict[str, str]) -> dict[str, Any]:
    data = json.loads(json.dumps(lesson))

    def repl(u: str) -> str:
        return url_map.get(u, u)

    for page in data.get("pages") or []:
        for block in page.get("blocks") or []:
            if block.get("type") == "image" and block.get("src"):
                block["src"] = repl(block["src"])
            elif block.get("type") == "gallery" and block.get("srcs"):
                block["srcs"] = [repl(s) for s in block["srcs"]]
            elif block.get("type") == "banner" and block.get("src"):
                block["src"] = repl(block["src"])

    for st in data.get("stages") or []:
        if st.get("image"):
            st["image"] = repl(st["image"])
        if st.get("images"):
            st["images"] = [repl(s) for s in st["images"]]
        for p in st.get("discussionPages") or []:
            if p.get("image"):
                p["image"] = repl(p["image"])
        for p in st.get("playPages") or []:
            if p.get("image"):
                p["image"] = repl(p["image"])
        for p in st.get("closingPages") or []:
            if p.get("image"):
                p["image"] = repl(p["image"])

    chars = data.get("characterImages")
    if isinstance(chars, dict):
        for key in list(chars.keys()):
            if chars.get(key):
                chars[key] = repl(chars[key])
    return data


def rewrite_html_urls(html: str, url_map: dict[str, str]) -> str:
    out = html
    # 긴 URL부터 치환(부분 문자열 충돌 방지)
    for old in sorted(url_map.keys(), key=len, reverse=True):
        out = out.replace(old, url_map[old])
    return out


def offline_preview_html(
    html_path: Path,
    out_dir: Path,
    *,
    repo_prefix: str | None = None,
) -> dict[str, Any]:
    """
    입력 HTML → out_dir/<차시제목>.html + assets/images/*
    이미지 src는 GitHub Raw 절대 URL로 치환.
    """
    html = html_path.read_text(encoding="utf-8")
    lesson = extract_lesson_from_html(html)
    html_name = preview_html_name((lesson or {}).get("title") or out_dir.name)
    urls = collect_image_urls(lesson) if lesson else []
    # HTML에만 있는 URL도 보강
    for u in collect_urls_from_html_text(html):
        if u not in urls:
            urls.append(u)

    images_dir = out_dir / "assets" / "images"
    file_map = download_images(urls, images_dir)  # url -> filename

    prefix = (repo_prefix or f"lessons/previews/{out_dir.name}").replace("\\", "/").strip("/")
    absolute_map = {
        old: github_raw_url(f"{prefix}/assets/images/{fname}")
        for old, fname in file_map.items()
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    new_html = rewrite_html_urls(html, absolute_map)
    if lesson:
        new_lesson = rewrite_lesson_urls(lesson, absolute_map)
        # lessonData 블록 교체
        m = LESSON_ASSIGN_RE.search(new_html)
        if m:
            start = m.end()
            while start < len(new_html) and new_html[start].isspace():
                start += 1
            try:
                _, end_offset = json.JSONDecoder().raw_decode(new_html[start:])
                end = start + end_offset
                payload = json.dumps(new_lesson, ensure_ascii=False)
                new_html = new_html[:start] + payload + new_html[end:]
            except json.JSONDecodeError:
                pass
        (out_dir / "lesson.json").write_text(
            json.dumps(new_lesson, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    out_html = out_dir / html_name
    out_html.write_text(new_html, encoding="utf-8")
    # 예전 preview.html 이 남아 있으면 혼동 방지
    legacy = out_dir / "preview.html"
    if legacy.exists() and legacy.resolve() != out_html.resolve():
        try:
            legacy.unlink()
        except OSError:
            pass
    (out_dir / "assets" / "manifest.json").write_text(
        json.dumps(
            {
                "githubRawBase": github_raw_url(prefix),
                "htmlFile": html_name,
                "mapping": absolute_map,
                "failed": [u for u in urls if u not in file_map],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "outDir": str(out_dir),
        "imageCount": len(file_map),
        "failed": [u for u in urls if u not in file_map],
        "preview": str(out_html),
        "htmlFile": html_name,
        "rawPreview": github_raw_url(f"{prefix}/{html_name}"),
    }


def offline_lesson_data(
    lesson: dict[str, Any],
    out_dir: Path,
    *,
    repo_prefix: str | None = None,
) -> dict[str, Any]:
    """변환 직후 lesson dict의 이미지를 받아 Raw URL로 치환한 lesson 반환."""
    urls = collect_image_urls(lesson)
    images_dir = out_dir / "assets" / "images"
    file_map = download_images(urls, images_dir)
    prefix = (repo_prefix or f"lessons/previews/{out_dir.name}").replace("\\", "/").strip("/")
    absolute_map = {
        old: github_raw_url(f"{prefix}/assets/images/{fname}")
        for old, fname in file_map.items()
    }
    rewritten = rewrite_lesson_urls(lesson, absolute_map)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "assets" / "manifest.json").write_text(
        json.dumps(
            {
                "githubRawBase": github_raw_url(prefix),
                "mapping": absolute_map,
                "failed": [u for u in urls if u not in file_map],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return rewritten


if __name__ == "__main__":
    import argparse
    import re as _re

    parser = argparse.ArgumentParser(description="preview.html 이미지 → GitHub Raw URL")
    parser.add_argument("html", type=Path, help="입력 preview.html")
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="출력 폴더 (기본: lessons/previews/<slug>)",
    )
    args = parser.parse_args()
    html_path = args.html.resolve()
    lesson = extract_lesson_from_html(html_path.read_text(encoding="utf-8"))
    title = (lesson or {}).get("title") or html_path.stem
    slug = _re.sub(r"[^\w\-가-힣]+", "-", title).strip("-")[:60] or "lesson"
    out = args.out or (ROOT / "lessons" / "previews" / slug)
    result = offline_preview_html(html_path, out)
    print(json.dumps(result, ensure_ascii=False, indent=2))
