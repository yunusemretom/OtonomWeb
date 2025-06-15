@echo off
REM Windows için otomatik başlatıcı



REM Python yüklü mü kontrol et
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python yüklü değil. Lütfen Python kurun.
    pause
    exit /b 1
)

REM Güncellemeleri kontrol et
python update.py

REM Gerekli paketler yüklü mü kontrol et
python -m pip show PySide6 >nul 2>nul
if %errorlevel% neq 0 (
    echo Gerekli paketler yükleniyor...
    python -m pip install -r requirements.txt
)

REM Uygulamayı başlat
python main4.py
pause