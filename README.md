# 교안변환툴

크레용스쿨 차시 **링크** → 디지털 교안 **HTML 미리보기** → **블록 편집기**에서 수정·저장.

차시 내용·목차는 고정하지 않는다. 고정된 것은 플레이어 껍데기(`block_shell.html`)와 변환 파이프뿐이다.

## 운영 흐름 (권장)

1. 실무자가 Teams에 **차시 링크 1개** 또는 **링크가 모인 엑셀(.xlsx)** 을 올린다.
2. `@Cursor`가 `batch_preview.py`로 변환(이미지 다운로드 → **GitHub Raw 절대 URL**) → `preview.html` 생성
3. 답변 맨 위에 Raw 링크(단건) 또는 목록(일괄)을 준다. (실무자는 Raw만 연다)
4. 이미지는 `lessons/previews/<slug>/assets/images/`에 커밋되어 원본 사이트와 무관하게 표시된다. H5P embed는 당분간 원본 유지.

에이전트 지시: `AGENT_INSTRUCTIONS.md`  
미리보기: `lessons/previews/<slug>/preview.html`

### 기존 preview.html만 이미지 오프라인화

```bash
python offline_images.py path/to/preview.html
# → lessons/previews/<제목슬러그>/preview.html + assets/images/
```


## 로컬

```bash
pip install -r requirements.txt
python app.py
# 링크 변환: http://127.0.0.1:5055
# 카드 데스크: http://127.0.0.1:5055/desk
# 블록 편집기: http://127.0.0.1:5055/editor
```

또는 `포털실행.bat`

## 폴더

| 경로 | 용도 |
|------|------|
| `converter.py` | 링크 수집·단계 구성 |
| `offline_images.py` | 이미지 다운로드 → GitHub Raw URL 치환 |
| `card_parser.py` | 수업 카드 → 데이터 (선택) |
| `block_shell.html` | 블록형 플레이어 |
| `crayon_shell.html` | 구 스테이지 플레이어 |
| `workspace.py` | 편집 워크스페이스 저장·파싱 |
| `app.py` / `templates/` / `static/` | 웹 UI·편집기 |
| `lessons/previews/` | Teams용 미리보기 HTML + 이미지 assets |
| `lessons/workspace/` | 편집 저장본 |
| `lessons/_양식/` | 카드 빈 양식 (선택) |

`lessons/previews/` 산출물은 GitHub에 커밋한다 (실무자 Raw 링크용).
