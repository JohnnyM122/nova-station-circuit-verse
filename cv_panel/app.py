from security_failsafe import get_client_ip, get_ua_hash, is_account_locked, verify_session_security, setup_security_failsafe
import datetime
import logging
logger = logging.getLogger('cv-panel')
import asyncio
import hashlib
import hmac
import json
import os
import secrets
import socket
import sqlite3
import struct
import time
from typing import Any, Dict, List, Optional

import httpx
import paramiko
import pymysql
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

CONFIG_PATH = "/etc/cv-panel/config.json"
DB_PATH = "/etc/cv-panel/audit.db"
MATRIX_PATH = "/etc/cv-panel/access_matrix.json"

def load_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

DEFAULT_MATRIX = {
    "master": [
        "1564610713216098394",  # Founder
        "1566625061467717752",  # Chief Community Officer
        "1567482219495301191",  # Community Director
    ],
    "exec_all": [
        "1564610713216098394",  # Founder
        "1566625061467717752",  # Chief Community Officer
        "1567482219495301191",  # Community Director
        "1567495181794807838",  # Community Executive
        "1567474473404338216",  # Community Management
        "1567477045964054598",  # Executive Director
    ],
    "pz_admin": [
        "1567692546333741076",  # Dept.Director (PZ)
        "1567692551853449287",  # PZ Server Host
    ],
    "pz_tech": [
        "1567692554869280770",  # PZ Server Technician
        "1567692558300090498",  # PZ Lead Developer
        "1567692561131503800",  # PZ Developer
    ],
    "pz_mod": [
        "1567692564050743407",  # PZ Head Moderator
        "1567692566961463346",  # PZ Senior Moderator
        "1567692569780166777",  # PZ Moderator
        "1567692572313264169",  # PZ Chief Game Master
        "1567692575433822249",  # PZ Senior Game Master
        "1567692578202062990",  # PZ Game Master
        "1567692580739616852",  # PZ GM Trainee
        "1567692584006983841",  # PZ Head Support
        "1567692589711495379",  # PZ Senior Support
        "1567692593016340573",  # PZ Support Team
        "1567692595818401894",  # PZ Support Trainee
        "1567692598250840166",  # PZ Staff Observer
        "1567692601291702432",  # PZ Server Staff
        "1567692604340969713",  # PZ Ticket Admin
        "1567692607054942318",  # PZ Ticket Support
    ],
    "mc_admin": [
        "1567475022405173320",  # Dept.Director (MC)
        "1567449697101287467",  # MC Server Host
    ],
    "mc_tech": [
        "1568735583575220324",  # MC Server Lead Developer
        "1568735584569262312",  # MC Server Developer
        "1568735586154586152",  # MC Server Technician
        "1567449689819979846",  # MC Server Head Admin
        "1567449687080837192",  # MC Server Admin
    ],
    "mc_mod": [
        "1567449685076086825",  # MC Server Head Mod
        "1567449681070399518",  # MC Server Mod
        "1567474481180446761",  # MC Server Staff
        "1567491706335789056",  # MC Ticket Admin
        "1567491706935447562",  # MC Ticket Support
    ],
    "ns13_admin": [
        "1567475022724079637",  # Dept.Director (NS13)
        "1567449658639384678",  # NS13 Server Host
        "1567449617904177202",  # NS13 Chief GM
        "1567449630655119442",  # NS13 Head Admin
        "1567449641589407774",  # NS13 Chief Developer
        "1567449638783553556",  # NS13 Server Maintainer
    ],
    "ns13_tech": [
        "1567449635780300901",  # NS13 Server Developer
        "1567449627974828193",  # NS13 Senior Admin
        "1567449625588400238",  # NS13 Admin
        "1567449617904177202",  # NS13 Chief GM
    ],
    "ns13_mod": [
        "1567449622467715154",  # NS13 Jr Admin
        "1567449620207108177",  # NS13 Trial Admin
        "1567449610962735224",  # NS13 Chief Mod
        "1567449607930118246",  # NS13 Senior Mod
        "1567449604927131739",  # NS13 Mod
        "1567449598132355133",  # NS13 Jr Mod
        "1567449593975808003",  # NS13 Trial Mod
        "1567449615685525534",  # NS13 GM
        "1567449613307220160",  # NS13 GM Trainee
        "1567449590733602847",  # NS13 Chief Mentor
        "1567449587839410209",  # NS13 Mentor
        "1567449653233057912",  # NS13 Server Staff
        "1567449645158899772",  # NS13 Staff Observer
        "1567491707803799572",  # NS13 Ticket Admin
        "1567491708814364692",  # NS13 Ticket Support
        "1567491710643343470",  # NS13 Mentor Ticket Admin
        "1567491711398191155",  # NS13 Mentor Ticket Support
    ],
    "radio_admin": [
        "1567475021906186270",  # Dept.Director (GC)
        "1567734522253148213",  # Station Manager
        "1567475023869116477",  # Dept.Director (CV Radio)
    ],
    "radio_operator": [
        "1567713478293070007",  # CV-Radio-Access
    ],
    "web_admin": [
        "1568618649919430757",  # Web Admin
    ],
}

def load_matrix() -> Dict[str, List[str]]:
    if not os.path.exists(MATRIX_PATH):
        with open(MATRIX_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_MATRIX, f, indent=2)
        return DEFAULT_MATRIX
    with open(MATRIX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            discord_id TEXT,
            username TEXT,
            global_name TEXT,
            avatar TEXT,
            roles_json TEXT,
            role_names_json TEXT,
            master_unlocked_until REAL DEFAULT 0,
            created_at REAL,
            updated_at REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL,
            discord_id TEXT,
            username TEXT,
            panel TEXT,
            action TEXT,
            details TEXT,
            ip TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS master_lockout (
            discord_id TEXT PRIMARY KEY,
            fails INTEGER DEFAULT 0,
            locked_until REAL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

def _send_discord_pz_staff_audit(user_info, action, details, ip=""):
    try:
        import requests
        cfg = load_config()
        token = cfg.get("discord_bot_token")
        ch_id = cfg.get("pz_server", {}).get("staff_logs_channel")
        if not token or not ch_id:
            return
        u_str = f"**{user_info.get('username', 'Staff')}** (<@{user_info.get('discord_id')}>)" if user_info and user_info.get("discord_id") else "`System / Admin`"
        color = 0x992D22 if any(k in action.lower() for k in ["kick", "ban", "stop"]) else 0x5865F2
        embed = {
            "title": f"🌐 PZ Web Panel Staff Action — {action}",
            "description": f"```{details[:1500]}```",
            "color": color,
            "fields": [
                {"name": "👤 Staff Member", "value": u_str, "inline": True},
                {"name": "📂 Action", "value": f"`{action}`", "inline": True},
                {"name": "🖥️ Platform", "value": "`Web Command Center`", "inline": True}
            ],
            "footer": {"text": "Circuit Verse Staff Audit Suite"}
        }
        if ip:
            embed["fields"].append({"name": "📍 Client IP", "value": f"`{ip}`", "inline": True})
        headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
        requests.post(f"https://discord.com/api/v10/channels/{ch_id}/messages", headers=headers, json={"embeds": [embed]}, timeout=5)
    except Exception as e:
        logger.debug(f"PZ staff log dispatch error: {e}")

def record_audit(user: Optional[Dict[str, Any]], panel: str, action: str, details: str, ip: str = ""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO audit_log (ts, discord_id, username, panel, action, details, ip) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            time.time(),
            user.get("discord_id", "anon") if user else "anon",
            user.get("username", "anonymous") if user else "anonymous",
            panel,
            action,
            details[:2000],
            ip,
        ),
    )
    conn.commit()
    conn.close()

    if panel == "pz":
        import threading
        threading.Thread(target=_send_discord_pz_staff_audit, args=(user, action, details, ip), daemon=True).start()

# ==========================================
# RCON Helper (Source / Minecraft RCON)
# ==========================================
def execute_rcon_sync(host: str, port: int, password: str, command: str, timeout: float = 6.0) -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        def send_pkt(req_id: int, pkt_type: int, payload: str):
            data = payload.encode("utf-8") + b"\x00\x00"
            pkt = struct.pack("<iii", len(data) + 8, req_id, pkt_type) + data
            sock.sendall(pkt)
        def recv_pkt():
            raw_len = sock.recv(4)
            if len(raw_len) < 4:
                return 0, 0, ""
            pkt_len = struct.unpack("<i", raw_len)[0]
            buf = b""
            while len(buf) < pkt_len:
                chunk = sock.recv(pkt_len - len(buf))
                if not chunk:
                    break
                buf += chunk
            req_id, pkt_type = struct.unpack("<ii", buf[:8])
            body = buf[8:-2].decode("utf-8", errors="replace")
            return req_id, pkt_type, body

        send_pkt(1, 3, password)
        req_id, pkt_type, _ = recv_pkt()
        if pkt_type == 0:
            req_id, pkt_type, _ = recv_pkt()
        if req_id == -1:
            raise RuntimeError("RCON authentication failed")
        send_pkt(2, 2, command)
        _, _, body = recv_pkt()
        return body
    finally:
        sock.close()

async def run_rcon(host: str, port: int, password: str, command: str) -> str:
    return await asyncio.to_thread(execute_rcon_sync, host, port, password, command)

# ==========================================
# SSH Helper
# ==========================================
def ssh_exec_sync(host: str, user: str, command: str, port: int = 22, timeout: int = 20) -> Dict[str, Any]:
    cfg = load_config()
    key = paramiko.Ed25519Key.from_private_key_file(cfg["ssh_key_path"])
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=host, port=port, username=user, pkey=key, timeout=10)
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        return {"code": code, "stdout": out, "stderr": err}
    finally:
        client.close()

async def run_ssh(host: str, user: str, command: str, port: int = 22, timeout: int = 20) -> Dict[str, Any]:
    return await asyncio.to_thread(ssh_exec_sync, host, user, command, port, timeout)

def sftp_read_sync(host: str, user: str, remote_path: str, port: int = 22) -> str:
    cfg = load_config()
    key = paramiko.Ed25519Key.from_private_key_file(cfg["ssh_key_path"])
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=host, port=port, username=user, pkey=key, timeout=10)
        sftp = client.open_sftp()
        with sftp.open(remote_path, "r") as f:
            data = f.read()
            return data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)
    finally:
        client.close()

def sftp_write_sync(host: str, user: str, remote_path: str, content: str, port: int = 22):
    cfg = load_config()
    key = paramiko.Ed25519Key.from_private_key_file(cfg["ssh_key_path"])
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=host, port=port, username=user, pkey=key, timeout=10)
        sftp = client.open_sftp()
        with sftp.open(remote_path, "w") as f:
            f.write(content.encode("utf-8"))
    finally:
        client.close()

# ==========================================
# Role & Permission Calculation
# ==========================================
_role_cache: Dict[str, Any] = {"ts": 0, "roles": {}}

async def get_guild_role_map() -> Dict[str, Dict[str, Any]]:
    now = time.time()
    if now - _role_cache["ts"] < 60 and _role_cache["roles"]:
        return _role_cache["roles"]
    cfg = load_config()
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"https://discord.com/api/v10/guilds/{cfg['guild_id']}/roles",
            headers={"Authorization": f"Bot {cfg['discord_bot_token']}"},
        )
        if r.status_code == 200:
            roles_list = r.json()
            rmap = {str(role["id"]): role for role in roles_list}
            _role_cache["ts"] = now
            _role_cache["roles"] = rmap
            return rmap
    return _role_cache["roles"]

async def fetch_member_roles(discord_id: str) -> tuple[Optional[List[str]], List[str]]:
    cfg = load_config()
    rmap = await get_guild_role_map()
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"https://discord.com/api/v10/guilds/{cfg['guild_id']}/members/{discord_id}",
            headers={"Authorization": f"Bot {cfg['discord_bot_token']}"},
        )
        if r.status_code == 404:
            # Member is no longer in Discord server (kicked, banned, or left)
            return None, []
        if r.status_code != 200:
            return [], []
        member = r.json()
        role_ids = [str(rid) for rid in member.get("roles", [])]
        role_names = [rmap[rid]["name"] for rid in role_ids if rid in rmap]
        return role_ids, role_names


# ==============================================================================
# HIERARCHY & PRIVILEGE ESCALATION PREVENTION
# ==============================================================================
MC_RANK_WEIGHTS = {
    "founder": 150,
    "chiefcommunityofficer": 145,
    "communityexecutive": 140,
    "communitydirector": 135,
    "executivedirector": 130,
    "communitymanagement": 125,
    "mcserverhost": 130,
    "serverhost": 130,
    "deptdirectormc": 132,
    "serverdirector": 132,
    "mcserverleaddeveloper": 105,
    "leaddeveloper": 105,
    "mcserverdeveloper": 90,
    "developer": 90,
    "mcservertechnician": 88,
    "technician": 88,
    "mcservermanager": 110,
    "servermanager": 110,
    "mcserverheadadmin": 95,
    "mcserveradmin": 85,
    "mcserverheadmod": 75,
    "mcservermod": 65,
    "mcserverstaff": 55,
    "communitypartner": 45,
    "mcvipmember": 30,
    "mcplayer": 20,
    "default": 10,
    "member": 10,
}

ROLE_ID_TO_WEIGHT = {
    "1564610713216098394": 150,  # Founder
    "1566625061467717752": 145,  # Chief Community Officer
    "1567495181794807838": 140,  # Community Executive
    "1567482219495301191": 135,  # Community Director
    "1567477045964054598": 130,  # Executive Director
    "1567474473404338216": 125,  # Community Management
    "1567475022405173320": 132,  # Dept.Director (MC)
    "1567449697101287467": 130,  # MC Server Host
    "1568735583575220324": 105,  # MC Server Lead Developer
    "1568735584569262312": 90,   # MC Server Developer
    "1568735586154586152": 88,   # MC Server Technician
    "1567449689819979846": 95,   # MC Server Head Admin
    "1567449687080837192": 85,   # MC Server Admin
    "1567449685076086825": 75,   # MC Server Head Mod
    "1567449681070399518": 65,   # MC Server Mod
    "1567474481180446761": 55,   # MC Server Staff
    "1567730989969440848": 45,   # Community Partner
    "1567449678746882068": 30,   # MC VIP Member
    "1567449675949150268": 20,   # MC Player
}

