# -*- coding: utf-8 -*-
"""교안 변환 툴 — 링크→블록형 HTML / 카드→미리보기 / 블록 편집기."""
from __future__ import annotations

import json
import os
import re
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

from card_parser import enrich_images_from_source, parse_lesson_card
from converter import convert_lesson
import workspace as ws

ROOT = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(ROOT / "templates"),
    static_folder=str(ROOT / "static"),
)

SAMPLE_CARD = ROOT / "lessons" / "지혜큐브_1차시" / "수업카드.txt"


def build_html(lesson_data: dict, shell: str = "block") -> str:
    """기본은 블록형 셸. shell='crayon'이면 구 스테이지 플레이어."""
    data = json.loads(json.dumps(lesson_data))
    for st in data.get("stages", []):
        st.pop("rawBlocks", None)
    data.pop("meta", None)

    use_block = shell != "crayon" and (
        data.get("mode") == "blocks" or data.get("pages")
    )
    path = ROOT / ("block_shell.html" if use_block else "crayon_shell.html")
    template = path.read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False)
    if "__LESSON_DATA__" not in template:
        raise RuntimeError("플레이어 템플릿에 __LESSON_DATA__ 자리가 없습니다.")
    return template.replace("__LESSON_DATA__", payload)


def safe_filename(title: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]+', "_", title or "lesson")
    name = re.sub(r"\s+", "_", name).strip("._")
    return (name[:60] or "lesson") + "_미리보기.html"


