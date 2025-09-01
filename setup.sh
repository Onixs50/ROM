#!/bin/bash

echo "🚀 Setting up Martius Network Bot..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${BLUE}🐍 Python version: $python_version${NC}"

# Create virtual environment
echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
python3 -m venv martius_bot_env

# Activate virtual environment
source martius_bot_env/bin/activate

# Upgrade pip
echo -e "${YELLOW}⬆️  Upgrading pip...${NC}"
pip install --upgrade pip

# Install requirements
echo -e "${YELLOW}📚 Installing dependencies...${NC}"
pip install -r requirements.txt

# Install additional system dependencies for solc
echo -e "${YELLOW}🔧 Installing system dependencies...${NC}"
sudo apt-get update
sudo apt-get install -y build-essential

# Create sample files if they don't exist
if [ ! -f "accounts.txt" ]; then
    echo -e "${YELLOW}📝 Creating accounts.txt file...${NC}"
    cp accounts.txt.sample accounts.txt
    echo -e "${RED}⚠️  Please add your private keys to accounts.txt before running the bot!${NC}"
fi

if [ ! -f "proxy.txt" ]; then
    echo -e "${YELLOW}📝 Creating proxy.txt file...${NC}"
    cp proxy.txt.sample proxy.txt
    echo -e "${BLUE}ℹ️  Add your proxies to proxy.txt (optional)${NC}"
fi

# Make the main script executable
chmod +x martius_bot.py

echo -e "${GREEN}✅ Setup completed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo -e "1. Add your private keys to ${YELLOW}accounts.txt${NC}"
echo -e "2. (Optional) Add proxies to ${YELLOW}proxy.txt${NC}"
echo -e "3. Run the bot: ${GREEN}source martius_bot_env/bin/activate && python3 martius_bot.py${NC}"
echo ""
echo -e "${YELLOW}⚠️  Important Security Notes:${NC}"
echo -e "• Never share your private keys"
echo -e "• Use test accounts with small amounts"
echo -e "• This bot is for educational purposes"
echo ""
echo -e "${GREEN}🎉 Ready to deploy on Martius Network!${NC}"
