# 교안변환툴 (Lesson-Plan-Generator)

크레용스쿨 차시 **링크** → 디지털 교안 **HTML 미리보기** (Teams Cursor / `batch_preview`).

**편집기(`/edit`)는 별도 레포:** `Lesson-Editor`  
**플레이어 원본:** 이 레포의 `block_shell.html` (Editor는 `scripts/sync_player.py`로 동기화)

## 운영 흐름 (권장)

1. 실무자가 Teams에 **차시 링크 1개** 또는 레포 CSV를 준다.
2. `@Cursor`가 `batch_preview.py`로 변환(이미지 → **GitHub Raw**) → `<차시제목>.html`
3. 답변 맨 위에 Raw 링크를 준다.
4. 편집이 필요하면 **Lesson-Editor**에서 HTML 가져오기 → 저장 → HTML 받기.

에이전트 지시: `AGENT_INSTRUCTIONS.md`

## 로컬 (변환 UI만)

```bash
pip install -r requirements.txt
python app.py
# http://127.0.0.1:5055
# /desk 카드 변환
```

`포털실행.bat`

## 폴더

| 경로 | 용도 |
|------|------|
| `converter.py` | 링크 수집·단계 구성 |
| `offline_images.py` | 이미지 → GitHub Raw |
| `batch_preview.py` | Teams용 단건/일괄 변환 |
| `lesson_normalize.py` | pages/blocks 정규화 |
| `block_shell.html` | **플레이어 원본 (SoT)** |
| `crayon_shell.html` | 구 스테이지 플레이어 |
| `lessons/previews/` | 미리보기 HTML + assets |
| `lessons/_양식/` | 카드 빈 양식 |

편집·workspace는 Generator에 두지 않는다.
