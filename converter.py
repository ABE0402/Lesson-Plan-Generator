# -*- coding: utf-8 -*-
"""크레용스쿨 레슨 URL → lessonData 변환."""
from __future__ import annotations

import html as H
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9",
    }
)

SKIP_IMG = (
    "로고",
    "icon_",
    "coupon",
    "유튜브",
    "인증마크",
    "cropped",
    "favicon",
    "교육설계_아이콘",
    "교육설계_항목",
    "주황체크",
    "크기변환아이콘",
    "크기변환꾸미기",
    "크기변환psxtg",
    "tip_수정",
)
SKIP_TXT = (
    "로그인",
    "회원가입",
    "장바구니",
    "개인정보",
    "이용약관",
    "바로가기",
    "주식회사",
    "고객센터",
    "강사 신청",
    "언어/사고",
    "사회/진로",
    "창의/탐구",
    "미술/표현",
    "부모교육",
    "강의 결제",
    "Family Site",
    "Copyright",
    "MY 정보",
    "알림장",
    "검색:",
    "구독",
    "강의로 돌아가기",
    "Complete",
    "Mark Complete",
    "Print",
    "이전 주제",
    "다음 주제",
)
META_TXT = (
    "자석소마큐브, 퍼즐미션 큐블로",
    "여러가지 퍼즐미션을 소마큐브로 풀어봐요",
    "소마큐브를 활용한 다양한 활동을 해봐요",
)


@dataclass
class Block:
    type: str
    text: str = ""
    src: str = ""


@dataclass
class Page:
    section: str
    title: str
    kind: str = "topic"
    blocks: list[Block] = field(default_factory=list)
    quizzes: list[dict[str, Any]] = field(default_factory=list)


