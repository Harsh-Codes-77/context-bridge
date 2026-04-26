#!/bin/bash

set -euo pipefail

echo "🔧 Installing context-bridge..."

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$INSTALL_DIR/venv"
CB_BIN="$VENV_DIR/bin/cb"

if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python3 not found. Please install Python 3.9+"
    exit 1
fi

if ! python3 - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 9) else 1)
PY
then
    PYVER=$(python3 --version 2>&1 | awk '{print $2}')
    echo "❌ Python 3.9+ required, found $PYVER"
    exit 1
fi

echo "📦 Creating virtual environment (if missing)..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "⬇️  Installing dependencies..."
python -m pip install --upgrade pip setuptools wheel >/dev/null
python -m pip install -e "$INSTALL_DIR"

SHELL_RC="$HOME/.bashrc"
case "${SHELL:-}" in
    */zsh)
        SHELL_RC="$HOME/.zshrc"
        ;;
    */bash)
        if [ "$(uname -s)" = "Darwin" ]; then
            SHELL_RC="$HOME/.bash_profile"
        else
            SHELL_RC="$HOME/.bashrc"
        fi
        ;;
    *)
        SHELL_RC="$HOME/.profile"
        ;;
esac

if ! grep -q "context-bridge" "$SHELL_RC" 2>/dev/null; then
    {
        echo ""
        echo "# context-bridge"
        echo "alias cb='$CB_BIN'"
    } >> "$SHELL_RC"
    echo "✅ Added cb alias to $SHELL_RC"
else
    echo "✅ cb alias already present in $SHELL_RC"
fi

if "$CB_BIN" --help >/dev/null 2>&1; then
    echo "✅ Installation health-check passed"
else
    echo "⚠️  cb installed but health-check failed; run '$CB_BIN --help' manually"
fi

echo ""
echo "✅ context-bridge installed successfully!"
echo ""
echo "Next steps:"
echo "1. source $SHELL_RC"
echo "2. cb init"
echo "3. cb status"
