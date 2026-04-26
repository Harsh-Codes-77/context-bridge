#!/bin/bash

# ---------------------------------------------
#   context-bridge - macOS Installer
# ---------------------------------------------

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# Banner
echo ""
echo -e "${CYAN}${BOLD}"
echo " ██████╗ ██████╗ ███╗   ██╗████████╗███████╗██╗  ██╗████████╗      ██████╗ ██████╗ ██╗██████╗  ██████╗ ███████╗"
echo "██╔════╝██╔═══██╗████╗  ██║╚══██╔══╝██╔════╝╚██╗██╔╝╚══██╔══╝     ██╔══██╗██╔══██╗██║██╔══██╗██╔════╝ ██╔════╝"
echo "██║     ██║   ██║██╔██╗ ██║   ██║   █████╗   ╚███╔╝    ██║   █████╗██████╔╝██████╔╝██║██║  ██║██║  ███╗█████╗  "
echo "██║     ██║   ██║██║╚██╗██║   ██║   ██╔══╝   ██╔██╗    ██║   ╚════╝██╔══██╗██╔══██╗██║██║  ██║██║   ██║██╔══╝  "
echo "╚██████╗╚██████╔╝██║ ╚████║   ██║   ███████╗██╔╝ ██╗   ██║         ██████╔╝██║  ██║██║██████╔╝╚██████╔╝███████╗"
echo " ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝   ╚═╝         ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝  ╚═════╝ ╚══════╝"
echo -e "${RESET}"
echo -e "${BOLD}  macOS Installer${RESET}"
echo "  ----------------------------------------"
echo ""

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python_is_compatible() {
    python3 - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 9) else 1)
PY
}

# --- Step 1: Check Python ---------------------------------------------------
echo -e "${BLUE}[1/6]${RESET} Checking Python..."

if command -v python3 &>/dev/null; then
    PYVER=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "  ${GREEN}OK${RESET} Python $PYVER found"
else
    echo -e "  ${RED}ERROR${RESET} Python3 not found"
    echo ""

    # Check if Homebrew is available
    if command -v brew &>/dev/null; then
        echo -e "  ${YELLOW}-> Installing Python via Homebrew...${RESET}"
        brew install python3
    else
        echo -e "  ${YELLOW}-> Homebrew not found either.${RESET}"
        echo "  Please install Python from: https://python.org/downloads"
        echo "  OR install Homebrew first: https://brew.sh"
        exit 1
    fi
fi

if ! python_is_compatible; then
    PYVER=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "  ${RED}ERROR${RESET} Python 3.9+ required, found $PYVER"
    exit 1
fi
echo ""

# --- Step 2: Check pip ------------------------------------------------------
echo -e "${BLUE}[2/6]${RESET} Checking pip..."
if python3 -m pip --version &>/dev/null; then
    echo -e "  ${GREEN}OK${RESET} pip available"
else
    echo -e "  ${YELLOW}-> Installing pip...${RESET}"
    curl https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    python3 /tmp/get-pip.py
fi
echo ""

# --- Step 3: Create Virtual Environment ------------------------------------
echo -e "${BLUE}[3/6]${RESET} Setting up virtual environment..."
if [ -d "$INSTALL_DIR/venv" ]; then
    echo -e "  ${YELLOW}->${RESET} venv already exists, skipping..."
else
    python3 -m venv "$INSTALL_DIR/venv"
    echo -e "  ${GREEN}OK${RESET} Virtual environment created"
fi
echo ""

# --- Step 4: Install context-bridge ----------------------------------------
echo -e "${BLUE}[4/6]${RESET} Installing context-bridge..."
source "$INSTALL_DIR/venv/bin/activate"
python -m pip install --upgrade pip setuptools wheel >/dev/null
python -m pip install -e "$INSTALL_DIR"
echo -e "  ${GREEN}OK${RESET} context-bridge installed"
echo ""

# --- Step 5: Detect shell & add alias --------------------------------------
echo -e "${BLUE}[5/6]${RESET} Configuring shell..."

CB_BIN="$INSTALL_DIR/venv/bin/cb"

# Detect shell config file
if [ "$SHELL" = "/bin/zsh" ] || [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
    SHELL_NAME="zsh"
elif [ "$SHELL" = "/bin/bash" ] || [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bash_profile"   # Mac uses .bash_profile not .bashrc
    SHELL_NAME="bash"
else
    SHELL_RC="$HOME/.profile"
    SHELL_NAME="sh"
fi

echo -e "  ${YELLOW}->${RESET} Detected shell: $SHELL_NAME ($SHELL_RC)"

# Add alias only if not already there
if grep -q "context-bridge" "$SHELL_RC" 2>/dev/null; then
    echo -e "  ${GREEN}OK${RESET} Alias already exists in $SHELL_RC"
else
    echo "" >> "$SHELL_RC"
    echo "# context-bridge" >> "$SHELL_RC"
    echo "alias cb='$CB_BIN'" >> "$SHELL_RC"
    echo -e "  ${GREEN}OK${RESET} Added alias to $SHELL_RC"
fi
echo ""

# --- Step 6: Verify installation --------------------------------------------
echo -e "${BLUE}[6/6]${RESET} Verifying installation..."
if "$CB_BIN" --version &>/dev/null || "$CB_BIN" --help &>/dev/null; then
    echo -e "  ${GREEN}OK${RESET} cb command working"
else
    echo -e "  ${YELLOW}WARN${RESET} cb installed but --version check skipped"
fi
echo ""

# --- Done -------------------------------------------------------------------
echo "  ========================================"
echo -e "  ${GREEN}${BOLD}context-bridge installed successfully!${RESET}"
echo "  ========================================"
echo ""
echo -e "  ${BOLD}Next steps:${RESET}"
echo ""
echo -e "  1. Reload your shell config:"
echo -e "     ${BOLD}source $SHELL_RC${RESET}"
echo ""
echo -e "  2. Set up your API tokens:"
echo -e "     ${BOLD}cb init${RESET}"
echo ""
echo -e "  3. Go to your project and run:"
echo -e "     ${BOLD}cb status${RESET}"
echo ""
echo -e "  4. Open web dashboard:"
echo -e "     ${BOLD}cb web${RESET}  ->  http://localhost:4242"
echo ""
