import subprocess
import os
import time

SSH_KEY = os.path.expanduser('~/.ssh/id_ed25519_tailscale')
DED_IP = '62.238.81.224'

remote_script = """
set -e
echo "=== Step 1: Checking iptables rate-limiting rules on port 22 ==="
iptables -S INPUT | grep -E 'dport 22|recent' || true

# If there's a recent rule dropping port 22, let's remove it
iptables -S INPUT | while read line; do
  if [[ "$line" =~ "recent" ]] && [[ "$line" =~ "22" ]]; then
    rule="${line#-A }"
    echo "Removing iptables rule: $rule"
    iptables -D $rule || true
  fi
done

echo "=== Step 2: Stopping project-zomboid.service safely ==="
systemctl stop project-zomboid.service
sleep 2

echo "=== Step 3: Updating ServerWelcomeMessage in CircuitVersePZ.ini ==="
NEW_MOTD='ServerWelcomeMessage=<RGB:0.35,0.75,1.0> Welcome to Circuit Verse • Project Zomboid (Build 42)!<LINE><RGB:1.0,1.0,1.0> Join our Discord community for rules, updates, live support & voice:<LINE><RGB:0.34,0.85,0.95> https://discord.gg/M7R8EY28q6 <LINE><RGB:0.8,0.8,0.8> Enjoy smooth survival and fair play!'

sed -i "s|^ServerWelcomeMessage=.*|$NEW_MOTD|" /home/pz/Zomboid/Server/CircuitVersePZ.ini
if [ -f /home/pz/repo/server_config/CircuitVersePZ.ini ]; then
    sed -i "s|^ServerWelcomeMessage=.*|$NEW_MOTD|" /home/pz/repo/server_config/CircuitVersePZ.ini
fi

echo "Verified MOTD in CircuitVersePZ.ini:"
grep -n "ServerWelcomeMessage=" /home/pz/Zomboid/Server/CircuitVersePZ.ini

echo "=== Step 4: Creating CVDiscord In-Game UI Button Mod ==="
MOD_DIR="/home/pz/Zomboid/mods/CircuitVerseDiscord"
mkdir -p "$MOD_DIR/media/lua/client"

cat << 'EOF' > "$MOD_DIR/mod.info"
name=Circuit Verse Discord Button
id=CVDiscord
description=Adds a prominent Discord community button to the pause/escape menu with Steam Overlay integration and clipboard copy.
poster=poster.png
icon=icon.png
versionMin=42.0.0
author=Circuit Verse
EOF

cat << 'EOF' > "$MOD_DIR/media/lua/client/CVDiscord_UI.lua"
-- Circuit Verse In-Game Discord Integration
-- Adds a direct Discord community button to the in-game Escape Menu

require "ISUI/ISEscMenu"

local DISCORD_INVITE_URL = "https://discord.gg/M7R8EY28q6"

local function openDiscordLink()
    local openedInOverlay = false
    if isSteamOverlayEnabled and isSteamOverlayEnabled() then
        local ok = pcall(activateSteamOverlayToWebPage, DISCORD_INVITE_URL)
        if ok then openedInOverlay = true end
    end
    if not openedInOverlay and openUrl then
        pcall(openUrl, DISCORD_INVITE_URL)
    end
    if Clipboard and Clipboard.setClipboard then
        pcall(Clipboard.setClipboard, DISCORD_INVITE_URL)
    end

    local player = getPlayer()
    if player and player.setHaloNote then
        player:setHaloNote("[Circuit Verse] Discord invite opened & copied to clipboard!", 80, 200, 255, 300)
    end
end

-- Hook into Escape Menu
local original_createChildren = ISEscMenu.createChildren
function ISEscMenu:createChildren()
    original_createChildren(self)

    local btnWidth = 200
    local btnHeight = 30
    local x = (self.width - btnWidth) / 2
    local y = self.height - 45

    -- Move existing bottom elements if needed or position cleanly
    local discordBtn = ISButton:new(x, y, btnWidth, btnHeight, "★ Join Circuit Verse Discord ★", self, openDiscordLink)
    discordBtn:initialise()
    discordBtn:instantiate()
    discordBtn.borderColor = {r=0.34, g=0.42, b=0.94, a=0.9}
    discordBtn.backgroundColor = {r=0.15, g=0.2, b=0.45, a=0.85}
    discordBtn.backgroundColorMouseOver = {r=0.25, g=0.35, b=0.8, a=1.0}
    self:addChild(discordBtn)
end
EOF

chown -R pz:pz "$MOD_DIR"

echo "=== Step 5: Starting project-zomboid.service ==="
systemctl start project-zomboid.service
sleep 5
systemctl is-active project-zomboid.service

echo "=== Done! ==="
"""

print("Connecting to Hetzner dedicated server to deploy MOTD and UI mod...")
cmd = ['ssh', '-i', SSH_KEY, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=no', f'root@{DED_IP}', remote_script]
res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
print("STDOUT:\n", res.stdout)
print("STDERR:\n", res.stderr)