def require_editor_token(view):
    """EDITOR_TOKEN이 설정돼 있으면 헤더/쿼리 검사."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        token = os.environ.get("EDITOR_TOKEN", "").strip()
        if not token:
            return view(*args, **kwargs)
        got = (
            request.headers.get("X-Editor-Token")
            or request.args.get("token")
            or ""
        ).strip()
        if got != token:
            return jsonify({"ok": False, "error": "편집 권한이 없습니다."}), 401
        return view(*args, **kwargs)

    return wrapped


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/desk")
def desk():
    return render_template("desk.html")


@app.after_request
def _no_cache_editor(resp):
    path = request.path or ""
    if path.startswith("/editor") or path.startswith("/edit") or path.startswith("/static/editor"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp


@app.get("/edit")
@require_editor_token
def editor_v2():
    """캐시 회피용 새 경로 — 밍글형 수업 편집."""
    return render_template("editor.html")


@app.get("/editor")
@require_editor_token
def editor():
    # 예전 캐시된 /editor HTML을 쓰지 않도록 새 경로로 보냄
    from flask import redirect
    return redirect("/edit", code=302)


@app.get("/api/sample-card")
def api_sample_card():
    if not SAMPLE_CARD.exists():
        return jsonify({"ok": False, "error": "샘플 수업카드가 없습니다."}), 404
    return jsonify({"ok": True, "text": SAMPLE_CARD.read_text(encoding="utf-8")})


@app.post("/api/card-to-preview")
def api_card_to_preview():
    body = request.get_json(silent=True) or {}
    card = (body.get("card") or "").strip()
    fetch_images = body.get("fetchImages", True)
    if not card:
        return jsonify({"ok": False, "error": "수업 카드 내용을 붙여넣어 주세요."}), 400
    try:
        lesson_data = parse_lesson_card(card)
        image_note = ""
        if fetch_images and lesson_data.get("sourceUrl"):
            lesson_data = enrich_images_from_source(lesson_data)
            with_img = sum(1 for s in lesson_data.get("stages", []) if s.get("image"))
            image_note = f"원본에서 이미지 채움 (단계 {with_img})"
        elif fetch_images:
            image_note = "원본 링크가 없어 이미지는 건너뜀"
        html = build_html(lesson_data, shell="crayon")
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"변환 실패: {exc}"}), 500

    filename = safe_filename(lesson_data.get("title", "lesson"))
    stages = [
        f"{s.get('displayName')} ({s.get('type')})" for s in lesson_data.get("stages", [])
    ]
    return jsonify(
        {
            "ok": True,
            "title": lesson_data.get("title"),
            "stageCount": len(lesson_data.get("stages", [])),
            "stages": stages,
            "filename": filename,
            "html": html,
            "imageNote": image_note,
        }
    )


@app.post("/api/convert")
def api_convert():
    body = request.get_json(silent=True) or {}
    url = (body.get("url") or "").strip()
    offline_images_flag = body.get("offlineImages", True)
    if not url:
        return jsonify({"ok": False, "error": "수업 링크를 입력해 주세요."}), 400
    if "crayonschool.co.kr" not in url:
        return jsonify({"ok": False, "error": "현재는 crayonschool.co.kr 레슨 링크만 지원합니다."}), 400

    try:
        from offline_images import offline_lesson_data, github_raw_url

        lesson_data = convert_lesson(url)
        cleaned = ws.normalize_lesson(lesson_data)
        slug = ws.slugify(cleaned.get("title") or "lesson")
        folder = ROOT / "lessons" / "previews" / slug
        prefix = f"lessons/previews/{slug}"
        image_note = ""
        if offline_images_flag:
            cleaned = offline_lesson_data(cleaned, folder, repo_prefix=prefix)
            image_note = "이미지를 GitHub Raw URL로 저장함"
        html = build_html(cleaned)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "preview.html").write_text(html, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"변환 실패: {exc}"}), 500

    filename = safe_filename(lesson_data.get("title", "lesson")).replace("_미리보기", "")
    return jsonify(
        {
            "ok": True,
            "title": cleaned.get("title"),
            "sections": lesson_data.get("meta", {}).get("sections", []),
            "logs": lesson_data.get("meta", {}).get("logs", []),
            "stageCount": len(cleaned.get("pages") or lesson_data.get("stages", [])),
            "filename": filename,
            "html": html,
            "imageNote": image_note,
            "previewPath": f"lessons/previews/{slug}/preview.html",
            "rawUrl": github_raw_url(f"{prefix}/preview.html"),
            "lessonData": cleaned,
        }
    )


# ── 편집 워크스페이스 ──────────────────────────────────────────


@app.get("/api/lessons")
@require_editor_token
def api_lessons():
    return jsonify({"ok": True, "lessons": ws.list_lessons()})


@app.post("/api/lessons/import")
@require_editor_token
def api_lessons_import():
    slug_hint = ""
    raw = ""
    filename = ""

    if request.files.get("file"):
        f = request.files["file"]
        filename = f.filename or "upload.html"
        raw = f.read().decode("utf-8", errors="replace")
        slug_hint = (request.form.get("slug") or "").strip()
    else:
        body = request.get_json(silent=True) or {}
        raw = body.get("html") or body.get("json") or body.get("text") or ""
        filename = body.get("filename") or ""
        slug_hint = (body.get("slug") or "").strip()
        if isinstance(body.get("lessonData"), dict):
            try:
                data = ws.normalize_lesson(body["lessonData"])
            except Exception as exc:  # noqa: BLE001
                return jsonify({"ok": False, "error": str(exc)}), 400
            slug = slug_hint or ws.unique_slug(data.get("title") or "lesson")
            saved = ws.save_lesson(slug, data, build_html)
            return jsonify(
                {
                    "ok": True,
                    "slug": slug,
                    "lesson": saved,
                    "previewUrl": f"/w/{slug}/preview",
                }
            )

    try:
        data = ws.parse_lesson_payload(raw, filename)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    slug = slug_hint or ws.unique_slug(data.get("title") or Path(filename).stem or "lesson")
    # slug 충돌 시 덮어쓰기 허용 (명시 slug) / 자동이면 unique
    if not slug_hint:
        slug = ws.unique_slug(data.get("title") or "lesson")
    saved = ws.save_lesson(slug, data, build_html)
    return jsonify(
        {
            "ok": True,
            "slug": slug,
            "lesson": saved,
            "previewUrl": f"/w/{slug}/preview",
        }
    )


@app.post("/api/lessons/import-default-preview")
@require_editor_token
def api_import_default_preview():
    """로컬 AI_model_design/preview.html 또는 최신 워크스페이스를 편집기로 연다."""
    candidates = [
        ROOT.parent / "preview.html",
        ROOT / "preview.html",
    ]
    for path in candidates:
        if path.is_file():
            try:
                raw = path.read_text(encoding="utf-8")
                data = ws.parse_lesson_payload(raw, path.name)
                slug = ws.unique_slug(data.get("title") or "preview")
                # 같은 제목 폴더가 있으면 덮어써서 중복 -2,-3 방지
                base = ws.slugify(data.get("title") or "preview")
                if (ws.WORKSPACE / base).exists():
                    slug = base
                saved = ws.save_lesson(slug, data, build_html)
                return jsonify(
                    {
                        "ok": True,
                        "slug": slug,
                        "lesson": saved,
                        "previewUrl": f"/w/{slug}/preview",
                        "source": str(path),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                return jsonify({"ok": False, "error": f"preview.html 읽기 실패: {exc}"}), 500

    lessons = ws.list_lessons()
    if lessons:
        slug = lessons[0]["slug"]
        data = ws.load_lesson(slug)
        return jsonify(
            {
                "ok": True,
                "slug": slug,
                "lesson": data,
                "previewUrl": f"/w/{slug}/preview",
                "source": "workspace",
            }
        )
    return jsonify({"ok": False, "error": "불러올 preview.html이 없습니다."}), 404


@app.get("/api/lessons/<slug>")
@require_editor_token
def api_lesson_get(slug: str):
    data = ws.load_lesson(slug)
    if data is None:
        return jsonify({"ok": False, "error": "교안을 찾을 수 없습니다."}), 404
    return jsonify(
        {
            "ok": True,
            "slug": slug,
            "lesson": data,
            "previewUrl": f"/w/{slug}/preview",
        }
    )


@app.post("/api/lessons/preview-draft")
@require_editor_token
def api_preview_draft():
    """저장 없이 현재 lesson JSON으로 플레이어 HTML 생성 (라이브 미리보기)."""
    body = request.get_json(silent=True) or {}
    lesson = body.get("lesson")
    if not isinstance(lesson, dict):
        return jsonify({"ok": False, "error": "lesson 객체가 필요합니다."}), 400
    try:
        page_index = int(body.get("pageIndex") or 0)
    except (TypeError, ValueError):
        page_index = 0
    try:
        normalized = ws.normalize_lesson(lesson)
        html = build_html(normalized, shell="block")
        page_count = len(normalized.get("pages") or [])
        if page_count:
            page_index = max(0, min(page_index, page_count - 1))
        # 편집 중인 페이지부터 보이도록
        html = html.replace("let index = 0;", f"let index = {page_index};", 1)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"미리보기 생성 실패: {exc}"}), 500
    return jsonify({"ok": True, "html": html, "pageIndex": page_index})


@app.put("/api/lessons/<slug>")
@require_editor_token
def api_lesson_put(slug: str):
    body = request.get_json(silent=True) or {}
    lesson = body.get("lesson") or body
    if not isinstance(lesson, dict):
        return jsonify({"ok": False, "error": "lesson 객체가 필요합니다."}), 400
    try:
        saved = ws.save_lesson(slug, lesson, build_html)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"저장 실패: {exc}"}), 500
    return jsonify(
        {
            "ok": True,
            "slug": slug,
            "lesson": saved,
            "previewUrl": f"/w/{slug}/preview",
            "downloadUrl": f"/api/lessons/{slug}/download",
        }
    )


@app.get("/api/lessons/<slug>/download")
@require_editor_token
def api_lesson_download(slug: str):
    path = ws.preview_path(slug)
    if not path.exists():
        data = ws.load_lesson(slug)
        if data is None:
            return jsonify({"ok": False, "error": "교안을 찾을 수 없습니다."}), 404
        ws.save_lesson(slug, data, build_html)
    return send_from_directory(
        ws.lesson_dir(slug),
        "preview.html",
        as_attachment=True,
        download_name=safe_filename(
            (ws.load_lesson(slug) or {}).get("title") or slug
        ).replace("_미리보기", "")
        + "_미리보기.html",
    )


@app.post("/api/lessons/<slug>/assets")
@require_editor_token
def api_lesson_assets(slug: str):
    if not ws.lesson_json_path(slug).exists():
        return jsonify({"ok": False, "error": "먼저 교안을 저장하세요."}), 404
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "파일이 없습니다."}), 400
    folder = ws.assets_dir(slug)
    folder.mkdir(parents=True, exist_ok=True)
    name = ws.safe_asset_name(f.filename)
    dest = folder / name
    f.save(dest)
    url = f"/w/{slug}/assets/{name}"
    return jsonify({"ok": True, "url": url, "filename": name})


@app.get("/w/<slug>/preview")
def workspace_preview(slug: str):
    path = ws.preview_path(slug)
    if not path.exists():
        data = ws.load_lesson(slug)
        if data is None:
            return "교안을 찾을 수 없습니다.", 404
        ws.save_lesson(slug, data, build_html)
    return send_from_directory(ws.lesson_dir(slug), "preview.html")


@app.get("/w/<slug>/assets/<path:filename>")
def workspace_asset(slug: str, filename: str):
    folder = ws.assets_dir(slug)
    if not (folder / filename).is_file():
        return "파일을 찾을 수 없습니다.", 404
    return send_from_directory(folder, filename)


@app.get("/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    ws.ensure_workspace_root()
    print("링크 변환: http://127.0.0.1:5055")
    print("카드 데스크: http://127.0.0.1:5055/desk")
    print("블록 편집기(새): http://127.0.0.1:5055/edit")
    print("블록 편집기: http://127.0.0.1:5055/editor  → /edit 로 이동")
    app.run(host="127.0.0.1", port=5055, debug=False)
