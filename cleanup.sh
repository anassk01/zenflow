#!/bin/bash
# cleanup.sh

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
APP_NAME="ZenFlow"
INSTALL_DIR="/opt/zenflow"
CONFIG_DIR="$HOME/.config/zenflow"
DATA_DIR="$HOME/.local/share/zenflow"

echo -e "${GREEN}Cleaning up ${APP_NAME}...${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (sudo ./cleanup.sh)${NC}"
    exit 1
fi

# Store the actual user
ACTUAL_USER=$SUDO_USER
if [ -z "$ACTUAL_USER" ]; then
    echo -e "${RED}Could not determine the actual user${NC}"
    exit 1
fi

# Kill any running processes
echo -e "\n${GREEN}Stopping running processes...${NC}"
pkill -f chrome 2>/dev/null || true
pkill -f chromium 2>/dev/null || true
pkill -f chromedriver 2>/dev/null || true
pkill -f "python.*zenflow" 2>/dev/null || true

# Clean up temporary files
echo -e "\n${GREEN}Removing temporary files...${NC}"
rm -rf /tmp/chrome-data 2>/dev/null || true
rm -f /tmp/chromedriver.log 2>/dev/null || true

# Remove iptables rules
echo -e "\n${GREEN}Removing iptables rules...${NC}"
iptables -D OUTPUT -j NFQUEUE --queue-num 1 2>/dev/null || true
iptables -D INPUT -j NFQUEUE --queue-num 1 2>/dev/null || true

# Remove application files
echo -e "\n${GREEN}Removing application files...${NC}"
# Remove user-specific files
sudo -u "$ACTUAL_USER" rm -rf "$CONFIG_DIR" 2>/dev/null || true
sudo -u "$ACTUAL_USER" rm -rf "$DATA_DIR" 2>/dev/null || true

# Remove system-wide installation
rm -rf "$INSTALL_DIR" 2>/dev/null || true
rm -f /usr/share/applications/zenflow.desktop 2>/dev/null || true
rm -f /usr/local/bin/zenflow 2>/dev/null || true

# Remove virtual environment if in development directory
if [ -d "venv" ]; then
    echo -e "\n${GREEN}Removing development virtual environment...${NC}"
    rm -rf venv/
fi

echo -e "\n${GREEN}Cleanup completed!${NC}"
echo -e "${YELLOW}Note: You may need to restart your system for all changes to take effect.${NC}"