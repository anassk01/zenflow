#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Error handling
set -e
trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
trap 'echo -e "${RED}ERROR: command \"${last_command}\" failed with exit code $?${NC}"' ERR

# Configuration
MIN_PYTHON_VERSION="3.8"
APP_NAME="ZenFlow"
INSTALL_DIR="/opt/zenflow"
ACTUAL_HOME=$(eval echo ~$SUDO_USER)
CONFIG_DIR="$ACTUAL_HOME/.config/zenflow"
DATA_DIR="$ACTUAL_HOME/.local/share/zenflow"

echo -e "${GREEN}${APP_NAME} Installation Script${NC}\n"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (sudo ./install.sh)${NC}"
    exit 1
fi

# Store the actual user
ACTUAL_USER=$SUDO_USER
if [ -z "$ACTUAL_USER" ]; then
    echo -e "${RED}Could not determine the actual user${NC}"
    exit 1
fi

# Check Python version
echo -e "\n${GREEN}Checking Python version...${NC}"
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if [ "$(printf '%s\n' "$MIN_PYTHON_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$MIN_PYTHON_VERSION" ]; then
    echo -e "${RED}Python $MIN_PYTHON_VERSION or higher is required. Found version $PYTHON_VERSION${NC}"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
else
    echo -e "${RED}Could not determine OS${NC}"
    exit 1
fi

echo -e "${YELLOW}Detected OS: $OS${NC}"

# Install system dependencies based on OS
echo -e "\n${GREEN}Installing system dependencies...${NC}"
case $OS in
    "Ubuntu"|"Debian")
        apt-get update || { echo -e "${RED}Failed to update package list${NC}"; exit 1; }
        apt-get install -y \
            python3-dev \
            python3-pip \
            python3-venv \
            libnetfilter-queue-dev \
            chromium-browser \
            chromium-chromedriver \
            build-essential \
            iptables || { echo -e "${RED}Failed to install dependencies${NC}"; exit 1; }
        ;;
    "Fedora"|"Fedora Linux")
        dnf install -y \
            python3-devel \
            python3-pip \
            libnetfilter_queue-devel \
            chromium \
            chromium-headless \
            chromedriver \
            gcc \
            iptables || { echo -e "${RED}Failed to install dependencies${NC}"; exit 1; }
        ;;
    "Arch Linux")
        pacman -Syu --noconfirm \
            python-pip \
            python-virtualenv \
            libnetfilter_queue \
            chromium \
            gcc \
            iptables || { echo -e "${RED}Failed to install dependencies${NC}"; exit 1; }
        ;;
    *)
        echo -e "${RED}Unsupported OS. Please install dependencies manually:${NC}"
        echo "- Python $MIN_PYTHON_VERSION or higher"
        echo "- python3-dev/python3-devel"
        echo "- libnetfilter-queue-dev"
        echo "- Chromium and ChromeDriver"
        echo "- gcc/build-essential"
        exit 1
        ;;
esac

# Create installation directory
echo -e "\n${GREEN}Setting up installation directory...${NC}"
mkdir -p "$INSTALL_DIR"
cp -r . "$INSTALL_DIR/"
chown -R "$ACTUAL_USER:$ACTUAL_USER" "$INSTALL_DIR"

# Create virtual environment
echo -e "\n${GREEN}Creating Python virtual environment...${NC}"
cd "$INSTALL_DIR"
python3 -m venv venv || { echo -e "${RED}Failed to create virtual environment${NC}"; exit 1; }

# Install Python dependencies
echo -e "\n${GREEN}Installing Python dependencies...${NC}"
source venv/bin/activate || { echo -e "${RED}Failed to activate virtual environment${NC}"; exit 1; }
pip install --upgrade pip || { echo -e "${RED}Failed to upgrade pip${NC}"; exit 1; }
pip install -r requirements.txt || { echo -e "${RED}Failed to install Python dependencies${NC}"; exit 1; }

# Create user directories with correct permissions
echo -e "\n${GREEN}Setting up user directories...${NC}"
mkdir -p "$CONFIG_DIR" || { echo -e "${RED}Failed to create config directory${NC}"; exit 1; }
mkdir -p "$DATA_DIR" || { echo -e "${RED}Failed to create data directory${NC}"; exit 1; }
chown -R "$ACTUAL_USER:$ACTUAL_USER" "$CONFIG_DIR"
chown -R "$ACTUAL_USER:$ACTUAL_USER" "$DATA_DIR"

# Set up desktop entry and icons
echo -e "\n${GREEN}Setting up application icons...${NC}"
# Copy icon to standard system locations
ICON_SOURCE="$INSTALL_DIR/resources/zenflow.png"
ICON_SIZES=("16x16" "22x22" "24x24" "32x32" "48x48" "64x64" "128x128" "256x256")

if [ -f "$ICON_SOURCE" ]; then
    # Copy to hicolor theme directories
    for size in "${ICON_SIZES[@]}"; do
        ICON_DIR="/usr/share/icons/hicolor/$size/apps"
        mkdir -p "$ICON_DIR"
        cp "$ICON_SOURCE" "$ICON_DIR/zenflow.png"
    done
    
    # Copy to pixmaps (some applications look here)
    cp "$ICON_SOURCE" "/usr/share/pixmaps/zenflow.png"
    
    # Set proper permissions
    find /usr/share/icons/hicolor -name "zenflow.png" -exec chmod 644 {} \;
    chmod 644 /usr/share/pixmaps/zenflow.png
else
    echo -e "${RED}Warning: Icon file not found at $ICON_SOURCE${NC}"
fi

echo -e "\n${GREEN}Creating desktop entry...${NC}"
cat > /usr/share/applications/zenflow.desktop << EOL
[Desktop Entry]
Version=1.0
Name=${APP_NAME}
Exec=zenflow
Icon=zenflow
Type=Application
Categories=Utility;
Comment=A powerful productivity suite that helps you achieve your optimal flow state
Terminal=false
StartupWMClass=zenflow
EOL

# Update icon caches
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications
fi

# Make main.py executable
chmod +x "$INSTALL_DIR/main.py"

# Create launcher script
echo -e "\n${GREEN}Creating launcher script...${NC}"
cat > /usr/local/bin/zenflow << EOL
#!/bin/bash
source $INSTALL_DIR/venv/bin/activate
sudo $INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py "\$@"
EOL
chmod +x /usr/local/bin/zenflow

# Final setup checks
echo -e "\n${GREEN}Performing final checks...${NC}"
source venv/bin/activate
python3 - << EOL
try:
    import netfilterqueue
    import selenium
    import scapy
    print("✓ All Python dependencies installed correctly")
except ImportError as e:
    print(f"✗ Error: {e}")
    import sys
    sys.exit(1)
EOL

# Verify resource files
if [ ! -f "$INSTALL_DIR/resources/zenflow.png" ]; then
    echo -e "${RED}Warning: Icon file not found at $INSTALL_DIR/resources/zenflow.png${NC}"
fi

echo -e "\n${GREEN}Installation completed!${NC}"
echo -e "\nYou can run ${APP_NAME} in the following ways:"
echo -e "1. ${YELLOW}From the applications menu${NC}"
echo -e "2. ${YELLOW}From terminal:${NC}"
echo -e "   zenflow"
echo -e "\n${RED}Note: The application requires root privileges to run.${NC}" 