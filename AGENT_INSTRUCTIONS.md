# Cursor 에이전트 지시 (Teams / Cloud)

실무자가 크레용스쿨 **차시 링크** 또는 **레포 안의 링크 목록(CSV/엑셀)** 을 주면 아래만 수행한다.

**중요:** Teams 채팅 첨부·PC 로컬 경로(`Downloads` 등)는 클라우드 워크스페이스에 **안 들어온다.**  
일괄 변환은 **이 GitHub 레포에 커밋된 파일**만 사용한다.

**산출물 = 블록형 HTML (`<차시제목>.html`) + 이미지 assets (GitHub Raw 절대 URL).**  
파일명은 `preview.html`이 아니라 차시 제목이다.  
예: `3차시-고-구-그를-배워요.html`  
PR만 주고 끝내지 마라.

## 입력 (둘 중 하나)

### A) 단건
- `https://crayonschool.co.kr/lessons/...` URL **1개** (채팅에 붙여도 됨)

### B) 레포 CSV/엑셀 일괄
- 기본 목록: `lessons/8월_사용_교안.csv`
- 또는 레포에 있는 다른 `.csv` / `.xlsx`
- (선택) “지혜큐브만”, “플라팜만” → `--course`
- (선택) “앞에서 5개만” → `--limit N`

채팅에만 파일을 첨부했다고 해서 변환을 중단하거나, 이전 런 트랜스크립트를 뒤지지 마라.  
파일이 없으면 **`lessons/8월_사용_교안.csv`가 있는지 먼저 확인**하고, 없으면 실무자에게 “레포에 CSV를 올려 달라”고 짧게 안내한다.

## 할 일

```bash
pip install -r requirements.txt
```

### A) 단건

```bash
python batch_preview.py --url 'PASTE_URL_HERE'
```

### B) CSV (권장)

```bash
python batch_preview.py --csv 'lessons/8월_사용_교안.csv'
python batch_preview.py --csv 'lessons/8월_사용_교안.csv' --course '플라팜'
python batch_preview.py --csv 'lessons/8월_사용_교안.csv' --limit 10
```

### B') 엑셀 (레포에 있을 때만)

```bash
python batch_preview.py --xlsx 'lessons/파일명.xlsx'
```

스크립트가 JSON으로 성공·실패·Raw URL·`htmlFile`을 출력한다.  
**한 번에 15개 초과**면 `--limit`으로 나눠 돌리고, 실패 건은 재시도한다.

### 배포 (Raw 404 방지 — 필수)

생성된 `lessons/previews/<slug>/` 를 **`main`에 올린 뒤에만** Raw 링크를 준다.

1. **가능하면 `main`에 직접 커밋·푸시**한다. (에이전트 브랜치만 남기고 PR만 열면 실무자 Raw는 404가 난다.)
2. 브랜치/PR로만 작업했다면 **`main`에 머지·푸시가 끝난 뒤**에만 답한다.
3. Raw URL의 브랜치는 반드시 **`main`** 이다. 파일이 `main`에 없는데 `/main/...` 링크를 만들지 마라.
4. 답변 전에 한 건이라도 Raw URL을 열어(또는 `curl -I`) **200**인지 확인한다. 404면 푸시/머지부터 고친다.

그다음 답변 **맨 위**:

### 단건 답변 형식

```text
✅ 미리보기 HTML (이미지=GitHub Raw, H5P=원본 embed 유지)
파일: 3차시-고-구-그를-배워요.html
Raw: https://github.com/ABE0402/Lesson-Plan-Generator/raw/main/lessons/previews/<slug>/<차시제목>.html
Blob: https://github.com/ABE0402/Lesson-Plan-Generator/blob/main/lessons/previews/<slug>/<차시제목>.html
```

### 일괄 답변 형식

```text
✅ 미리보기 N건 완료 / 실패 M건

| 차시 | 파일 | Raw |
|------|------|-----|
| (title) | (htmlFile) | https://github.com/.../lessons/previews/<slug>/<차시제목>.html |

실패:
- (url) — (error)
```

실무자는 **Raw HTML 링크만** 연다.

## 하지 말 것

- 소개/생각나누기/활동 5막으로 재구성
- localhost 스크린샷만 주고 HTML 링크 생략
- 차시 문장 창작
- 이미지를 상대경로만 넣고 Raw로 열게 하기 (깨짐)
- 채팅 첨부가 안 보인다고 이전 에이전트 기록만 길게 탐색하기
- 필터/limit 없이 목록을 받았는데 첫 링크 1개만 변환하고 끝내기
- 산출물 파일명을 `preview.html`로 남기기
- PR/에이전트 브랜치에만 올리고 **`main` Raw 링크를 먼저 주기** (실무자 404)
- “커밋했다”고만 하고 `main` 푸시·머지·Raw 200 확인을 생략하기

편집(`/edit`)은 **Lesson-Editor** 레포에서 한다. 이 Generator 레포·Teams Cursor는 변환만 한다.  
이 단계에서는 **`main`에 올라간** HTML Raw 링크를 반드시 준다.

`block_shell.html`을 고치면 Editor 쪽에서 `python scripts/sync_player.py`로 맞춰야 한다.
