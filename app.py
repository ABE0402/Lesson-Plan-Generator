# -*- coding: utf-8 -*-
"""교안 변환 툴 — 링크→블록형 HTML / 카드→미리보기(로컬 백업)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from card_parser import enrich_images_from_source, parse_lesson_card
from converter import convert_lesson

ROOT = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(ROOT / "templates"))

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


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/desk")
def desk():
    return render_template("desk.html")


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
    if not url:
        return jsonify({"ok": False, "error": "수업 링크를 입력해 주세요."}), 400
    if "crayonschool.co.kr" not in url:
        return jsonify({"ok": False, "error": "현재는 crayonschool.co.kr 레슨 링크만 지원합니다."}), 400

    try:
        lesson_data = convert_lesson(url)
        html = build_html(lesson_data)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"변환 실패: {exc}"}), 500

    filename = safe_filename(lesson_data.get("title", "lesson")).replace("_미리보기", "")
    return jsonify(
        {
            "ok": True,
            "title": lesson_data.get("title"),
            "sections": lesson_data.get("meta", {}).get("sections", []),
            "logs": lesson_data.get("meta", {}).get("logs", []),
            "stageCount": len(lesson_data.get("pages") or lesson_data.get("stages", [])),
            "filename": filename,
            "html": html,
            "lessonData": {
                "title": lesson_data.get("title"),
                "level": lesson_data.get("level"),
                "sourceUrl": lesson_data.get("sourceUrl"),
                "mode": lesson_data.get("mode"),
                "pageCount": len(lesson_data.get("pages") or []),
            },
        }
    )


@app.get("/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    print("링크 변환: http://127.0.0.1:5055")
    print("카드 데스크: http://127.0.0.1:5055/desk")
    app.run(host="127.0.0.1", port=5055, debug=False)
