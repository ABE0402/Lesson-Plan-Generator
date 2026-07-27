# 교안변환툴

크레용스쿨 차시 **링크** → 디지털 교안 **HTML 미리보기**.

차시 내용·목차는 고정하지 않는다. 고정된 것은 플레이어 껍데기(`crayon_shell.html`)와 변환 파이프뿐이다.

## 운영 흐름 (권장)

1. 실무자가 Teams에 **차시 링크**를 올린다. (H5P iframe 복붙은 선택)
2. `@Cursor`가 `convert_lesson` → **블록형** `block_shell.html` 미리보기를 만든다.
3. 답변 맨 위에 `preview.html` Raw 다운로드 링크를 준다.
4. 실무자가 파일로 검수한다.

에이전트 지시: `AGENT_INSTRUCTIONS.md`  
미리보기: `lessons/previews/<slug>/preview.html`

## 로컬 백업

```bash
pip install -r requirements.txt
python app.py
# 링크 변환: http://127.0.0.1:5055
# 카드→미리보기: http://127.0.0.1:5055/desk
```

또는 `포털실행.bat`

## 폴더

| 경로 | 용도 |
|------|------|
| `converter.py` | 링크 수집·단계 구성 |
| `card_parser.py` | 수업 카드 → 데이터 (선택) |
| `crayon_shell.html` | 플레이어 |
| `app.py` / `templates/` | 로컬 웹 UI |
| `lessons/_양식/` | 카드 빈 양식 (선택) |
| `lessons/*/` | 예시 카드·생성물 |

생성 HTML은 repo에 커밋하지 않아도 된다. `.gitignore` 참고.
