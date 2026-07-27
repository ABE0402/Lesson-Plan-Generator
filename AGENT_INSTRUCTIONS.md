# Cursor 에이전트 지시 (Teams / Cloud)

실무자가 크레용스쿨 레슨 링크를 주면 아래만 수행한다.

## 입력

- `https://crayonschool.co.kr/lessons/...` URL 1개
- (선택) 수정 요청 문구

## 할 일

1. `교안변환툴` 디렉터리에서:

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
safe = re.sub(r'[\\\\/:*?\"<>|]+', '_', title)
safe = re.sub(r'\\s+', '_', safe).strip('._')[:60] or 'lesson'
folder = Path('lessons') / safe
folder.mkdir(parents=True, exist_ok=True)
html = app.build_html(d, shell='crayon')
out = folder / '미리보기_크레용형.html'
out.write_text(html, encoding='utf-8')
(folder / 'lesson_meta.json').write_text(
    json.dumps({'title': d.get('title'), 'level': d.get('level'), 'sourceUrl': d.get('sourceUrl'),
                'stages': [{'type': s.get('type'), 'label': s.get('label')} for s in d.get('stages', [])]},
               ensure_ascii=False, indent=2),
    encoding='utf-8')
print(out.resolve())
"
```

2. URL의 `PASTE_URL_HERE`를 실제 링크로 바꿔 실행한다.
3. 생성된 `미리보기_크레용형.html` 경로를 사용자에게 알려 주고, 가능하면 파일을 첨부·커밋·PR한다.
4. 차시 문장을 창작하거나 Custom GPT 카드를 요구하지 않는다. 링크만으로 `convert_lesson`을 쓴다.
5. JSON/HTML 구조를 설명하지 말고, **미리보기 파일**만 전달한다.

## 하지 말 것

- 다른 차시 내용으로 메우기
- 플레이어 디자인을 새로 만들기
- 불필요한 리팩터·문서 장문 작성
