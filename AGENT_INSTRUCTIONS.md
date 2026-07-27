# Cursor 에이전트 지시 (Teams / Cloud)

실무자가 크레용스쿨 **차시 링크**를 주면 아래만 수행한다.

**산출물 = 블록형 HTML (`preview.html`). PR만 주고 끝내지 마라.**

## 입력

- `https://crayonschool.co.kr/lessons/...` URL 1개 (필수)
- (선택) H5P embed URL 목록 — 있으면 참고만, 보통 링크만으로 수집됨

## 할 일

```bash
pip install -r requirements.txt
python -c "
from pathlib import Path
import json, re
from converter import convert_lesson
import app

url = '''PASTE_URL_HERE'''
d = convert_lesson(url)
title = d.get('title') or 'lesson'
slug = re.sub(r'[^a-zA-Z0-9_-]+', '-', title).strip('-')[:40].lower() or 'lesson'
folder = Path('lessons') / 'previews' / slug
folder.mkdir(parents=True, exist_ok=True)
html = app.build_html(d)  # block_shell
out = folder / 'preview.html'
out.write_text(html, encoding='utf-8')
(folder / 'meta.json').write_text(
    json.dumps({
        'title': d.get('title'), 'level': d.get('level'), 'sourceUrl': d.get('sourceUrl'),
        'mode': d.get('mode'), 'pageCount': len(d.get('pages') or []),
    }, ensure_ascii=False, indent=2),
    encoding='utf-8')
print(out.as_posix())
"
```

답변 **맨 위**:

```text
✅ 미리보기 HTML
Raw: https://github.com/ABE0402/Lesson-Plan-Generator/raw/<브랜치>/lessons/previews/<slug>/preview.html
Blob: https://github.com/ABE0402/Lesson-Plan-Generator/blob/<브랜치>/lessons/previews/<slug>/preview.html
```

## 하지 말 것

- 소개/생각나누기/활동 5막으로 재구성
- localhost 스크린샷만 주고 HTML 링크 생략
- 차시 문장 창작
