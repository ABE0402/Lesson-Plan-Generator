# Cursor 에이전트 지시 (Teams / Cloud)

실무자가 크레용스쿨 **차시 링크**를 주면 아래만 수행한다.

**산출물 = 블록형 HTML (`preview.html`) + 이미지 assets (GitHub Raw 절대 URL).**  
PR만 주고 끝내지 마라.

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
from offline_images import offline_lesson_data, github_raw_url
import app

url = '''PASTE_URL_HERE'''
d = convert_lesson(url)
title = d.get('title') or 'lesson'
slug = re.sub(r'[^\w\-가-힣]+', '-', title).strip('-')[:40] or 'lesson'
folder = Path('lessons') / 'previews' / slug
folder.mkdir(parents=True, exist_ok=True)

# 이미지를 받아 GitHub Raw 절대 URL로 치환 (원본 미디어 의존 제거)
prefix = f'lessons/previews/{slug}'
d = offline_lesson_data(d, folder, repo_prefix=prefix)

html = app.build_html(d)  # block_shell
out = folder / 'preview.html'
out.write_text(html, encoding='utf-8')
(folder / 'meta.json').write_text(
    json.dumps({
        'title': d.get('title'), 'level': d.get('level'), 'sourceUrl': d.get('sourceUrl'),
        'mode': d.get('mode'), 'pageCount': len(d.get('pages') or []),
        'imagesOffline': True,
    }, ensure_ascii=False, indent=2),
    encoding='utf-8')
print(out.as_posix())
print(github_raw_url(prefix + '/preview.html'))
"
```

변경분을 커밋·푸시한 뒤, 답변 **맨 위**:

```text
✅ 미리보기 HTML (이미지=GitHub Raw, H5P=원본 embed 유지)
Raw: https://github.com/ABE0402/Lesson-Plan-Generator/raw/main/lessons/previews/<slug>/preview.html
Blob: https://github.com/ABE0402/Lesson-Plan-Generator/blob/main/lessons/previews/<slug>/preview.html
```

실무자는 **Raw HTML 링크만** 연다. 이미지 src는 `raw.githubusercontent.com/...` 절대경로라서 Raw로 열어도 보인다.

## 하지 말 것

- 소개/생각나누기/활동 5막으로 재구성
- localhost 스크린샷만 주고 HTML 링크 생략
- 차시 문장 창작
- 이미지를 상대경로만 넣고 Raw로 열게 하기 (깨짐)

편집은 Azure/로컬 **`/edit`** 에서 한다. 이 단계에서는 HTML Raw 링크를 반드시 준다.
