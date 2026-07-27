# -*- coding: utf-8 -*-
"""한글 수업 카드 → lessonData (담당자용 내부 변환)."""
from __future__ import annotations

import re
from typing import Any


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _meta(text: str) -> dict[str, str]:
    out = {"title": "수업 교안", "level": "크레용스쿨", "sourceUrl": ""}
    for line in text.splitlines():
        if ":" not in line or line.strip().startswith("["):
            continue
        k, v = line.split(":", 1)
        k, v = _clean(k), v.strip()
        if k == "차시 제목" and v:
            out["title"] = v
        elif k == "과정명" and v:
            out["level"] = v
        elif k == "원본 링크" and v:
            out["sourceUrl"] = v
    return out


def _split_screens(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"\n\s*\[화면\s*\d+\]\s*", text)
    headers = re.findall(r"\[화면\s*\d+\]\s*([^\n]+)", text)
    body_parts = parts[1:] if len(parts) > 1 else []
    screens: list[tuple[str, str]] = []
    for i, header in enumerate(headers):
        body = body_parts[i] if i < len(body_parts) else ""
        screens.append((_clean(header), body))
    return screens


def _fields(body: str) -> dict[str, str]:
    """- 키: 값 과 들여쓴 연속 줄을 모은다."""
    fields: dict[str, str] = {}
    current: str | None = None
    for raw in body.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("("):
            continue
        m = re.match(r"^\s*-\s*([^:：]+)\s*[:：]\s*(.*)$", line)
        if m:
            current = _clean(m.group(1))
            fields[current] = m.group(2).strip()
            continue
        m2 = re.match(r"^\s{2,}([^:：]+)\s*[:：]\s*(.*)$", line)
        if m2 and current:
            # 활동 하위 안내/순서 — 키를 활동 맥락에 붙임
            sub = _clean(m2.group(1))
            val = m2.group(2).strip()
            # 직전에 본 활동N 제목 찾기
            act_keys = [k for k in fields if re.match(r"활동\d+\s*제목", k)]
            prefix = act_keys[-1] if act_keys else current
            act_no = re.match(r"(활동\d+)", prefix)
            key = f"{act_no.group(1)} {sub}" if act_no else f"{current} {sub}"
            fields[key] = val
            continue
        if current and line.startswith(" ") or (current and not line.startswith("-")):
            if line.startswith(" ") or line.startswith("\t"):
                fields[current] = _clean(fields.get(current, "") + " " + line.strip())
    return fields


def _guess_type(title: str) -> str:
    if any(k in title for k in ("소개", "안내")):
        return "intro"
    if any(k in title for k in ("생각", "질문", "나누기")):
        return "discussion"
    if any(k in title for k in ("영상", "H5P", "동영상")):
        return "video"
    if any(k in title for k in ("활동", "놀이", "게임")):
        return "play"
    if any(k in title for k in ("마무리", "평가", "회상")):
        return "closing"
    return "discussion"


def _split_options(s: str) -> list[str]:
    parts = re.split(r"\s*/\s*|\s*\|\s*", s)
    return [_clean(p) for p in parts if _clean(p)]


def _split_steps(s: str) -> list[str]:
    s = s.strip()
    if not s:
        return []
    parts = re.split(r"\s*\d+\)\s*|\s*;\s*|\s*/\s*", s)
    out = [_clean(p) for p in parts if _clean(p)]
    return out or [s]


def _materials(s: str) -> list[str]:
    return [_clean(x) for x in re.split(r"\s*,\s*", s) if _clean(x)]