def fetch(url: str, timeout: int = 35) -> str:
    r = SESSION.get(url, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def clean_text(s: str) -> str:
    return H.unescape(re.sub(r"\s+", " ", s or "")).strip()


def is_content_img(url: str) -> bool:
    if not url:
        return False
    if any(x in url for x in SKIP_IMG):
        return False
    if any(x in url for x in ("-300x", "-600x", "-624x", "-768x", "-100x", "-32x", "-180x", "-192x")):
        return False
    return "media.crayonschool" in url or "/wp-content/uploads/" in url


def extract_h5p_ids(html: str) -> list[str]:
    found = re.findall(
        r'h5p[_-]iframe[_-](\d+)|data-content-id="(\d+)"|h5p_embed&id=(\d+)',
        html,
        re.I,
    )
    out: list[str] = []
    for a, b, c in found:
        v = a or b or c
        if v and v not in out:
            out.append(v)
    return out


def extract_main_soup(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "html.parser")
    for sel in ("div.ld-tab-content", "div.learndash_content_wrap", "div.entry-content", "article"):
        node = soup.select_one(sel)
        if node and len(node.get_text(" ", strip=True)) > 80:
            return node
    return soup.body or soup


def is_noise_text(text: str) -> bool:
    if len(text) < 4:
        return True
    if any(s in text for s in SKIP_TXT):
        return True
    if text in ("크레용스쿨", "0% 완료", "완료", "Mark as Complete"):
        return True
    if re.fullmatch(r"\d+%?\s*(완료|Complete)?", text):
        return True
    if any(m in text for m in META_TXT) and len(text) < 80:
        return True
    if text.startswith("*") and "힌트" not in text and len(text) < 12:
        return True
    return False


def extract_wp_quizzes(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(".wpProQuiz_listItem")
    quizzes: list[dict[str, Any]] = []
    for item in items:
        q_el = item.select_one(".wpProQuiz_question_text")
        if not q_el:
            continue
        question = clean_text(q_el.get_text(" ", strip=True))
        options: list[str] = []
        for li in item.select(".wpProQuiz_questionListItem, .wpProQuiz_questionList li"):
            raw = clean_text(li.get_text(" ", strip=True))
            raw = re.sub(
                r"\s*(정답|틀림|Correct answer|Wrong|올바른\s*답).*$",
                "",
                raw,
                flags=re.I,
            ).strip()
            raw = re.sub(r"^\d+\s*[.)]\s*", "", raw)
            if raw and raw not in options and len(raw) < 80:
                options.append(raw)
        if question and options:
            quizzes.append(
                {
                    "question": question,
                    "options": options,
                    "correctIndex": 0,
                    "correctFeedback": "고마워요! 생각을 말해줘서 좋아요.",
                    "wrongFeedback": "고마워요! 생각을 말해줘서 좋아요.",
                }
            )
    return quizzes


def extract_blocks_from_html(html: str) -> list[Block]:
    """본문 DOM 순서대로 text/image/h5p 블록을 뽑는다."""
    root = extract_main_soup(html)
    blocks: list[Block] = []

    for el in root.find_all(
        ["img", "p", "li", "h1", "h2", "h3", "h4", "hr", "iframe", "strong", "b"],
        recursive=True,
    ):
        name = el.name.lower()

        if name == "iframe":
            src = el.get("src") or ""
            if src.startswith("//"):
                src = "https:" + src
            if "h5p" not in src.lower() and "action=h5p" not in src.lower():
                continue
            title = clean_text(el.get("title") or "")
            blocks.append(Block(type="h5p", src=src, text=title or "인터랙티브"))
            continue

        if name == "img":
            src = el.get("src") or ""
            if src.startswith("//"):
                src = "https:" + src
            if not is_content_img(src):
                continue
            w = el.get("width")
            try:
                wi = int(w) if w else 0
            except ValueError:
                wi = 0
            if wi and wi <= 40:
                continue
            # 소제목 옆 작은 아이콘 제외, 교재/단어카드 컷은 살림
            if wi and wi < 80 and "media.crayonschool" not in src:
                continue
            if wi >= 500 or re.search(
                r"(수정|안내|활동하기|소개하기|회상하기|평가하기|인터렉티브|교구활동)\.(jpg|png)$",
                src,
            ):
                btype = "banner"
            else:
                btype = "image"
            blocks.append(Block(type=btype, src=src))
            continue

        if name == "hr":
            blocks.append(Block(type="hr"))
            continue

        # strong/b 단독 소제목
        if name in ("strong", "b"):
            if el.find_parent(["p", "li", "h1", "h2", "h3", "h4"]):
                continue
            text = clean_text(el.get_text(" ", strip=True))
            if text and not is_noise_text(text):
                blocks.append(Block(type="heading", text=text))
            continue

        text = clean_text(el.get_text(" ", strip=True))
        if is_noise_text(text):
            continue
        if el.find_parent(class_=re.compile(r"wpProQuiz")):
            continue
        # 자식에 이미 처리한 img만 있는 p는 스킵(중복 텍스트 방지 어려우니 텍스트만)
        if name in ("h1", "h2", "h3", "h4"):
            blocks.append(Block(type="heading", text=text))
        else:
            m = re.match(r"^(<[^>\n]{1,40}>)\s*(.*)$", text, re.DOTALL)
            if m:
                blocks.append(Block(type="heading", text=m.group(1).strip()))
                rest = clean_text(m.group(2) or "")
                if rest:
                    blocks.append(Block(type="text", text=rest))
            else:
                blocks.append(Block(type="text", text=text))

    # HTML에 iframe이 스크립트만 있고 DOM walk에 빠진 H5P 보강(순서 끝)
    seen_h5p = {b.src for b in blocks if b.type == "h5p" and b.src}
    for hid in extract_h5p_ids(html):
        src = f"https://crayonschool.co.kr/wp-admin/admin-ajax.php?action=h5p_embed&id={hid}"
        if src not in seen_h5p:
            blocks.append(Block(type="h5p", src=src, text=f"인터랙티브 #{hid}"))
            seen_h5p.add(src)

    deduped: list[Block] = []
    seen_txt: set[str] = set()
    for b in blocks:
        if b.type in ("text", "heading"):
            if not b.text or b.text in seen_txt:
                continue
            seen_txt.add(b.text)
        if (
            deduped
            and deduped[-1].type == b.type
            and deduped[-1].text == b.text
            and deduped[-1].src == b.src
        ):
            continue
        deduped.append(b)
    return deduped[:200]


def _serialize_blocks(blocks: list[Block]) -> list[dict[str, Any]]:
    """연속 이미지를 gallery로 묶고 JSON용 dict로 직렬화."""
    out: list[dict[str, Any]] = []
    img_buf: list[str] = []

    def flush_imgs() -> None:
        nonlocal img_buf
        if not img_buf:
            return
        if len(img_buf) == 1:
            out.append({"type": "image", "src": img_buf[0]})
        else:
            out.append({"type": "gallery", "srcs": list(img_buf)})
        img_buf = []

    for b in blocks:
        if b.type in ("image", "banner") and b.src:
            img_buf.append(b.src)
            continue
        flush_imgs()
        if b.type == "hr":
            out.append({"type": "divider"})
        elif b.type == "h5p" and b.src:
            out.append({"type": "h5p", "src": b.src, "title": b.text or "인터랙티브"})
        elif b.type == "heading" and b.text:
            out.append({"type": "heading", "text": b.text})
        elif b.type == "text" and b.text:
            out.append({"type": "text", "text": b.text})
    flush_imgs()
    return out


def pages_to_block_pages(pages: list[Page]) -> list[dict[str, Any]]:
    """토픽을 원본 블록 순서 페이지로 나눈다. heading에서 슬라이드를 쪼갠다."""
    result: list[dict[str, Any]] = []

    for page in pages:
        serialized = _serialize_blocks(page.blocks)
        # 퀴즈는 블록으로 추가
        for q in page.quizzes or []:
            serialized.append(
                {
                    "type": "quiz",
                    "question": q.get("question") or "",
                    "options": q.get("options") or [],
                }
            )

        if not serialized:
            continue

        # heading 기준으로 슬라이드 분할 (첫 블록이 heading이 아니면 토픽 타이틀 슬라이드)
        chunks: list[list[dict[str, Any]]] = []
        current: list[dict[str, Any]] = []
        for blk in serialized:
            if blk.get("type") == "heading" and current:
                chunks.append(current)
                current = [blk]
            else:
                current.append(blk)
        if current:
            chunks.append(current)

        for i, chunk in enumerate(chunks):
            title = page.title or page.section
            for blk in chunk:
                if blk.get("type") == "heading" and blk.get("text"):
                    t = blk["text"]
                    title = t if len(t) <= 48 else (t[:45] + "…")
                    break
            if i == 0 and page.section and page.section != title:
                kicker = page.section
            else:
                kicker = page.section or page.title
            result.append(
                {
                    "kicker": kicker,
                    "title": title,
                    "kind": page.kind,
                    "blocks": chunk,
                }
            )

    # 번호
    for i, p in enumerate(result, start=1):
        p["displayName"] = f"{i:02d} {p.get('title') or p.get('kicker') or '화면'}"
    return result



def find_lesson_items(lesson_url: str, html: str) -> tuple[str, str, list[dict[str, str]]]:
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.select_one("h1")
    title = clean_text(title_el.get_text()) if title_el else "수업 교안"

    course = ""
    for sel in (".course-entry-title", ".ld-course-navigation h2", "h2.course-entry-title"):
        node = soup.select_one(sel)
        if node:
            course = clean_text(node.get_text())
            break

    items: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    scopes = soup.select(".ld-lesson-topic-list, .ld-topic-list, div.ld-table-list-items")
    if not scopes:
        scopes = [soup]

    for scope in scopes:
        if scope.find_parent(class_=re.compile(r"lms-topic-sidebar|ld-course-navigation|bb-lessons-list")):
            continue
        for a in scope.find_all("a", href=True):
            href = a["href"]
            label_el = a.select_one(".ld-topic-title, .ld-item-title")
            label = clean_text(label_el.get_text() if label_el else a.get_text(" ", strip=True))
            if not label or len(label) > 90:
                continue
            full = urljoin(lesson_url, href)
            path = urlparse(full).path
            if "/topic/" in path or "/topics/" in path:
                kind = "topic"
            elif "/quizzes/" in path or "/quiz/" in path:
                kind = "quiz"
            else:
                continue
            if label in ("이전", "다음", "강의로 돌아가기"):
                continue
            key = (kind, full)
            if key in seen:
                continue
            seen.add(key)
            items.append({"kind": kind, "title": label, "url": full})
        if items:
            break

    if not items:
        for a in soup.select(".ld-table-list-item a[href], .ld-table-list-item-quiz a[href]"):
            href = a.get("href") or ""
            label_el = a.select_one(".ld-topic-title")
            label = clean_text(label_el.get_text() if label_el else a.get_text(" ", strip=True))
            full = urljoin(lesson_url, href)
            path = urlparse(full).path
            if "/topic/" in path:
                kind = "topic"
            elif "/quizzes/" in path or "/quiz/" in path:
                kind = "quiz"
            else:
                continue
            key = (kind, full)
            if key in seen or not label:
                continue
            seen.add(key)
            items.append({"kind": kind, "title": label, "url": full})

    out: list[dict[str, str]] = []
    seen_t: set[str] = set()
    for it in items:
        if it["title"] in seen_t:
            continue
        seen_t.add(it["title"])
        out.append(it)
    return title, course, out[:12]


def split_sentences(text: str) -> list[str]:
    """질문/지시문을 페이지 단위로 쪼갠다."""
    text = clean_text(text)
    if not text:
        return []
    # 물음표 기준으로 먼저 분리
    chunks = re.split(r"(?<=[?？])\s+", text)
    out: list[str] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        # 긴 지시문은 문장 단위로 추가 분리
        if len(chunk) > 90 and "?" not in chunk:
            parts = re.split(r"(?<=[.!。])\s+|(?<=요)\s+(?=[가-힣A-Z*])", chunk)
            for p in parts:
                p = p.strip(" ·-")
                if p and len(p) >= 4:
                    out.append(p)
        else:
            out.append(chunk)
    # 중복 제거
    uniq: list[str] = []
    for t in out:
        if t not in uniq:
            uniq.append(t)
    return uniq


def is_welcome_text(t: str) -> bool:
    return any(k in t for k in ("환영", "온 친구", "탐험대", "수업에 온"))


def is_question_text(t: str) -> bool:
    return ("?" in t) or t.endswith("까요?") or t.endswith("나요?") or "어떤" in t


def is_video_cue(t: str) -> bool:
    return any(k in t for k in ("영상을 플레이", "아래 영상을", "인터랙티브 영상", "동영상을 플레이"))


def is_activity_title(t: str) -> bool:
    keys = (
        "응용해봐요",
        "준비해 주세요",
        "준비해주세요",
        "플레이해요",
        "만들어봐요",
        "힌트",
        "도전해요",
        "레이스",
    )
    return any(k in t for k in keys) and len(t) < 80


def activity_head(t: str) -> str | None:
    """긴 문단 앞머리의 활동 제목을 뽑는다."""
    first = re.split(r"(?<=[.!?。])\s+|(?<=요)\s+(?=[가-힣A-Z*「])", t.strip(), maxsplit=1)[
        0
    ].strip()
    if not first:
        return None
    if is_activity_title(first) or is_activity_title(t[:80]):
        return first[:70]
    return None


def looks_like_step(t: str) -> bool:
    if is_activity_title(t) or "힌트" in t:
        return False
    return bool(
        re.search(r"(해보세요|해봐요|조립해요|분리해요|비교해봐요|찾아보세요|시도해보세요|승리해요)", t)
    )


def pick_image(blocks: list[Block], prefer: tuple[str, ...] = ()) -> str:
    images = [b.src for b in blocks if b.type in ("banner", "image") and b.src]
    if prefer:
        for img in images:
            if any(p in img for p in prefer):
                return img
    return images[0] if images else ""


def clip_bubble(text: str, limit: int = 220) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def materials_from_texts(texts: list[str]) -> list[str]:
    mats: list[str] = []
    patterns = (
        r"자석소마큐브",
        r"소마큐브",
        r"퍼즐미션\s*큐블로\s*\d*단계?",
        r"퍼즐미션카드\s*[0-9]+[A-Z]+",
        r"미션카드\s*[0-9]+[A-Z]+",
    )
    for t in texts:
        for pat in patterns:
            for m in re.findall(pat, t):
                m = clean_text(m)
                if m and m not in mats:
                    mats.append(m)
    return mats[:6]


def goals_from_pages(title: str, pages: list[Page]) -> list[str]:
    goals: list[str] = []
    for p in pages:
        sec = p.section
        if "영상" in sec:
            goals.append("인터랙티브 영상으로 퍼즐미션에 도전한다.")
        elif "연계" in sec or "활동" in sec or "게임" in sec:
            goals.append(f"「{sec}」에서 배운 내용을 응용·놀이한다.")
        elif "탐색" in sec or "생각" in sec:
            goals.append(f"「{sec}」로 개념을 탐색한다.")
        elif "학습" in sec:
            goals.append(f"「{sec}」내용을 익힌다.")
        elif "마무리" in sec:
            goals.append("오늘 수업을 회상하고 생각을 나눈다.")
    if not goals:
        goals = [f"「{title}」 수업 목표를 달성한다."]
    # 중복 제거
    uniq: list[str] = []
    for g in goals:
        if g not in uniq:
            uniq.append(g)
    return uniq[:4]


def build_stage(
    *,
    label: str,
    index: int,
    stype: str,
    title: str,
    bubble: str,
    teacher_talk: str,
    image: str = "",
    video_url: str = "",
    materials: list[str] | None = None,
    discussion_pages: list[dict] | None = None,
    play_pages: list[dict] | None = None,
    closing_pages: list[dict] | None = None,
    homework: str = "",
) -> dict[str, Any]:
    stage: dict[str, Any] = {
        "label": label,
        "displayName": f"{index:02d} {label}",
        "type": stype,
        "title": title,
        "bubble": bubble,
        "teacherTalk": teacher_talk,
        "resources": [],
    }
    if image:
        stage["image"] = image
    if video_url:
        stage["videoUrl"] = video_url
    if materials:
        stage["materials"] = materials
    if discussion_pages:
        stage["discussionPages"] = discussion_pages
    if play_pages:
        stage["playPages"] = play_pages
    if closing_pages:
        stage["closingPages"] = closing_pages
    if homework:
        stage["homework"] = homework
    return stage


def expand_videoish_page(page: Page, start_index: int) -> list[dict[str, Any]]:
    """영상 토픽에 환영+질문이 섞여 있으면 intro/discussion/video로 분리."""
    blocks = page.blocks
    texts = [b.text for b in blocks if b.type == "text" and b.text]
    h5ps = [b.src for b in blocks if b.type == "h5p" and b.src]
    stages: list[dict[str, Any]] = []
    idx = start_index

    welcome = next((t for t in texts if is_welcome_text(t)), "")
    question_bits: list[str] = []
    for t in texts:
        if is_welcome_text(t) or is_video_cue(t):
            continue
        if is_question_text(t) or "소마큐브" in t or "블럭" in t or "기대" in t or "출발" in t:
            question_bits.extend(split_sentences(t))

    # 중복·잡음 정리
    q_pages: list[str] = []
    for q in question_bits:
        if is_noise_text(q) or is_video_cue(q):
            continue
        if q not in q_pages:
            q_pages.append(q)

    if welcome:
        stages.append(
            build_stage(
                label="수업 소개",
                index=idx,
                stype="intro",
                title=page.title or "수업 소개",
                bubble=clip_bubble(welcome),
                teacher_talk="인사 후 오늘 수업의 흐름을 짧게 안내하세요.",
                image=pick_image(blocks, ("소개", "반가워요", "수업")),
                materials=materials_from_texts(texts),
            )
        )
        idx += 1

    if q_pages:
        stages.append(
            build_stage(
                label="생각나누기",
                index=idx,
                stype="discussion",
                title="함께 이야기해요",
                bubble=q_pages[0],
                teacher_talk="질문에 자유롭게 답하게 한 뒤 영상으로 연결하세요.",
                image=pick_image(blocks, ("반가워요", "소개")),
                discussion_pages=[
                    {"bubble": q, "teacherTalk": "아이 응답을 들어주세요."} for q in q_pages[:8]
                ],
            )
        )
        idx += 1

    if h5ps or "영상" in page.section:
        cue = next((t for t in texts if is_video_cue(t)), "준비된 친구들은 영상을 플레이 해주세요.")
        stages.append(
            build_stage(
                label=page.section if "영상" in page.section else "영상 학습",
                index=idx,
                stype="video",
                title=page.section,
                bubble=clip_bubble(cue),
                teacher_talk="인터랙티브 영상을 함께 보며 미션에 참여하게 하세요.",
                image=pick_image(blocks, ("인터렉티브", "영상", "소개하기")),
                video_url=h5ps[0] if h5ps else "",
            )
        )
    return stages


def expand_play_page(page: Page, start_index: int) -> list[dict[str, Any]]:
    blocks = page.blocks
    texts = [b.text for b in blocks if b.type == "text" and b.text]
    # 섹션 배너(활동하기_수정 등) 제외하고 교구 이미지 우선
    images = [
        b.src
        for b in blocks
        if b.type in ("banner", "image")
        and b.src
        and not re.search(r"활동하기_수정|안내_수정", b.src)
    ]
    if not images:
        images = [b.src for b in blocks if b.type in ("banner", "image") and b.src]

    intro = texts[0] if texts else page.section
    rest = texts[1:] if len(texts) > 1 else []

    play_pages: list[dict[str, Any]] = []
    current_title = page.title or page.section
    current_bubble = ""
    current_steps: list[str] = []
    current_image = ""
    img_i = 0
    started = False

    def take_image() -> str:
        nonlocal img_i
        if img_i < len(images):
            src = images[img_i]
            img_i += 1
            return src
        return images[-1] if images else ""

    def flush() -> None:
        nonlocal current_title, current_bubble, current_steps, current_image, started
        if not started and not (current_bubble or current_steps):
            return
        if not (current_bubble or current_steps):
            return
        steps = [s for s in current_steps if s and s != current_bubble][:6]
        play_pages.append(
            {
                "title": current_title.lstrip("* ").strip(),
                "bubble": current_bubble or current_title,
                "image": current_image,
                "hideGuide": True,
                "steps": steps or [current_bubble or "활동을 진행해 보세요."],
                "teacherTalk": f"「{current_title}」활동을 진행하세요.",
                "materials": materials_from_texts([current_title, current_bubble] + current_steps),
            }
        )
        current_bubble = ""
        current_steps = []
        current_image = ""
        started = False

    def start_activity(title: str, bubble: str | None = None) -> None:
        nonlocal current_title, current_bubble, current_image, started
        flush()
        current_title = title.lstrip("* ").strip().rstrip(".")
        current_bubble = (bubble or title).strip()
        current_image = take_image()
        started = True

    for t in rest:
        if "힌트" in t:
            start_activity("힌트", "천천히 다시 도전해봐요!")
            current_steps = [x for x in split_sentences(t) if "힌트" not in x] or [
                "힌트 그림을 보고 다시 도전해보세요."
            ]
            if images:
                current_image = images[-1]
            continue

        head = activity_head(t)
        parts = split_sentences(t)

        if is_activity_title(t) and len(t) < 80:
            start_activity(t)
            continue

        if head:
            start_activity(head, head)
            for p in parts[1:]:
                if p != head:
                    current_steps.append(p)
            continue

        # 이미 활동 중이면 지시문을 steps로 이어붙임
        if started and (looks_like_step(t) or len(parts) >= 2):
            for p in parts:
                current_steps.append(p)
            continue

        for p in parts:
            if not started:
                start_activity(p)
            else:
                current_steps.append(p)

    flush()

    if not play_pages:
        play_pages = [
            {
                "title": page.title or page.section,
                "bubble": intro,
                "image": images[0] if images else "",
                "hideGuide": True,
                "steps": split_sentences(" ".join(texts[1:]))[:6] or ["활동을 진행해 보세요."],
                "teacherTalk": f"「{page.section}」내용을 지도하세요.",
            }
        ]

    return [
        build_stage(
            label=page.section,
            index=start_index,
            stype="play",
            title=page.section,
            bubble=clip_bubble(intro),
            teacher_talk="배운 내용을 응용하고 게임을 진행하세요.",
            image=pick_image(blocks, ("활동하기", "교구활동")),
            play_pages=play_pages[:6],
        )
    ]


def expand_closing_page(page: Page, start_index: int) -> list[dict[str, Any]]:
    blocks = page.blocks
    texts = [b.text for b in blocks if b.type == "text" and b.text]
    recall = next((t for t in texts if not is_question_text(t)), texts[0] if texts else "오늘 정말 잘했어요!")
    ask = next((t for t in texts if is_question_text(t)), "오늘 수업에 대한 생각을 말해주세요.")

    closing_pages: list[dict[str, Any]] = [
        {
            "displayName": f"{start_index:02d} 회상하기",
            "title": "오늘 정말 잘했어요!",
            "bubble": clip_bubble(recall),
            "teacherTalk": "오늘 한 활동을 짧게 회상하게 하세요.",
            "isClosingFinale": True,
        }
    ]

    quizzes = page.quizzes or []
    for i, q in enumerate(quizzes[:4]):
        closing_pages.append(
            {
                "displayName": f"{start_index:02d} 평가하기",
                "title": q["question"][:48],
                "bubble": ask if i == 0 else q["question"],
                "quiz": q,
                "teacherTalk": "응답을 확인하세요.",
            }
        )

    if not quizzes:
        for t in texts:
            if is_question_text(t):
                closing_pages.append(
                    {
                        "displayName": f"{start_index:02d} 평가하기",
                        "title": t[:48],
                        "bubble": t,
                        "quiz": {
                            "question": t,
                            "options": ["네", "보통이에요", "아니요"],
                            "correctIndex": 0,
                            "correctFeedback": "고마워요!",
                            "wrongFeedback": "고마워요!",
                        },
                        "teacherTalk": "응답을 확인하세요.",
                    }
                )

    homework = "부모님·친구들과 오늘 배운 활동을 다시 해보세요."
    for t in texts:
        if "부모님" in t or "가정" in t or "대결" in t:
            homework = t
            break

    closing_pages.append(
        {
            "displayName": f"{start_index:02d} Bye!",
            "title": "다음 시간에 또 만나요",
            "bubble": "오늘 수업에 열심히 참여한 친구들, 고마워요!\n그럼 다음 시간에 또 만나요.",
            "teacherTalk": "가정연계를 안내하며 마무리합니다.",
            "isClosingFinale": True,
            "homework": homework,
        }
    )

    return [
        build_stage(
            label=page.section,
            index=start_index,
            stype="closing",
            title=page.section,
            bubble=clip_bubble(recall),
            teacher_talk="오늘 활동을 회상한 뒤 생각을 나누고 마무리하세요.",
            image=pick_image(blocks, ("회상", "평가", "정리")),
            closing_pages=closing_pages,
            homework=homework,
        )
    ]


def append_h5p_stages(
    stages: list[dict[str, Any]],
    *,
    section: str,
    h5ps: list[str],
    start_index: int,
) -> int:
    """본문 단계 뒤에 H5P를 영상 단계로 붙인다."""
    idx = start_index
    for n, url in enumerate(h5ps[:4], start=1):
        label = section if len(h5ps) == 1 else f"{section} · 영상{n}"
        stages.append(
            build_stage(
                label=label,
                index=idx,
                stype="video",
                title=label,
                bubble="준비된 친구들은 영상을 플레이 해주세요.",
                teacher_talk="인터랙티브 활동을 함께 진행하세요.",
                video_url=url,
            )
        )
        idx += 1
    return idx


def pages_to_stages(pages: list[Page]) -> list[dict[str, Any]]:
    stages: list[dict[str, Any]] = []
    idx = 1

    for page in pages:
        section = page.section
        blocks = page.blocks
        texts = [b.text for b in blocks if b.type == "text" and b.text]
        h5ps = [b.src for b in blocks if b.type == "h5p" and b.src]

        # 레슨 랜딩
        if section == "차시 안내":
            useful = [
                t
                for t in texts
                if not is_noise_text(t) and not any(m in t for m in META_TXT)
            ]
            if not useful:
                continue
            stages.append(
                build_stage(
                    label="차시 안내",
                    index=idx,
                    stype="intro",
                    title=page.title or section,
                    bubble=clip_bubble(useful[0]),
                    teacher_talk="오늘 수업 목표와 준비물을 안내하세요.",
                    image=pick_image(blocks),
                    materials=materials_from_texts(texts),
                )
            )
            idx += 1
            continue

        # 영상 학습 토픽만 환영/질문/영상으로 분리
        if "영상" in section:
            built = expand_videoish_page(page, idx)
            if built and built[0]["type"] == "intro":
                stages = [s for s in stages if s["type"] != "intro"]
            stages.extend(built)
            idx += len(built)
            continue

        if page.kind == "quiz" or "마무리" in section or "평가" in section:
            built = expand_closing_page(page, idx)
            stages.extend(built)
            idx += len(built)
            continue

        if any(k in section for k in ("활동", "게임", "만들기", "놀이", "학습", "탐색")):
            # 탐색/학습은 discussion, 활동/게임은 play
            if any(k in section for k in ("탐색", "생각", "학습")) and not any(
                k in section for k in ("게임", "놀이")
            ):
                pages_list: list[str] = []
                for t in texts:
                    pages_list.extend(split_sentences(t))
                pages_list = [p for p in pages_list if not is_noise_text(p)][:12]
                # 환영 문장이면 intro로 승격(아직 intro 없을 때)
                if pages_list and is_welcome_text(pages_list[0]) and not any(
                    s.get("type") == "intro" for s in stages
                ):
                    stages.append(
                        build_stage(
                            label="수업 소개",
                            index=idx,
                            stype="intro",
                            title=page.title or section,
                            bubble=clip_bubble(pages_list[0]),
                            teacher_talk="오늘 수업 흐름을 안내하세요.",
                            image=pick_image(blocks),
                            materials=materials_from_texts(texts),
                        )
                    )
                    idx += 1
                    pages_list = pages_list[1:]
                if pages_list:
                    stages.append(
                        build_stage(
                            label=section,
                            index=idx,
                            stype="discussion",
                            title=page.title or section,
                            bubble=pages_list[0],
                            teacher_talk=f"「{section}」내용을 함께 살펴보세요.",
                            image=pick_image(blocks),
                            materials=materials_from_texts(texts),
                            discussion_pages=[
                                {"bubble": p, "teacherTalk": "아이 응답을 들어주세요."}
                                for p in pages_list
                            ],
                        )
                    )
                    idx += 1
                idx = append_h5p_stages(stages, section=section, h5ps=h5ps, start_index=idx)
            else:
                built = expand_play_page(page, idx)
                stages.extend(built)
                idx += len(built)
                idx = append_h5p_stages(stages, section=section, h5ps=h5ps, start_index=idx)
            continue

        # 기타
        pages_list = []
        for t in texts:
            pages_list.extend(split_sentences(t))
        pages_list = [p for p in pages_list if not is_noise_text(p)][:10]
        stages.append(
            build_stage(
                label=section,
                index=idx,
                stype="discussion",
                title=page.title or section,
                bubble=pages_list[0] if pages_list else section,
                teacher_talk=f"「{section}」내용을 지도하세요.",
                image=pick_image(blocks),
                discussion_pages=[
                    {"bubble": p, "teacherTalk": "아이 응답을 들어주세요."} for p in pages_list
                ]
                if pages_list
                else None,
            )
        )
        idx += 1
        idx = append_h5p_stages(stages, section=section, h5ps=h5ps, start_index=idx)

    # displayName 재번호
    for i, s in enumerate(stages, start=1):
        label = s.get("label") or s.get("title") or f"단계 {i}"
        s["displayName"] = f"{i:02d} {label}"
        if s.get("type") == "closing" and s.get("closingPages"):
            for cp in s["closingPages"]:
                if cp.get("displayName", "").endswith("회상하기"):
                    cp["displayName"] = f"{i:02d} 회상하기"
                elif "평가" in cp.get("displayName", ""):
                    cp["displayName"] = f"{i:02d} 평가하기"
                elif "Bye" in cp.get("displayName", ""):
                    cp["displayName"] = f"{i:02d} Bye!"

    return stages


def convert_lesson(lesson_url: str) -> dict[str, Any]:
    html = fetch(lesson_url)
    title, course, items = find_lesson_items(lesson_url, html)

    pages: list[Page] = []
    logs: list[str] = []

    intro_blocks = [
        b
        for b in extract_blocks_from_html(html)
        if b.type in ("text", "banner", "image")
    ][:16]
    if intro_blocks:
        pages.append(Page(section="차시 안내", title=title, kind="lesson", blocks=intro_blocks))

    for it in items:
        logs.append(f"수집: {it['title']}")
        try:
            sub_html = fetch(it["url"])
        except Exception as exc:  # noqa: BLE001
            logs.append(f"실패: {it['title']} ({exc})")
            continue
        blocks = extract_blocks_from_html(sub_html)
        quizzes = extract_wp_quizzes(sub_html) if it["kind"] == "quiz" else []
        pages.append(
            Page(
                section=it["title"],
                title=it["title"],
                kind=it["kind"],
                blocks=blocks,
                quizzes=quizzes,
            )
        )
        if quizzes:
            logs.append(f"퀴즈 {len(quizzes)}문항: {it['title']}")

    stages = pages_to_stages(pages)
    block_pages = pages_to_block_pages(pages)

    # 인트로 준비물: 전체 페이지에서 보강
    all_texts: list[str] = []
    for p in pages:
        all_texts.extend(b.text for b in p.blocks if b.type == "text" and b.text)
    mats = materials_from_texts(all_texts)
    for s in stages:
        if s.get("type") == "intro":
            merged = list(dict.fromkeys((s.get("materials") or []) + mats))
            if merged:
                s["materials"] = merged[:6]
            break

    return {
        "mode": "blocks",
        "level": course or "크레용스쿨",
        "title": title,
        "sourceUrl": lesson_url,
        "expression": "",
        "characterImages": {"intro": "", "thinking": "", "guide": ""},
        "goals": goals_from_pages(title, pages),
        "materials": mats[:8],
        "pages": block_pages,
        "stages": stages,
        "meta": {
            "sections": [p.section for p in pages],
            "logs": logs,
            "pageCount": len(block_pages),
            "topicCount": len(pages),
            "itemCount": len(items),
            "stageTypes": [s.get("type") for s in stages],
        },
    }
