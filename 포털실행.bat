@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  교안 변환 툴을 시작합니다...
echo  링크 변환:     http://127.0.0.1:5055
echo  담당자 데스크: http://127.0.0.1:5055/desk
echo  블록 편집기:   Lesson-Editor 레포 (별도)
echo  종료하려면 이 창을 닫으세요.
echo.
start "" http://127.0.0.1:5055
python app.py
pause