def parse_lesson_card(text: str) -> dict[str, Any]:
    meta = _meta(text)
    screens = _split_screens(text)
    stages: list[dict[str, Any]] = []

    for i, (header, body) in enumerate(screens, start=1):
        fields = _fields(body)
        stype = _guess_type(header)
        teacher = fields.get("선생님 멘트", f"「{header}」를 진행하세요.")
        display = f"{i:02d} {header}"

        if stype == "intro":
            bubble = fields.get("아이에게 보여줄 말") or fields.get("안내 말") or header
            stage: dict[str, Any] = {
                "label": header,
                "displayName": display,
                "type": "intro",
                "title": header,
                "bubble": bubble,
                "teacherTalk": teacher,
            }
            if fields.get("준비물"):
                stage["materials"] = _materials(fields["준비물"])
            imgs = _parse_image_list(fields.get("이미지", ""))
            if imgs:
                stage["images"] = imgs
                stage["image"] = imgs[0]
            stages.append(stage)
            continue

        if stype == "discussion":
            questions = []
            for k, v in fields.items():
                if re.match(r"질문\d+", k) and v:
                    questions.append(
                        {"bubble": v, "teacherTalk": "아이 응답을 들어주세요."}
                    )
            if not questions and fields.get("아이에게 보여줄 말"):
                questions = [
                    {
                        "bubble": fields["아이에게 보여줄 말"],
                        "teacherTalk": teacher,
                    }
                ]
            stage = {
                "label": header,
                "displayName": display,
                "type": "discussion",
                "title": header,
                "bubble": questions[0]["bubble"] if questions else header,
                "teacherTalk": teacher,
                "discussionPages": questions
                or [{"bubble": header, "teacherTalk": teacher}],
            }
            if fields.get("이미지"):
                stage["image"] = fields["이미지"].strip()
            stages.append(stage)
            continue

        if stype == "video":
            stage = {
                "label": header,
                "displayName": display,
                "type": "video",
                "title": header,
                "bubble": fields.get("안내 말")
                or "준비된 친구들은 영상을 플레이 해주세요.",
                "teacherTalk": teacher,
                "videoUrl": fields.get("영상/H5P 주소", "").replace("확인 필요", "").strip(),
            }
            if fields.get("이미지"):
                stage["image"] = fields["이미지"].strip()
            stages.append(stage)
            continue

        if stype == "play":
            play_pages = []
            act_nos = sorted(
                {
                    m.group(1)
                    for k in fields
                    if (m := re.match(r"(활동\d+)", k))
                },
                key=lambda x: int(re.search(r"\d+", x).group()),
            )
            for no in act_nos:
                title = fields.get(f"{no} 제목") or no
                bubble = fields.get(f"{no} 안내") or title
                steps = _split_steps(fields.get(f"{no} 순서", ""))
                page = {
                    "title": title,
                    "bubble": bubble,
                    "hideGuide": True,
                    "steps": steps or [bubble],
                    "teacherTalk": f"「{title}」활동을 진행하세요.",
                }
                if fields.get(f"{no} 이미지"):
                    page["image"] = fields[f"{no} 이미지"].strip()
                play_pages.append(page)
            intro = fields.get("활동 도입") or header
            if not play_pages:
                play_pages = [
                    {
                        "title": header,
                        "bubble": intro,
                        "hideGuide": True,
                        "steps": [intro],
                        "teacherTalk": teacher,
                    }
                ]
            stage = {
                "label": header,
                "displayName": display,
                "type": "play",
                "title": header,
                "bubble": intro,
                "teacherTalk": teacher,
                "playPages": play_pages,
            }
            if fields.get("이미지"):
                stage["image"] = fields["이미지"].strip()
            stages.append(stage)
            continue

        # closing
        recall = fields.get("회상 말") or header
        bye = fields.get("끝 인사") or "다음 시간에 또 만나요."
        quizzes = _parse_quizzes_from_body(body, i)
        closing_pages: list[dict[str, Any]] = [
            {
                "displayName": f"{i:02d} 회상하기",
                "title": "오늘 정말 잘했어요!",
                "bubble": recall,
                "teacherTalk": "오늘 한 활동을 짧게 회상하게 하세요.",
                "isClosingFinale": True,
            },
            *quizzes,
            {
                "displayName": f"{i:02d} Bye!",
                "title": "다음 시간에 또 만나요",
                "bubble": bye,
                "teacherTalk": "가정연계를 안내하며 마무리합니다.",
                "isClosingFinale": True,
                "homework": bye if "부모님" in bye else "",
            },
        ]
        stage = {
            "label": header,
            "displayName": display,
            "type": "closing",
            "title": header,
            "bubble": recall,
            "teacherTalk": teacher,
            "closingPages": closing_pages,
            "homework": bye if "부모님" in bye else "",
        }
        if fields.get("이미지"):
            stage["image"] = fields["이미지"].strip()
        stages.append(stage)

    if not stages:
        raise ValueError("수업 카드에서 [화면] 블록을 찾지 못했습니다.")

    return {
        "level": meta["level"],
        "title": meta["title"],
        "sourceUrl": meta["sourceUrl"],
        "expression": "",
        "characterImages": {"intro": "", "thinking": "", "guide": ""},
        "goals": [f"「{meta['title']}」 수업을 진행한다."],
        "stages": stages,
    }


