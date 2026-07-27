# Cursor 에이전트 지시 (Teams / Cloud)

실무자가 크레용스쿨 레슨 링크를 주면 아래만 수행한다.

**최종 산출물은 HTML 파일이다. PR·스크린샷만 주고 끝내지 마라.**

## 입력

- `https://crayonschool.co.kr/lessons/...` URL 1개
- (선택) 수정 요청 문구

## 할 일

1. 의존성 설치 후 변환 실행:

```bash
pip install -r requirements.txt
python -c "
from pathlib import Path
import json, re, hashlib
from converter import convert_lesson
import app

url = '''PASTE_URL_HERE'''
d = convert_lesson(url)
title = d.get('title') or 'lesson'
# Teams/GitHub에서 받기 쉽게 ASCII 폴더명 사용
slug = re.sub(r'[^a-zA-Z0-9_-]+', '-', title).strip('-')[:40] or 'lesson'
slug = slug.lower()
folder = Path('lessons') / 'previews' / slug
folder.mkdir(parents=True, exist_ok=True)
html = app.build_html(d, shell='crayon')
out = folder / 'preview.html'
out.write_text(html, encoding='utf-8')
(folder / 'meta.json').write_text(
    json.dumps({
        'title': d.get('title'),
        'level': d.get('level'),
        'sourceUrl': d.get('sourceUrl'),
        'stages': [{'type': s.get('type'), 'label': s.get('label')} for s in d.get('stages', [])],
    }, ensure_ascii=False, indent=2),
    encoding='utf-8',
)
print(out.as_posix())
"
```

2. `PASTE_URL_HERE`를 실제 링크로 바꾼다.
3. 커밋·푸시(또는 PR)한다.
4. **Teams/채팅 답변 맨 위**에 반드시 아래 형식으로 쓴다 (개발 설명보다 먼저):

```text
✅ 미리보기 HTML
1) 다운로드(Raw): https://github.com/ABE0402/Lesson-Plan-Generator/raw/<브랜치>/lessons/previews/<slug>/preview.html
2) GitHub에서 보기: https://github.com/ABE0402/Lesson-Plan-Generator/blob/<브랜치>/lessons/previews/<slug>/preview.html
   → 페이지에서 Download raw file / Raw 저장

받은 preview.html 을 더블클릭하면 브라우저에서 열립니다.
```

5. PR 링크는 보조로만 적는다. View PR만 안내하고 끝내지 않는다.
6. 차시 문장 창작·카드 양식 요구 금지. `convert_lesson`만 사용.

## 하지 말 것

- localhost 스크린샷만 보여주고 HTML 링크 안 주기
- 다른 차시 내용으로 메우기
- 플레이어 디자인 새로 만들기
- 불필요한 리팩터·장문 설명
