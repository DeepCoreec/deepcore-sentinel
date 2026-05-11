@echo off
echo ========================================
echo  DeepCore Sentinel - Build
echo ========================================

pip install -r requirements.txt
pip install pyinstaller

pyinstaller ^
  --windowed ^
  --onedir ^
  --noconfirm ^
  --name "DeepCore Sentinel" ^
  --add-data "modules;modules" ^
  --hidden-import customtkinter ^
  --hidden-import matplotlib ^
  --hidden-import psutil ^
  --hidden-import watchdog ^
  --hidden-import reportlab ^
  main.py

echo.
echo Build completado en dist/
pause