def _uniq(urls: list[str]) -> list[str]:
    out: list[str] = []
    for u in urls:
        if u and u not in out:
            out.append(u)
    return out


def _prefer(urls: list[str], keys: tuple[str, ...]) -> str:
    for u in urls:
        if any(k in u for k in keys):
            return u
    return urls[0] if urls else ""


def fetch_image_pools(source_url: str) -> dict[str, list[str]]:
    """원본 레슨/토픽에서 이미지 URL 풀을 모은다."""
    from converter import extract_blocks_from_html, fetch, find_lesson_items

    pools: dict[str, list[str]] = {
        "intro": [],
        "discussion": [],
        "video": [],
        "play": [],
        "closing": [],
        "all": [],
    }
    if not source_url or "crayonschool.co.kr" not in source_url:
        return pools

    html = fetch(source_url)
    _title, _course, items = find_lesson_items(source_url, html)

    def take(blocks: list) -> list[str]:
        return [
            b.src
            for b in blocks
            if getattr(b, "type", "") in ("banner", "image") and getattr(b, "src", "")
        ]

    landing = take(extract_blocks_from_html(html))
    pools["intro"].extend(landing)
    pools["all"].extend(landing)

    for it in items:
        try:
            blocks = extract_blocks_from_html(fetch(it["url"]))
        except Exception:  # noqa: BLE001
            continue
        imgs = take(blocks)
        pools["all"].extend(imgs)
        title = it.get("title") or ""
        if "영상" in title:
            pools["video"].extend(imgs)
            pools["intro"].extend(imgs)
            pools["discussion"].extend(imgs)
        elif any(k in title for k in ("연계", "활동", "게임", "놀이")):
            pools["play"].extend(imgs)
        elif any(k in title for k in ("마무리", "평가")):
            pools["closing"].extend(imgs)
        else:
            pools["discussion"].extend(imgs)

    for k in pools:
        pools[k] = _uniq(pools[k])
    return pools


def _missing_image(value: Any) -> bool:
    """카드의 이미지 칸이 비었거나 '확인 필요'면 True."""
    if value is None:
        return True
    s = str(value).strip()
    if not s:
        return True
    if s in ("확인 필요", "없음", "-", "N/A", "n/a"):
        return True
    if not s.startswith(("http://", "https://", "/")):
        return True
    return False


def _parse_image_list(raw: str) -> list[str]:
    if _missing_image(raw):
        return []
    parts = re.split(r"\s*[,|\n]\s*", raw.strip())
    return [p.strip() for p in parts if p.strip().startswith(("http://", "https://", "/"))]


def _pick_many(urls: list[str], keys: tuple[str, ...], limit: int = 3) -> list[str]:
    """키워드 매칭 이미지를 앞에 두고 최대 limit장."""
    hit: list[str] = []
    rest: list[str] = []
    for u in urls:
        if any(k in u for k in keys):
            if u not in hit:
                hit.append(u)
        else:
            if u not in rest:
                rest.append(u)
    return (hit + rest)[:limit]


