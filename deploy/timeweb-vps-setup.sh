#!/bin/bash
# Setup script for Timeweb Cloud VPS (Amsterdam)
# Run as root on fresh Ubuntu 22.04

set -e

echo "=== AgentsTG Multi-Bot Setup ==="

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3-pip python3-venv git curl htop nano

# Create user for bots (optional but recommended)
useradd -m -s /bin/bash botsuser || true

# Clone repo (replace with your actual repo)
cd /opt
if [ ! -d "agentsTG" ]; then
    echo "Please clone your repository first:"
    echo "  cd /opt && git clone https://github.com/YOUR_USERNAME/agentsTG.git"
    exit 1
fi

chown -R botsuser:botsuser /opt/agentsTG

# Install Poetry
su - botsuser -c "curl -sSL https://install.python-poetry.org | python3 -"
echo 'export PATH="/home/botsuser/.local/bin:$PATH"' >> /home/botsuser/.bashrc

# Install dependencies
su - botsuser -c "cd /opt/agentsTG && /home/botsuser/.local/bin/poetry install --no-root"

echo "=== Setup Complete ==="
echo "Next steps:"
echo "1. Create /opt/agentsTG/.env with your tokens"
echo "2. Copy systemd service: sudo cp deploy/agents-tg.service /etc/systemd/system/"
echo "3. Enable service: sudo systemctl enable --now agents-tg"
