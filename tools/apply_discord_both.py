import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

remote_script = """
set -e
echo "=== Step 1: Stopping project-zomboid.service safely ==="
sudo systemctl stop project-zomboid.service
sleep 2

echo "=== Step 2: Updating ServerWelcomeMessage in CircuitVersePZ.ini ==="
NEW_MOTD='ServerWelcomeMessage=<RGB:0.35,0.75,1.0> Welcome to Circuit Verse • Project Zomboid (Build 42)!<LINE><RGB:1.0,1.0,1.0> Join our Discord community for rules, updates, live support & voice:<LINE><RGB:0.34,0.85,0.95> https://discord.gg/M7R8EY28q6 <LINE><RGB:0.8,0.8,0.8> Enjoy smooth survival and fair play!'

sudo sed -i "s|^ServerWelcomeMessage=.*|$NEW_MOTD|" /home/pz/Zomboid/Server/CircuitVersePZ.ini
if [ -f /home/pz/repo/server_config/CircuitVersePZ.ini ]; then
    sudo sed -i "s|^ServerWelcomeMessage=.*|$NEW_MOTD|" /home/pz/repo/server_config/CircuitVersePZ.ini
fi

echo "Verified MOTD in /home/pz/Zomboid/Server/CircuitVersePZ.ini:"
sudo grep -n "ServerWelcomeMessage=" /home/pz/Zomboid/Server/CircuitVersePZ.ini

echo "=== Step 3: Creating CircuitVerseDiscord Mod Structure ==="
MOD_DIR="/home/pz/Zomboid/mods/CircuitVerseDiscord"
sudo mkdir -p "$MOD_DIR/42/media/lua/client" "$MOD_DIR/common/media/lua/client"

sudo bash -c "cat << 'EOF' > '$MOD_DIR/mod.info'
name=Circuit Verse Discord Button
id=CVDiscord
description=Adds a dedicated Circuit Verse Discord community button to the in-game Escape Menu with Steam Overlay integration and clipboard copying.
poster=poster.png
icon=icon.png
versionMin=42.0.0
author=Circuit Verse
EOF"

sudo bash -c "cat << 'EOF' > '$MOD_DIR/42/mod.info'
name=Circuit Verse Discord Button
id=CVDiscord
description=Adds a dedicated Circuit Verse Discord community button to the in-game Escape Menu with Steam Overlay integration and clipboard copying.
poster=poster.png
icon=icon.png
versionMin=42.0.0
author=Circuit Verse
EOF"

LUA_CLIENT_CODE='-- Circuit Verse Discord UI Integration for Build 42
-- Injects an active Discord button into the in-game pause/escape menu (MainScreen)

require "OptionScreens/MainScreen"

local DISCORD_URL = "https://discord.gg/M7R8EY28q6"

local function openDiscordInvite()
    local opened = false
    if isSteamOverlayEnabled and isSteamOverlayEnabled() then
        local ok = pcall(activateSteamOverlayToWebPage, DISCORD_URL)
        if ok then opened = true end
    end
    if not opened and openUrl then
        pcall(openUrl, DISCORD_URL)
    end
    if Clipboard and Clipboard.setClipboard then
        pcall(Clipboard.setClipboard, DISCORD_URL)
    end

    local player = nil
    if getSpecificPlayer then player = getSpecificPlayer(0) end
    if not player and getPlayer then player = getPlayer() end
    if player and player.setHaloNote then
        player:setHaloNote("[Circuit Verse] Discord invite opened in Steam Overlay & copied to clipboard!", 80, 200, 255, 300)
    end
end

-- Hook MainScreen bottom panel to add Discord link
local old_instantiate = MainScreen.instantiate
function MainScreen:instantiate()
    old_instantiate(self)
    
    if self.bottomPanel and not self.discordOption then
        local labelX = 0
        local labelY = 0
        local labelHgt = self.returnOption and self.returnOption.height or 30
        
        self.discordOption = ISLabel:new(labelX, labelY, labelHgt, "★ Join Circuit Verse Discord ★", 0.35, 0.75, 1.0, 1.0, UIFont.Medium, true)
        self.discordOption.internal = "DISCORD_LINK"
        self.discordOption:initialise()
        self.bottomPanel:addChild(self.discordOption)
        self.discordOption.onMouseDown = function(target, item, x, y)
            openDiscordInvite()
        end
    end
end

-- Hook setBottomPanelVisible to position the Discord button cleanly between Invite and Quit
local old_setBottomPanelVisible = MainScreen.setBottomPanelVisible
function MainScreen:setBottomPanelVisible(visible)
    old_setBottomPanelVisible(self, visible)
    
    if visible and self.discordOption and self.bottomPanel then
        local anchor = self.inviteOption or self.returnOption
        if anchor then
            local newY = anchor:getBottom() + 6
            self.discordOption:setY(newY)
            if self.quitToDesktopOption then
                self.quitToDesktopOption:setY(self.discordOption:getBottom() + 6)
                self.bottomPanel:setHeight(self.quitToDesktopOption:getBottom() + 10)
            end
        end
    end
end
'

echo "$LUA_CLIENT_CODE" | sudo tee "$MOD_DIR/42/media/lua/client/CVDiscord_UI.lua" > /dev/null
echo "$LUA_CLIENT_CODE" | sudo tee "$MOD_DIR/common/media/lua/client/CVDiscord_UI.lua" > /dev/null

sudo chown -R pz:pz "$MOD_DIR"

echo "=== Step 4: Starting project-zomboid.service ==="
sudo systemctl start project-zomboid.service
sleep 5
sudo systemctl is-active project-zomboid.service

echo "=== Step 5: Checking PZ listening ports ==="
sudo ss -tulpn | grep -E '(16261|16262|27015)' || true

echo "=== Verification complete! ==="
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, remote_script], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