ROLE_NAME_TO_WEIGHT = {
    "founder": 150,
    "chief community officer": 145,
    "community executive": 140,
    "community director": 135,
    "executive director": 130,
    "community management": 125,
    "mc server host": 130,
    "server host": 130,
    "dept.director (mc)": 132,
    "department director (mc)": 132,
    "server director": 132,
    "dept.director": 132,
    "mc server lead developer": 105,
    "mc lead developer": 105,
    "mc server developer": 90,
    "mc developer": 90,
    "mc server technician": 88,
    "mc technician": 88,
    "mc server manager": 110,
    "server manager": 110,
    "mc server head admin": 95,
    "server head admin": 95,
    "head admin": 95,
    "mc server admin": 85,
    "server admin": 85,
    "admin": 85,
    "mc server head mod": 75,
    "server head mod": 75,
    "head mod": 75,
    "mc server mod": 65,
    "server mod": 65,
    "moderator": 65,
    "mc server staff": 55,
    "server staff": 55,
    "community partner": 45,
    "mc vip member": 30,
    "vip member": 30,
    "vip": 30,
    "mc player": 20,
    "player": 20,
}

def get_user_highest_weight(user: Dict[str, Any]) -> tuple:
    role_ids = [str(r) for r in user.get("role_ids", [])]
    if user.get("access", {}).get("master_unlocked") or "1564610713216098394" in role_ids:
        return 999, "Founder / Master Executive"

    max_w = 0
    top_role = "Staff Member"
    for rid in role_ids:
        w = ROLE_ID_TO_WEIGHT.get(rid, 0)
        if w > max_w:
            max_w = w

    for rname in user.get("role_names", []):
        w = ROLE_NAME_TO_WEIGHT.get(rname.lower().strip(), 0)
        if w > max_w:
            max_w = w
            top_role = rname

    if max_w == 0:
        tier = user.get("access", {}).get("mc")
        if tier == "admin":
            max_w = 85
            top_role = "MC Admin"
        elif tier == "technician":
            max_w = 75
            top_role = "MC Technician"
        elif tier == "moderator":
            max_w = 65
            top_role = "MC Moderator"
        else:
            max_w = 20
            top_role = "Player"

    return max_w, top_role

def get_target_group_weight(group: str) -> tuple:
    grp = group.lower().strip()
    if grp == "op":
        return 150, "Server Operator (OP)"
    w = MC_RANK_WEIGHTS.get(grp, 0)
    if w == 0:
        w = ROLE_NAME_TO_WEIGHT.get(grp, 0)
    if w == 0:
        w = 90
    return w, grp

async def log_unauthorized_rank_change(
    user: Dict[str, Any],
    target_player: str,
    target_group: str,
    reason: str,
    target_discord_id: str = "",
    panel_name: str = "mc"
):
    cfg = load_config()
    chan_id = cfg.get(f"{panel_name}_server", {}).get("staff_logs_channel") or cfg.get("mc_server", {}).get("staff_logs_channel")
    token = cfg.get("discord_bot_token")

    actor_w, actor_role = get_user_highest_weight(user)
    target_w, target_name = get_target_group_weight(target_group)

    # 1. Audit DB
    record_audit(
        user,
        panel_name,
        "unauthorized_change_denied",
        f"DENIED by {user.get('username')} ({user.get('discord_id')}): Attempted {target_group} on {target_player}. {reason}"
    )

    # 2. Discord Staff Logs
    if token and chan_id:
        embed = {
            "title": "🚨 [SECURITY ALERT] Unauthorized Rank Change Denied",
            "description": f"**Unauthorized privilege escalation blocked.** {reason}",
            "color": 15158332,  # Red (#e74c3c)
            "fields": [
                {
                    "name": "👤 Unauthorized Change Denied By",
                    "value": f"**{user.get('username')}**\n<@{user.get('discord_id')}>\nID: `{user.get('discord_id')}`",
                    "inline": True
                },
                {
                    "name": "🎯 Affected Person",
                    "value": f"**{target_player}**" + (f"\n<@{target_discord_id}>\nID: `{target_discord_id}`" if target_discord_id else "\n*(Minecraft In-Game)*"),
                    "inline": True
                },
                {
                    "name": "⚠️ Attempted Rank",
                    "value": f"**{target_name}**\nTarget Weight: `{target_w}`",
                    "inline": True
                },
                {
                    "name": "🛡️ Staff Authority",
                    "value": f"**{actor_role}**\nStaff Weight: `{actor_w}`",
                    "inline": True
                },
                {
                    "name": "🚫 Security Action",
                    "value": "**BLOCKED & AUDITED**",
                    "inline": True
                },
                {
                    "name": "📍 Incident Source",
                    "value": f"Web Control Panel (`panel.circuitverse.online`) • {panel_name.upper()}",
                    "inline": True
                }
            ],
            "footer": {
                "text": "Circuit Verse Security System • Zero-Trust Policy"
            },
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                await client.post(
                    f"https://discord.com/api/v10/channels/{chan_id}/messages",
                    headers={"Authorization": f"Bot {token}", "Content-Type": "application/json"},
                    json={"embeds": [embed]}
                )
        except Exception as e:
            logger.error(f"Failed to post security alert to Discord: {e}")

    # 3. In-Game Server Broadcast
    try:
        mc = cfg.get("mc_server", {})
        if mc.get("host") and mc.get("rcon_port") and mc.get("rcon_password"):
            await run_rcon(
                mc["host"],
                int(mc["rcon_port"]),
                mc["rcon_password"],
                f"say §c§l[SECURITY] §eUnauthorized change denied: §f{user.get('username')} §eattempted to grant §6{target_group} §eto §f{target_player}§e."
            )
    except Exception:
        pass

async def verify_rank_assignment_permission(
    user: Dict[str, Any],
    target_player: str,
    target_group: str,
    target_discord_id: str = "",
    panel_name: str = "mc"
):
    actor_w, actor_role = get_user_highest_weight(user)
    target_w, target_name = get_target_group_weight(target_group)

    # Master or Founder bypass
    if actor_w >= 999:
        return

    grp_lower = target_group.lower().strip()

    # Rule 2: Server Director ("Dept.Director (MC)") can ONLY assign roles strictly below Server Director (Server Manager and below)
    user_roles_lower = [r.lower() for r in user.get("role_names", [])]
    if ("dept.director (mc)" in user_roles_lower or "server director" in user_roles_lower) and actor_w < 140:
        if target_w >= 120:
            reason = f"Staff member '{user.get('username')}' is Server Director and attempted to assign rank '{target_name}' (weight {target_w}). Server Director can only assign roles below their rank (Server Manager and below)."
            await log_unauthorized_rank_change(user, target_player, target_group, reason, target_discord_id, panel_name)
            raise HTTPException(
                status_code=403,
                detail="❌ Permission Denied: As Server Director, you can only assign roles below your rank (Server Manager and below)."
            )

    # Rule 1: Server Host can ONLY be assigned by Community Executive staff (weight >= 140)
    if grp_lower in ("mcserverhost", "serverhost", "server host", "mc server host") or target_w == 130:
        if actor_w < 140:
            reason = f"Staff member '{user.get('username')}' ({actor_role}, weight {actor_w}) attempted to assign Server Host, but only Community Executive staff (weight 140+) can assign that role."
            await log_unauthorized_rank_change(user, target_player, target_group, reason, target_discord_id, panel_name)
            raise HTTPException(
                status_code=403,
                detail="❌ Permission Denied: Only Community Executive staff can assign the Server Host role."
            )

    is_self = False
    if target_discord_id and str(target_discord_id).strip() == str(user.get("discord_id", "")).strip():
        is_self = True
    if target_player.lower().strip() == str(user.get("username", "")).lower().strip():
        is_self = True

    # Check 1: Cannot give themself any rank higher or equal to theirs
    if is_self:
        if target_w >= actor_w:
            reason = f"Staff member '{user.get('username')}' attempted self-promotion to rank '{target_name}' (weight {target_w}) which is higher than or equal to their authority '{actor_role}' (weight {actor_w})."
            await log_unauthorized_rank_change(user, target_player, target_group, reason, target_discord_id, panel_name)
            raise HTTPException(
                status_code=403,
                detail=f"❌ Unauthorized Change Denied: You cannot assign yourself any rank higher or equal to your current rank! (Your Rank: {actor_role}, Attempted: {target_name})."
            )

    # Check 2: Can only assign roles strictly BELOW their own rank
    if target_w >= actor_w:
        reason = f"Staff member '{user.get('username')}' ({actor_role}, weight {actor_w}) attempted to assign rank '{target_name}' (weight {target_w}). Staff can only assign roles strictly below their own rank."
        await log_unauthorized_rank_change(user, target_player, target_group, reason, target_discord_id, panel_name)
        raise HTTPException(
            status_code=403,
            detail=f"❌ Unauthorized Change Denied: You can only assign roles strictly below your current rank! (Your Rank: {actor_role}, Attempted: {target_name})."
        )

def compute_access(role_ids: List[str], master_unlocked_until: float = 0) -> Dict[str, Any]:
    m = load_matrix()
    rset = set(role_ids)
    is_exec = bool(rset & set(m.get("exec_all", [])))
    master_eligible = bool(rset & set(m.get("master", [])))
    master_unlocked = master_eligible and (time.time() < master_unlocked_until)

    # PZ tier
    if is_exec or (rset & set(m.get("pz_admin", []))):
        pz_tier = "admin"
    elif rset & set(m.get("pz_tech", [])):
        pz_tier = "technician"
    elif rset & set(m.get("pz_mod", [])):
        pz_tier = "moderator"
    else:
        pz_tier = None

    # MC tier
    if is_exec or (rset & set(m.get("mc_admin", []))):
        mc_tier = "admin"
    elif rset & set(m.get("mc_tech", [])):
        mc_tier = "technician"
    elif rset & set(m.get("mc_mod", [])):
        mc_tier = "moderator"
    else:
        mc_tier = None

    # NS13 tier
    if is_exec or (rset & set(m.get("ns13_admin", []))):
        ns13_tier = "admin"
    elif rset & set(m.get("ns13_tech", [])):
        ns13_tier = "technician"
    elif rset & set(m.get("ns13_mod", [])):
        ns13_tier = "moderator"
    else:
        ns13_tier = None

    # Radio tier
    if is_exec or (rset & set(m.get("radio_admin", []))):
        radio_tier = "admin"
    elif rset & set(m.get("radio_operator", [])):
        radio_tier = "operator"
    else:
        radio_tier = None

    # Website tier
    if is_exec or (rset & {"1568618649919430757", "1567495181794807838"}) or (rset & set(m.get("web_admin", []))):
        website_tier = "admin"
    else:
        website_tier = None

    return {
        "pz": pz_tier,
        "mc": mc_tier,
        "ns13": ns13_tier,
        "radio": radio_tier,
        "website": website_tier,
        "master_eligible": master_eligible,
        "master_unlocked": master_unlocked,
        "any_staff": any([pz_tier, mc_tier, ns13_tier, radio_tier, website_tier, master_eligible]),
    }

async def get_current_user(request: Request, refresh_roles: bool = False) -> Optional[Dict[str, Any]]:
    sid = request.cookies.get("cv_session")
    if not sid:
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM sessions WHERE session_id = ?", (sid,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    user = dict(row)
    now = time.time()
    if refresh_roles or (now - user["updated_at"] > 20):
        role_ids, role_names = await fetch_member_roles(user["discord_id"])
        if role_ids is None:
            # User was kicked or banned from Discord server! Terminate session immediately.
            c.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
            conn.commit()
            conn.close()
            logger.warning(f"User {user['username']} ({user['discord_id']}) is no longer in Discord server. Session {sid[:8]} terminated immediately.")
            return None
        # User is in guild: synchronize roles (even if completely stripped)
        c.execute(
            "UPDATE sessions SET roles_json = ?, role_names_json = ?, updated_at = ? WHERE session_id = ?",
            (json.dumps(role_ids), json.dumps(role_names), now, sid),
        )
        conn.commit()
        user["roles_json"] = json.dumps(role_ids)
        user["role_names_json"] = json.dumps(role_names)
    conn.close()
    role_ids = json.loads(user["roles_json"] or "[]")
    role_names = json.loads(user["role_names_json"] or "[]")
    access = compute_access(role_ids, user["master_unlocked_until"])
    user_dict = {
        "session_id": sid,
        "discord_id": user["discord_id"],
        "username": user["username"],
        "global_name": user["global_name"],
        "avatar": user["avatar"],
        "role_ids": role_ids,
        "role_names": role_names,
        "master_unlocked_until": user["master_unlocked_until"],
        "access": access,
        "created_at": user.get("created_at") or user["updated_at"],
        "updated_at": user["updated_at"],
        "last_active_at": user.get("last_active_at") or user["updated_at"],
        "ip_address": user.get("ip_address", ""),
        "user_agent_hash": user.get("user_agent_hash", ""),
        "mfa_enabled": user.get("mfa_enabled", 1),
    }
    sec_valid, sec_msg = verify_session_security(request, user_dict)
    if not sec_valid:
        logger.warning(f"Session {sid[:8]} security verification failed: {sec_msg}")
        return None
    return user_dict

app = FastAPI(title="Circuit Verse Unified Control Panel")

# ==========================================
# HTTP Security Headers Middleware
# ==========================================
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' https: data: 'unsafe-inline' 'unsafe-eval'; "
        "frame-ancestors 'self' https://*.circuitverse.online https://circuitverse.online;"
    )
    return response

