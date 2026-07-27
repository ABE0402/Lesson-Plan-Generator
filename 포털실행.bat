@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  교안 변환 툴을 시작합니다...
echo  담당자 데스크: http://127.0.0.1:5055/desk
echo  링크 수집:     http://127.0.0.1:5055
echo  종료하려면 이 창을 닫으세요.
echo.
start "" http://127.0.0.1:5055/desk
python app.py
pause