def enrich_images_from_source(lesson_data: dict[str, Any]) -> dict[str, Any]:
    """카드에 이미지가 비어 있으면 원본 링크에서 채워 넣는다."""
    source = lesson_data.get("sourceUrl") or ""
    pools = fetch_image_pools(source)
    if not pools.get("all"):
        return lesson_data

    play_i = 0
    play_imgs = pools.get("play") or pools.get("all") or []

    for stage in lesson_data.get("stages", []):
        stype = stage.get("type")
        if stype == "intro":
            have = [
                u
                for u in (stage.get("images") or ([stage["image"]] if stage.get("image") else []))
                if not _missing_image(u)
            ]
            if len(have) < 2:
                pool = pools.get("intro") or pools["all"]
                if stage.get("materials"):
                    # 교구재·큐블로처럼 준비물 컷이 여러 장이면 전부 보이게
                    mat_keys = ("교구재", "교구", "큐블로", "준비물")
                    mat_hits = _pick_many(pool, mat_keys, limit=3)
                    # 키워드에 실제로 걸린 것만 (나머지 채움분 제외)
                    mat_only = [
                        u
                        for u in mat_hits
                        if any(k in u for k in mat_keys)
                    ]
                    if len(mat_only) >= 2:
                        picked = mat_only[:3]
                    else:
                        picked = _pick_many(
                            pool,
                            mat_keys + ("수업소개하기", "소개하기"),
                            limit=3,
                        )
                else:
                    picked = _pick_many(
                        pool,
                        ("수업소개하기", "소개하기", "소개", "교구재", "반가워요"),
                        limit=2,
                    )
                # 기존 유효 URL 유지 + 부족분 채움
                merged = list(have)
                for u in picked:
                    if u not in merged:
                        merged.append(u)
                    if len(merged) >= 3:
                        break
                if merged:
                    stage["images"] = merged
                    stage["image"] = merged[0]
        elif stype == "discussion":
            if _missing_image(stage.get("image")):
                stage["image"] = _prefer(
                    pools.get("discussion") or pools["all"],
                    ("반가워요", "수업소개하기", "소개"),
                )
            for page in stage.get("discussionPages") or []:
                if _missing_image(page.get("image")):
                    page["image"] = stage.get("image") or _prefer(
                        pools.get("discussion") or pools["all"],
                        ("반가워요", "수업소개하기", "소개"),
                    )
        elif stype == "video" and _missing_image(stage.get("image")):
            stage["image"] = _prefer(
                pools.get("video") or pools["all"],
                ("인터렉티브", "영상", "소개하기"),
            )
        elif stype == "play":
            if _missing_image(stage.get("image")):
                stage["image"] = _prefer(
                    pools.get("play") or pools["all"],
                    ("활동하기", "교구활동"),
                )
            for page in stage.get("playPages") or []:
                if not _missing_image(page.get("image")):
                    continue
                candidates = [
                    u
                    for u in play_imgs
                    if "활동하기_수정" not in u and "안내_수정" not in u
                ] or play_imgs
                if play_i < len(candidates):
                    page["image"] = candidates[play_i]
                    play_i += 1
                elif candidates:
                    page["image"] = candidates[-1]
        elif stype == "closing":
            if _missing_image(stage.get("image")):
                stage["image"] = _prefer(
                    pools.get("closing") or pools["all"],
                    ("회상", "평가", "정리"),
                )
            for page in stage.get("closingPages") or []:
                if not _missing_image(page.get("image")):
                    continue
                if page.get("quiz"):
                    page["image"] = _prefer(
                        pools.get("closing") or pools["all"],
                        ("평가", "정리"),
                    )
                else:
                    page["image"] = _prefer(
                        pools.get("closing") or pools["all"],
                        ("회상", "정리"),
                    ) or stage.get("image")

    return lesson_data


def _parse_quizzes_from_body(body: str, stage_i: int) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    chunks = re.split(r"-\s*퀴즈(\d+)\s*질문\s*[:：]\s*", body)
    # chunks: [pre, num, content, num, content, ...]
    if len(chunks) < 3:
        return pages
    it = iter(chunks[1:])
    for num, content in zip(it, it):
        lines = content.strip().splitlines()
        question = _clean(lines[0]) if lines else f"퀴즈{num}"
        options: list[str] = []
        for line in lines[1:]:
            if "보기" in line and (":" in line or "：" in line):
                options = _split_options(line.split(":", 1)[-1].split("：", 1)[-1])
                break
        pages.append(
            {
                "displayName": f"{stage_i:02d} 평가하기",
                "title": question[:48],
                "bubble": question,
                "quiz": {
                    "question": question,
                    "options": options or ["예", "아니오"],
                    "correctIndex": 0,
                    "correctFeedback": "고마워요!",
                    "wrongFeedback": "고마워요!",
                },
                "teacherTalk": "응답을 확인하세요.",
            }
        )
    return pages