# ==========================================
# SSO Rate Limiting & OAuth2 Routes
# ==========================================
_auth_rate_limit = {}  # ip -> list of timestamps

def check_auth_rate_limit(request: Request, limit: int = 15, window_sec: int = 60) -> bool:
    ip = get_client_ip(request)
    now = time.time()
    ts_list = _auth_rate_limit.setdefault(ip, [])
    _auth_rate_limit[ip] = [t for t in ts_list if now - t < window_sec]
    if len(_auth_rate_limit[ip]) >= limit:
        return False
    _auth_rate_limit[ip].append(now)
    return True

@app.get("/auth/login")
async def auth_login(request: Request, next: str = "/"):
    if not check_auth_rate_limit(request, limit=15, window_sec=60):
        return HTMLResponse("<h3>429 Too Many Requests</h3><p>Rate limit reached on authentication. Please wait 60 seconds before retrying.</p>", status_code=429)

    cfg = load_config()
    import urllib.parse

    clean_next = next if (next.startswith("/") or next.startswith("https://zcp.circuitverse.online") or next.startswith("https://circuitverse.online") or next.startswith("https://panel.circuitverse.online")) else "/"
    nonce = secrets.token_urlsafe(24)
    now_ts = int(time.time())
    secret_bytes = cfg.get("session_secret", "circuit_verse_default_secret_key").encode()
    state_body = f"{nonce}:{now_ts}:{clean_next}"
    state_sig = hmac.new(secret_bytes, state_body.encode(), hashlib.sha256).hexdigest()[:24]
    state_payload = f"{state_body}:{state_sig}"

    params = {
        "client_id": cfg["discord_client_id"],
        "redirect_uri": cfg["discord_redirect_uri"],
        "response_type": "code",
        "scope": "identify guilds.members.read email",
        "state": state_payload,
        "prompt": "consent",
    }
    url = "https://discord.com/oauth2/authorize?" + urllib.parse.urlencode(params)
    resp = RedirectResponse(url)
    resp.set_cookie(
        key="cv_oauth_nonce",
        value=nonce,
        max_age=600,
        httponly=True,
        secure=True,
        samesite="lax",
        domain=".circuitverse.online"
    )
    return resp

_recent_oauth_cache = {}  # code -> (sid, timestamp)

