#!/bin/bash

# ---------------------------------------------
#   context-bridge - Linux Installer
#   Supports: Ubuntu, Debian, Fedora, Arch
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
echo -e "${BOLD}  Linux Installer${RESET}"
echo "  ----------------------------------------"
echo ""

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python_is_compatible() {
    python3 - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 9) else 1)
PY
}

# --- Detect Linux Distro ----------------------------------------------------
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    elif command -v apt &>/dev/null; then
        echo "debian"
    elif command -v dnf &>/dev/null; then
        echo "fedora"
    elif command -v pacman &>/dev/null; then
        echo "arch"
    else
        echo "unknown"
    fi
}

DISTRO=$(detect_distro)
echo -e "  ${YELLOW}->${RESET} Detected distro: $DISTRO"
echo ""

# --- Step 1: Check and Install Python --------------------------------------
echo -e "${BLUE}[1/6]${RESET} Checking Python..."

if command -v python3 &>/dev/null; then
    PYVER=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "  ${GREEN}OK${RESET} Python $PYVER found"
else
    echo -e "  ${RED}ERROR${RESET} Python3 not found. Installing..."
    case "$DISTRO" in
        ubuntu|debian|linuxmint|pop)
            sudo apt update -qq
            sudo apt install -y python3 python3-pip python3-venv python3-full
            ;;
        fedora|rhel|centos)
            sudo dnf install -y python3 python3-pip
            ;;
        arch|manjaro)
            sudo pacman -Sy --noconfirm python python-pip
            ;;
        *)
            echo -e "  ${RED}ERROR Could not auto-install Python for your distro.${RESET}"
            echo "  Please install python3 manually and re-run this script."
            exit 1
            ;;
    esac
    echo -e "  ${GREEN}OK${RESET} Python installed"
fi

if ! python_is_compatible; then
    PYVER=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "  ${RED}ERROR${RESET} Python 3.9+ required, found $PYVER"
    exit 1
fi
echo ""

# --- Step 2: Check python3-venv --------------------------------------------
echo -e "${BLUE}[2/6]${RESET} Checking python3-venv..."

# Try creating a test venv - this is the real check
if ! python3 -m venv /tmp/cb-test-venv &>/dev/null; then
    echo -e "  ${YELLOW}->${RESET} python3-venv missing. Installing..."
    case "$DISTRO" in
        ubuntu|debian|linuxmint|pop)
            sudo apt install -y python3-venv python3-full
            ;;
        fedora|rhel|centos)
            sudo dnf install -y python3-venv
            ;;
        arch|manjaro)
            echo -e "  ${GREEN}OK${RESET} venv is built-in on Arch"
            ;;
    esac
else
    echo -e "  ${GREEN}OK${RESET} python3-venv available"
fi
rm -rf /tmp/cb-test-venv
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

# --- Step 5: Detect shell and add alias ------------------------------------
echo -e "${BLUE}[5/6]${RESET} Configuring shell..."

CB_BIN="$INSTALL_DIR/venv/bin/cb"

if [ -n "$ZSH_VERSION" ] || [ "$SHELL" = "/usr/bin/zsh" ] || [ "$SHELL" = "/bin/zsh" ]; then
    SHELL_RC="$HOME/.zshrc"
    SHELL_NAME="zsh"
elif [ -n "$BASH_VERSION" ] || [ "$SHELL" = "/bin/bash" ]; then
    SHELL_RC="$HOME/.bashrc"
    SHELL_NAME="bash"
else
    SHELL_RC="$HOME/.profile"
    SHELL_NAME="sh"
fi

echo -e "  ${YELLOW}->${RESET} Shell: $SHELL_NAME -> $SHELL_RC"

if grep -q "context-bridge" "$SHELL_RC" 2>/dev/null; then
    echo -e "  ${GREEN}OK${RESET} Alias already in $SHELL_RC"
else
    echo "" >> "$SHELL_RC"
    echo "# context-bridge" >> "$SHELL_RC"
    echo "alias cb='$CB_BIN'" >> "$SHELL_RC"
    echo -e "  ${GREEN}OK${RESET} Alias added to $SHELL_RC"
fi
echo ""

# --- Step 6: Symlink for global access (optional) --------------------------
echo -e "${BLUE}[6/6]${RESET} Creating global symlink..."
if [ -w /usr/local/bin ]; then
    ln -sf "$CB_BIN" /usr/local/bin/cb
    echo -e "  ${GREEN}OK${RESET} Symlinked to /usr/local/bin/cb (works globally, no source needed)"
else
    sudo ln -sf "$CB_BIN" /usr/local/bin/cb 2>/dev/null && \
    echo -e "  ${GREEN}OK${RESET} Symlinked to /usr/local/bin/cb" || \
    echo -e "  ${YELLOW}WARN${RESET} Skipped symlink (no sudo). Use 'source $SHELL_RC' instead."
fi
echo ""

# --- Done -------------------------------------------------------------------
echo "  ========================================"
echo -e "  ${GREEN}${BOLD}context-bridge installed successfully!${RESET}"
echo "  ========================================"
echo ""
echo -e "  ${BOLD}Next steps:${RESET}"
echo ""
echo -e "  1. Reload your shell:"
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
