@echo off
chcp 65001 > nul
echo ==================================
echo   ビジュアル漢字クイズ 起動中...
echo ==================================
echo.

cd /d "%~dp0"

:: ── Python 3.10+ を確認 ──────────────────────────────────
python --version > nul 2>&1
if errorlevel 1 (
    echo Python が見つかりません。
    echo https://www.python.org からインストールしてください。
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python -c "import sys; print(sys.version_info >= (3,10))"') do set PYOK=%%i
if "%PYOK%" neq "True" (
    echo Python 3.10 以上が必要です。
    echo 現在のバージョン:
    python --version
    pause
    exit /b 1
)

:: ── 初回セットアップ ─────────────────────────────────────
if not exist ".venv" (
    echo.
    echo [初回セットアップ] 仮想環境を作成中...
    python -m venv .venv
    echo [初回セットアップ] ライブラリをインストール中...
    .venv\Scripts\pip install --upgrade pip -q
    .venv\Scripts\pip install -e . -q
    echo [初回セットアップ] 完了
)

if not exist ".venv\installed_marker" (
    echo ライブラリを確認中...
    .venv\Scripts\pip install -e . -q
    echo. > .venv\installed_marker
)

echo.
echo アプリを起動中... ブラウザが自動で開きます
echo 終了するには このウィンドウを閉じてください
echo.

.venv\Scripts\python app.py