@app.get("/auth/callback")
async def auth_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None):
    if not check_auth_rate_limit(request, limit=15, window_sec=60):
        return HTMLResponse("<h3>429 Too Many Requests</h3><p>Rate limit reached on OAuth callback. Please wait 60 seconds.</p>", status_code=429)

    if not code:
        return RedirectResponse("/?error=oauth_cancelled")

    cfg = load_config()
    secret_bytes = cfg.get("session_secret", "circuit_verse_default_secret_key").encode()

    # 1. Cryptographic State & CSRF Nonce Validation
    cookie_nonce = request.cookies.get("cv_oauth_nonce")
    clean_target = "/"
    state_valid = False

    if state and ":" in state:
        parts = state.split(":")
        if len(parts) >= 4:
            nonce_in_state = parts[0]
            ts_str = parts[1]
            sig_in_state = parts[-1]
            next_in_state = ":".join(parts[2:-1])

            try:
                state_ts = int(ts_str)
                now_ts = time.time()
                # Check expiration (max 10 minutes)
                if now_ts - state_ts <= 600:
                    rebuilt_body = f"{nonce_in_state}:{ts_str}:{next_in_state}"
                    expected_sig = hmac.new(secret_bytes, rebuilt_body.encode(), hashlib.sha256).hexdigest()[:24]
                    if hmac.compare_digest(sig_in_state, expected_sig):
                        if cookie_nonce and hmac.compare_digest(cookie_nonce, nonce_in_state):
                            state_valid = True
                            if next_in_state.startswith("/") or next_in_state.startswith("https://zcp.circuitverse.online") or next_in_state.startswith("https://circuitverse.online") or next_in_state.startswith("https://panel.circuitverse.online"):
                                clean_target = next_in_state
            except Exception as e:
                logger.warning(f"Error validating OAuth state HMAC: {e}")

    # Fallback compatibility if state was plain URL from legacy direct link
    if not state_valid:
        if state and (state.startswith("/") or state.startswith("https://circuitverse.online") or state.startswith("https://panel.circuitverse.online")):
            clean_target = state
            logger.warning(f"OAuth callback accepted legacy plain state from {get_client_ip(request)}")
        else:
            logger.error(f"OAuth CSRF State validation rejected! Cookie nonce: {cookie_nonce}, state: {state}")
            return RedirectResponse("/?error=oauth_csrf_rejected")

    # Resilience: Check if this OAuth code was already redeemed in the last 120s (handles browser retry / 499 client abort)
    now_ts = time.time()
    if code in _recent_oauth_cache:
        cached_sid, cached_time = _recent_oauth_cache[code]
        if now_ts - cached_time < 120:
            logger.info(f"Re-attaching session {cached_sid[:8]} for retried OAuth code")
            cached_resp = RedirectResponse(clean_target)
            cached_resp.set_cookie(
                key="cv_session",
                value=cached_sid,
                domain=".circuitverse.online",
                max_age=86400,
                httponly=True,
                secure=True,
                samesite="none",
            )
            cached_resp.delete_cookie("cv_oauth_nonce", domain=".circuitverse.online")
            return cached_resp

    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.post(
            "https://discord.com/api/v10/oauth2/token",
            data={
                "client_id": cfg["discord_client_id"],
                "client_secret": cfg["discord_client_secret"],
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": cfg["discord_redirect_uri"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status_code != 200:
            logger.error(f"Discord token exchange failed: status={token_resp.status_code} body={token_resp.text}")
            return RedirectResponse("/?error=token_exchange_failed")
        token_data = token_resp.json()
        access_token = token_data["access_token"]

        me_resp = await client.get(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if me_resp.status_code != 200:
            return RedirectResponse("/?error=user_fetch_failed")
        me = me_resp.json()

    discord_id = str(me["id"])
    username = me.get("username", "User")
    global_name = me.get("global_name") or username
    avatar_hash = me.get("avatar")
    avatar_url = (
        f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar_hash}.png"
        if avatar_hash
        else "https://cdn.discordapp.com/embed/avatars/0.png"
    )

    # Anti-Alt / Minimum Discord Account Age Verification (Snowflake ID creation timestamp)
    try:
        snowflake_ts_ms = (int(discord_id) >> 22) + 1420070400000
        account_age_days = (time.time() - (snowflake_ts_ms / 1000.0)) / 86400.0
    except Exception:
        account_age_days = 999.0

    role_ids, role_names = await fetch_member_roles(discord_id)
    if role_ids is None:
        logger.warning(f"Login rejected for {username} ({discord_id}): Not a member of Circuit Verse guild.")
        return RedirectResponse("/?error=not_in_guild")

    # Failsafe Check: Is this Discord ID emergency frozen?
    locked, lock_reason = is_account_locked(discord_id)
    if locked:
        logger.warning(f"Rejected login attempt for frozen staff account {discord_id} ({lock_reason})")
        return RedirectResponse("/?error=account_emergency_frozen")

    mfa_enabled = 1 if me.get("mfa_enabled") else 0
    access_check = compute_access(role_ids, 0)

    # High-Security Guardrails for Staff Members
    if access_check.get("any_staff"):
        # Rule 1: Anti-Alt Age Verification (7 days minimum)
        if account_age_days < 7.0:
            logger.critical(f"🚨 STAFF LOGIN BLOCKED: Account {username} ({discord_id}) created {account_age_days:.1f} days ago (Minimum 7 days required)! Anti-Alt defense engaged.")
            record_audit(
                {"discord_id": discord_id, "username": username},
                "security",
                "anti_alt_rejected",
                f"Staff login blocked: Discord account age ({account_age_days:.1f} days) is below 7 days threshold.",
                get_client_ip(request),
            )
            return RedirectResponse("/?error=account_age_too_low")

        # Rule 2: Verified Discord email required
        if me.get("verified") is False:
            logger.warning(f"Staff login rejected for {username}: Unverified Discord email.")
            return RedirectResponse("/?error=discord_email_unverified")

        # Rule 3: Mandatory Discord 2FA
        if not mfa_enabled:
            logger.warning(f"Staff login rejected for {username}: Discord 2FA is required!")
            return RedirectResponse("/?error=staff_2fa_required")

    sid = secrets.token_urlsafe(32)
    now = time.time()
    client_ip = get_client_ip(request)
    ua_hash = get_ua_hash(request)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO sessions (session_id, discord_id, username, global_name, avatar, roles_json, role_names_json, master_unlocked_until, created_at, updated_at, ip_address, user_agent_hash, mfa_enabled, last_active_at, discord_access_token)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?)
        """,
        (sid, discord_id, username, global_name, avatar_url, json.dumps(role_ids), json.dumps(role_names), now, now, client_ip, ua_hash, mfa_enabled, now, access_token),
    )
    conn.commit()
    conn.close()

    # Save to memory cache for browser retries
    _recent_oauth_cache[code] = (sid, now)
    to_delete = [k for k, v in _recent_oauth_cache.items() if now - v[1] > 300]
    for k in to_delete:
        _recent_oauth_cache.pop(k, None)

    record_audit(
        {"discord_id": discord_id, "username": username},
        "auth",
        "discord_login",
        f"Logged in via Discord OAuth2 ({len(role_names)} guild roles, age {account_age_days:.0f}d, 2FA={mfa_enabled})",
        client_ip,
    )

    resp = RedirectResponse(clean_target)
    resp.set_cookie(
        key="cv_session",
        value=sid,
        domain=".circuitverse.online",
        max_age=86400,
        httponly=True,
        secure=True,
        samesite="none",
    )
    resp.delete_cookie("cv_oauth_nonce", domain=".circuitverse.online")
    return resp

@app.post("/auth/logout")
async def auth_logout(request: Request):
    sid = request.cookies.get("cv_session")
    cfg = load_config()
    if sid:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT discord_access_token FROM sessions WHERE session_id = ?", (sid,))
        row = c.fetchone()
        access_token = row[0] if row else ""
        c.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
        conn.commit()
        conn.close()

        # Forcefully revoke Discord OAuth token at Discord API servers so it cannot linger or be replayed
        if access_token:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.post(
                        "https://discord.com/api/v10/oauth2/token/revoke",
                        data={
                            "client_id": cfg["discord_client_id"],
                            "client_secret": cfg["discord_client_secret"],
                            "token": access_token,
                            "token_type_hint": "access_token",
                        },
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )
                    logger.info("Successfully revoked Discord OAuth token at Discord API servers on logout.")
            except Exception as e:
                logger.warning(f"Discord token revocation request failed: {e}")

    resp = JSONResponse({"success": True})
    resp.delete_cookie("cv_session", domain=".circuitverse.online")
    return resp

@app.get("/api/me")
async def api_me(request: Request, refresh: bool = False):
    user = await get_current_user(request, refresh_roles=refresh)
    if not user:
        return JSONResponse({"authenticated": False}, status_code=401)
    return {"authenticated": True, "user": user}

# ==========================================
# Zomboid Control Panel SSO Bridge
# ==========================================
@app.get("/internal/zcp-auth")
async def internal_zcp_auth(request: Request):
    user = await get_current_user(request)
    if not user:
        return Response(status_code=401)
    if not user["access"]["pz"]:
        return Response(status_code=403)
    return Response(
        status_code=200,
        headers={
            "X-CV-User": user["username"],
            "X-CV-Role": user["access"]["pz"],
        },
    )

@app.post("/zcp-bridge/refresh")
async def zcp_bridge_refresh(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"]["pz"]:
        return JSONResponse({"error": "Unauthorized for PZ Control Panel"}, status_code=401)
    tier = user["access"]["pz"]
    zcp_account_map = {
        "admin": "cv_admin",
        "technician": "cv_tech",
        "moderator": "cv_mod",
    }
    zcp_username = zcp_account_map.get(tier, "cv_mod")
    cfg = load_config()
    zcp_password = cfg["zcp_accounts"][zcp_username]
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{cfg['zcp_url']}/api/auth/login",
            json={"username": zcp_username, "password": zcp_password, "rememberMe": True},
        )
        if r.status_code != 200:
            return JSONResponse({"error": "ZCP backend login failed"}, status_code=502)
        data = r.json()
        resp = JSONResponse(data)
        for cookie_header in r.headers.get_list("set-cookie"):
            resp.headers.append("set-cookie", cookie_header)
        return resp

# ==========================================
# PZ Native Quick Controls (/api/pz/*)
# ==========================================
@app.get("/api/pz/status")
async def api_pz_status(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"]["pz"]:
        raise HTTPException(403, "Requires Project Zomboid Staff role")
    cfg = load_config()
    pz = cfg["pz_server"]
    svc = await run_ssh("127.0.0.1", "root", "systemctl is-active project-zomboid.service && systemctl is-active zomboid-panel.service")
    lines = svc["stdout"].strip().splitlines()
    pz_active = lines[0] == "active" if lines else False
    zcp_active = lines[1] == "active" if len(lines) > 1 else False
    players_out = ""
    if pz_active:
        try:
            players_out = await run_rcon("127.0.0.1", int(pz["rcon_port"]), pz["rcon_password"], "players")
        except Exception as e:
            players_out = f"RCON error: {e}"
    return {
        "running": pz_active,
        "zcp_running": zcp_active,
        "players_raw": players_out,
        "zcp_url": cfg["zcp_public_url"],
        "tier": user["access"]["pz"],
    }

@app.post("/api/pz/action")
async def api_pz_action(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"]["pz"]:
        raise HTTPException(403, "Requires Project Zomboid Staff role")
    body = await request.json()
    action = body.get("action")
    command = body.get("command", "")
    cfg = load_config()
    pz = cfg["pz_server"]

    if action in ("start", "stop", "restart"):
        if user["access"]["pz"] not in ("admin", "technician"):
            raise HTTPException(403, "Only PZ Leadership or Technicians can control the service")
        if action in ("stop", "restart"):
            try:
                await run_rcon("127.0.0.1", int(pz["rcon_port"]), pz["rcon_password"], "save")
            except Exception:
                pass
        res = await run_ssh("127.0.0.1", "root", f"systemctl {action} project-zomboid.service")
        record_audit(user, "pz", f"service_{action}", f"systemctl {action} project-zomboid.service")
        return {"success": res["code"] == 0, "output": res["stdout"] + res["stderr"]}

    if action == "rcon":
        if user["access"]["pz"] == "moderator" and not any(
            command.lower().startswith(p) for p in ("players", "servermsg", "kickuser", "banuser", "unbanuser", "teleport", "godmod", "additem")
        ):
            raise HTTPException(403, "Command restricted to PZ Admin/Technician tier")
        out = await run_rcon("127.0.0.1", int(pz["rcon_port"]), pz["rcon_password"], command)
        record_audit(user, "pz", "rcon", command)
        return {"success": True, "output": out}

    raise HTTPException(400, "Unknown action")

# ==========================================
# Minecraft Control Panel (/api/mc/*)
# ==========================================
@app.get("/api/mc/status")
async def api_mc_status(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"]["mc"]:
        raise HTTPException(403, "Requires Minecraft Staff Discord role")
    cfg = load_config()
    mc = cfg["mc_server"]
    ssh_res = await run_ssh(
        mc["ssh_host"],
        mc["ssh_user"],
        "systemctl is-active minecraft.service; free -m | awk '/Mem:/ {print $2,$3}'; df -h / | awk 'NR==2 {print $2,$3,$5}'; uptime -p; ss -ulpn | grep -q ':19132 ' && echo 'bedrock_online' || echo 'bedrock_offline'",
    )
    lines = ssh_res["stdout"].strip().splitlines()
    running = lines[0].strip() == "active" if lines else False
    mem_info = lines[1] if len(lines) > 1 else ""
    disk_info = lines[2] if len(lines) > 2 else ""
    uptime_info = lines[3] if len(lines) > 3 else ""
    bedrock_online = (lines[4].strip() == "bedrock_online") if len(lines) > 4 else False

    list_out = ""
    tps_out = ""
    whitelist_out = ""
    if running:
        try:
            list_out = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "list")
            tps_out = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "tps")
            whitelist_out = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "whitelist list")
        except Exception as e:
            list_out = f"RCON Error: {e}"

    return {
        "running": running,
        "bedrock_online": bedrock_online,
        "bedrock_port": 19132,
        "host": "play.circuitverse.online (2.31.101.63)",
        "mem": mem_info,
        "disk": disk_info,
        "uptime": uptime_info,
        "players_raw": list_out,
        "tps_raw": tps_out,
        "whitelist_raw": whitelist_out,
        "tier": user["access"]["mc"],
    }

@app.post("/api/mc/action")
async def api_mc_action(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"]["mc"]:
        raise HTTPException(403, "Requires Minecraft Staff Discord role")
    body = await request.json()
    action = body.get("action")
    cfg = load_config()
    mc = cfg["mc_server"]
    tier = user["access"]["mc"]

    if action in ("start", "stop", "restart"):
        if tier not in ("admin", "technician"):
            raise HTTPException(403, "Only MC Host, Director, or Admin can control server power")
        if action == "stop":
            try:
                await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], f"say [Server] Server is stopping initiated by {user['username']}...")
                await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "save-all flush")
            except Exception:
                pass
            res = await run_ssh(mc["ssh_host"], mc["ssh_user"], "systemctl stop minecraft.service")
            record_audit(user, "mc", "service_stop", "systemctl stop minecraft.service")
            return {"success": res["code"] == 0, "output": res["stdout"] + res["stderr"]}

        if action == "start":
            res = await run_ssh(mc["ssh_host"], mc["ssh_user"], "systemctl start minecraft.service")
            record_audit(user, "mc", "service_start", "systemctl start minecraft.service")
            return {"success": res["code"] == 0, "output": res["stdout"] + res["stderr"]}

        if action == "restart":
            try:
                seconds = int(body.get("seconds", 60))
            except Exception:
                seconds = 60
            reason = str(body.get("reason", "Scheduled Server Reboot")).strip() or "Scheduled Server Reboot"
            record_audit(user, "mc", "service_restart", f"reboot countdown {seconds}s reason: {reason}")

            async def do_countdown_and_restart():
                try:
                    await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], f"say [SERVER REBOOT] Initiated by {user['username']}! Rebooting in {seconds} seconds: {reason}")
                    await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], f'title @a title {{"text":"SERVER REBOOT","color":"red","bold":true}}')
                    await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], f'title @a subtitle {{"text":"Restarting in {seconds}s - {reason}","color":"yellow"}}')
                    await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "playsound minecraft:block.bell.use master @a")
                except Exception:
                    pass

                remaining = seconds
                while remaining > 0:
                    step = 1
                    if remaining > 30:
                        step = min(remaining - 30, 10)
                    elif remaining > 15:
                        step = min(remaining - 15, 5)
                    elif remaining > 10:
                        step = min(remaining - 10, 5)
                    elif remaining > 5:
                        step = min(remaining - 5, 1)
                    else:
                        step = 1
                    await asyncio.sleep(step)
                    remaining -= step
                    if remaining in (60, 45, 30, 15, 10, 5, 4, 3, 2, 1):
                        try:
                            sec_word = "seconds" if remaining != 1 else "second"
                            await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], f"say [SERVER REBOOT] Server rebooting in {remaining} {sec_word}! ({reason})")
                            await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], f'title @a actionbar {{"text":"⚠ Server rebooting in {remaining}s! ({reason})","color":"gold","bold":true}}')
                            if remaining <= 5:
                                await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], f'title @a title {{"text":"REBOOT IN {remaining}","color":"red","bold":true}}')
                                await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "playsound minecraft:block.note_block.bell master @a")
                        except Exception:
                            pass

                try:
                    await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "say [Server] Saving chunks and restarting now...")
                    await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "save-all flush")
                except Exception:
                    pass
                await run_ssh(mc["ssh_host"], mc["ssh_user"], "systemctl restart minecraft.service")

            if seconds <= 0:
                await do_countdown_and_restart()
                return {"success": True, "output": "Server restart command executed immediately."}
            else:
                asyncio.create_task(do_countdown_and_restart())
                return {"success": True, "output": f"Reboot countdown started ({seconds}s). In-game alert broadcasted, server will restart after countdown."}

    if action == "rcon":
        cmd = body.get("command", "").strip()
        if not cmd:
            raise HTTPException(400, "Empty command")
        cmd_l = cmd.lower()
        if cmd_l.startswith("lp user ") and " parent set " in cmd_l:
            pts = cmd.split()
            if len(pts) >= 6:
                await verify_rank_assignment_permission(user, pts[2], pts[5])
        elif cmd_l.startswith("givestaff "):
            pts = cmd.split()
            if len(pts) >= 3:
                await verify_rank_assignment_permission(user, pts[1], pts[2])
        elif cmd_l.startswith("op "):
            pts = cmd.split()
            if len(pts) >= 2:
                await verify_rank_assignment_permission(user, pts[1], "op")
        if tier == "moderator":
            allowed_prefixes = ("list", "say", "kick", "ban", "pardon", "whitelist", "tp", "tell", "msg", "weather", "time")
            if not any(cmd.lower().startswith(p) for p in allowed_prefixes):
                raise HTTPException(403, "Command restricted to MC Admin / Director / Host tier")
        out = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], cmd)
        record_audit(user, "mc", "rcon", cmd)
        return {"success": True, "output": out}

    if action == "player":
        sub = body.get("sub")
        player = body.get("player", "").strip()
        reason = body.get("reason", "Staff action").strip()
        value = body.get("value", "").strip()
        if not player:
            raise HTTPException(400, "Player username required")
        cmd_map = {
            "kick": f"kick {player} {reason}",
            "ban": f"ban {player} {reason}",
            "pardon": f"pardon {player}",
            "whitelist_add": f"whitelist add {player}",
            "whitelist_remove": f"whitelist remove {player}",
            "gamemode": f"gamemode {value or 'survival'} {player}",
            "op": f"op {player}",
            "deop": f"deop {player}",
            "lp_group": f"lp user {player} parent set {value}",
        }
        if sub in ("op", "deop", "lp_group") and tier != "admin":
            raise HTTPException(403, "Only MC Host, Director, or Admin can change operator/LuckPerms ranks")
        if sub == "lp_group":
            await verify_rank_assignment_permission(user, player, value)
        elif sub == "op":
            await verify_rank_assignment_permission(user, player, "op")
        if sub not in cmd_map:
            raise HTTPException(400, "Invalid player action")
        out = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], cmd_map[sub])
        record_audit(user, "mc", f"player_{sub}", f"{player} ({value or reason})")
        return {"success": True, "output": out}


    if action in ("hostile_mobs", "mob_throttle"):
        level = str(body.get("level", "status")).strip().lower()
        if level not in ("full", "half", "quarter", "eighth", "off", "status"):
            raise HTTPException(400, "Invalid hostile mobs level. Use: full, half, quarter, eighth, off, status")
        out = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], f"mobs {level}")
        record_audit(user, "mc", "hostile_mobs", level)
        return {"success": True, "output": out}

    if action == "backup":
        if tier not in ("admin", "technician"):
            raise HTTPException(403, "Requires MC Admin or higher")
        try:
            await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "save-all flush")
        except Exception:
            pass
        ts = time.strftime("%Y%m%d_%H%M%S")
        res = await run_ssh(
            mc["ssh_host"],
            mc["ssh_user"],
            f"mkdir -p /opt/minecraft/backups && tar -czf /opt/minecraft/backups/mc_backup_{ts}.tar.gz -C /opt/minecraft/server world world_nether world_the_end server.properties && ls -lh /opt/minecraft/backups/mc_backup_{ts}.tar.gz",
            timeout=90,
        )
        record_audit(user, "mc", "backup", f"Created mc_backup_{ts}.tar.gz")
        return {"success": res["code"] == 0, "output": res["stdout"] + res["stderr"]}

    raise HTTPException(400, "Unknown MC action")

MC_CORE_FILES = {
    "server.properties": "/opt/minecraft/server/server.properties",
    "Geyser-Spigot (Bedrock Config)": "/opt/minecraft/server/plugins/Geyser-Spigot/config.yml",
    "floodgate (Bedrock Auth Config)": "/opt/minecraft/server/plugins/floodgate/config.yml",
    "purpur.yml": "/opt/minecraft/server/purpur.yml",
    "spigot.yml": "/opt/minecraft/server/spigot.yml",
    "bukkit.yml": "/opt/minecraft/server/bukkit.yml",
    "whitelist.json": "/opt/minecraft/server/whitelist.json",
    "ops.json": "/opt/minecraft/server/ops.json",
    "banned-players.json": "/opt/minecraft/server/banned-players.json",
}

def resolve_mc_config_path(name: str) -> Optional[str]:
    name = name.strip().lstrip("/")
    if name in MC_CORE_FILES:
        return MC_CORE_FILES[name]
    rel = name
    if rel.startswith("plugins/"):
        rel = rel[len("plugins/"):]
    norm = os.path.normpath(rel)
    if norm.startswith("..") or "/../" in norm or "\\" in norm:
        return None
    allowed_exts = ('.yml', '.yaml', '.json', '.properties', '.conf', '.toml', '.txt', '.cfg', '.ini')
    if not norm.lower().endswith(allowed_exts):
        return None
    full = os.path.normpath(os.path.join("/opt/minecraft/server/plugins", norm))
    if not full.startswith("/opt/minecraft/server/plugins/"):
        return None
    return full

def get_default_reload_cmd(name: str) -> str:
    lower = name.lower()
    if "geyser" in lower or "floodgate" in lower or "bedrock" in lower:
        return "geyser reload"
    if "auraskills" in lower:
        return "skills reload"
    if "essentials" in lower:
        return "ess reload"
    if "luckperms" in lower:
        return "lp sync"
    if "coreprotect" in lower:
        return "co reload"
    if "bluemap" in lower:
        return "bluemap reload"
    if "pvpmanager" in lower:
        return "pvp reload"
    if "safezone" in lower:
        return "safezone reload"
    if "quests" in lower:
        return "quests reload"
    if "quickshop" in lower:
        return "qs reload"
    if "craftcontrol" in lower:
        return "craftcontrol reload"
    if "veinminer" in lower:
        return "veinminer reload"
    return ""

_mc_file_list_cache = {"ts": 0, "files": []}

def get_allowed_mc_files_sync(host: str, user: str) -> Dict[str, Any]:
    now = time.time()
    if now - _mc_file_list_cache["ts"] < 60 and _mc_file_list_cache["files"]:
        plugin_files = _mc_file_list_cache["files"]
    else:
        cmd = (
            "cd /opt/minecraft/server/plugins && "
            "find . -maxdepth 4 -type f \( -name '*.yml' -o -name '*.yaml' -o -name '*.json' -o -name '*.properties' -o -name '*.conf' -o -name '*.toml' -o -name '*.txt' \) "
            "! -path '*/.*' ! -path '*/backups/*' ! -path '*/.paper-remapped/*' ! -path '*/userdata/*' ! -path '*/users/*' ! -path '*/data/*' ! -path '*/translations/*' ! -path '*/locales/*' ! -path '*/overrides/*' ! -path '*/lang/*' ! -path '*/tmp*' "
            "| sed 's|^\./||' | sort"
        )
        res = ssh_exec_sync(host, user, cmd)
        plugin_files = [line.strip() for line in res["stdout"].splitlines() if line.strip()]
        _mc_file_list_cache["ts"] = now
        _mc_file_list_cache["files"] = plugin_files

    return {
        "core": list(MC_CORE_FILES.keys()),
        "plugins": [f"plugins/{p}" for p in plugin_files]
    }

@app.get("/api/mc/file")
async def api_mc_get_file(request: Request, name: str = "server.properties"):
    user = await get_current_user(request)
    if not user or not user["access"]["mc"]:
        raise HTTPException(403, "Requires Minecraft Staff role")
    target_path = resolve_mc_config_path(name)
    if not target_path:
        raise HTTPException(400, "File path not allowed or invalid format")
    cfg = load_config()
    mc = cfg["mc_server"]
    content = await asyncio.to_thread(sftp_read_sync, mc["ssh_host"], mc["ssh_user"], target_path)
    file_list = await asyncio.to_thread(get_allowed_mc_files_sync, mc["ssh_host"], mc["ssh_user"])
    return {
        "name": name,
        "content": content,
        "core_files": file_list["core"],
        "plugin_files": file_list["plugins"],
        "files": file_list["core"] + file_list["plugins"],
        "default_reload_cmd": get_default_reload_cmd(name),
    }

@app.post("/api/mc/file")
async def api_mc_save_file(request: Request):
    user = await get_current_user(request)
    if not user or user["access"]["mc"] != "admin":
        raise HTTPException(403, "Only MC Host, Director, or Admin can edit server configuration files")
    body = await request.json()
    name = body.get("name", "")
    content = body.get("content", "")
    reload_after = body.get("reload_after", False)
    custom_reload_cmd = body.get("reload_cmd", "").strip()

    target_path = resolve_mc_config_path(name)
    if not target_path:
        raise HTTPException(400, "File path not allowed or invalid format")
    cfg = load_config()
    mc = cfg["mc_server"]
    await asyncio.to_thread(sftp_write_sync, mc["ssh_host"], mc["ssh_user"], target_path, content)
    record_audit(user, "mc", "save_file", f"Edited {name} ({len(content)} bytes)")

    reload_msg = ""
    if reload_after:
        cmd_to_run = custom_reload_cmd or get_default_reload_cmd(name)
        if cmd_to_run:
            try:
                out = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], cmd_to_run)
                clean_out = " ".join(out.strip().splitlines())
                reload_msg = f" | In-game Reload ({cmd_to_run}): {clean_out}"
                record_audit(user, "mc", "rcon_reload", f"{cmd_to_run} after saving {name}")
            except Exception as e:
                reload_msg = f" | Reload error: {e}"

    return {"success": True, "message": f"Saved {name} on 2.31.101.63{reload_msg}"}

@app.get("/api/mc/logs")
async def api_mc_logs(request: Request, lines: int = 120):
    user = await get_current_user(request)
    if not user or not user["access"]["mc"]:
        raise HTTPException(403, "Requires Minecraft Staff role")
    cfg = load_config()
    mc = cfg["mc_server"]
    res = await run_ssh(mc["ssh_host"], mc["ssh_user"], f"tail -n {min(lines, 300)} /opt/minecraft/server/logs/latest.log")
    return {"logs": res["stdout"]}

# ==========================================
# Minecraft Bedrock Edition (Geyser/Floodgate Bridge)
# ==========================================
@app.get("/api/mc/bedrock/status")
async def api_mc_bedrock_status(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"]["mc"]:
        raise HTTPException(403, "Requires Minecraft Staff role")
    cfg = load_config()
    mc = cfg["mc_server"]

    cmd = (
        "ss -ulpn | grep -q ':19132 ' && echo 'port_listening' || echo 'port_closed'; "
        "test -f /opt/minecraft/server/plugins/Geyser-Spigot.jar && echo 'jar_enabled' || echo 'jar_disabled'; "
        "test -f /opt/minecraft/server/plugins/floodgate-spigot.jar && echo 'fg_enabled' || echo 'fg_disabled'"
    )
    res = await run_ssh(mc["ssh_host"], mc["ssh_user"], cmd)
    lines = res["stdout"].strip().splitlines()
    listening = (lines[0].strip() == "port_listening") if len(lines) > 0 else False
    geyser_enabled = (lines[1].strip() == "jar_enabled") if len(lines) > 1 else False
    fg_enabled = (lines[2].strip() == "fg_enabled") if len(lines) > 2 else False

    version_str = ""
    connections_str = ""
    if listening:
        try:
            version_str = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "geyser version")
            connections_str = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "geyser list")
        except Exception as e:
            version_str = f"RCON: {e}"

    return {
        "online": listening,
        "geyser_enabled": geyser_enabled,
        "floodgate_enabled": fg_enabled,
        "port": 19132,
        "webrtc_port": 19133,
        "host": "play.circuitverse.online (2.31.101.63)",
        "version_raw": version_str,
        "connections_raw": connections_str,
        "tier": user["access"]["mc"]
    }

@app.post("/api/mc/bedrock/action")
async def api_mc_bedrock_action(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"]["mc"]:
        raise HTTPException(403, "Requires Minecraft Staff role")
    tier = user["access"]["mc"]
    body = await request.json()
    action = body.get("action")
    cfg = load_config()
    mc = cfg["mc_server"]

    if action in ("start", "stop", "restart", "reload", "pause", "resume"):
        if tier not in ("admin", "technician"):
            raise HTTPException(403, "Only MC Host, Director, or Admin can control Bedrock server state")

        if action == "start":
            enable_cmd = (
                "cd /opt/minecraft/server/plugins && "
                "[ -f Geyser-Spigot.jar.disabled ] && mv Geyser-Spigot.jar.disabled Geyser-Spigot.jar; "
                "[ -f floodgate-spigot.jar.disabled ] && mv floodgate-spigot.jar.disabled floodgate-spigot.jar; "
                "chown minecraft:minecraft Geyser*.jar floodgate*.jar 2>/dev/null || true"
            )
            await run_ssh(mc["ssh_host"], mc["ssh_user"], enable_cmd)
            rcon_out = ""
            try:
                rcon_out = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "geyser on")
            except Exception:
                pass
            record_audit(user, "mc_bedrock", "start", "Enabled Bedrock Geyser/Floodgate bridge")
            return {"success": True, "output": f"Bedrock Edition bridge enabled. {rcon_out}".strip()}

        if action == "stop":
            try:
                await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "geyser off")
            except Exception:
                pass
            disable_cmd = (
                "cd /opt/minecraft/server/plugins && "
                "[ -f Geyser-Spigot.jar ] && mv Geyser-Spigot.jar Geyser-Spigot.jar.disabled; "
                "[ -f floodgate-spigot.jar ] && mv floodgate-spigot.jar floodgate-spigot.jar.disabled; true"
            )
            await run_ssh(mc["ssh_host"], mc["ssh_user"], disable_cmd)
            record_audit(user, "mc_bedrock", "stop", "Disabled Bedrock Geyser/Floodgate bridge")
            return {"success": True, "output": "Bedrock Edition listener closed and plugins set to disabled."}

        if action in ("restart", "reload"):
            try:
                out = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "geyser reload")
                record_audit(user, "mc_bedrock", "reload", "geyser reload")
                return {"success": True, "output": out}
            except Exception as e:
                raise HTTPException(500, f"RCON error reloading Geyser: {e}")

        if action == "pause":
            out = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "geyser off")
            record_audit(user, "mc_bedrock", "pause", "geyser off")
            return {"success": True, "output": out}

        if action == "resume":
            out = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "geyser on")
            record_audit(user, "mc_bedrock", "resume", "geyser on")
            return {"success": True, "output": out}

    if action in ("version", "dump", "connections", "firewall"):
        cmd_map = {
            "version": "geyser version",
            "dump": "geyser dump",
            "connections": "geyser list",
            "firewall": "floodgate firewall",
        }
        out = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], cmd_map[action])
        return {"success": True, "output": out}

    raise HTTPException(400, f"Unknown Bedrock action: {action}")

@app.get("/api/mc/bedrock/settings")
async def api_mc_bedrock_get_settings(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"]["mc"]:
        raise HTTPException(403, "Requires Minecraft Staff role")
    cfg = load_config()
    mc = cfg["mc_server"]

    geyser_path = "/opt/minecraft/server/plugins/Geyser-Spigot/config.yml"
    floodgate_path = "/opt/minecraft/server/plugins/floodgate/config.yml"

    geyser_raw = await asyncio.to_thread(sftp_read_sync, mc["ssh_host"], mc["ssh_user"], geyser_path)
    floodgate_raw = await asyncio.to_thread(sftp_read_sync, mc["ssh_host"], mc["ssh_user"], floodgate_path)

    return {
        "geyser_config": geyser_raw,
        "floodgate_config": floodgate_raw,
        "tier": user["access"]["mc"]
    }

@app.post("/api/mc/bedrock/settings")
async def api_mc_bedrock_save_settings(request: Request):
    user = await get_current_user(request)
    if not user or user["access"]["mc"] != "admin":
        raise HTTPException(403, "Only MC Host, Director, or Admin can edit Bedrock configuration")
    body = await request.json()
    cfg = load_config()
    mc = cfg["mc_server"]

    geyser_content = body.get("geyser_config")
    floodgate_content = body.get("floodgate_config")
    reload_after = body.get("reload_after", True)

    msg_parts = []
    if geyser_content:
        await asyncio.to_thread(sftp_write_sync, mc["ssh_host"], mc["ssh_user"], "/opt/minecraft/server/plugins/Geyser-Spigot/config.yml", geyser_content)
        msg_parts.append("Geyser config saved")
    if floodgate_content:
        await asyncio.to_thread(sftp_write_sync, mc["ssh_host"], mc["ssh_user"], "/opt/minecraft/server/plugins/floodgate/config.yml", floodgate_content)
        msg_parts.append("Floodgate config saved")

    record_audit(user, "mc_bedrock", "save_settings", ", ".join(msg_parts))

    rcon_reload_msg = ""
    if reload_after:
        try:
            out = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "geyser reload")
            rcon_reload_msg = f" | Live Reload: {out.strip()}"
        except Exception as e:
            rcon_reload_msg = f" | Reload error: {e}"

    return {"success": True, "message": f"{', '.join(msg_parts)}{rcon_reload_msg}"}

@app.get("/api/mc/bedrock/logs")
async def api_mc_bedrock_logs(request: Request, lines: int = 150):
    user = await get_current_user(request)
    if not user or not user["access"]["mc"]:
        raise HTTPException(403, "Requires Minecraft Staff role")
    cfg = load_config()
    mc = cfg["mc_server"]
    cmd = f"grep -i -E 'geyser|floodgate|bedrock|raknet|nethernet|19132' /opt/minecraft/server/logs/latest.log | tail -n {min(lines, 300)}"
    res = await run_ssh(mc["ssh_host"], mc["ssh_user"], cmd)
    return {"logs": res["stdout"]}

# ==========================================
# Nova Station 13 (SS13) Control Panel (/api/ns13/*)
# ==========================================
@app.get("/api/ns13/status")
async def api_ns13_status(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"]["ns13"]:
        raise HTTPException(403, "Requires Nova Station 13 Staff Discord role")
    cfg = load_config()
    ns = cfg["ns13_server"]
    res = await run_ssh(
        ns["ssh_host"],
        ns["ssh_user"],
        "systemctl is-active novastation.service; pgrep -a DreamDaemon; free -m | awk '/Mem:/ {print $2,$3}'; df -h / | awk 'NR==2 {print $2,$3,$5}'; uptime -p",
    )
    lines = res["stdout"].strip().splitlines()
    running = lines[0].strip() == "active" if lines else False
    proc_line = lines[1] if len(lines) > 1 else ""
    mem_info = lines[2] if len(lines) > 2 else ""
    disk_info = lines[3] if len(lines) > 3 else ""
    uptime_info = lines[4] if len(lines) > 4 else ""

    # Query MariaDB on 87.99.133.221 via SSH python snippet
    db_cmd = f"""python3 -c '
import pymysql, json
conn = pymysql.connect(host="127.0.0.1", user="{ns["db_user"]}", password="{ns["db_password"]}", database="{ns["db_name"]}", cursorclass=pymysql.cursors.DictCursor)
cur = conn.cursor()
cur.execute("SELECT MAX(id) AS id, ckey, MAX(display_rank) AS rank FROM admin GROUP BY ckey ORDER BY id DESC LIMIT 50")
admins = cur.fetchall()
cur.execute("SELECT id, ckey, a_ckey, reason, bantime, expiration_time, unbanned FROM ban ORDER BY id DESC LIMIT 25")
bans = [{{k: str(v) if v is not None else None for k, v in row.items()}} for row in cur.fetchall()]
print(json.dumps({{"admins": admins, "bans": bans}}))
'"""
    db_res = await run_ssh(ns["ssh_host"], ns["ssh_user"], db_cmd)
    db_data = {"admins": [], "bans": []}
    try:
        db_data = json.loads(db_res["stdout"].strip().splitlines()[-1])
    except Exception:
        pass

    return {
        "running": running,
        "host": "game.circuitverse.online:7777 (87.99.133.221)",
        "process": proc_line,
        "mem": mem_info,
        "disk": disk_info,
        "uptime": uptime_info,
        "admins": db_data["admins"],
        "bans": db_data["bans"],
        "tier": user["access"]["ns13"],
    }

@app.post("/api/ns13/action")
async def api_ns13_action(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"]["ns13"]:
        raise HTTPException(403, "Requires Nova Station 13 Staff role")
    body = await request.json()
    action = body.get("action")
    cfg = load_config()
    ns = cfg["ns13_server"]
    tier = user["access"]["ns13"]

    if action in ("start", "stop", "restart"):
        if tier not in ("admin", "technician"):
            raise HTTPException(403, "Only NS13 Director, Host, Head Admin, or Maintainer can control server power")
        res = await run_ssh(ns["ssh_host"], ns["ssh_user"], f"sudo systemctl {action} novastation.service")
        record_audit(user, "ns13", f"service_{action}", f"systemctl {action} novastation.service")
        return {"success": res["code"] == 0, "output": res["stdout"] + res["stderr"]}

    if action == "compile":
        if tier not in ("admin", "technician"):
            raise HTTPException(403, "Requires NS13 Developer / Maintainer / Host / Director")
        res = await run_ssh(ns["ssh_host"], ns["ssh_user"], "bash /home/ubuntu/compile.sh && tail -n 30 /home/ubuntu/compile.log", timeout=180)
        record_audit(user, "ns13", "compile_dmb", "Triggered DreamMaker compile.sh")
        return {"success": res["code"] == 0, "output": res["stdout"] + res["stderr"]}

    if action == "set_admin_rank":
        if tier != "admin":
            raise HTTPException(403, "Only NS13 Director, Host, or Head Admin can assign in-game admin ranks")
        ckey = "".join(ch for ch in body.get("ckey", "").lower() if ch.isalnum())
        rank = body.get("rank", "Admin").strip()
        if not ckey:
            raise HTTPException(400, "Valid ckey required")
        py_cmd = f"""python3 -c '
import pymysql
conn = pymysql.connect(host="127.0.0.1", user="{ns["db_user"]}", password="{ns["db_password"]}", database="{ns["db_name"]}")
cur = conn.cursor()
cur.execute("SELECT id FROM admin WHERE ckey = %s", ({ckey!r},))
if cur.fetchone():
    cur.execute("UPDATE admin SET display_rank = %s WHERE ckey = %s", ({rank!r}, {ckey!r}))
else:
    cur.execute("INSERT INTO admin (ckey, display_rank, permissions_rank) VALUES (%s, %s, 101)", ({ckey!r}, {rank!r}))
conn.commit()
print("Updated", {ckey!r}, "to", {rank!r})
'"""
        res = await run_ssh(ns["ssh_host"], ns["ssh_user"], py_cmd)
        record_audit(user, "ns13", "set_admin_rank", f"{ckey} -> {rank}")
        return {"success": res["code"] == 0, "output": res["stdout"] + res["stderr"]}

    if action == "remove_admin":
        if tier != "admin":
            raise HTTPException(403, "Only NS13 Director, Host, or Head Admin can remove in-game admin ranks")
        ckey = "".join(ch for ch in body.get("ckey", "").lower() if ch.isalnum())
        py_cmd = f"""python3 -c '
import pymysql
conn = pymysql.connect(host="127.0.0.1", user="{ns["db_user"]}", password="{ns["db_password"]}", database="{ns["db_name"]}")
cur = conn.cursor()
cur.execute("DELETE FROM admin WHERE ckey = %s", ({ckey!r},))
conn.commit()
print("Removed admin rank for", {ckey!r})
'"""
        res = await run_ssh(ns["ssh_host"], ns["ssh_user"], py_cmd)
        record_audit(user, "ns13", "remove_admin", ckey)
        return {"success": res["code"] == 0, "output": res["stdout"] + res["stderr"]}

    if action == "unban":
        ban_id = int(body.get("ban_id", 0))
        py_cmd = f"""python3 -c '
import pymysql
conn = pymysql.connect(host="127.0.0.1", user="{ns["db_user"]}", password="{ns["db_password"]}", database="{ns["db_name"]}")
cur = conn.cursor()
cur.execute("UPDATE ban SET unbanned = 1, unbanned_ckey = %s, unbanned_datetime = NOW() WHERE id = %s", ({user["username"]!r}, {ban_id}))
conn.commit()
print("Unbanned ID", {ban_id})
'"""
        res = await run_ssh(ns["ssh_host"], ns["ssh_user"], py_cmd)
        record_audit(user, "ns13", "unban", f"Ban ID #{ban_id}")
        return {"success": res["code"] == 0, "output": res["stdout"] + res["stderr"]}

    raise HTTPException(400, "Unknown NS13 action")

NS13_ALLOWED_FILES = {
    "config.txt": "/home/ubuntu/NovaStation/config/config.txt",
    "motd.txt": "/home/ubuntu/NovaStation/config/motd.txt",
    "admin_ranks.txt": "/home/ubuntu/NovaStation/config/admin_ranks.txt",
    "admins.txt": "/home/ubuntu/NovaStation/config/admins.txt",
}

@app.get("/api/ns13/file")
async def api_ns13_get_file(request: Request, name: str = "motd.txt"):
    user = await get_current_user(request)
    if not user or not user["access"]["ns13"]:
        raise HTTPException(403, "Requires NS13 Staff role")
    if name not in NS13_ALLOWED_FILES:
        raise HTTPException(400, "File not in allowed list")
    cfg = load_config()
    ns = cfg["ns13_server"]
    content = await asyncio.to_thread(sftp_read_sync, ns["ssh_host"], ns["ssh_user"], NS13_ALLOWED_FILES[name])
    return {"name": name, "content": content, "files": list(NS13_ALLOWED_FILES.keys())}

@app.post("/api/ns13/file")
async def api_ns13_save_file(request: Request):
    user = await get_current_user(request)
    if not user or user["access"]["ns13"] not in ("admin", "technician"):
        raise HTTPException(403, "Requires NS13 Admin / Developer / Host / Director")
    body = await request.json()
    name = body.get("name", "")
    content = body.get("content", "")
    if name not in NS13_ALLOWED_FILES:
        raise HTTPException(400, "File not in allowed list")
    cfg = load_config()
    ns = cfg["ns13_server"]
    await asyncio.to_thread(sftp_write_sync, ns["ssh_host"], ns["ssh_user"], NS13_ALLOWED_FILES[name], content)
    record_audit(user, "ns13", "save_file", f"Edited {name} ({len(content)} bytes)")
    return {"success": True, "message": f"Saved {name} on 87.99.133.221"}

@app.get("/api/ns13/logs")
async def api_ns13_logs(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"]["ns13"]:
        raise HTTPException(403, "Requires NS13 Staff role")
    cfg = load_config()
    ns = cfg["ns13_server"]
    res = await run_ssh(
        ns["ssh_host"],
        ns["ssh_user"],
        "echo '=== NOVA STARTUP LOG ===' && tail -n 80 /home/ubuntu/NovaStation/nova-startup.log 2>/dev/null; echo '=== COMPILE LOG ===' && tail -n 40 /home/ubuntu/compile.log 2>/dev/null",
    )
    return {"logs": res["stdout"]}

# ==========================================
# CV Radio Control Panel (/api/radio/*)
# ==========================================
async def azura_request(method: str, path: str, json_body: Any = None) -> tuple[int, Any]:
    cfg = load_config()
    url = f"http://87.99.133.221{path}"
    headers = {
        "Host": "radio.circuitverse.online",
        "X-Forwarded-Proto": "https",
        "X-API-Key": cfg["azuracast_api_key"],
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=15, follow_redirects=True, verify=False) as client:
        r = await client.request(method, url, headers=headers, json=json_body)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, {"text": r.text}

@app.get("/api/radio/status")
async def api_radio_status(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"]["radio"]:
        raise HTTPException(403, "Requires CV-Radio-Access or Dept.Director (CV Radio) Discord role")
    _, np = await azura_request("GET", "/api/nowplaying/1")
    _, st = await azura_request("GET", "/api/station/1/status")
    _, queue = await azura_request("GET", "/api/station/1/queue")
    _, playlists = await azura_request("GET", "/api/station/1/playlists")
    _, streamers = await azura_request("GET", "/api/station/1/streamers")
    return {
        "nowplaying": np,
        "status": st,
        "queue": queue if isinstance(queue, list) else [],
        "playlists": playlists if isinstance(playlists, list) else [],
        "streamers": streamers if isinstance(streamers, list) else [],
        "tier": user["access"]["radio"],
    }

@app.get("/api/radio/requests")
async def api_radio_requests(request: Request, q: str = ""):
    user = await get_current_user(request)
    if not user or not user["access"]["radio"]:
        raise HTTPException(403, "Requires CV-Radio-Access role")
    _, items = await azura_request("GET", "/api/station/1/requests")
    if not isinstance(items, list):
        return {"items": []}
    if q:
        ql = q.lower()
        items = [
            it for it in items
            if ql in (it.get("song", {}).get("text", "") or "").lower()
        ]
    return {"items": items[:60]}

@app.post("/api/radio/action")
async def api_radio_action(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"]["radio"]:
        raise HTTPException(403, "Requires CV-Radio-Access role")
    body = await request.json()
    action = body.get("action")

    if action == "skip":
        code, data = await azura_request("POST", "/api/station/1/backend/skip")
        record_audit(user, "radio", "skip_song", "Skipped current song on CV-Radio")
        return {"success": code < 400, "data": data}

    if action == "restart":
        code, data = await azura_request("POST", "/api/station/1/restart")
        record_audit(user, "radio", "restart_station", "Restarted Icecast & Liquidsoap")
        return {"success": code < 400, "data": data}

    if action in ("frontend_start", "frontend_stop", "frontend_restart"):
        sub = action.split("_")[1]
        code, data = await azura_request("POST", f"/api/station/1/frontend/{sub}")
        record_audit(user, "radio", action, f"Frontend {sub}")
        return {"success": code < 400, "data": data}

    if action in ("backend_start", "backend_stop", "backend_restart"):
        sub = action.split("_")[1]
        code, data = await azura_request("POST", f"/api/station/1/backend/{sub}")
        record_audit(user, "radio", action, f"Backend {sub}")
        return {"success": code < 400, "data": data}

    if action == "clear_queue":
        code, data = await azura_request("DELETE", "/api/station/1/queue")
        record_audit(user, "radio", "clear_queue", "Cleared upcoming broadcast queue")
        return {"success": code < 400, "data": data}

    if action == "queue_song":
        req_id = body.get("request_id")
        code, data = await azura_request("POST", f"/api/station/1/request/{req_id}")
        record_audit(user, "radio", "queue_song", f"Queued song request ID {req_id}")
        return {"success": code < 400, "data": data}

    if action == "toggle_playlist":
        pl_id = int(body.get("playlist_id"))
        code, data = await azura_request("PUT", f"/api/station/1/playlist/{pl_id}/toggle")
        record_audit(user, "radio", "toggle_playlist", f"Toggled playlist #{pl_id}")
        return {"success": code < 400, "data": data}

    if action == "create_streamer":
        username = body.get("streamer_username", "").strip()
        password = body.get("streamer_password", "").strip()
        display_name = body.get("display_name", username).strip()
        if not username or not password:
            raise HTTPException(400, "DJ username and password required")
        code, data = await azura_request(
            "POST",
            "/api/station/1/streamers",
            {
                "streamer_username": username,
                "streamer_password": password,
                "display_name": display_name,
                "is_active": True,
            },
        )
        record_audit(user, "radio", "create_streamer", f"Created DJ account {username}")
        return {"success": code < 400, "data": data}

    if action == "delete_streamer":
        st_id = int(body.get("streamer_id"))
        code, data = await azura_request("DELETE", f"/api/station/1/streamer/{st_id}")
        record_audit(user, "radio", "delete_streamer", f"Deleted DJ account #{st_id}")
        return {"success": code < 400, "data": data}

    raise HTTPException(400, "Unknown radio action")

# ==========================================
# ALL-IN-ONE MASTER CONTROL PANEL (/api/master/*)
# Restricted strictly to Founder, Chief Community Officer, Community Director + Master Password
# ==========================================
async def require_master(request: Request) -> Dict[str, Any]:
    user = await get_current_user(request)
    if not user or not user["access"]["master_eligible"]:
        raise HTTPException(403, "Restricted to Founder, Chief Community Officer, and Community Director")
    if not user["access"]["master_unlocked"]:
        raise HTTPException(428, "Master Password unlock required")
    return user

@app.post("/api/master/unlock")
async def api_master_unlock(request: Request):
    user = await get_current_user(request, refresh_roles=True)
    if not user or not user["access"]["master_eligible"]:
        raise HTTPException(403, "Access Denied: Only Founder, Chief Community Officer, and Community Director may unlock the Master Panel.")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM master_lockout WHERE discord_id = ?", (user["discord_id"],))
    lock = c.fetchone()
    now = time.time()
    if lock and lock["locked_until"] > now:
        rem = int(lock["locked_until"] - now)
        conn.close()
        raise HTTPException(429, f"Too many failed attempts. Locked for {rem}s.")

    body = await request.json()
    pw = body.get("password", "")
    cfg = load_config()
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        pw.encode("utf-8"),
        cfg["master_password_salt"].encode("utf-8"),
        200000,
    ).hex()

    if not hmac.compare_digest(candidate, cfg["master_password_hash"]):
        fails = (lock["fails"] + 1) if lock else 1
        locked_until = (now + 900) if fails >= 5 else 0
        c.execute(
            "INSERT OR REPLACE INTO master_lockout (discord_id, fails, locked_until) VALUES (?, ?, ?)",
            (user["discord_id"], fails, locked_until),
        )
        conn.commit()
        conn.close()
        record_audit(user, "master", "unlock_failed", f"Failed master password attempt #{fails}", request.client.host if request.client else "")
        raise HTTPException(401, f"Invalid Master Password (attempt {fails}/5)")

    c.execute("DELETE FROM master_lockout WHERE discord_id = ?", (user["discord_id"],))
    unlock_until = now + 3600
    c.execute("UPDATE sessions SET master_unlocked_until = ? WHERE session_id = ?", (unlock_until, user["session_id"]))
    conn.commit()
    conn.close()
    record_audit(user, "master", "unlock_success", "Unlocked All-in-One Master Control Panel", request.client.host if request.client else "")
    return {"success": True, "unlocked_until": unlock_until}

@app.get("/api/master/overview")
async def api_master_overview(request: Request):
    await require_master(request)
    cfg = load_config()

    # Query Hetzner Cloud servers if token available
    hetzner_servers = []
    seen_ips = set()
    if cfg.get("hetzner_api_token"):
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                r = await client.get(
                    "https://api.hetzner.cloud/v1/servers",
                    headers={"Authorization": f"Bearer {cfg['hetzner_api_token']}"},
                )
                if r.status_code == 200:
                    for srv in r.json().get("servers", []):
                        ip = srv.get("public_net", {}).get("ipv4", {}).get("ip")
                        seen_ips.add(ip)
                        hetzner_servers.append({
                            "id": srv["id"],
                            "name": srv["name"],
                            "status": srv["status"],
                            "ip": ip,
                            "type": srv.get("server_type", {}).get("name"),
                            "cores": srv.get("server_type", {}).get("cores"),
                            "memory_gb": srv.get("server_type", {}).get("memory"),
                            "disk_gb": srv.get("server_type", {}).get("disk"),
                            "datacenter": srv.get("datacenter", {}).get("name"),
                        })
            except Exception as e:
                logger.debug(f"Hetzner API query error: {e}")

    # Ensure all Hetzner cloud dedicated instances are present
    standard_hetzner = [
        {
            "id": 174435350,
            "name": "circuit-verse-mc",
            "status": "running",
            "ip": "2.31.101.63",
            "type": "cax31",
            "cores": 8,
            "memory_gb": 16,
            "disk_gb": 160,
            "datacenter": "fsn1-dc14 (Falkenstein)",
        },
        {
            "id": 174435351,
            "name": "circuit-verse-pz",
            "status": "running",
            "ip": "2.31.52.69",
            "type": "cx32",
            "cores": 4,
            "memory_gb": 8,
            "disk_gb": 80,
            "datacenter": "fsn1-dc14 (Falkenstein)",
        },
        {
            "id": 174034628,
            "name": "nova-station-13",
            "status": "running",
            "ip": "87.99.133.221",
            "type": "cpx31",
            "cores": 4,
            "memory_gb": 8,
            "disk_gb": 160,
            "datacenter": "ash-dc1 (Ashburn, US-East)",
        },
        {
            "id": 174966750,
            "name": "circuit-verse-general",
            "status": "running",
            "ip": "2.31.173.113",
            "type": "cx32",
            "cores": 4,
            "memory_gb": 8,
            "disk_gb": 80,
            "datacenter": "fsn1-dc14 (Falkenstein)",
        },
    ]
    for def_srv in standard_hetzner:
        if def_srv["ip"] not in seen_ips:
            hetzner_servers.append(def_srv)
            seen_ips.add(def_srv["ip"])

    # Query live service state across all 4 nodes in parallel
    pz_task = run_ssh("127.0.0.1", "root", "systemctl is-active project-zomboid.service zomboid-panel.service cv-panel.service pz-staff-logger.service nginx.service; free -m | awk '/Mem:/ {print $2,$3}'; df -h / | awk 'NR==2 {print $2,$3,$5}'")
    mc_task = run_ssh("2.31.101.63", "root", "systemctl is-active minecraft.service mc-staff-logger.service; free -m | awk '/Mem:/ {print $2,$3}'; df -h / | awk 'NR==2 {print $2,$3,$5}'")
    ns_task = run_ssh("87.99.133.221", "ubuntu", "systemctl is-active novastation.service mariadb.service docker.service; free -m | awk '/Mem:/ {print $2,$3}'; df -h / | awk 'NR==2 {print $2,$3,$5}'")
    gen_task = run_ssh("2.31.173.113", "ubuntu", "systemctl is-active cv-nova-helper.service cv-radio-helper.service docker.service; free -m | awk '/Mem:/ {print $2,$3}'; df -h / | awk 'NR==2 {print $2,$3,$5}'")
    pz_res, mc_res, ns_res, gen_res = await asyncio.gather(pz_task, mc_task, ns_task, gen_task, return_exceptions=True)

    def parse_node(res, svc_names):
        if isinstance(res, Exception):
            return {"error": str(res), "services": {}}
        lines = res["stdout"].strip().splitlines()
        svcs = {}
        for i, name in enumerate(svc_names):
            svcs[name] = lines[i].strip() if i < len(lines) else "unknown"
        mem = lines[len(svc_names)] if len(lines) > len(svc_names) else ""
        disk = lines[len(svc_names) + 1] if len(lines) > len(svc_names) + 1 else ""
        return {"services": svcs, "mem": mem, "disk": disk}

    return {
        "hetzner_servers": hetzner_servers,
        "nodes": {
            "pz_node": parse_node(pz_res, ["project-zomboid.service", "zomboid-panel.service", "cv-panel.service", "pz-staff-logger.service", "nginx.service"]),
            "mc_node": parse_node(mc_res, ["minecraft.service", "mc-staff-logger.service"]),
            "ns13_node": parse_node(ns_res, ["novastation.service", "mariadb.service", "docker.service"]),
            "general_node": parse_node(gen_res, ["cv-nova-helper.service", "cv-radio-helper.service", "docker.service"]),
        },
    }

@app.post("/api/master/node-service")
async def api_master_node_service(request: Request):
    user = await require_master(request)
    body = await request.json()
    node = body.get("node")
    service = body.get("service", "")
    op = body.get("op", "restart")
    if op not in ("start", "stop", "restart"):
        raise HTTPException(400, "Invalid operation")
    allowed_services = {
        "pz_node": ("127.0.0.1", "root", {"project-zomboid.service", "zomboid-panel.service", "cv-panel.service", "pz-staff-logger.service", "nginx.service"}),
        "mc_node": ("2.31.101.63", "root", {"minecraft.service", "mc-staff-logger.service"}),
        "ns13_node": ("87.99.133.221", "ubuntu", {"novastation.service", "mariadb.service", "docker.service"}),
        "general_node": ("2.31.173.113", "ubuntu", {"cv-nova-helper.service", "cv-radio-helper.service", "docker.service"}),
    }
    if node not in allowed_services:
        raise HTTPException(400, "Invalid node")
    host, ssh_user, valid_svcs = allowed_services[node]
    if service not in valid_svcs:
        raise HTTPException(400, "Invalid service")
    prefix = "sudo " if ssh_user != "root" else ""
    res = await run_ssh(host, ssh_user, f"{prefix}systemctl {op} {service}")
    record_audit(user, "master", "node_service", f"{node}: systemctl {op} {service}")
    return {"success": res["code"] == 0, "output": res["stdout"] + res["stderr"]}

@app.post("/api/master/hetzner-power")
async def api_master_hetzner_power(request: Request):
    user = await require_master(request)
    body = await request.json()
    server_id = int(body.get("server_id"))
    action = body.get("action")  # reboot, poweron, poweroff
    if action not in ("reboot", "poweron", "poweroff"):
        raise HTTPException(400, "Invalid Hetzner power action")
    cfg = load_config()
    server_ip_map = {
        174435350: ("2.31.101.63", "root"),
        174538528: ("127.0.0.1", "root"),
        174435351: ("127.0.0.1", "root"),
        174034628: ("87.99.133.221", "ubuntu"),
        174966750: ("2.31.173.113", "ubuntu"),
        174435352: ("2.31.173.113", "ubuntu"),
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"https://api.hetzner.cloud/v1/servers/{server_id}/actions/{action}",
                headers={"Authorization": f"Bearer {cfg['hetzner_api_token']}"},
            )
            if r.status_code < 400:
                record_audit(user, "master", f"hetzner_{action}", f"Hetzner API Server ID {server_id}")
                return {"success": True, "data": r.json()}
    except Exception as e:
        logger.debug(f"Hetzner power API error: {e}")

    # Fallback to SSH power control if server is in another project or API call failed
    if action in ("reboot", "poweroff") and server_id in server_ip_map:
        host, s_user = server_ip_map[server_id]
        prefix = "sudo " if s_user != "root" else ""
        cmd = "systemctl reboot" if action == "reboot" else "systemctl poweroff"
        res = await run_ssh(host, s_user, f"{prefix}{cmd}")
        record_audit(user, "master", f"ssh_node_{action}", f"Node {host} {action}")
        return {"success": True, "data": {"action": {"status": "running", "command": f"ssh_{action}"}}}

    record_audit(user, "master", f"hetzner_{action}_failed", f"Hetzner Server ID {server_id}")
    return {"success": False, "data": {"error": "Server action failed or unavailable"}}

@app.post("/api/master/global-broadcast")
async def api_master_global_broadcast(request: Request):
    user = await require_master(request)
    body = await request.json()
    message = body.get("message", "").strip()
    targets = body.get("targets", ["pz", "mc", "ns13", "discord"])
    discord_channel_id = body.get("channel_id", "1567427447811739698")  # #announcements-and-news
    if not message:
        raise HTTPException(400, "Broadcast message required")
    cfg = load_config()
    results = {}

    if "pz" in targets:
        try:
            out = await run_rcon("127.0.0.1", int(cfg["pz_server"]["rcon_port"]), cfg["pz_server"]["rcon_password"], f'servermsg "[CIRCUIT VERSE BROADCAST] {message}"')
            results["pz"] = out or "Sent"
        except Exception as e:
            results["pz"] = f"Error: {e}"

    if "mc" in targets:
        try:
            mc = cfg["mc_server"]
            out = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], f"say §b§l[CIRCUIT VERSE BROADCAST] §f{message}")
            results["mc"] = out or "Sent"
        except Exception as e:
            results["mc"] = f"Error: {e}"

    if "ns13" in targets:
        try:
            import struct
            import urllib.parse
            ns = cfg.get("ns13_server", {})
            byond_host = ns.get("byond_host", "87.99.133.221")
            byond_port = int(ns.get("byond_port", 7777))
            comms_key = ns.get("comms_key", "")

            params = {
                'control': '1',
                'key': comms_key,
                'action': 'announce',
                'msg': f"[CIRCUIT VERSE BROADCAST] {message}",
                'sender': f"Circuit Verse ({user.get('global_name', 'Executive')})"
            }
            query_str = '?' + urllib.parse.urlencode(params)
            reader, writer = await asyncio.wait_for(asyncio.open_connection(byond_host, byond_port), timeout=6)
            qbytes = query_str.encode('latin1')
            packet = bytes([0, 131]) + struct.pack('>H', len(qbytes) + 6) + bytes([0]*5) + qbytes + bytes([0])
            writer.write(packet)
            await writer.drain()
            resp = await asyncio.wait_for(reader.read(65536), timeout=6)
            writer.close()
            await writer.wait_closed()
            results["ns13"] = "Broadcasted successfully to NSS Cyberiad"
        except Exception as e:
            results["ns13"] = f"Error: {e}"

    if "discord" in targets:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"https://discord.com/api/v10/channels/{discord_channel_id}/messages",
                headers={"Authorization": f"Bot {cfg['discord_bot_token']}"},
                json={
                    "embeds": [
                        {
                            "title": "📢 Circuit Verse Executive Network Broadcast",
                            "description": message,
                            "color": 0x00F0FF,
                            "footer": {"text": f"Broadcast by {user['global_name']} ({user['username']}) • Master Control Panel"},
                        }
                    ]
                },
            )
            results["discord"] = f"HTTP {r.status_code}"

    record_audit(user, "master", "global_broadcast", f"Targets={targets}: {message}")
    return {"success": True, "results": results}

# ---- Discord Bot Config & Cogs ----
@app.get("/api/master/bot-config")
async def api_master_get_bot_config(request: Request):
    await require_master(request)
    content = await asyncio.to_thread(sftp_read_sync, "87.99.133.221", "ubuntu", "/home/ubuntu/CV-Nova-Helper/config.json")
    cogs_res = await run_ssh("87.99.133.221", "ubuntu", "ls -1 /home/ubuntu/CV-Nova-Helper/cogs/*.py | xargs -n1 basename")
    cogs = [c.strip() for c in cogs_res["stdout"].splitlines() if c.strip()]
    return {"config_raw": content, "cogs": cogs}

@app.post("/api/master/bot-config")
async def api_master_save_bot_config(request: Request):
    user = await require_master(request)
    body = await request.json()
    raw = body.get("config_raw", "")
    restart = body.get("restart", True)
    try:
        parsed = json.loads(raw)
        formatted = json.dumps(parsed, indent=2)
    except Exception as e:
        raise HTTPException(400, f"Invalid JSON: {e}")

    await asyncio.to_thread(sftp_write_sync, "87.99.133.221", "ubuntu", "/home/ubuntu/CV-Nova-Helper/config.json", formatted)
    # Also update snapshot on panel host
    with open("/etc/cv-panel/bot_config_snapshot.json", "w", encoding="utf-8") as f:
        f.write(formatted)
    if restart:
        await run_ssh("87.99.133.221", "ubuntu", "sudo systemctl restart cv-nova-helper.service")
    record_audit(user, "master", "save_bot_config", f"Updated bot config.json (restart={restart})")
    return {"success": True, "message": "Saved /home/ubuntu/CV-Nova-Helper/config.json" + (" and restarted bot!" if restart else "")}

@app.get("/api/master/bot-cog")
async def api_master_get_bot_cog(request: Request, name: str = "project_zomboid.py"):
    await require_master(request)
    safe_name = os.path.basename(name)
    if not safe_name.endswith(".py"):
        raise HTTPException(400, "Invalid cog filename")
    content = await asyncio.to_thread(sftp_read_sync, "87.99.133.221", "ubuntu", f"/home/ubuntu/CV-Nova-Helper/cogs/{safe_name}")
    return {"name": safe_name, "content": content}

@app.post("/api/master/bot-cog")
async def api_master_save_bot_cog(request: Request):
    user = await require_master(request)
    body = await request.json()
    safe_name = os.path.basename(body.get("name", ""))
    content = body.get("content", "")
    restart = body.get("restart", True)
    if not safe_name.endswith(".py"):
        raise HTTPException(400, "Invalid cog filename")
    await asyncio.to_thread(sftp_write_sync, "87.99.133.221", "ubuntu", f"/home/ubuntu/CV-Nova-Helper/cogs/{safe_name}", content)
    if restart:
        await run_ssh("87.99.133.221", "ubuntu", "sudo systemctl restart cv-nova-helper.service")
    record_audit(user, "master", "save_bot_cog", f"Updated cog {safe_name} (restart={restart})")
    return {"success": True, "message": f"Saved cogs/{safe_name}" + (" and restarted bot!" if restart else "")}

@app.get("/api/master/bot-logs")
async def api_master_bot_logs(request: Request):
    await require_master(request)
    res = await run_ssh("87.99.133.221", "ubuntu", "sudo journalctl -u cv-nova-helper.service -n 100 --no-pager")
    return {"logs": res["stdout"]}

# ---- Discord Guild Roles, Members & Channels ----
@app.get("/api/master/discord")
async def api_master_discord(request: Request):
    await require_master(request)
    cfg = load_config()
    headers = {"Authorization": f"Bot {cfg['discord_bot_token']}"}
    async with httpx.AsyncClient(timeout=15) as client:
        r_roles, r_mems, r_chs = await asyncio.gather(
            client.get(f"https://discord.com/api/v10/guilds/{cfg['guild_id']}/roles", headers=headers),
            client.get(f"https://discord.com/api/v10/guilds/{cfg['guild_id']}/members?limit=200", headers=headers),
            client.get(f"https://discord.com/api/v10/guilds/{cfg['guild_id']}/channels", headers=headers),
        )
        roles = sorted(r_roles.json(), key=lambda x: -x.get("position", 0)) if r_roles.status_code == 200 else []
        members = r_mems.json() if r_mems.status_code == 200 else []
        channels = r_chs.json() if r_chs.status_code == 200 else []
    return {
        "roles": [{"id": r["id"], "name": r["name"], "color": r["color"], "position": r["position"]} for r in roles if r["name"] != "@everyone"],
        "members": [
            {
                "id": m["user"]["id"],
                "username": m["user"]["username"],
                "display_name": m.get("nick") or m["user"].get("global_name") or m["user"]["username"],
                "roles": m.get("roles", []),
                "bot": m["user"].get("bot", False),
            }
            for m in members
        ],
        "channels": [
            {"id": c["id"], "name": c["name"], "type": c["type"]}
            for c in channels
            if c.get("type") in (0, 5)
        ],
    }

@app.post("/api/master/discord-role")
async def api_master_discord_role(request: Request):
    user = await require_master(request)
    body = await request.json()
    op = body.get("op")  # add, remove, create_role
    cfg = load_config()
    headers = {"Authorization": f"Bot {cfg['discord_bot_token']}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=15) as client:
        if op in ("add", "remove"):
            member_id = body.get("member_id")
            role_id = body.get("role_id")
            method = "PUT" if op == "add" else "DELETE"
            r = await client.request(
                method,
                f"https://discord.com/api/v10/guilds/{cfg['guild_id']}/members/{member_id}/roles/{role_id}",
                headers=headers,
            )
            _role_cache["ts"] = 0
            record_audit(user, "master", f"discord_role_{op}", f"Member {member_id} role {role_id}")
            return {"success": r.status_code < 300, "status": r.status_code}
        if op == "create_role":
            name = body.get("name", "").strip()
            color = int(body.get("color", "00f0ff").lstrip("#"), 16)
            r = await client.post(
                f"https://discord.com/api/v10/guilds/{cfg['guild_id']}/roles",
                headers=headers,
                json={"name": name, "color": color, "hoist": bool(body.get("hoist", False))},
            )
            _role_cache["ts"] = 0
            record_audit(user, "master", "discord_create_role", f"Created role {name}")
            return {"success": r.status_code < 300, "role": r.json()}
    raise HTTPException(400, "Unknown Discord role operation")

# ---- Website Config, Live File Editor & Maintenance Toggle ----
WEB_ALLOWED_FILES = {
    "preview/index.html": "/home/circxust/public_html/preview/index.html",
    "preview/directory.html": "/home/circxust/public_html/preview/directory.html",
    "preview/partnerships.html": "/home/circxust/public_html/preview/partnerships.html",
    "preview/style.css": "/home/circxust/public_html/preview/style.css",
    "preview/script.js": "/home/circxust/public_html/preview/script.js",
    "index.html (Root)": "/home/circxust/public_html/index.html",
    "directory.html (Root)": "/home/circxust/public_html/directory.html",
    "partnerships.html (Root)": "/home/circxust/public_html/partnerships.html",
    "maintenance.html (Root)": "/home/circxust/public_html/maintenance.html",
    "preview/maintenance.html": "/home/circxust/public_html/preview/maintenance.html",
    "style.css (Root)": "/home/circxust/public_html/style.css",
    "script.js (Root)": "/home/circxust/public_html/script.js",
}

@app.get("/api/master/website")
async def api_master_get_website(request: Request, name: str = "preview/index.html"):
    await require_master(request)
    if name not in WEB_ALLOWED_FILES:
        raise HTTPException(400, "Invalid website file")
    cfg = load_config()
    w = cfg["website_server"]
    content = await asyncio.to_thread(sftp_read_sync, w["ssh_host"], w["ssh_user"], WEB_ALLOWED_FILES[name], w["ssh_port"])
    root_head = await run_ssh(w["ssh_host"], w["ssh_user"], "head -n 8 /home/circxust/public_html/index.html", port=w["ssh_port"])
    is_maintenance = "Maintenance Mode" in root_head["stdout"]
    return {
        "name": name,
        "content": content,
        "files": list(WEB_ALLOWED_FILES.keys()),
        "maintenance_mode": is_maintenance,
    }

@app.post("/api/master/website")
async def api_master_save_website(request: Request):
    user = await require_master(request)
    body = await request.json()
    action = body.get("action", "save_file")
    cfg = load_config()
    w = cfg["website_server"]

    if action == "save_file":
        name = body.get("name", "")
        content = body.get("content", "")
        if name not in WEB_ALLOWED_FILES:
            raise HTTPException(400, "Invalid website file")
        await asyncio.to_thread(sftp_write_sync, w["ssh_host"], w["ssh_user"], WEB_ALLOWED_FILES[name], content, w["ssh_port"])
        record_audit(user, "master", "save_website_file", f"Saved {name} ({len(content)} bytes)")
        return {"success": True, "message": f"Deployed {name} to Namecheap web server!"}

    if action == "publish_preview_to_root":
        res = await run_ssh(
            w["ssh_host"],
            w["ssh_user"],
            "cp -f /home/circxust/public_html/index.html /home/circxust/public_html/maintenance_backup.html && cp -f /home/circxust/public_html/preview/index.html /home/circxust/public_html/index.html && cp -f /home/circxust/public_html/preview/style.css /home/circxust/public_html/style.css && cp -f /home/circxust/public_html/preview/script.js /home/circxust/public_html/script.js",
            port=w["ssh_port"],
        )
        record_audit(user, "master", "publish_preview_to_root", "Published preview portal to root circuitverse.online")
        return {"success": res["code"] == 0, "message": "Published full portal to circuitverse.online!"}

    if action in ["enable_maintenance", "toggle_maintenance"]:
        head_res = await run_ssh(w["ssh_host"], w["ssh_user"], "head -n 8 /home/circxust/public_html/index.html", port=w["ssh_port"])
        is_maint = "Maintenance Mode" in head_res.get("stdout", "")
        if is_maint:
            cmd = "if [ -f /home/circxust/public_html/live_site_backup.html ]; then cp -f /home/circxust/public_html/live_site_backup.html /home/circxust/public_html/index.html; elif [ -f /home/circxust/public_html/preview/index.html ]; then cp -f /home/circxust/public_html/preview/index.html /home/circxust/public_html/index.html; fi && chmod 644 /home/circxust/public_html/index.html"
            res = await run_ssh(w["ssh_host"], w["ssh_user"], cmd, port=w["ssh_port"])
            record_audit(user, "master", "disable_maintenance", "Deactivated Maintenance Mode — Full site live on root circuitverse.online")
            return {"success": res["code"] == 0, "maintenance_mode": False, "message": "🟢 Maintenance Mode DEACTIVATED! Full public portal is live."}
        else:
            cmd = "if ! grep -q 'Maintenance Mode' /home/circxust/public_html/index.html; then cp -f /home/circxust/public_html/index.html /home/circxust/public_html/live_site_backup.html; fi && cp -f /home/circxust/public_html/maintenance.html /home/circxust/public_html/index.html && chmod 644 /home/circxust/public_html/index.html"
            res = await run_ssh(w["ssh_host"], w["ssh_user"], cmd, port=w["ssh_port"])
            record_audit(user, "master", "enable_maintenance", "Activated Maintenance Mode on root circuitverse.online")
            return {"success": res["code"] == 0, "maintenance_mode": True, "message": "🚧 Maintenance Mode ACTIVATED on root circuitverse.online! (Full site remains viewable on /preview/)"}

    raise HTTPException(400, "Unknown website action")

# ---- Cloudflare DNS & Cache Manager ----
@app.get("/api/master/cloudflare")
async def api_master_cloudflare(request: Request):
    await require_master(request)
    cfg = load_config()
    headers = {"Authorization": f"Bearer {cfg['cloudflare_api_token']}"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"https://api.cloudflare.com/client/v4/zones/{cfg['cloudflare_zone_id']}/dns_records?per_page=100", headers=headers)
        return {"records": r.json().get("result", [])}

@app.post("/api/master/cloudflare")
async def api_master_cloudflare_action(request: Request):
    user = await require_master(request)
    body = await request.json()
    action = body.get("action")
    cfg = load_config()
    headers = {"Authorization": f"Bearer {cfg['cloudflare_api_token']}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=15) as client:
        if action == "purge_cache":
            r = await client.post(
                f"https://api.cloudflare.com/client/v4/zones/{cfg['cloudflare_zone_id']}/purge_cache",
                headers=headers,
                json={"purge_everything": True},
            )
            record_audit(user, "master", "cloudflare_purge", "Purged all Cloudflare cache")
            return {"success": r.status_code < 400, "data": r.json()}
        if action == "create_dns":
            rec = {
                "type": body.get("type", "A"),
                "name": body.get("name", ""),
                "content": body.get("content", ""),
                "proxied": bool(body.get("proxied", True)),
                "ttl": 1,
            }
            r = await client.post(
                f"https://api.cloudflare.com/client/v4/zones/{cfg['cloudflare_zone_id']}/dns_records",
                headers=headers,
                json=rec,
            )
            record_audit(user, "master", "cloudflare_create_dns", f"{rec['type']} {rec['name']} -> {rec['content']}")
            return {"success": r.status_code < 400, "data": r.json()}
        if action == "delete_dns":
            rec_id = body.get("record_id")
            r = await client.delete(
                f"https://api.cloudflare.com/client/v4/zones/{cfg['cloudflare_zone_id']}/dns_records/{rec_id}",
                headers=headers,
            )
            record_audit(user, "master", "cloudflare_delete_dns", f"Deleted DNS record {rec_id}")
            return {"success": r.status_code < 400, "data": r.json()}
    raise HTTPException(400, "Unknown Cloudflare action")

# ---- Access Matrix, Password Change & Audit Log ----
@app.get("/api/master/security")
async def api_master_security(request: Request):
    await require_master(request)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 150")
    logs = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"matrix": load_matrix(), "audit_log": logs}

@app.post("/api/master/security")
async def api_master_security_update(request: Request):
    user = await require_master(request)
    body = await request.json()
    action = body.get("action")
    if action == "save_matrix":
        matrix = body.get("matrix")
        if not isinstance(matrix, dict):
            raise HTTPException(400, "Invalid matrix")
        with open(MATRIX_PATH, "w", encoding="utf-8") as f:
            json.dump(matrix, f, indent=2)
        record_audit(user, "master", "save_access_matrix", "Updated panel Discord role access matrix")
        return {"success": True, "message": "Access matrix updated!"}
    if action == "change_master_password":
        new_pw = body.get("new_password", "")
        if len(new_pw) < 12:
            raise HTTPException(400, "New master password must be at least 12 characters")
        cfg = load_config()
        salt = secrets.token_hex(16)
        pw_hash = hashlib.pbkdf2_hmac("sha256", new_pw.encode("utf-8"), salt.encode("utf-8"), 200000).hex()
        cfg["master_password_salt"] = salt
        cfg["master_password_hash"] = pw_hash
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        record_audit(user, "master", "change_master_password", "Rotated Master Control Panel secret password")
        return {"success": True, "message": "Master password updated!"}
    raise HTTPException(400, "Unknown security action")

from panel_extensions import setup_extensions
setup_extensions(app, {
    "load_config": load_config,
    "get_current_user": get_current_user,
    "get_guild_role_map": get_guild_role_map,
    "run_ssh": run_ssh,
    "run_rcon": run_rcon,
    "record_audit": record_audit,
    "sftp_read_sync": sftp_read_sync,
    "sftp_write_sync": sftp_write_sync,
    "verify_rank_assignment_permission": verify_rank_assignment_permission,
})

from website_and_backup_ext import setup_website_and_backup
setup_security_failsafe(app, {
    "load_config": load_config,
    "get_current_user": get_current_user,
    "run_rcon": run_rcon,
    "run_ssh": run_ssh,
    "record_audit": record_audit,
})

from ddos_defense import setup_ddos_defense
setup_ddos_defense(app, {
    "load_config": load_config,
    "get_current_user": get_current_user,
    "run_ssh": run_ssh,
    "record_audit": record_audit,
})
setup_website_and_backup(app, {
    "load_config": load_config,
    "get_current_user": get_current_user,
    "run_ssh": run_ssh,
    "record_audit": record_audit,
    "sftp_read_sync": sftp_read_sync,
    "sftp_write_sync": sftp_write_sync,
})

app.mount("/", StaticFiles(directory="/opt/cv-panel/static", html=True), name="static")
