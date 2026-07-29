# Cursor 에이전트 지시 (Teams / Cloud)

실무자가 크레용스쿨 **차시 링크** 또는 **링크가 모인 엑셀**을 주면 아래만 수행한다.

**산출물 = 블록형 HTML (`preview.html`) + 이미지 assets (GitHub Raw 절대 URL).**  
PR만 주고 끝내지 마라.

## 입력 (둘 중 하나)

### A) 단건
- `https://crayonschool.co.kr/lessons/...` URL **1개**

### B) 엑셀 일괄
- `.xlsx` 파일 (예: `8월 사용 교안.xlsx`)
- 시트 안 어디에든 `crayonschool.co.kr/lessons/...` 링크가 있으면 수집
- (선택) 실무자가 “지혜큐브만”, “플라팜만”처럼 **강좌 필터**를 말하면 `--course`로 좁힌다
- (선택) “앞에서 5개만” 등이면 `--limit N`

(선택) H5P embed URL 목록 — 있으면 참고만, 보통 링크만으로 수집됨

## 할 일

```bash
pip install -r requirements.txt
```

### A) 단건

```bash
python batch_preview.py --url 'PASTE_URL_HERE'
```

### B) 엑셀

```bash
# 첨부/워크스페이스에 있는 엑셀 경로로 교체
python batch_preview.py --xlsx '8월 사용 교안.xlsx'

# 강좌만 / 개수 제한 예시
python batch_preview.py --xlsx '8월 사용 교안.xlsx' --course '플라팜'
python batch_preview.py --xlsx '8월 사용 교안.xlsx' --limit 10
```

스크립트가 JSON으로 성공·실패·Raw URL을 출력한다.  
**한 번에 15개 초과**면 `--limit`으로 나눠 돌리고, 실패 건은 재시도한다.

변경분(생성된 `lessons/previews/<slug>/` 포함)을 **커밋·푸시**한 뒤, 답변 **맨 위**:

### 단건 답변 형식

```text
✅ 미리보기 HTML (이미지=GitHub Raw, H5P=원본 embed 유지)
Raw: https://github.com/ABE0402/Lesson-Plan-Generator/raw/main/lessons/previews/<slug>/preview.html
Blob: https://github.com/ABE0402/Lesson-Plan-Generator/blob/main/lessons/previews/<slug>/preview.html
```

### 일괄 답변 형식

```text
✅ 미리보기 N건 완료 / 실패 M건

| 차시 | Raw |
|------|-----|
| (title) | https://github.com/ABE0402/Lesson-Plan-Generator/raw/main/lessons/previews/<slug>/preview.html |

실패:
- (url) — (error)
```

실무자는 **Raw HTML 링크만** 연다. 이미지 src는 `raw.githubusercontent.com/...` 절대경로라서 Raw로 열어도 보인다.

## 하지 말 것

- 소개/생각나누기/활동 5막으로 재구성
- localhost 스크린샷만 주고 HTML 링크 생략
- 차시 문장 창작
- 이미지를 상대경로만 넣고 Raw로 열게 하기 (깨짐)
- 엑셀을 받았는데 첫 링크 1개만 변환하고 끝내기 (필터/limit 지시가 없으면 **수집된 URL 전부**)

편집은 Azure/로컬 **`/edit`** 에서 한다. 이 단계에서는 HTML Raw 링크를 반드시 준다.
