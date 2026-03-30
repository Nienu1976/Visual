#!/bin/bash
# ========================================================
#  ビジュアル漢字クイズ - macOS ランチャー
#  このファイルをダブルクリックするだけでアプリが起動します
# ========================================================

# スクリプトのディレクトリに移動
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "=================================="
echo "  ビジュアル漢字クイズ 起動中..."
echo "=================================="

# ── Python 3.10+ を探す ──────────────────────────────────
find_python() {
    for py in \
        /opt/homebrew/bin/python3.13 \
        /opt/homebrew/bin/python3.12 \
        /opt/homebrew/bin/python3.11 \
        /opt/homebrew/bin/python3.10 \
        /usr/local/bin/python3.13 \
        /usr/local/bin/python3.12 \
        /usr/local/bin/python3.11 \
        /usr/local/bin/python3.10 \
        python3; do
        if command -v "$py" &>/dev/null; then
            VER=$("$py" -c "import sys; print(sys.version_info >= (3,10))" 2>/dev/null)
            if [ "$VER" = "True" ]; then
                echo "$py"
                return
            fi
        fi
    done
    echo ""
}

PYTHON=$(find_python)

if [ -z "$PYTHON" ]; then
    osascript -e 'display dialog "Python 3.10以上が必要です。\nhttps://www.python.org からインストールしてください。" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

echo "✓ Python: $($PYTHON --version)"

# ── 初回セットアップ（仮想環境の作成） ──────────────────
if [ ! -d ".venv" ]; then
    echo ""
    echo "🔧 初回セットアップを実行中..."
    echo "   （次回以降はすぐに起動します）"
    echo ""
    "$PYTHON" -m venv .venv

    echo "📦 ライブラリをインストール中..."
    .venv/bin/pip install --upgrade pip -q
    .venv/bin/pip install -e . -q

    echo "✓ セットアップ完了"
fi

# ── 依存ライブラリのアップデート確認 ────────────────────
if [ ! -f ".venv/installed_marker" ]; then
    echo "📦 ライブラリを確認中..."
    .venv/bin/pip install -e . -q
    touch .venv/installed_marker
fi

echo ""
echo "🚀 アプリを起動中... ブラウザが自動で開きます"
echo "   終了するには このウィンドウを閉じてください"
echo ""

# ── アプリ起動 ──────────────────────────────────────────
.venv/bin/python app.py
