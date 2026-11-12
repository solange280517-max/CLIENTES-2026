@echo off
cd /d "%~dp0"
if not exist venv ( py -3 -m venv venv || (echo Instale Python desde python.org y marque "Add to PATH" & pause & exit /b) )
call venv\Scripts\activate
pip install -q -r requirements.txt
start "" http://127.0.0.1:5000
python app.py
pause
