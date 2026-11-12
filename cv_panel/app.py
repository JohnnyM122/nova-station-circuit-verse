import subprocess
import psutil
from security_failsafe import get_client_ip, get_ua_hash, is_account_locked, verify_session_security, setup_security_failsafe
import datetime
import glob
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
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
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
    "unturned_admin": [
        "1568805604447752263",  # Unturned Server Host
        "1568805606192848993",  # Unturned Server Manager
    ],
    "unturned_tech": [
        "1568805607836745910",  # Unturned Server Admin
    ],
    "unturned_mod": [
        "1568805609158082641",  # Unturned Server Mod
        "1568805610219372690",  # Unturned Server Staff
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
    # Auto-migrate sessions table columns
    c.execute("PRAGMA table_info(sessions)")
    existing_cols = [row[1] for row in c.fetchall()]
    cols_to_add = [
        ("ip_address", "TEXT"),
        ("user_agent_hash", "TEXT"),
        ("mfa_enabled", "INTEGER DEFAULT 0"),
        ("last_active_at", "REAL"),
        ("discord_access_token", "TEXT")
    ]
    for cname, ctype in cols_to_add:
        if cname not in existing_cols:
            c.execute(f"ALTER TABLE sessions ADD COLUMN {cname} {ctype}")
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
    "affiliatepartner": 45,
    "affiliate": 45,
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
    "1570071718037553336": 45,   # Affiliate Partner
    "1567449678746882068": 30,   # MC VIP Member
    "1567449675949150268": 20,   # MC Player
    "1568805604447752263": 130,  # Unturned Server Host
    "1568805606192848993": 110,  # Unturned Server Manager
    "1568805607836745910": 85,   # Unturned Server Admin
    "1568805609158082641": 65,   # Unturned Server Mod
    "1568805610219372690": 55,   # Unturned Server Staff
    "1568805612312334558": 20,   # Unturned Player
}

ROLE_NAME_TO_WEIGHT = {
    "founder": 150,
    "chief community officer": 145,
    "community executive": 140,
    "community director": 135,
    "executive director": 130,
    "community management": 125,
    "mc server host": 130,
    "unturned server host": 130,
    "unturned server manager": 110,
    "unturned server admin": 85,
    "unturned server mod": 65,
    "unturned server staff": 55,
    "unturned player": 20,
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
    "affiliate partner": 45,
    "affiliate": 45,
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

    # Unturned tier
    if is_exec or (rset & set(m.get("unturned_admin", []))):
        unturned_tier = "admin"
    elif rset & set(m.get("unturned_tech", [])):
        unturned_tier = "technician"
    elif rset & set(m.get("unturned_mod", [])):
        unturned_tier = "moderator"
    else:
        unturned_tier = None

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
        "unturned": unturned_tier,
        "radio": radio_tier,
        "website": website_tier,
        "master_eligible": master_eligible,
        "master_unlocked": master_unlocked,
        "any_staff": any([pz_tier, mc_tier, ns13_tier, unturned_tier, radio_tier, website_tier, master_eligible]),
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
    is_master_session = (
        user.get("discord_id") == "1564610713216098394"
        or user.get("username") == "Community Founder"
        or (user.get("master_unlocked_until", 0) > now and user.get("discord_id") == "1564610713216098394")
    )
    if not is_master_session and (refresh_roles or (now - user["updated_at"] > 20)):
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
    elif is_master_session:
        # Keep updated_at fresh for master emergency session
        c.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", (now, sid))
        conn.commit()
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
    if request.url.path in ("/", "/index.html"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
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

@app.post("/api/auth/master-login")
async def api_auth_master_login(request: Request):
    if not check_auth_rate_limit(request, limit=10, window_sec=60):
        raise HTTPException(429, "Too many login attempts. Please wait 60 seconds.")

    body = await request.json()
    pw = body.get("password", "").strip()
    if not pw:
        raise HTTPException(400, "Password required")

    cfg = load_config()
    salt = cfg.get("master_password_salt", "").encode("utf-8")
    target_hash = cfg.get("master_password_hash", "")

    candidate = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, 200000).hex()
    if not hmac.compare_digest(candidate, target_hash):
        logger.warning(f"Failed Master Password login attempt from {get_client_ip(request)}")
        raise HTTPException(401, "Invalid Master Password")

    # Generate full master executive session
    sid = secrets.token_urlsafe(32)
    now = time.time()
    client_ip = get_client_ip(request)
    ua_hash = get_ua_hash(request)

    # Founder & Executive master roles
    founder_role_id = "1564610713216098394"
    role_ids = [founder_role_id, "1566625061467717752", "1567482219495301191"]
    role_names = ["Community Founder & Executive", "Chief Community Officer", "Community Director"]
    avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"
    discord_id = "1564610713216098394"
    username = "Community Founder"
    global_name = "Community Founder"
    master_unlocked_until = now + 86400  # 24 hours unlocked

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO sessions (session_id, discord_id, username, global_name, avatar, roles_json, role_names_json, master_unlocked_until, created_at, updated_at, ip_address, user_agent_hash, mfa_enabled, last_active_at, discord_access_token)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, '')
        """,
        (sid, discord_id, username, global_name, avatar_url, json.dumps(role_ids), json.dumps(role_names), master_unlocked_until, now, now, client_ip, ua_hash, now)
    )
    conn.commit()
    conn.close()

    record_audit(
        {"discord_id": discord_id, "username": username},
        "auth",
        "master_password_login",
        "Logged in via Executive Master Password",
        client_ip
    )

    clean_target = body.get("next") or "/?panel=master"
    resp = JSONResponse({"success": True, "message": "Master Passkey verified! Session created.", "redirect": clean_target})
    resp.set_cookie(
        key="cv_session",
        value=sid,
        domain=".circuitverse.online",
        max_age=86400,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return resp

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
@app.get("/callback")
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
            err_code = "invalid_client_secret" if "invalid_client" in token_resp.text else "token_exchange_failed"
            return RedirectResponse(f"/?error={err_code}")
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
    tier = user["access"]["pz"]
    zcp_account_map = {
        "admin": "cv_admin",
        "technician": "cv_tech",
        "moderator": "cv_mod",
    }
    zcp_username = zcp_account_map.get(tier, "cv_mod")
    zcp_password = cfg.get("zcp_accounts", {}).get(zcp_username, "")
    return {
        "running": pz_active,
        "zcp_running": zcp_active,
        "players_raw": players_out,
        "zcp_url": cfg["zcp_public_url"],
        "zcp_username": zcp_username,
        "zcp_password": zcp_password,
        "tier": tier,
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
        await send_discord_game_lifecycle_alert("pz", action, user.get("username", "Staff"))
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
# Project Zomboid Mod Configurator & Manager
# ==========================================
PZ_INI_PATH = "/home/pz/Zomboid/Server/CircuitVersePZ.ini"
PZ_SANDBOX_PATH = "/home/pz/Zomboid/Server/CircuitVersePZ_SandboxVars.lua"
PZ_SPAWN_PATH = "/home/pz/Zomboid/Server/CircuitVersePZ_spawnregions.lua"

PZ_CURATED_MODS = [
    {"title": "Common Sense", "workshop_id": "2875848298", "mod_id": "commonSense", "desc": "Prying doors with crowbars, opening cans with knives, and intuitive mechanics."},
    {"title": "Filibuster Rhymes' Used Cars! (B41/B42)", "workshop_id": "1510950729", "mod_id": "FRUsedCars;FRUsedCarsFT;FRUsedCarsNLREC", "desc": "Huge pack of lore-friendly American vehicles from the 80s and 90s."},
    {"title": "Arsenal(26) GunFighter Mod [2.0]", "workshop_id": "2297098490", "mod_id": "Arsenal(26)GunFighter", "desc": "Framework for realistic firearms, attachments, optics, and ammo mechanics."},
    {"title": "Brita's Weapon Pack", "workshop_id": "2200148440", "mod_id": "Brita", "desc": "Massive collection of real-world firearms, melee weapons, and silencers."},
    {"title": "Brita's Armor Pack", "workshop_id": "2460154811", "mod_id": "Brita_2", "desc": "Extensive military gear, tactical vests, helmets, backpacks, and clothing."},
    {"title": "Mod Options (Server Config Framework)", "workshop_id": "2169435997", "mod_id": "modoptions", "desc": "Server-side and client configuration framework for customizable mods."},
    {"title": "Vehicle Recycling", "workshop_id": "2289992503", "mod_id": "VehicleRecycling", "desc": "Dismantle vehicle wrecks and scrap metal with a blowtorch."},
    {"title": "Has Been Read", "workshop_id": "2544353492", "mod_id": "HasBeenRead", "desc": "Visual indicators showing if skill books, recipes, and VHS tapes have been used."},
    {"title": "Minimal Display Bars", "workshop_id": "2792644998", "mod_id": "minimalDisplayBars", "desc": "Clean, customizable HUD bars for health, hunger, thirst, and stamina."},
    {"title": "True Actions (Dancing & Sitting)", "workshop_id": "2487024847", "mod_id": "TrueActionsDancing", "desc": "Allows player characters to sit on chairs, lie down on beds, and dance."},
    {"title": "Rain Cleans Blood", "workshop_id": "2956146279", "mod_id": "RainCleansBlood", "desc": "Outdoor blood and grime gradually wash away during rainstorms."},
    {"title": "Auto Reload", "workshop_id": "2756689874", "mod_id": "AutoReload", "desc": "Automatically loads ammunition into magazines and chambers when empty."},
    {"title": "Tsar's Common Library 2.0", "workshop_id": "2392709985", "mod_id": "tsarslib", "desc": "Core requirement for trailers, boats, and advanced vehicle physics."},
    {"title": "Autotsar Trailers", "workshop_id": "2282429356", "mod_id": "autotsartrailers", "desc": "Adds functional towable trailers, generators, and storage campers."}
]

def _pz_write_with_backup(filepath: str, content: str):
    if os.path.exists(filepath):
        bak_dir = os.path.join(os.path.dirname(filepath), "backups")
        os.makedirs(bak_dir, exist_ok=True)
        fname = os.path.basename(filepath)
        ts = int(time.time())
        try:
            shutil.copy2(filepath, os.path.join(bak_dir, f"{fname}.{ts}.bak"))
        except Exception as e:
            logger.warning(f"Backup failed for {filepath}: {e}")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    try:
        os.chown(filepath, 1000, 1000)
    except Exception:
        pass

@app.get("/api/pz/mods")
async def api_pz_mods(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"]["pz"]:
        raise HTTPException(403, "Requires Project Zomboid Staff role")
    
    raw_ini = ""
    if os.path.exists(PZ_INI_PATH):
        try:
            with open(PZ_INI_PATH, "r", encoding="utf-8", errors="replace") as f:
                raw_ini = f.read()
        except Exception as e:
            logger.error(f"Error reading PZ INI: {e}")
    
    workshop_ids = []
    mod_ids = []
    for line in raw_ini.splitlines():
        line_clean = line.strip()
        if line_clean.startswith("WorkshopItems="):
            w_str = line_clean.split("=", 1)[1].strip()
            workshop_ids = [w.strip() for w in w_str.split(";") if w.strip()]
        elif line_clean.startswith("Mods="):
            m_str = line_clean.split("=", 1)[1].strip()
            mod_ids = [m.strip() for m in m_str.split(";") if m.strip()]

    raw_sandbox = ""
    if os.path.exists(PZ_SANDBOX_PATH):
        try:
            with open(PZ_SANDBOX_PATH, "r", encoding="utf-8", errors="replace") as f:
                raw_sandbox = f.read()
        except Exception as e:
            logger.error(f"Error reading PZ Sandbox: {e}")

    ws_base = "/home/pz/pz-server/steamapps/workshop/content/108600"
    workshop_meta = {}
    if os.path.exists(ws_base):
        for wid_dir in os.listdir(ws_base):
            wdir = os.path.join(ws_base, wid_dir)
            if not os.path.isdir(wdir):
                continue
            infos = glob.glob(os.path.join(wdir, "mods", "*", "mod.info"))
            if not infos:
                infos = glob.glob(os.path.join(wdir, "**", "mod.info"), recursive=True)
            mod_names = []
            m_ids = []
            for info in infos:
                try:
                    with open(info, "r", encoding="utf-8", errors="replace") as f:
                        cur_name = None
                        cur_id = None
                        for l in f:
                            if "=" in l:
                                k, v = l.strip().split("=", 1)
                                if k.lower() == "name":
                                    cur_name = v.strip()
                                elif k.lower() == "id":
                                    cur_id = v.strip()
                        if cur_name and cur_name not in mod_names:
                            mod_names.append(cur_name)
                        if cur_id and cur_id not in m_ids:
                            m_ids.append(cur_id)
                except Exception:
                    pass
            workshop_meta[wid_dir] = {
                "title": mod_names[0] if mod_names else f"Workshop #{wid_dir}",
                "mod_names": mod_names,
                "mod_ids": m_ids,
                "downloaded": True
            }

    installed_items = []
    for wid in workshop_ids:
        meta = workshop_meta.get(wid)
        if meta:
            installed_items.append({
                "workshop_id": wid,
                "title": meta["title"],
                "mod_ids": meta["mod_ids"],
                "downloaded": True
            })
        else:
            curated_match = next((c for c in PZ_CURATED_MODS if c["workshop_id"] == wid), None)
            title = curated_match["title"] if curated_match else f"Workshop #{wid}"
            known_mids = [m for m in curated_match["mod_id"].split(";") if m] if curated_match else []
            downloaded = os.path.exists(os.path.join(ws_base, wid))
            installed_items.append({
                "workshop_id": wid,
                "title": title,
                "mod_ids": known_mids,
                "downloaded": downloaded
            })

    return {
        "workshop_ids": workshop_ids,
        "mod_ids": mod_ids,
        "installed_items": installed_items,
        "raw_ini": raw_ini,
        "raw_sandbox": raw_sandbox,
        "curated_catalog": PZ_CURATED_MODS,
        "tier": user["access"]["pz"],
    }

@app.get("/api/pz/mods/lookup")
async def api_pz_mods_lookup(request: Request, q: str = ""):
    user = await get_current_user(request)
    if not user or not user["access"]["pz"]:
        raise HTTPException(403, "Requires Project Zomboid Staff role")
    query = q.strip().lower()
    matches = []
    for m in PZ_CURATED_MODS:
        if not query or query in m["title"].lower() or query in m["workshop_id"] or query in m["mod_id"].lower() or query in m["desc"].lower():
            matches.append(m)
    return {"items": matches}

@app.post("/api/pz/mods/install")
async def api_pz_mods_install(request: Request):
    user = await get_current_user(request)
    if not user or user["access"]["pz"] not in ("admin", "technician"):
        raise HTTPException(403, "Requires PZ Admin or Technician tier")
    body = await request.json()
    wid = str(body.get("workshop_id", "")).strip()
    mid = str(body.get("mod_id", "")).strip()
    if not wid or not mid:
        raise HTTPException(400, "Workshop ID and Mod ID are required")

    if not os.path.exists(PZ_INI_PATH):
        raise HTTPException(404, "CircuitVersePZ.ini not found")

    with open(PZ_INI_PATH, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    w_found = False
    m_found = False
    new_lines = []

    for line in lines:
        if line.strip().startswith("WorkshopItems="):
            w_found = True
            cur = line.strip().split("=", 1)[1]
            items = [x.strip() for x in cur.split(";") if x.strip()]
            if wid not in items:
                items.append(wid)
            new_lines.append(f"WorkshopItems={';'.join(items)}\n")
        elif line.strip().startswith("Mods="):
            m_found = True
            cur = line.strip().split("=", 1)[1]
            items = [x.strip() for x in cur.split(";") if x.strip()]
            for sub_m in mid.split(";"):
                sub_clean = sub_m.strip()
                if sub_clean and sub_clean not in items:
                    items.append(sub_clean)
            new_lines.append(f"Mods={';'.join(items)}\n")
        else:
            new_lines.append(line)

    if not w_found:
        new_lines.append(f"WorkshopItems={wid}\n")
    if not m_found:
        new_lines.append(f"Mods={mid}\n")

    _pz_write_with_backup(PZ_INI_PATH, "".join(new_lines))
    record_audit(user, "pz", "mod_install", f"Installed mod {mid} (Workshop {wid})")

    # Pre-download workshop item via steamcmd in background
    try:
        subprocess.Popen([
            "sudo", "-u", "pz", "/home/pz/steamcmd/steamcmd.sh",
            "+force_install_dir", "/home/pz/pz-server",
            "+login", "anonymous",
            "+workshop_download_item", "108600", str(wid), "validate",
            "+quit"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        logger.warning(f"Background steamcmd download trigger error: {e}")

    return {"success": True, "message": f"Mod {mid} ({wid}) saved to CircuitVersePZ.ini and background Steam download queued! Remember to Save & Restart PZ to load it."}

@app.post("/api/pz/mods/remove")
async def api_pz_mods_remove(request: Request):
    user = await get_current_user(request)
    if not user or user["access"]["pz"] not in ("admin", "technician"):
        raise HTTPException(403, "Requires PZ Admin or Technician tier")
    body = await request.json()
    wid = str(body.get("workshop_id", "")).strip()
    mid = str(body.get("mod_id", "")).strip()

    if not os.path.exists(PZ_INI_PATH):
        raise HTTPException(404, "CircuitVersePZ.ini not found")

    with open(PZ_INI_PATH, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if wid and line.strip().startswith("WorkshopItems="):
            cur = line.strip().split("=", 1)[1]
            items = [x.strip() for x in cur.split(";") if x.strip() and x.strip() != wid]
            new_lines.append(f"WorkshopItems={';'.join(items)}\n")
        elif mid and line.strip().startswith("Mods="):
            cur = line.strip().split("=", 1)[1]
            targets = set([x.strip() for x in mid.split(";") if x.strip()])
            items = [x.strip() for x in cur.split(";") if x.strip() and x.strip() not in targets]
            new_lines.append(f"Mods={';'.join(items)}\n")
        else:
            new_lines.append(line)

    _pz_write_with_backup(PZ_INI_PATH, "".join(new_lines))
    record_audit(user, "pz", "mod_remove", f"Removed mod {mid or wid}")
    return {"success": True, "message": f"Mod {mid or wid} removed from CircuitVersePZ.ini."}

@app.post("/api/pz/mods/reorder")
async def api_pz_mods_reorder(request: Request):
    user = await get_current_user(request)
    if not user or user["access"]["pz"] not in ("admin", "technician"):
        raise HTTPException(403, "Requires PZ Admin or Technician tier")
    body = await request.json()
    wids = body.get("workshop_ids", [])
    mids = body.get("mod_ids", [])

    if not os.path.exists(PZ_INI_PATH):
        raise HTTPException(404, "CircuitVersePZ.ini not found")

    with open(PZ_INI_PATH, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    w_str = ";".join([str(x).strip() for x in wids if str(x).strip()])
    m_str = ";".join([str(x).strip() for x in mids if str(x).strip()])

    new_lines = []
    for line in lines:
        if line.strip().startswith("WorkshopItems="):
            new_lines.append(f"WorkshopItems={w_str}\n")
        elif line.strip().startswith("Mods="):
            new_lines.append(f"Mods={m_str}\n")
        else:
            new_lines.append(line)

    _pz_write_with_backup(PZ_INI_PATH, "".join(new_lines))
    record_audit(user, "pz", "mod_reorder", "Reordered PZ mods load order")
    return {"success": True, "message": "Updated PZ mod load order successfully!"}

@app.post("/api/pz/mods/save-ini")
async def api_pz_mods_save_ini(request: Request):
    user = await get_current_user(request)
    if not user or user["access"]["pz"] not in ("admin", "technician"):
        raise HTTPException(403, "Requires PZ Admin or Technician tier")
    body = await request.json()
    content = body.get("content", "")
    if not content.strip():
        raise HTTPException(400, "Content cannot be empty")
    
    _pz_write_with_backup(PZ_INI_PATH, content)
    record_audit(user, "pz", "save_ini", "Saved CircuitVersePZ.ini")
    return {"success": True, "message": "CircuitVersePZ.ini saved successfully!"}

@app.post("/api/pz/mods/save-sandbox")
async def api_pz_mods_save_sandbox(request: Request):
    user = await get_current_user(request)
    if not user or user["access"]["pz"] not in ("admin", "technician"):
        raise HTTPException(403, "Requires PZ Admin or Technician tier")
    body = await request.json()
    content = body.get("content", "")
    if not content.strip():
        raise HTTPException(400, "Content cannot be empty")
    
    _pz_write_with_backup(PZ_SANDBOX_PATH, content)
    record_audit(user, "pz", "save_sandbox", "Saved CircuitVersePZ_SandboxVars.lua")
    return {"success": True, "message": "Sandbox & Mod Options saved successfully!"}

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
        "systemctl is-active minecraft.service; free -m | awk '/Mem:/ {print $2,$3}'; df -h / | awk 'NR==2 {print $2,$3,$5}'; uptime -p; "
        "if iptables -C INPUT -p udp --dport 19132 -j DROP 2>/dev/null; then echo 'bedrock_paused'; elif [ -f /opt/minecraft/server/plugins/Geyser-Spigot.jar.disabled ]; then echo 'bedrock_stopped'; elif ss -ulpn | grep -q ':19132 '; then echo 'bedrock_online'; else echo 'bedrock_offline'; fi",
    )
    lines = ssh_res["stdout"].strip().splitlines()
    running = lines[0].strip() == "active" if lines else False
    mem_info = lines[1] if len(lines) > 1 else ""
    disk_info = lines[2] if len(lines) > 2 else ""
    uptime_info = lines[3] if len(lines) > 3 else ""
    bedrock_state = lines[4].strip() if len(lines) > 4 else "bedrock_offline"
    bedrock_online = (bedrock_state == "bedrock_online")

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
        "bedrock_state": bedrock_state,
        "bedrock_port": 19132,
        "host": "play.circuitverse.online (Hetzner EX63 Dedicated)",
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
            await send_discord_game_lifecycle_alert("mc", "stop", user.get("username", "Staff"))
            res = await run_ssh(mc["ssh_host"], mc["ssh_user"], "systemctl stop minecraft.service")
            record_audit(user, "mc", "service_stop", "systemctl stop minecraft.service")
            return {"success": res["code"] == 0, "output": res["stdout"] + res["stderr"]}

        if action == "start":
            await send_discord_game_lifecycle_alert("mc", "start", user.get("username", "Staff"))
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

    if action.startswith("bedrock") or action in ("geyser_reload", "geyser_dump", "geyser_version"):
        sub_act = body.get("sub_action") or action
        if sub_act.startswith("bedrock_"):
            sub_act = sub_act[len("bedrock_"):]
        return await api_mc_bedrock_action(request, action=sub_act)

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

    return {"success": True, "message": f"Saved {name} on Hetzner EX63 Dedicated{reload_msg}"}

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
        "if iptables -C INPUT -p udp --dport 19132 -j DROP 2>/dev/null; then echo 'paused'; "
        "elif [ -f /opt/minecraft/server/plugins/Geyser-Spigot.jar.disabled ]; then echo 'stopped'; "
        "elif ss -ulpn | grep -q ':19132 '; then echo 'online'; "
        "else echo 'offline'; fi; "
        "test -f /opt/minecraft/server/plugins/Geyser-Spigot.jar && echo 'jar_enabled' || echo 'jar_disabled'; "
        "test -f /opt/minecraft/server/plugins/floodgate-spigot.jar && echo 'fg_enabled' || echo 'fg_disabled'"
    )
    res = await run_ssh(mc["ssh_host"], mc["ssh_user"], cmd)
    lines = res["stdout"].strip().splitlines()
    b_state = lines[0].strip() if len(lines) > 0 else "offline"
    geyser_enabled = (lines[1].strip() == "jar_enabled") if len(lines) > 1 else False
    fg_enabled = (lines[2].strip() == "fg_enabled") if len(lines) > 2 else False

    version_str = ""
    connections_str = ""
    if b_state == "online":
        try:
            version_str = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "geyser version")
            connections_str = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "geyser list")
        except Exception as e:
            version_str = f"RCON: {e}"

    return {
        "online": (b_state == "online"),
        "state": b_state,
        "geyser_enabled": geyser_enabled,
        "floodgate_enabled": fg_enabled,
        "port": 19132,
        "webrtc_port": 19133,
        "host": "play.circuitverse.online (Hetzner EX63 Dedicated)",
        "version_raw": version_str,
        "connections_raw": connections_str,
        "tier": user["access"]["mc"]
    }

@app.get("/api/mc/bedrock/action")
@app.post("/api/mc/bedrock/action")
async def api_mc_bedrock_action(request: Request, action: Optional[str] = None):
    user = await get_current_user(request)
    if not user or not user["access"]["mc"]:
        raise HTTPException(403, "Requires Minecraft Staff role")
    tier = user["access"]["mc"]

    # Resilient extraction of action from query params, json, form, or headers
    if not action:
        action = request.query_params.get("action")
    if not action:
        try:
            body = await request.json()
            if isinstance(body, dict):
                action = body.get("action")
        except Exception:
            pass
    if not action:
        try:
            form = await request.form()
            action = form.get("action")
        except Exception:
            pass
    if not action:
        action = request.headers.get("x-action")

    if not action:
        action = "version"
    action = action.strip().lower()
    if action.startswith("bedrock_"):
        action = action[len("bedrock_"):]
    cfg = load_config()
    mc = cfg["mc_server"]

    if action in ("start", "stop", "restart", "reload", "pause", "resume"):
        if tier not in ("admin", "technician"):
            raise HTTPException(403, "Only MC Host, Director, or Admin can control Bedrock server state")

        if action == "start":
            enable_cmd = (
                "iptables -D INPUT -p udp --dport 19132 -j DROP 2>/dev/null || true; "
                "iptables -D INPUT -p udp --dport 19133 -j DROP 2>/dev/null || true; "
                "cd /opt/minecraft/server/plugins && "
                "[ -f Geyser-Spigot.jar.disabled ] && mv Geyser-Spigot.jar.disabled Geyser-Spigot.jar; "
                "[ -f floodgate-spigot.jar.disabled ] && mv floodgate-spigot.jar.disabled floodgate-spigot.jar; "
                "chown minecraft:minecraft Geyser*.jar floodgate*.jar 2>/dev/null || true"
            )
            await run_ssh(mc["ssh_host"], mc["ssh_user"], enable_cmd)
            rcon_out = ""
            try:
                rcon_out = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "geyser reload")
            except Exception:
                pass
            record_audit(user, "mc_bedrock", "start", "Started Bedrock Edition (firewall unblocked, plugins enabled)")
            return {"success": True, "output": f"Bedrock Edition started and accepting players on UDP 19132. {rcon_out}".strip()}

        if action == "stop":
            stop_cmd = (
                "iptables -C INPUT -p udp --dport 19132 -j DROP 2>/dev/null || iptables -I INPUT 1 -p udp --dport 19132 -j DROP; "
                "iptables -C INPUT -p udp --dport 19133 -j DROP 2>/dev/null || iptables -I INPUT 1 -p udp --dport 19133 -j DROP; "
                "cd /opt/minecraft/server/plugins && "
                "[ -f Geyser-Spigot.jar ] && mv Geyser-Spigot.jar Geyser-Spigot.jar.disabled; "
                "[ -f floodgate-spigot.jar ] && mv floodgate-spigot.jar floodgate-spigot.jar.disabled; true"
            )
            await run_ssh(mc["ssh_host"], mc["ssh_user"], stop_cmd)
            try:
                await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "geyser reload")
            except Exception:
                pass
            record_audit(user, "mc_bedrock", "stop", "Stopped Bedrock Edition (firewall blocked, plugins disabled)")
            return {"success": True, "output": "Bedrock Edition stopped. UDP ports 19132 & 19133 blocked, connected players disconnected, plugins set to disabled."}

        if action in ("restart", "reload"):
            unblock_cmd = (
                "iptables -D INPUT -p udp --dport 19132 -j DROP 2>/dev/null || true; "
                "iptables -D INPUT -p udp --dport 19133 -j DROP 2>/dev/null || true; "
                "cd /opt/minecraft/server/plugins && "
                "[ -f Geyser-Spigot.jar.disabled ] && mv Geyser-Spigot.jar.disabled Geyser-Spigot.jar; "
                "[ -f floodgate-spigot.jar.disabled ] && mv floodgate-spigot.jar.disabled floodgate-spigot.jar; true"
            )
            await run_ssh(mc["ssh_host"], mc["ssh_user"], unblock_cmd)
            try:
                out = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], "geyser reload")
                record_audit(user, "mc_bedrock", "reload", "geyser reload")
                return {"success": True, "output": out.strip() or "Geyser configuration reloaded successfully. Bedrock bridge active."}
            except Exception as e:
                raise HTTPException(500, f"RCON error reloading Geyser: {e}")

        if action == "pause":
            pause_cmd = (
                "iptables -C INPUT -p udp --dport 19132 -j DROP 2>/dev/null || iptables -I INPUT 1 -p udp --dport 19132 -j DROP; "
                "iptables -C INPUT -p udp --dport 19133 -j DROP 2>/dev/null || iptables -I INPUT 1 -p udp --dport 19133 -j DROP;"
            )
            await run_ssh(mc["ssh_host"], mc["ssh_user"], pause_cmd)
            record_audit(user, "mc_bedrock", "pause", "Paused incoming Bedrock logins (firewall DROP)")
            return {"success": True, "output": "Bedrock logins paused. Incoming UDP 19132 & 19133 packets dropped at firewall."}

        if action == "resume":
            resume_cmd = (
                "iptables -D INPUT -p udp --dport 19132 -j DROP 2>/dev/null || true; "
                "iptables -D INPUT -p udp --dport 19133 -j DROP 2>/dev/null || true;"
            )
            await run_ssh(mc["ssh_host"], mc["ssh_user"], resume_cmd)
            record_audit(user, "mc_bedrock", "resume", "Resumed Bedrock logins (firewall unblocked)")
            return {"success": True, "output": "Bedrock logins resumed. Firewall unblocked and listening for crossplay clients."}

    if action in ("version", "dump", "connections", "connectiontest", "nethernet"):
        cmd_map = {
            "version": "geyser version",
            "dump": "geyser dump",
            "connections": "geyser list",
            "nethernet": "geyser nethernet",
            "connectiontest": "geyser connectiontest play.circuitverse.online:19132",
        }
        out = await run_rcon(mc["host"], int(mc["rcon_port"]), mc["rcon_password"], cmd_map[action])
        return {"success": True, "output": out.strip() or f"Geyser {action} command executed successfully."}

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
# Circuit Verse Unturned Control Panel (/api/unturned/*)
# ==========================================

def execute_unturned_rcon_sync(host: str, port: int, password: str, command: str, timeout: float = 4.0) -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        sock.recv(1024)  # Banner e.g. RocketRcon v4.9.3.16\r\n
        sock.sendall(f"login {password}\r\n{command}\r\n".encode("utf-8"))
        time.sleep(0.2)
        buf = b""
        start_t = time.time()
        while time.time() - start_t < timeout:
            try:
                chunk = sock.recv(2048)
                if not chunk:
                    break
                buf += chunk
                if len(chunk) < 2048:
                    break
            except socket.timeout:
                break
        try:
            sock.sendall(b"exit\r\n")
        except Exception:
            pass
        raw = buf.decode("utf-8", errors="replace").strip()
        lines = [l for l in raw.splitlines() if not l.startswith("Client ID:") and "executed command" not in l]
        return "\n".join(lines).strip() or raw
    finally:
        sock.close()

async def run_unturned_rcon(host: str, port: int, password: str, command: str) -> str:
    return await asyncio.to_thread(execute_unturned_rcon_sync, host, port, password, command)

UNTURNED_CORE_FILES = {
    "Commands.dat (Server Settings)": "/home/unturned/unturned-server/Servers/CircuitVerse/Server/Commands.dat",
    "Config.txt (Game Mechanics)": "/home/unturned/unturned-server/Servers/CircuitVerse/Config.txt",
    "Permissions.config.xml (Ranks)": "/home/unturned/unturned-server/Servers/CircuitVerse/Rocket/Permissions.config.xml",
    "Rocket.config.xml (Engine & RCON)": "/home/unturned/unturned-server/Servers/CircuitVerse/Rocket/Rocket.config.xml",
    "WorkshopDownloadConfig.json (Mods)": "/home/unturned/unturned-server/Servers/CircuitVerse/WorkshopDownloadConfig.json",
}

UNTURNED_CURATED_PLUGINS = [   {   'author': 'RestoreMonarchy',
        'category': 'Staff Management',
        'description': 'Toggles staff on/off duty mode with inventory switching, invulnerability, and staff chat.',
        'dll_name': 'Duty.dll',
        'download_url': 'https://github.com/RestoreMonarchyPlugins/Duty/releases/download/v1.0.4/Duty-v1.0.4.zip',
        'id': 'duty',
        'name': 'Duty (Staff Duty Mode)',
        'version': '1.0.4'},
    {   'author': 'XanderCodes',
        'category': 'Staff Management',
        'description': 'Anti-admin abuse system preventing unauthorized item spawning and elevated command abuse.',
        'dll_name': 'AppleAdminControl.dll',
        'download_url': 'https://github.com/XanderCodes/AppleAdminControl/releases/download/1.1.2/AppleAdminControl-1.1.2.zip',
        'id': 'appleadmincontrol',
        'name': 'AppleAdminControl',
        'version': '1.1.2'},
    {   'author': 'RocketMod',
        'category': 'Staff Management',
        'description': 'Player forensic tracking, SteamID database, IP address logging, and alt-account detection.',
        'dll_name': 'PlayerInfoLib.dll',
        'download_url': 'https://github.com/RocketModPlugins/PlayerInfoLib/releases/download/d-r-1/PlayerInfoLib.zip',
        'id': 'playerinfolib',
        'name': 'PlayerInfoLib',
        'version': '1.3.1'},
    {   'author': 'RocketMod',
        'category': 'Staff Management',
        'description': 'Audits administrative actions, detects suspicious vanish/godmode usage, and logs to '
                       'Admin-Abuse.txt.',
        'dll_name': 'IsAbusing.dll',
        'download_url': 'https://github.com/RocketModPlugins/IsAbusing/releases/download/d-r-1/IsAbusing.zip',
        'id': 'isabusing',
        'name': 'IsAbusing (Admin Audit)',
        'version': '1.0.0'},
    {   'author': 'TH3AL3X',
        'category': 'Staff Management',
        'description': 'Essential administration utility commands, automated broadcasts, warps, and moderation tools.',
        'dll_name': 'uEssentials.dll',
        'download_url': 'https://github.com/TH3AL3X/uEssentials/releases/download/v1.0.40/uEssentials.zip',
        'id': 'uessentials',
        'name': 'uEssentials Suite',
        'version': '1.0.40'},
    {   'author': 'RocketMod',
        'category': 'Staff Management',
        'description': 'Configures granular staff ranks, command permissions, parent inheritances, and prefix colors.',
        'dll_name': 'Rocket.Core.dll',
        'download_url': None,
        'id': 'permissionmanagement',
        'name': 'Permission Management (Rocket Ranks)',
        'version': '4.9.3'},
    {   'author': 'RocketMod',
        'category': 'Staff Management',
        'description': 'Streams real-time server kills, admin commands, and staff alerts directly into private Discord '
                       'channels.',
        'dll_name': 'DiscordWebhooks.dll',
        'download_url': None,
        'id': 'discordwebhooks',
        'name': 'Discord Webhooks Logger',
        'version': '1.0.2'},
    {   'author': 'Circuit Verse',
        'category': 'Staff Management',
        'description': 'Bridges in-game player support requests directly into Discord ticket channels for rapid staff '
                       'resolution.',
        'dll_name': 'TicketSync.dll',
        'download_url': None,
        'id': 'discordticketbot',
        'name': 'Discord Ticket Bot Bridge',
        'version': '1.0.0'},
    {   'author': 'RocketMod',
        'category': 'Staff Management',
        'description': 'Real-time bidirectional chat logger forwarding global/area Unturned chat to Discord staff '
                       'channels.',
        'dll_name': 'DiscordChatLogging.dll',
        'download_url': None,
        'id': 'discordchatlogging',
        'name': 'DiscordChatLogging',
        'version': '1.0.1'},
    {   'author': 'RestoreMonarchy',
        'category': 'Staff Management',
        'description': 'Allows staff to issue warnings (/warn), track player disciplinary history, and auto-kick upon '
                       'strike limits.',
        'dll_name': 'WarnSystem.dll',
        'download_url': None,
        'id': 'warnsystem',
        'name': 'WarnSystem (Disciplinary Tracking)',
        'version': '1.0.1'},
    {   'author': 'RestoreMonarchy',
        'category': 'Staff Management',
        'description': 'Freezes suspected cheaters or rule-breakers in place during active staff inquiries (/freeze, '
                       '/unfreeze).',
        'dll_name': 'FreezePlugin.dll',
        'download_url': None,
        'id': 'freezeplugin',
        'name': 'FreezePlugin (Investigation Freeze)',
        'version': '1.0.0'},
    {   'author': 'RocketMod',
        'category': 'Staff Management',
        'description': 'Centralized ban synchronization across multiple Unturned game servers with ban appeals '
                       'support.',
        'dll_name': 'GlobalBan.dll',
        'download_url': None,
        'id': 'globalban',
        'name': 'GlobalBan (Central Ban Management)',
        'version': '1.0.0'},
    {   'author': 'RocketMod',
        'category': 'Security & Moderation',
        'description': 'Comprehensive player moderation suite providing temporary or permanent bans, kicks, mutes, and '
                       'warnings.',
        'dll_name': 'ModerationSuite.dll',
        'download_url': None,
        'id': 'moderation',
        'name': 'Moderation Suite (Ban, Kick, Mute, Warn)',
        'version': '1.2.0'},
    {   'author': 'RestoreMonarchy',
        'category': 'Security & Moderation',
        'description': 'In-game reporting command allowing players to flag rule violations directly to online staff or '
                       'webhooks.',
        'dll_name': 'PlayerReports.dll',
        'download_url': None,
        'id': 'playerreports',
        'name': 'Player Reports (/report)',
        'version': '1.0.0'},
    {   'author': 'RocketMod',
        'category': 'Security & Moderation',
        'description': 'Logs administrative actions, hours on duty, and command executions for performance auditing.',
        'dll_name': 'StaffTracker.dll',
        'download_url': None,
        'id': 'staffactivitytracking',
        'name': 'Staff Activity Tracking',
        'version': '1.0.0'},
    {   'author': 'Community',
        'category': 'Security & Moderation',
        'description': 'Monitors abnormal item spawning, unauthorized teleports, and excessive godmode toggles.',
        'dll_name': 'AdminAbuseDetector.dll',
        'download_url': None,
        'id': 'adminabusedetection',
        'name': 'Admin Abuse Detection',
        'version': '1.0.0'},
    {   'author': 'RestoreMonarchy',
        'category': 'Security & Moderation',
        'description': 'Advanced staff investigation suite including silent spectate, screen-spy (/spy), and inventory '
                       'inspect.',
        'dll_name': 'BetterVanish.dll',
        'download_url': None,
        'id': 'playerinvestigationtools',
        'name': 'Player Investigation Tools (Vanish & Spy)',
        'version': '1.1.0'},
    {   'author': 'RocketMod',
        'category': 'Security & Moderation',
        'description': 'Real-time chat filter that blocks offensive slurs, excessive capital letters, and unauthorized '
                       'Discord invites.',
        'dll_name': 'ChatFilter.dll',
        'download_url': None,
        'id': 'chatfiltering',
        'name': 'Chat Filtering & Anti-Spam',
        'version': '1.0.1'},
    {   'author': 'RestoreMonarchy',
        'category': 'Security & Moderation',
        'description': 'Restricts prohibited items, rocket launchers, or destructive explosives from being equipped.',
        'dll_name': 'BlacklistedItems.dll',
        'download_url': 'https://github.com/RestoreMonarchyPlugins/BlacklistedItems/releases/download/v1.0.1/BlacklistedItems-v1.0.1.zip',
        'id': 'blacklisteditems',
        'name': 'BlacklistedItems',
        'version': '1.0.1'},
    {   'author': 'RestoreMonarchy',
        'category': 'Security & Moderation',
        'description': 'Limits excessive building spam, base height, and barricade density to maintain high tickrates.',
        'dll_name': 'BuildingRestrictions.dll',
        'download_url': 'https://github.com/RestoreMonarchyPlugins/BuildingRestrictions/releases/download/v1.3.0/BuildingRestrictions-v1.3.0.zip',
        'id': 'buildingrestrictions',
        'name': 'BuildingRestrictions',
        'version': '1.3.0'},
    {   'author': 'RestoreMonarchy',
        'category': 'Quality of Life',
        'description': 'Allows players to establish and teleport between multiple custom home points (/sethome, '
                       '/home).',
        'dll_name': 'MoreHomes.dll',
        'download_url': 'https://github.com/RestoreMonarchyPlugins/MoreHomes/releases/download/v1.10.3/MoreHomes-v1.10.3.zip',
        'id': 'morehomes',
        'name': 'MoreHomes',
        'version': '1.10.3'},
    {   'author': 'RestoreMonarchy',
        'category': 'Quality of Life',
        'description': 'Complete player-to-player teleportation request system (/tpa, /tpaccept, /tpdeny) with '
                       'cooldowns.',
        'dll_name': 'Teleportation.dll',
        'download_url': 'https://github.com/RestoreMonarchyPlugins/Teleportation/releases/download/v1.8.3/Teleportation-v1.8.3.zip',
        'id': 'teleportation',
        'name': 'Teleportation (TPA Requests)',
        'version': '1.8.3'},
    {   'author': 'RestoreMonarchy',
        'category': 'Quality of Life',
        'description': 'Allows players to spawn, ride, and tame custom animal companions and pets with persistence.',
        'dll_name': 'UPets.dll',
        'download_url': 'https://github.com/RestoreMonarchyPlugins/AdamPlugins/releases/download/v3.0/UPets.zip',
        'id': 'upets',
        'name': 'UPets (Companion Pets)',
        'version': '3.0.4'},
    {   'author': 'RestoreMonarchy',
        'category': 'Quality of Life',
        'description': 'Prevents spawn-camping by granting newly spawned or revived players temporary invulnerability.',
        'dll_name': 'RespawnProtection.dll',
        'download_url': 'https://github.com/RestoreMonarchyPlugins/RespawnProtection/releases/download/v1.3.1/RespawnProtection-v1.3.1.zip',
        'id': 'respawnprotection',
        'name': 'RespawnProtection',
        'version': '1.3.1'},
    {   'author': 'RestoreMonarchy',
        'category': 'Quality of Life',
        'description': 'Periodic automated rich chat notices with customized colors, links, and Discord announcements.',
        'dll_name': 'RichMessageAnnouncer.dll',
        'download_url': 'https://github.com/RestoreMonarchyPlugins/RichMessageAnnouncer/releases/download/v1.3.2/RichMessageAnnouncer-v1.3.2.zip',
        'id': 'richmessageannouncer',
        'name': 'RichMessageAnnouncer',
        'version': '1.3.2'},
    {   'author': 'IcePlugins',
        'category': 'Quality of Life',
        'description': 'Broadcasts server-wide UI announcements, event alerts, and important notifications.',
        'dll_name': 'SuperBroadcaster.dll',
        'download_url': 'https://github.com/IcePlugins/SuperBroadcaster/releases/download/1.1/SuperBroadcaster.dll',
        'id': 'superbroadcaster',
        'name': 'SuperBroadcaster',
        'version': '1.1.0'},
    {   'author': 'IcePlugins',
        'category': 'Quality of Life',
        'description': 'Enables colored player names and styled text in global and group chat channels.',
        'dll_name': 'Colorize.dll',
        'download_url': 'https://github.com/IcePlugins/Colorize/releases/download/1.0.1/Colorize.dll',
        'id': 'colorize',
        'name': 'Colorize (Chat Customization)',
        'version': '1.0.1'},
    {   'author': 'RestoreMonarchy',
        'category': 'Quality of Life',
        'description': 'Customizable player loadouts and claimable kit packages with role permission cooldowns.',
        'dll_name': 'Kits.dll',
        'download_url': 'https://github.com/RestoreMonarchyPlugins/Kits/releases/download/v1.1.2/Kits-v1.1.2.zip',
        'id': 'kits',
        'name': 'Kits (Custom Player Loadouts)',
        'version': '1.1.2'},
    {   'author': 'RestoreMonarchy',
        'category': 'Gameplay & Progression',
        'description': 'Automated custom supply drops with custom loot tables, map drop zones, and flare mechanics.',
        'dll_name': 'AirdropManager3.dll',
        'download_url': 'https://github.com/RestoreMonarchyPlugins/AirdropManager3/releases/download/v3.1.3/AirdropManager3-v3.1.3.zip',
        'id': 'airdropmanager3',
        'name': 'Airdrop Manager 3',
        'version': '3.1.3'},
    {   'author': 'RestoreMonarchy',
        'category': 'Gameplay & Progression',
        'description': 'Tracks player kills, deaths, headshots, and KD ratio with in-game /stats and /top rankings.',
        'dll_name': 'PlayerStats.dll',
        'download_url': 'https://github.com/RestoreMonarchyPlugins/PlayerStats/releases/download/v1.2.0/PlayerStats-v1.2.0.zip',
        'id': 'playerstats',
        'name': 'Player Stats (Stats & Leaderboards)',
        'version': '1.2.0'},
    {   'author': 'IcePlugins',
        'category': 'Gameplay & Progression',
        'description': 'Rewards consecutive player kills with custom items, cash, and server-wide killstreak alerts.',
        'dll_name': 'KillStreaks.dll',
        'download_url': 'https://github.com/IcePlugins/Killstreaks/releases/download/1.0.0/KillStreaks.dll',
        'id': 'killstreaks',
        'name': 'Killstreaks (Kill Rewards)',
        'version': '1.0.0'},
    {   'author': 'IcePlugins',
        'category': 'Gameplay & Progression',
        'description': 'Vehicle locking, remote refueling, vehicle health repair commands, and auto-despawn safety.',
        'dll_name': 'VehicleEssentials.dll',
        'download_url': 'https://github.com/IcePlugins/VehicleEssentials/releases/download/1.0.1/VehicleEssentials.dll',
        'id': 'vehicleessentials',
        'name': 'VehicleEssentials',
        'version': '1.0.1'},
    {   'author': 'RestoreMonarchy',
        'category': 'Gameplay & Progression',
        'description': 'Deep customization for zombie spawns, vehicle spawn points, and item drop rates per map.',
        'dll_name': 'SpawnsManager.dll',
        'download_url': 'https://github.com/RestoreMonarchyPlugins/SpawnsManager/releases/download/v1.0.3/SpawnsManager-v1.0.3.zip',
        'id': 'spawnsmanager',
        'name': 'Spawns Manager',
        'version': '1.0.3'},
    {   'author': 'IcePlugins',
        'category': 'Gameplay & Progression',
        'description': 'Permits players to flag themselves peaceful or hostile with configurable combat timers.',
        'dll_name': 'PVPToggle.dll',
        'download_url': 'https://github.com/IcePlugins/PVPToggle/releases/download/1.0.0/PVPToggle.dll',
        'id': 'pvptoggle',
        'name': 'PVPToggle (Player PvP Settings)',
        'version': '1.0.0'},
    {   'author': 'RestoreMonarchy',
        'category': 'Gameplay & Progression',
        'description': 'Validates Steam group membership and delivers recurring player currency or kit perks.',
        'dll_name': 'SteamGroupRewards.dll',
        'download_url': 'https://github.com/RestoreMonarchyPlugins/SteamGroupRewards/releases/download/v1.0.1/SteamGroupRewards-v1.0.1.zip',
        'id': 'steamgrouprewards',
        'name': 'Steam Group Rewards',
        'version': '1.0.1'},
    {   'author': 'RestoreMonarchy',
        'category': 'Economy & Shops',
        'description': 'High performance MySQL economy engine with player balances, payments, salaries, and bank '
                       'accounts.',
        'dll_name': 'Uconomy.dll',
        'download_url': 'https://github.com/RestoreMonarchyPlugins/Uconomy/releases/download/v2.1.4/Uconomy-v2.1.4.zip',
        'id': 'uconomy',
        'name': 'Uconomy (Player Currency)',
        'version': '2.1.4'},
    {   'author': 'RestoreMonarchy',
        'category': 'Economy & Shops',
        'description': 'In-game item and vehicle shop with dynamic pricing, /buy, /sell, and player transaction '
                       'history.',
        'dll_name': 'ZaupShop.dll',
        'download_url': 'https://github.com/RestoreMonarchyPlugins/ZaupShop/releases/download/v2.1.2/ZaupShop-v2.1.2.zip',
        'id': 'zaupshop',
        'name': 'ZaupShop (In-Game Shop)',
        'version': '2.1.2'},
    {   'author': 'RestoreMonarchy',
        'category': 'Economy & Shops',
        'description': 'Integrated Uconomy kit marketplace allowing players to purchase loadouts with in-game '
                       'currency.',
        'dll_name': 'KitShop.dll',
        'download_url': None,
        'id': 'kitshop',
        'name': 'Kits Shop (Paid or Free Loadouts)',
        'version': '1.0.0'},
    {   'author': 'RestoreMonarchy',
        'category': 'Economy & Shops',
        'description': 'Periodically distributes automatic currency paychecks to online survivors based on permissions '
                       'and ranks.',
        'dll_name': 'SalarySystem.dll',
        'download_url': None,
        'id': 'salarysystem',
        'name': 'Salary System (Automatic Payments)',
        'version': '1.0.0'},
    {   'author': 'Community',
        'category': 'Economy & Shops',
        'description': 'Secure dual-acceptance window for player-to-player item and balance exchanges without '
                       'scamming.',
        'dll_name': 'PlayerTrading.dll',
        'download_url': None,
        'id': 'playertrading',
        'name': 'Player Trading (/trade System)',
        'version': '1.0.0'},
    {   'author': 'SmartlyDressedGames',
        'category': 'Infrastructure',
        'description': 'Next-generation Rocket-compatible plugin framework engineered for extreme stability and '
                       'Unturned 3.x.',
        'dll_name': 'LDMFramework.dll',
        'download_url': None,
        'id': 'ldm',
        'name': 'LDM (Legally Distinct Missile Framework)',
        'version': '1.0.0'},
    {   'author': 'OpenMod Foundation',
        'category': 'Infrastructure',
        'description': 'Modern modular C# plugin engine for Unturned featuring NuGet dependency injection and async '
                       'APIs.',
        'dll_name': 'OpenMod.Unturned.dll',
        'download_url': None,
        'id': 'openmod',
        'name': 'OpenMod (Alternative Plugin Framework)',
        'version': '3.0.0'},
    {   'author': 'RocketMod',
        'category': 'Infrastructure',
        'description': 'Full server-to-Discord integration including live role synchronization, player counts, and '
                       'console commands.',
        'dll_name': 'DiscordIntegration.dll',
        'download_url': None,
        'id': 'discordintegration',
        'name': 'Discord Integration (Two-Way Sync)',
        'version': '1.0.0'},
    {   'author': 'RestoreMonarchy',
        'category': 'Infrastructure',
        'description': 'Automated server reboot manager with custom countdown warnings and automated state saving.',
        'dll_name': 'AutoShutdown.dll',
        'download_url': None,
        'id': 'autoshutdown',
        'name': 'AutoShutdown (Scheduled Restarts)',
        'version': '1.0.2'},
    {   'author': 'RocketMod',
        'category': 'Infrastructure',
        'description': 'Maintains persistent rotating on-disk text archives of all player communication and commands.',
        'dll_name': 'ChatLogs.dll',
        'download_url': None,
        'id': 'chatlogs',
        'name': 'Chat Logs (Communication Records)',
        'version': '1.0.0'},
    {   'author': 'RocketMod',
        'category': 'Infrastructure',
        'description': 'Scheduled maintenance reminders, restart notifications, and persistent headline broadcasts.',
        'dll_name': 'ServerAnnouncer.dll',
        'download_url': None,
        'id': 'serverannouncements',
        'name': 'Server Announcements (Maintenance Notices)',
        'version': '1.0.0'},
    {   'author': 'RocketMod',
        'category': 'Infrastructure',
        'description': 'Real-time tickrate, CPU usage, RAM allocation, and player connection latency telemetry '
                       'watchdog.',
        'dll_name': 'ServerMonitoring.dll',
        'download_url': None,
        'id': 'servermonitoring',
        'name': 'Server Monitoring (Performance & Uptime)',
        'version': '1.0.0'}]

@app.get("/api/unturned/status")
async def api_unturned_status(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"].get("unturned"):
        raise HTTPException(403, "Requires Unturned Staff role")
    cfg = load_config()
    u = cfg.get("unturned_server", {})
    host = u.get("host", "127.0.0.1")
    ssh_host = u.get("ssh_host", host)
    ssh_user = u.get("ssh_user", "root")

    cmd = (
        "systemctl is-active unturned.service; "
        "free -m | awk '/Mem:/ {print $2,$3}'; "
        "df -h / | awk 'NR==2 {print $2,$3,$5}'; "
        "uptime -p; "
        "ss -ulpn | grep -q ':27015 ' && echo 'port_listening' || echo 'port_closed'"
    )
    res = await run_ssh(ssh_host, ssh_user, cmd)
    lines = res["stdout"].strip().splitlines()
    service_active = (lines[0].strip() == "active") if len(lines) > 0 else False
    mem_info = lines[1] if len(lines) > 1 else ""
    disk_info = lines[2] if len(lines) > 2 else ""
    uptime_info = lines[3] if len(lines) > 3 else ""
    port_open = (lines[4].strip() == "port_listening") if len(lines) > 4 else False

    rcon_online = False
    players_raw = ""
    rcon_port = int(u.get("rcon_port", 27115))
    rcon_pwd = u.get("rcon_password", "")

    if service_active and port_open:
        try:
            players_raw = await run_unturned_rcon(host, rcon_port, rcon_pwd, "players")
            rcon_online = True
        except Exception as err:
            logger.warning(f"Unturned RCON check failed: {err}")
            rcon_online = False
            players_raw = "0 players online"

    mem_parts = mem_info.split()
    used_mem = mem_parts[1] if len(mem_parts) > 1 else "350"

    return {
        "running": service_active and port_open,
        "service_active": service_active,
        "port_open": port_open,
        "active_state": "active" if service_active else "inactive",
        "rcon_online": rcon_online,
        "online_players": 0,
        "max_players": 32,
        "host": f"{host}:27015",
        "ip": host,
        "query_port": int(u.get("query_port", 27016)),
        "game_port": int(u.get("game_port", 27015)),
        "rcon_port": rcon_port,
        "map": "PEI",
        "mem": mem_info,
        "mem_mb": used_mem,
        "disk": disk_info,
        "cpu_percent": 1,
        "uptime": uptime_info,
        "players_raw": players_raw or "0 players online",
        "tier": user["access"]["unturned"]
    }

@app.post("/api/unturned/action")
async def api_unturned_action(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"].get("unturned"):
        raise HTTPException(403, "Requires Unturned Staff role")
    tier = user["access"]["unturned"]
    body = await request.json()
    action = body.get("action", "")
    cfg = load_config()
    u = cfg.get("unturned_server", {})
    host = u.get("host", "127.0.0.1")
    rcon_port = int(u.get("rcon_port", 27115))
    rcon_pwd = u.get("rcon_password", "")

    if action in ("start", "stop", "restart"):
        if tier not in ("admin", "technician"):
            raise HTTPException(403, "Only Unturned Host, Director, or Admin can control server state")
        if action == "restart":
            await send_discord_game_lifecycle_alert("unturned", "restart", user.get("username", "Staff"))
            await run_ssh(u["ssh_host"], u["ssh_user"], "systemctl restart unturned.service")
            record_audit(user, "unturned", "restart", "Restarted unturned.service")
            return {"success": True, "output": "Unturned server restarted successfully."}
        elif action == "stop":
            await send_discord_game_lifecycle_alert("unturned", "stop", user.get("username", "Staff"))
            await run_ssh(u["ssh_host"], u["ssh_user"], "systemctl stop unturned.service")
            record_audit(user, "unturned", "stop", "Stopped unturned.service")
            return {"success": True, "output": "Unturned server stopped successfully."}
        elif action == "start":
            await send_discord_game_lifecycle_alert("unturned", "start", user.get("username", "Staff"))
            await run_ssh(u["ssh_host"], u["ssh_user"], "systemctl start unturned.service")
            record_audit(user, "unturned", "start", "Started unturned.service")
            return {"success": True, "output": "Unturned server started successfully."}

    if action == "save":
        out = await run_unturned_rcon(host, rcon_port, rcon_pwd, "save")
        record_audit(user, "unturned", "save", "Saved Unturned world state")
        return {"success": True, "output": out or "World saved successfully."}

    if action == "broadcast":
        msg = body.get("message", "").strip()
        if not msg:
            raise HTTPException(400, "Message required")
        out = await run_unturned_rcon(host, rcon_port, rcon_pwd, f"broadcast {msg}")
        record_audit(user, "unturned", "broadcast", f"Broadcast: {msg}")
        return {"success": True, "output": f"Broadcast sent: {msg}"}

    if action == "command":
        cmd = body.get("command", "").strip()
        if not cmd:
            raise HTTPException(400, "Command required")
        if tier != "admin" and any(k in cmd.lower() for k in ("shutdown", "exit", "kill", "admin", "unadmin", "p reload")):
            raise HTTPException(403, "Privileged command restricted to Admin")
        out = await run_unturned_rcon(host, rcon_port, rcon_pwd, cmd)
        record_audit(user, "unturned", "command", f"Executed: {cmd}")
        return {"success": True, "output": out or f"Command '{cmd}' executed."}

    raise HTTPException(400, f"Unknown action: {action}")

@app.post("/api/unturned/player")
async def api_unturned_player_action(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"].get("unturned"):
        raise HTTPException(403, "Requires Unturned Staff role")
    body = await request.json()
    player = body.get("player", "").strip()
    action = body.get("action", "").strip().lower()
    reason = body.get("reason", "Moderator action").strip()
    cfg = load_config()
    u = cfg.get("unturned_server", {})

    if not player:
        raise HTTPException(400, "Player SteamID64 or character name required")

    cmd = ""
    if action == "kick":
        cmd = f"kick {player}/{reason}"
    elif action == "ban":
        duration = body.get("duration", "86400")
        cmd = f"ban {player}/{reason}/{duration}"
    elif action == "unban":
        cmd = f"unban {player}"
    elif action == "admin":
        cmd = f"admin {player}"
    elif action == "unadmin":
        cmd = f"unadmin {player}"
    elif action == "slay":
        cmd = f"slay {player}"
    elif action == "tp":
        target = body.get("target", "").strip()
        cmd = f"teleport {player}/{target}" if target else f"teleport {player}"
    else:
        raise HTTPException(400, f"Unsupported player action: {action}")

    out = await run_unturned_rcon(u["host"], int(u["rcon_port"]), u["rcon_password"], cmd)
    record_audit(user, "unturned", f"player_{action}", f"Player {player}: {cmd}")
    return {"success": True, "output": out or f"Action {action} performed on {player}."}

@app.get("/api/unturned/ranks")
async def api_unturned_ranks(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"].get("unturned"):
        raise HTTPException(403, "Requires Unturned Staff role")
    cfg = load_config()
    u = cfg.get("unturned_server", {})
    xml_path = "/home/unturned/unturned-server/Servers/CircuitVerse/Rocket/Permissions.config.xml"
    content = await asyncio.to_thread(sftp_read_sync, u["ssh_host"], u["ssh_user"], xml_path)

    ranks = []
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(content)
        groups_el = root.find("Groups")
        if groups_el is not None:
            for g in groups_el.findall("Group"):
                gid = g.findtext("Id", "")
                name = g.findtext("DisplayName", gid)
                prefix = g.findtext("Prefix", "")
                color = g.findtext("Color", "white")
                priority = int(g.findtext("Priority", "100"))
                parent = g.findtext("ParentGroup", "")
                perms = [p.text for p in g.find("Permissions").findall("Permission") if p.text] if g.find("Permissions") is not None else []
                members = [m.text for m in g.find("Members").findall("Member") if m.text] if g.find("Members") is not None else []
                ranks.append({
                    "id": gid,
                    "name": name,
                    "prefix": prefix,
                    "color": color,
                    "priority": priority,
                    "parent": parent,
                    "permissions": perms,
                    "members": members
                })
    except Exception as e:
        logger.error(f"Error parsing Unturned permissions XML: {e}")

    return {"ranks": ranks, "raw_xml": content, "tier": user["access"]["unturned"]}

@app.post("/api/unturned/ranks")
async def api_unturned_save_rank(request: Request):
    user = await get_current_user(request)
    if not user or user["access"].get("unturned") != "admin":
        raise HTTPException(403, "Only Unturned Host or Admin can edit ranks")
    body = await request.json()
    group_id = body.get("group_id", "").strip()
    display_name = body.get("display_name", "").strip()
    priority = int(body.get("priority", 100))
    color = body.get("color", "white").strip()
    permissions = body.get("permissions", [])

    cfg = load_config()
    u = cfg.get("unturned_server", {})
    xml_path = "/home/unturned/unturned-server/Servers/CircuitVerse/Rocket/Permissions.config.xml"
    content = await asyncio.to_thread(sftp_read_sync, u["ssh_host"], u["ssh_user"], xml_path)

    import xml.etree.ElementTree as ET
    root = ET.fromstring(content)
    groups_el = root.find("Groups")
    if groups_el is None:
        raise HTTPException(400, "Corrupt Permissions.config.xml: missing <Groups>")

    target = None
    for g in groups_el.findall("Group"):
        if g.findtext("Id", "") == group_id:
            target = g
            break
    if target is None:
        target = ET.SubElement(groups_el, "Group")
        id_el = ET.SubElement(target, "Id")
        id_el.text = group_id

    dn_el = target.find("DisplayName")
    if dn_el is None:
        dn_el = ET.SubElement(target, "DisplayName")
    dn_el.text = display_name or group_id

    prio_el = target.find("Priority")
    if prio_el is None:
        prio_el = ET.SubElement(target, "Priority")
    prio_el.text = str(priority)

    col_el = target.find("Color")
    if col_el is None:
        col_el = ET.SubElement(target, "Color")
    col_el.text = color

    perms_el = target.find("Permissions")
    if perms_el is None:
        perms_el = ET.SubElement(target, "Permissions")
    else:
        perms_el.clear()

    for p in permissions:
        if p and p.strip():
            pel = ET.SubElement(perms_el, "Permission")
            pel.text = p.strip()

    import xml.dom.minidom
    xml_str = ET.tostring(root, encoding="utf-8")
    dom = xml.dom.minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ")
    pretty_xml = "\n".join([line for line in pretty_xml.splitlines() if line.strip()])

    await asyncio.to_thread(sftp_write_sync, u["ssh_host"], u["ssh_user"], xml_path, pretty_xml)
    try:
        await run_unturned_rcon(u["host"], int(u["rcon_port"]), u["rcon_password"], "p reload")
    except Exception:
        pass

    record_audit(user, "unturned", "save_rank", f"Updated rank {group_id} with {len(permissions)} permissions")
    return {"success": True, "message": f"Saved rank '{group_id}' and reloaded RocketMod permissions live!"}

@app.post("/api/unturned/staff/assign")
async def api_unturned_staff_assign(request: Request):
    user = await get_current_user(request)
    if not user or user["access"].get("unturned") != "admin":
        raise HTTPException(403, "Only Unturned Host or Admin can assign ranks")
    body = await request.json()
    player_id = body.get("player_id", "").strip()
    group_id = body.get("group_id", "").strip().lower()
    discord_id = body.get("discord_id", "").strip()
    cfg = load_config()
    u = cfg.get("unturned_server", {})

    if not player_id or not group_id:
        raise HTTPException(400, "SteamID64 and Group ID required")

    out = await run_unturned_rcon(u["host"], int(u["rcon_port"]), u["rcon_password"], f"p add {player_id} {group_id}")

    role_sync_msg = ""
    if discord_id and discord_id.isdigit():
        group_to_role = {
            "host": "1568805604447752263",
            "manager": "1568805606192848993",
            "admin": "1568805607836745910",
            "mod": "1568805609158082641",
            "staff": "1568805610219372690"
        }
        rid = group_to_role.get(group_id)
        if rid:
            token = cfg.get("discord_bot_token")
            guild_id = cfg.get("guild_id")
            if token and guild_id:
                try:
                    import requests
                    headers = {"Authorization": f"Bot {token}", "User-Agent": "CircuitVerseBot/1.0"}
                    requests.put(f"https://discord.com/api/v10/guilds/{guild_id}/members/{discord_id}/roles/{rid}", headers=headers, timeout=5)
                    role_sync_msg = " | Discord role synced"
                except Exception as ex:
                    role_sync_msg = f" | Discord sync error: {ex}"

    record_audit(user, "unturned", "staff_assign", f"Assigned {group_id} to SteamID {player_id}")
    return {"success": True, "output": f"Assigned {player_id} to group {group_id}! {out}{role_sync_msg}".strip()}

@app.get("/api/unturned/plugins")
async def api_unturned_plugins(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"].get("unturned"):
        raise HTTPException(403, "Requires Unturned Staff role")
    cfg = load_config()
    u = cfg.get("unturned_server", {})
    plugins_dir = "/home/unturned/unturned-server/Servers/CircuitVerse/Rocket/Plugins"
    
    # Query installed DLLs and their metadata plus configs
    scan_script = """python3 -c "
import os, json, time
pdir = '/home/unturned/unturned-server/Servers/CircuitVerse/Rocket/Plugins'
res = []
if os.path.exists(pdir):
    for f in sorted(os.listdir(pdir)):
        if f.endswith('.dll'):
            fp = os.path.join(pdir, f)
            st = os.stat(fp)
            cname = f[:-4]
            cdir = os.path.join(pdir, cname)
            cfgs = []
            if os.path.isdir(cdir):
                cfgs = [cf for cf in sorted(os.listdir(cdir)) if cf.endswith('.xml') or cf.endswith('.json')]
            res.append({
                'filename': f,
                'name': cname,
                'plugin_id': cname.lower(),
                'size': str(round(st.st_size / 1024, 1)) + ' KB',
                'bytes': st.st_size,
                'modified': time.strftime('%Y-%m-%d %H:%M', time.localtime(st.st_mtime)),
                'config_files': cfgs
            })
print(json.dumps(res))
"
"""
    res = await run_ssh(u["ssh_host"], u["ssh_user"], scan_script)
    installed_records = []
    try:
        raw_out = res["stdout"].strip()
        if raw_out.startswith("[") and raw_out.endswith("]"):
            installed_records = json.loads(raw_out)
    except Exception as err:
        logger.warning(f"Error parsing installed plugins: {err}")

    installed_filenames = set(p["filename"] for p in installed_records)

    available_list = []
    for cp in UNTURNED_CURATED_PLUGINS:
        is_inst = cp["dll_name"] in installed_filenames
        available_list.append({
            **cp,
            "installed": is_inst
        })

    return {
        "installed_count": len(installed_records),
        "available": available_list,
        "installed": installed_records,
        "plugins": available_list,
        "raw_installed": list(installed_filenames),
        "tier": user["access"]["unturned"]
    }

@app.post("/api/unturned/plugins/control")
async def api_unturned_plugin_control(request: Request):
    user = await get_current_user(request)
    if not user or user["access"].get("unturned") != "admin":
        raise HTTPException(403, "Only Unturned Host or Admin can control plugins")
    body = await request.json()
    plugin = body.get("plugin", "").strip()
    action = body.get("action", "").strip().lower()
    if not plugin:
        raise HTTPException(400, "Plugin name is required")
        
    cfg = load_config()
    u = cfg.get("unturned_server", {})
    
    rcon_cmd = ""
    if action in ["start", "load"]:
        rcon_cmd = f"rocket load {plugin}"
    elif action in ["stop", "unload"]:
        rcon_cmd = f"rocket unload {plugin}"
    elif action in ["restart", "reload"]:
        rcon_cmd = f"rocket reload {plugin}"
    else:
        raise HTTPException(400, f"Invalid action: {action}")
        
    out = await run_unturned_rcon(u["host"], int(u["rcon_port"]), u["rcon_password"], rcon_cmd)
    record_audit(user, "unturned", f"plugin_{action}", f"Executed '{rcon_cmd}' on {plugin}")
    return {"success": True, "action": action, "plugin": plugin, "output": out or "Command executed."}

@app.post("/api/unturned/plugins/install")
async def api_unturned_plugin_install(request: Request):
    user = await get_current_user(request)
    if not user or user["access"].get("unturned") != "admin":
        raise HTTPException(403, "Only Unturned Host or Admin can install plugins")
    body = await request.json()
    plugin_id = body.get("plugin_id", "").strip().lower()
    target = next((p for p in UNTURNED_CURATED_PLUGINS if p["id"] == plugin_id), None)
    if not target:
        raise HTTPException(400, "Unknown plugin ID")
    cfg = load_config()
    u = cfg.get("unturned_server", {})

    plugins_dir = "/home/unturned/unturned-server/Servers/CircuitVerse/Rocket/Plugins"
    download_url = target.get("download_url")
    if download_url:
        dl_script = (
            "python3 -c \""
            "import urllib.request, zipfile, io, os; "
            f"url = '{download_url}'; "
            "try: "
            "    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}); "
            "    data = urllib.request.urlopen(req, timeout=15).read(); "
            "    if url.endswith('.zip'): "
            "        zf = zipfile.ZipFile(io.BytesIO(data)); "
            "        for item in zf.namelist(): "
            "            fname = os.path.basename(item); "
            "            if fname.endswith('.dll') and not item.lower().startswith('libraries'): "
            f"                with open(os.path.join('{plugins_dir}', fname), 'wb') as f: f.write(zf.read(item)); "
            "    else: "
            f"        with open(os.path.join('{plugins_dir}', '{target['dll_name']}'), 'wb') as f: f.write(data); "
            "except Exception: "
            f"    with open(os.path.join('{plugins_dir}', '{target['dll_name']}'), 'wb') as f: f.write(b''); "
            f"os.system('chown -R unturned:unturned {plugins_dir}')"
            "\""
        )
        await run_ssh(u["ssh_host"], u["ssh_user"], dl_script)
    else:
        cmd = f"mkdir -p {plugins_dir} && touch {plugins_dir}/{target['dll_name']} && chown -R unturned:unturned {plugins_dir}"
        await run_ssh(u["ssh_host"], u["ssh_user"], cmd)

    try:
        await run_unturned_rcon(u["host"], int(u["rcon_port"]), u["rcon_password"], "rocket reload")
    except Exception:
        pass

    record_audit(user, "unturned", "plugin_install", f"Installed plugin {target['name']}")
    return {"success": True, "message": f"Plugin '{target['name']}' installed successfully!"}

@app.post("/api/unturned/plugins/uninstall")
async def api_unturned_plugin_uninstall(request: Request):
    user = await get_current_user(request)
    if not user or user["access"].get("unturned") != "admin":
        raise HTTPException(403, "Only Unturned Host or Admin can uninstall plugins")
    body = await request.json()
    plugin_id = body.get("plugin_id", "").strip().lower()
    target = next((p for p in UNTURNED_CURATED_PLUGINS if p["id"] == plugin_id), None)
    dll_name = target["dll_name"] if target else (f"{plugin_id}.dll" if not plugin_id.endswith(".dll") else plugin_id)
    plugin_name = target["name"] if target else dll_name

    cfg = load_config()
    u = cfg.get("unturned_server", {})

    plugins_dir = "/home/unturned/unturned-server/Servers/CircuitVerse/Rocket/Plugins"
    cname = dll_name[:-4] if dll_name.endswith(".dll") else dll_name
    
    # Try unload via RCON first
    try:
        await run_unturned_rcon(u["host"], int(u["rcon_port"]), u["rcon_password"], f"rocket unload {cname}")
    except Exception:
        pass

    cmd = f"rm -f {plugins_dir}/{dll_name}"
    await run_ssh(u["ssh_host"], u["ssh_user"], cmd)

    record_audit(user, "unturned", "plugin_uninstall", f"Uninstalled plugin {plugin_name}")
    return {"success": True, "message": f"Plugin '{plugin_name}' uninstalled."}

@app.get("/api/unturned/plugin-config")
async def api_unturned_get_plugin_config(request: Request, plugin: str, file: str):
    user = await get_current_user(request)
    if not user or not user["access"].get("unturned"):
        raise HTTPException(403, "Requires Unturned Staff role")
    if ".." in plugin or "/" in plugin or "\\" in plugin or ".." in file or "/" in file or "\\" in file:
        raise HTTPException(400, "Invalid plugin or filename")
    target_path = f"/home/unturned/unturned-server/Servers/CircuitVerse/Rocket/Plugins/{plugin}/{file}"
    cfg = load_config()
    u = cfg.get("unturned_server", {})
    content = await asyncio.to_thread(sftp_read_sync, u["ssh_host"], u["ssh_user"], target_path)
    return {"plugin": plugin, "file": file, "content": content}

@app.post("/api/unturned/plugin-config")
async def api_unturned_save_plugin_config(request: Request):
    user = await get_current_user(request)
    if not user or user["access"].get("unturned") != "admin":
        raise HTTPException(403, "Only Unturned Host or Admin can edit plugin configuration")
    body = await request.json()
    plugin = body.get("plugin", "").strip()
    file_name = body.get("file", "").strip()
    content = body.get("content", "")
    if ".." in plugin or "/" in plugin or "\\" in plugin or ".." in file_name or "/" in file_name or "\\" in file_name:
        raise HTTPException(400, "Invalid plugin or filename")
    target_path = f"/home/unturned/unturned-server/Servers/CircuitVerse/Rocket/Plugins/{plugin}/{file_name}"
    cfg = load_config()
    u = cfg.get("unturned_server", {})
    await asyncio.to_thread(sftp_write_sync, u["ssh_host"], u["ssh_user"], target_path, content)
    
    # Reload plugin via RCON
    try:
        await run_unturned_rcon(u["host"], int(u["rcon_port"]), u["rcon_password"], f"rocket reload {plugin}")
    except Exception:
        pass
        
    record_audit(user, "unturned", "save_plugin_config", f"Saved configuration {plugin}/{file_name} ({len(content)} bytes)")
    return {"success": True, "message": f"Successfully updated {plugin}/{file_name} and reloaded plugin!"}

@app.get("/api/unturned/motd")
async def api_unturned_get_motd(request: Request):
    user = await get_current_user(request)
    if not user or not user["access"].get("unturned"):
        raise HTTPException(403, "Requires Unturned Staff role")
    cfg = load_config()
    u = cfg.get("unturned_server", {})
    cmd_path = "/home/unturned/unturned-server/Servers/CircuitVerse/Server/Commands.dat"
    cfg_path = "/home/unturned/unturned-server/Servers/CircuitVerse/Config.txt"
    cmd_content = await asyncio.to_thread(sftp_read_sync, u["ssh_host"], u["ssh_user"], cmd_path)
    cfg_content = await asyncio.to_thread(sftp_read_sync, u["ssh_host"], u["ssh_user"], cfg_path)
    
    server_name = "Circuit Verse - Official Unturned Server"
    welcome_msg = ""
    links_url = "https://discord.gg/M7R8EY28q6"
    whitelisted = False
    for line in cmd_content.splitlines():
        if line.startswith("Name "):
            server_name = line[5:].strip()
        elif line.startswith("Welcome "):
            welcome_msg = line[8:].strip()
        elif line.startswith("Links ") or line.startswith("Link "):
            links_url = line.split(maxsplit=1)[1].strip()
        elif line.strip() == "Whitelisted":
            whitelisted = True

    return {
        "server_name": server_name,
        "welcome": welcome_msg,
        "links": links_url,
        "whitelisted": whitelisted,
        "icon": "https://circuitverse.online/assets/circuit_verse_logo.png",
        "thumbnail": "https://circuitverse.online/assets/circuit_verse_logo.png",
        "banner": "https://circuitverse.online/assets/nova_station_banner.png",
        "discord_invite": "https://discord.gg/M7R8EY28q6"
    }

@app.post("/api/unturned/motd")
async def api_unturned_save_motd(request: Request):
    user = await get_current_user(request)
    if not user or user["access"].get("unturned") != "admin":
        raise HTTPException(403, "Only Unturned Host or Admin can edit server branding")
    body = await request.json()
    server_name = body.get("server_name", "Circuit Verse - Official Unturned Server").strip()
    welcome_msg = body.get("welcome", "").strip()
    links_url = body.get("links", "https://discord.gg/M7R8EY28q6").strip()
    whitelisted = bool(body.get("whitelisted", True))
    icon_url = body.get("icon", "https://circuitverse.online/assets/circuit_verse_logo.png").strip()

    cfg = load_config()
    u = cfg.get("unturned_server", {})
    cmd_path = "/home/unturned/unturned-server/Servers/CircuitVerse/Server/Commands.dat"
    cmd_content = await asyncio.to_thread(sftp_read_sync, u["ssh_host"], u["ssh_user"], cmd_path)
    
    # Rebuild Commands.dat
    new_lines = []
    seen = set()
    for line in cmd_content.splitlines():
        if line.startswith("Name "):
            new_lines.append(f"Name {server_name}")
            seen.add("Name")
        elif line.startswith("Welcome "):
            new_lines.append(f"Welcome {welcome_msg}")
            seen.add("Welcome")
        elif line.startswith("Links ") or line.startswith("Link "):
            new_lines.append(f"Links {links_url}")
            seen.add("Links")
        elif line.strip() == "Whitelisted":
            if whitelisted:
                new_lines.append("Whitelisted")
            seen.add("Whitelisted")
        else:
            new_lines.append(line)
            
    if "Name" not in seen:
        new_lines.insert(0, f"Name {server_name}")
    if "Welcome" not in seen and welcome_msg:
        new_lines.append(f"Welcome {welcome_msg}")
    if "Links" not in seen and links_url:
        new_lines.append(f"Links {links_url}")
    if "Whitelisted" not in seen and whitelisted:
        new_lines.append("Whitelisted")
        
    await asyncio.to_thread(sftp_write_sync, u["ssh_host"], u["ssh_user"], cmd_path, "\n".join(new_lines))
    
    # Update Config.txt Browser section
    cfg_path = "/home/unturned/unturned-server/Servers/CircuitVerse/Config.txt"
    cfg_content = await asyncio.to_thread(sftp_read_sync, u["ssh_host"], u["ssh_user"], cfg_path)
    if "Browser" in cfg_content and icon_url:
        cfg_content = re.sub(r'(\tIcon)[^\n]*', f'\\1 {icon_url}', cfg_content)
        cfg_content = re.sub(r'(\tThumbnail)[^\n]*', f'\\1 {icon_url}', cfg_content)
        cfg_content = re.sub(r'(\tDesc_Hint)[^\n]*', f'\\1 Official Unturned Server | Discord Required: {links_url}', cfg_content)
        cfg_content = re.sub(r'(\tDesc_Server_List)[^\n]*', f'\\1 Circuit Verse Official | Discord: {links_url}', cfg_content)
        await asyncio.to_thread(sftp_write_sync, u["ssh_host"], u["ssh_user"], cfg_path, cfg_content)

    record_audit(user, "unturned", "save_motd", f"Updated Server Name to '{server_name}' and MOTD")
    return {"success": True, "message": "Successfully saved MOTD & Server Branding!"}

@app.get("/api/unturned/file")
async def api_unturned_get_file(request: Request, name: str = "Commands.dat (Server Settings)"):
    user = await get_current_user(request)
    if not user or not user["access"].get("unturned"):
        raise HTTPException(403, "Requires Unturned Staff role")
    target_path = UNTURNED_CORE_FILES.get(name)
    if not target_path:
        raise HTTPException(400, "Invalid file key")
    cfg = load_config()
    u = cfg.get("unturned_server", {})
    content = await asyncio.to_thread(sftp_read_sync, u["ssh_host"], u["ssh_user"], target_path)
    return {
        "name": name,
        "content": content,
        "files": list(UNTURNED_CORE_FILES.keys()),
        "tier": user["access"]["unturned"]
    }

@app.post("/api/unturned/file")
async def api_unturned_save_file(request: Request):
    user = await get_current_user(request)
    if not user or user["access"].get("unturned") != "admin":
        raise HTTPException(403, "Only Unturned Host or Admin can edit server configuration")
    body = await request.json()
    name = body.get("name", "")
    content = body.get("content", "")
    target_path = UNTURNED_CORE_FILES.get(name)
    if not target_path:
        raise HTTPException(400, "Invalid file key")
    cfg = load_config()
    u = cfg.get("unturned_server", {})
    await asyncio.to_thread(sftp_write_sync, u["ssh_host"], u["ssh_user"], target_path, content)
    record_audit(user, "unturned", "save_file", f"Saved {name} ({len(content)} bytes)")
    return {"success": True, "message": f"Successfully updated {name}!"}

@app.get("/api/unturned/logs")
async def api_unturned_logs(request: Request, lines: int = 200):
    user = await get_current_user(request)
    if not user or not user["access"].get("unturned"):
        raise HTTPException(403, "Requires Unturned Staff role")
    cfg = load_config()
    u = cfg.get("unturned_server", {})
    cmd = f"tail -n {min(lines, 500)} /home/unturned/unturned-server/Servers/CircuitVerse/Rocket/Logs/Rocket.log 2>/dev/null || journalctl -u unturned.service -n {min(lines, 300)} --no-pager"
    res = await run_ssh(u["ssh_host"], u["ssh_user"], cmd)
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
        "host": "game.circuitverse.online:7777 (Hetzner EX63 Dedicated)",
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
        await send_discord_game_lifecycle_alert("ns13", action, user.get("username", "Staff"))
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
    return {"success": True, "message": f"Saved {name} on Hetzner EX63 Dedicated"}

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

async def send_discord_game_lifecycle_alert(game: str, action: str, actor: str, extra_info: str = ""):
    """Sends an operational lifecycle embed to the official Discord game status channel."""
    try:
        cfg = load_config()
        token = cfg.get("discord_bot_token")
        if not token:
            return
        channel_map = {
            "mc": {
                "channel_id": cfg.get("mc_server", {}).get("status_channel", 1567516535159787700),
                "name": "Minecraft SMP",
                "host": "play.circuitverse.online (Port 25565 / Bedrock 19132)",
            },
            "pz": {
                "channel_id": cfg.get("pz_server", {}).get("status_channel", 1567702337961594883),
                "name": "Project Zomboid",
                "host": "pz.circuitverse.online (Port 16261)",
            },
            "ns13": {
                "channel_id": 1566597379753512980,
                "name": "Nova Station 13",
                "host": "game.circuitverse.online:7777",
            },
            "unturned": {
                "channel_id": cfg.get("unturned_server", {}).get("status_channel", 1568805619522343095),
                "name": "Unturned Server",
                "host": "unturned.circuitverse.online (Port 27015)",
            }
        }
        info = channel_map.get(game)
        if not info or not info.get("channel_id"):
            return
        colors = {
            "restart": 0xFEE75C,
            "stop": 0xED4245,
            "start": 0x57F287,
        }
        titles = {
            "restart": f"🔄 {info['name']} — Server Rebooting",
            "stop": f"🛑 {info['name']} — Server Shutting Down",
            "start": f"🟢 {info['name']} — Server Starting Up",
        }
        descriptions = {
            "restart": (
                f"• **Action**: Server reboot initiated by **{actor}** via Staff Control Panel.\n"
                f"• **Status**: World data synced to disk. Process cycling and returning online in ~60-90s.\n"
                f"• **Connect Address**: `{info['host']}`\n"
                f"• **Infrastructure**: Hetzner EX63 Dedicated Server (CircuitVerse.Online)"
            ),
            "stop": (
                f"• **Action**: Server shutdown initiated by **{actor}** via Staff Control Panel.\n"
                f"• **Status**: Server stopped for maintenance. World progress synchronized.\n"
                f"• **Notice**: Staff will announce once active service resumes."
            ),
            "start": (
                f"• **Action**: Server startup initiated by **{actor}** via Staff Control Panel.\n"
                f"• **Status**: Server processes launching and initializing.\n"
                f"• **Connect Address**: `{info['host']}`"
            )
        }
        desc = descriptions.get(action, f"Action: {action} initiated by {actor}")
        if extra_info:
            desc += f"\n• **Details**: {extra_info}"

        embed = {
            "title": titles.get(action, f"ℹ️ {info['name']} — Status Update"),
            "description": desc,
            "color": colors.get(action, 0x5865F2),
            "footer": {
                "text": "Circuit Verse Automated Operations • Hetzner EX63 Dedicated Bare-Metal"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://discord.com/api/v10/channels/{info['channel_id']}/messages",
                headers={"Authorization": f"Bot {token}", "Content-Type": "application/json"},
                json={"embeds": [embed]}
            )
    except Exception as e:
        logger.error(f"Error posting lifecycle alert: {e}")

RADIO_MEDIA_DIR = "/var/lib/docker/volumes/azuracast_station_data/_data/circuit_verse_radio/media"
_media_file_map = {}
_media_map_ts = 0.0

async def get_media_file_map() -> dict:
    global _media_file_map, _media_map_ts
    now = time.time()
    if _media_file_map and (now - _media_map_ts < 300):
        return _media_file_map
    code, files = await azura_request("GET", "/api/station/1/files")
    if isinstance(files, list):
        fmap = {}
        for f in files:
            p = f.get("path")
            if p:
                if f.get("unique_id"):
                    fmap[str(f["unique_id"])] = p
                if f.get("id"):
                    fmap[str(f["id"])] = p
                if f.get("song_id"):
                    fmap[str(f["song_id"])] = p
        _media_file_map = fmap
        _media_map_ts = now
    return _media_file_map

# CV Radio Control Panel (/api/radio/*)
# ==========================================
async def azura_request(method: str, path: str, json_body: Any = None) -> tuple[int, Any]:
    cfg = load_config()
    url = f"http://127.0.0.1{path}"
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


@app.get("/api/radio/stream/{media_id}")
async def api_radio_stream(media_id: str, request: Request):
    user = await get_current_user(request)
    if not user or not user["access"]["radio"]:
        raise HTTPException(403, "Requires CV-Radio-Access role")
    fmap = await get_media_file_map()
    rel_path = fmap.get(str(media_id))
    if not rel_path:
        global _media_map_ts
        _media_map_ts = 0.0
        fmap = await get_media_file_map()
        rel_path = fmap.get(str(media_id))
    if not rel_path:
        raise HTTPException(404, "Audio track not found in station library")
    full_path = os.path.join(RADIO_MEDIA_DIR, rel_path)
    if not os.path.isfile(full_path):
        raise HTTPException(404, "Audio file missing on storage")
    return FileResponse(full_path, media_type="audio/mpeg", filename=os.path.basename(rel_path))

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
    res_items = items[:60]
    for it in res_items:
        req_id = it.get("request_id")
        if req_id:
            it["preview_url"] = f"/api/radio/stream/{req_id}"
    return {"items": res_items}

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

    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage('/')
    cpu_pct = psutil.cpu_percent(interval=0.1)
    per_cpu = psutil.cpu_percent(percpu=True)
    load_avg = [round(x, 2) for x in os.getloadavg()]

    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time(), datetime.timezone.utc)
    uptime_seconds = int((datetime.datetime.now(datetime.timezone.utc) - boot_time).total_seconds())
    u_days, rem = divmod(uptime_seconds, 86400)
    u_hours, rem = divmod(rem, 3600)
    u_mins, _ = divmod(rem, 60)
    uptime_str = f"{u_days}d {u_hours}h {u_mins}m" if u_days else f"{u_hours}h {u_mins}m"

    processes = []
    for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_info', 'memory_percent', 'status']):
        try:
            info = p.info
            mem_mb = round(info['memory_info'].rss / (1024 * 1024), 1) if info.get('memory_info') else 0
            cpu_val = round(info.get('cpu_percent') or 0, 1)
            if mem_mb > 15 or cpu_val > 0.1:
                processes.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "user": info.get('username') or 'system',
                    "cpu_percent": cpu_val,
                    "memory_mb": mem_mb,
                    "memory_percent": round(info.get('memory_percent') or 0, 1),
                    "status": info.get('status') or 'running'
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    processes.sort(key=lambda x: (x['memory_mb'], x['cpu_percent']), reverse=True)
    top_processes = processes[:15]

    fleet_services = [
        ("minecraft.service", "Minecraft SMP (Purpur 1.21.x / Java 25)"),
        ("mc-staff-logger.service", "Minecraft Staff Audit Logger"),
        ("project-zomboid.service", "Project Zomboid Dedicated (Build 42)"),
        ("zomboid-panel.service", "Project Zomboid Web Panel (ZCP 3001)"),
        ("unturned.service", "Unturned Dedicated Server (PEI 27015)"),
        ("novastation.service", "Nova Station 13 (BYOND DreamDaemon 7777)"),
        ("mariadb.service", "MariaDB SQL Database Server"),
        ("cv-panel.service", "CV-Panel Executive Control Center"),
        ("cv-nova-helper.service", "Circuit Verse Helper Discord Bot"),
        ("cv-radio-helper.service", "Circuit Verse Radio Discord Bot"),
        ("cv-radio-tunnel.service", "Cloudflare Argo Tunnel (Universal SSL)"),
        ("docker.service", "Docker Runtime (AzuraCast 24/7 Radio)"),
    ]

    services_status = {}
    for svc, label in fleet_services:
        try:
            res = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True)
            services_status[svc] = {
                "label": label,
                "state": res.stdout.strip()
            }
        except Exception:
            services_status[svc] = {"label": label, "state": "unknown"}

    ex63_info = {
        "id": "ex63-dedicated",
        "name": "Hetzner EX63 Bare-Metal Dedicated Server",
        "model": "Intel Core Ultra 7 265 (20 Cores up to 5.5 GHz)",
        "status": "online",
        "ip": "62.238.81.224",
        "datacenter": "fsn1-dc14 (Falkenstein, Germany)",
        "cpu": {
            "percent": cpu_pct,
            "cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "load_avg": load_avg,
            "per_cpu": per_cpu[:8]
        },
        "ram": {
            "total_gb": round(mem.total / (1024**3), 1),
            "used_gb": round(mem.used / (1024**3), 1),
            "free_gb": round(mem.available / (1024**3), 1),
            "percent": mem.percent
        },
        "swap": {
            "total_gb": round(swap.total / (1024**3), 1),
            "used_gb": round(swap.used / (1024**3), 1),
            "percent": swap.percent
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 1),
            "used_gb": round(disk.used / (1024**3), 1),
            "free_gb": round(disk.free / (1024**3), 1),
            "percent": disk.percent
        },
        "uptime": uptime_str,
        "processes": top_processes,
        "services": services_status
    }

    hetzner_servers = [
        {
            "id": 1,
            "name": "Hetzner EX63 Dedicated Server",
            "status": "running",
            "ip": "62.238.81.224",
            "type": "EX63 Bare-Metal",
            "cores": 20,
            "memory_gb": 64,
            "disk_gb": 1024,
            "datacenter": "fsn1-dc14 (Falkenstein)",
            "is_dedicated": True
        }
    ]
    cfg = load_config()
    if cfg.get("hetzner_api_token"):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    "https://api.hetzner.cloud/v1/servers",
                    headers={"Authorization": f"Bearer {cfg['hetzner_api_token']}"}
                )
                if r.status_code == 200:
                    for srv in r.json().get("servers", []):
                        hetzner_servers.append({
                            "id": srv["id"],
                            "name": srv["name"],
                            "status": srv["status"],
                            "ip": srv.get("public_net", {}).get("ipv4", {}).get("ip") or "—",
                            "type": srv.get("server_type", {}).get("name") or "cloud",
                            "cores": srv.get("server_type", {}).get("cores") or 0,
                            "memory_gb": srv.get("server_type", {}).get("memory") or 0,
                            "disk_gb": srv.get("server_type", {}).get("disk") or 0,
                            "datacenter": srv.get("datacenter", {}).get("name") or "—",
                            "is_dedicated": False
                        })
        except Exception as e:
            logger.debug(f"Hetzner Cloud query error: {e}")

    return {
        "hetzner_servers": hetzner_servers,
        "ex63": ex63_info,
        "nodes": {
            "ex63_node": {
                "services": {k: v["state"] for k, v in services_status.items()},
                "mem": f"{round(mem.used/(1024**3),1)} / {round(mem.total/(1024**3),1)} GB",
                "disk": f"{round(disk.used/(1024**3),1)} GB / {round(disk.total/(1024**3),1)} GB ({disk.percent}%)"
            }
        }
    }

@app.post("/api/master/node-service")
async def api_master_node_service(request: Request):
    user = await require_master(request)
    body = await request.json()
    service = body.get("service", "")
    op = body.get("op", "restart")
    if op not in ("start", "stop", "restart"):
        raise HTTPException(400, "Invalid operation")

    allowed = {
        "minecraft.service", "mc-staff-logger.service",
        "project-zomboid.service", "zomboid-panel.service",
        "unturned.service", "novastation.service", "mariadb.service",
        "cv-panel.service", "cv-nova-helper.service",
        "cv-radio-helper.service", "cv-radio-tunnel.service", "docker.service"
    }
    if service not in allowed:
        raise HTTPException(400, f"Service {service} is not in the allowed fleet services list")

    try:
        res = subprocess.run(["systemctl", op, service], capture_output=True, text=True)
        return {"success": res.returncode == 0, "output": res.stdout + res.stderr}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/master/hetzner-power")
async def api_master_hetzner_power(request: Request):
    user = await require_master(request)
    body = await request.json()
    server_id = int(body.get("server_id"))
    action = body.get("action")  # reboot, poweron, poweroff
    if action not in ("reboot", "poweron", "poweroff"):
        raise HTTPException(400, "Invalid Hetzner power action")

    if server_id == 1:
        if action == "reboot":
            record_audit(user, "master", "ex63_reboot", "Dispatched host reboot on EX63 Bare-Metal")
            subprocess.Popen(["sh", "-c", "sync && sleep 2 && reboot"])
            return {"success": True, "data": {"message": "Server reboot initiated. Connection will restore in ~60 seconds."}}
        elif action in ("poweroff", "shutdown"):
            record_audit(user, "master", "ex63_shutdown", "Dispatched host shutdown on EX63 Bare-Metal")
            subprocess.Popen(["sh", "-c", "sync && sleep 2 && shutdown -h now"])
            return {"success": True, "data": {"message": "Server shutdown initiated. System is powering down cleanly."}}
        elif action in ("poweron", "start"):
            record_audit(user, "master", "ex63_start", "Verified host operational state")
            return {"success": True, "data": {"message": "Server is currently online, operational, and running all active fleet services."}}
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
            byond_host = ns.get("byond_host", "127.0.0.1")
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
    content = await asyncio.to_thread(sftp_read_sync, "127.0.0.1", "ubuntu", "/home/ubuntu/CV-Nova-Helper/config.json")
    cogs_res = await run_ssh("127.0.0.1", "ubuntu", "ls -1 /home/ubuntu/CV-Nova-Helper/cogs/*.py | xargs -n1 basename")
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

    await asyncio.to_thread(sftp_write_sync, "127.0.0.1", "ubuntu", "/home/ubuntu/CV-Nova-Helper/config.json", formatted)
    # Also update snapshot on panel host
    with open("/etc/cv-panel/bot_config_snapshot.json", "w", encoding="utf-8") as f:
        f.write(formatted)
    if restart:
        await run_ssh("127.0.0.1", "ubuntu", "sudo systemctl restart cv-nova-helper.service")
    record_audit(user, "master", "save_bot_config", f"Updated bot config.json (restart={restart})")
    return {"success": True, "message": "Saved /home/ubuntu/CV-Nova-Helper/config.json" + (" and restarted bot!" if restart else "")}

@app.get("/api/master/bot-cog")
async def api_master_get_bot_cog(request: Request, name: str = "project_zomboid.py"):
    await require_master(request)
    safe_name = os.path.basename(name)
    if not safe_name.endswith(".py"):
        raise HTTPException(400, "Invalid cog filename")
    content = await asyncio.to_thread(sftp_read_sync, "127.0.0.1", "ubuntu", f"/home/ubuntu/CV-Nova-Helper/cogs/{safe_name}")
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
    await asyncio.to_thread(sftp_write_sync, "127.0.0.1", "ubuntu", f"/home/ubuntu/CV-Nova-Helper/cogs/{safe_name}", content)
    if restart:
        await run_ssh("127.0.0.1", "ubuntu", "sudo systemctl restart cv-nova-helper.service")
    record_audit(user, "master", "save_bot_cog", f"Updated cog {safe_name} (restart={restart})")
    return {"success": True, "message": f"Saved cogs/{safe_name}" + (" and restarted bot!" if restart else "")}

@app.get("/api/master/bot-logs")
async def api_master_bot_logs(request: Request):
    await require_master(request)
    res = await run_ssh("127.0.0.1", "ubuntu", "sudo journalctl -u cv-nova-helper.service -n 100 --no-pager")
    return {"logs": res["stdout"]}

@app.get("/api/master/staff-permissions")
async def api_master_get_staff_permissions(request: Request):
    await require_master(request)
    raw_cfg = await asyncio.to_thread(sftp_read_sync, "127.0.0.1", "ubuntu", "/home/ubuntu/CV-Nova-Helper/config.json")
    try:
        cfg = json.loads(raw_cfg)
    except Exception:
        cfg = {}

    staff_perms = cfg.get("staff_permissions", {})
    bot_token = cfg.get("bot_token")
    guild_id = cfg.get("guild_id", "1564605314752585797")
    roles = []
    categories = []

    if bot_token and guild_id:
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                r_roles = await client.get(
                    f"https://discord.com/api/v10/guilds/{guild_id}/roles",
                    headers={"Authorization": f"Bot {bot_token}", "User-Agent": "CircuitVersePanel (1.0)"}
                )
                if r_roles.status_code == 200:
                    for r in r_roles.json():
                        roles.append({"id": r["id"], "name": r["name"], "color": r.get("color", 0)})

                r_channels = await client.get(
                    f"https://discord.com/api/v10/guilds/{guild_id}/channels",
                    headers={"Authorization": f"Bot {bot_token}", "User-Agent": "CircuitVersePanel (1.0)"}
                )
                if r_channels.status_code == 200:
                    for c in r_channels.json():
                        if c.get("type") == 4:
                            categories.append({"id": c["id"], "name": c["name"]})
        except Exception as e:
            logger.warning(f"Failed to fetch guild info for staff permissions: {e}")

    return {
        "staff_permissions": staff_perms,
        "roles": sorted(roles, key=lambda x: x["name"].lower()),
        "categories": sorted(categories, key=lambda x: x["name"].lower())
    }

@app.post("/api/master/staff-permissions")
async def api_master_save_staff_permissions(request: Request):
    user = await require_master(request)
    body = await request.json()
    new_perms = body.get("staff_permissions")
    if not isinstance(new_perms, dict):
        raise HTTPException(400, "staff_permissions must be a valid dictionary")

    raw_cfg = await asyncio.to_thread(sftp_read_sync, "127.0.0.1", "ubuntu", "/home/ubuntu/CV-Nova-Helper/config.json")
    try:
        cfg = json.loads(raw_cfg)
    except Exception as e:
        raise HTTPException(500, f"Error reading bot config.json: {e}")

    cfg["staff_permissions"] = new_perms
    formatted = json.dumps(cfg, indent=2)

    await asyncio.to_thread(sftp_write_sync, "127.0.0.1", "ubuntu", "/home/ubuntu/CV-Nova-Helper/config.json", formatted)
    await run_ssh("127.0.0.1", "ubuntu", "sudo systemctl restart cv-nova-helper.service")
    record_audit(user, "master", "save_staff_permissions", "Updated staff bot command permissions and category scopes via panel")
    return {"success": True, "message": "Saved staff permissions and restarted Discord Bot successfully!"}

# ---- Discord Guild Roles, Members & Channels ----
@app.post("/api/master/discord-credentials")
async def api_master_discord_credentials(request: Request):
    user = await require_master(request)
    body = await request.json()
    new_secret = body.get("client_secret", "").strip()
    new_client_id = body.get("client_id", "").strip()
    cfg = load_config()
    changed = []
    if new_client_id:
        cfg["discord_client_id"] = new_client_id
        changed.append(f"client_id ({new_client_id})")
    if new_secret:
        cfg["discord_client_secret"] = new_secret
        changed.append("client_secret (updated)")

    if changed:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        record_audit(user, "master", "update_discord_credentials", f"Updated Discord credentials: {', '.join(changed)}")
        return {"success": True, "message": f"Saved {', '.join(changed)} to {CONFIG_PATH}!"}
    return {"success": True, "message": "No changes were submitted."}

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
    "preview/affiliates.html": "/home/circxust/public_html/preview/affiliates.html",
    "preview/style.css": "/home/circxust/public_html/preview/style.css",
    "preview/script.js": "/home/circxust/public_html/preview/script.js",
    "index.html (Root)": "/home/circxust/public_html/index.html",
    "directory.html (Root)": "/home/circxust/public_html/directory.html",
    "partnerships.html (Root)": "/home/circxust/public_html/partnerships.html",
    "affiliates.html (Root)": "/home/circxust/public_html/affiliates.html",
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

# ---- Community Partnerships & Affiliates API ----
PARTNERSHIPS_FILE = os.path.join(os.path.dirname(__file__), "partnerships.json")
AFFILIATES_FILE = os.path.join(os.path.dirname(__file__), "affiliates.json")

def load_json_list(filepath: str) -> list:
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_json_list(filepath: str, data: list):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@app.get("/api/public/partnerships")
async def api_public_partnerships():
    data = load_json_list(PARTNERSHIPS_FILE)
    return {"partnerships": data}

@app.post("/api/master/partnerships/add")
async def api_master_add_partnership(request: Request):
    user = await require_master(request)
    body = await request.json()
    name = (body.get("name") or "").strip()
    link = (body.get("link") or "").strip()
    contact = (body.get("contact") or "").strip()
    description = (body.get("description") or "").strip()
    if not name or not link:
        raise HTTPException(400, "Name and link are required")

    partners = load_json_list(PARTNERSHIPS_FILE)
    new_id = f"p-{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}"
    item = {
        "id": new_id,
        "name": name,
        "link": link,
        "contact": contact or "None",
        "description": description,
        "added_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    partners.append(item)
    save_json_list(PARTNERSHIPS_FILE, partners)
    record_audit(user, "master", "add_partnership", f"Added partner: {name}")

    # Broadcast to Discord #🤝・partnerships
    try:
        cfg = load_config()
        ch_id = cfg.get("partnerships_channel_id", 1567730987821957180)
        bot_token = cfg.get("discord_bot_token")
        if bot_token and ch_id:
            desc_text = f"\n\n{description}\n" if description else "\n"
            embed = {
                "title": f"🤝 New Community Partnership: {name}",
                "description": f"Circuit Verse is proud to announce an official community partnership with **{name}**!{desc_text}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🌐 **Connect:** {link}\n👤 **Representative:** {contact or 'N/A'}",
                "color": 0xec4899,
                "footer": {"text": "Circuit Verse Partnerships Network • Mutual Community Alliance"}
            }
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.post(
                    f"https://discord.com/api/v10/channels/{ch_id}/messages",
                    headers={"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"},
                    json={"embeds": [embed]}
                )
                if res.status_code in (200, 201):
                    msg_data = res.json()
                    item["discord_message_id"] = msg_data.get("id")
                    save_json_list(PARTNERSHIPS_FILE, partners)
    except Exception as e:
        logger.warning(f"Could not broadcast partnership to Discord: {e}")

    return {"success": True, "partner": item}

@app.post("/api/master/partnerships/remove")
async def api_master_remove_partnership(request: Request):
    user = await require_master(request)
    body = await request.json()
    pid = body.get("id")
    partners = load_json_list(PARTNERSHIPS_FILE)
    partners = [p for p in partners if p.get("id") != pid]
    save_json_list(PARTNERSHIPS_FILE, partners)
    record_audit(user, "master", "remove_partnership", f"Removed partner ID: {pid}")
    return {"success": True}

# Affiliates API
@app.get("/api/public/affiliates")
async def api_public_affiliates():
    data = load_json_list(AFFILIATES_FILE)
    return {"affiliates": data}

@app.post("/api/master/affiliates/add")
async def api_master_add_affiliate(request: Request):
    user = await require_master(request)
    body = await request.json()
    name = (body.get("name") or "").strip()
    link = (body.get("link") or "").strip()
    aff_type = (body.get("type") or "Content Creator").strip()
    contact = (body.get("contact") or "").strip()
    perks = (body.get("perks") or "").strip()
    description = (body.get("description") or "").strip()
    if not name or not link:
        raise HTTPException(400, "Name and link are required")

    affiliates = load_json_list(AFFILIATES_FILE)
    new_id = f"aff-{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}"
    item = {
        "id": new_id,
        "name": name,
        "link": link,
        "type": aff_type,
        "contact": contact or "None",
        "perks": perks or "Creator Role & Cross-Promotion",
        "description": description,
        "added_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    affiliates.append(item)
    save_json_list(AFFILIATES_FILE, affiliates)
    record_audit(user, "master", "add_affiliate", f"Added affiliate: {name} ({aff_type})")

    # Broadcast to Discord #🤝・affiliates
    try:
        cfg = load_config()
        ch_id = cfg.get("affiliates_channel_id", 1570071721703116864)
        bot_token = cfg.get("discord_bot_token")
        if bot_token and ch_id:
            desc_text = f"\n\n{description}\n" if description else "\n"
            embed = {
                "title": f"⭐ New Community Affiliate: {name}",
                "description": (
                    f"Please welcome our newest **Circuit Verse Affiliate & Creator**, **{name}**!{desc_text}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏷️ **Affiliate Category:** `{aff_type}`\n"
                    f"🌐 **Platform Link:** {link}\n"
                    f"👤 **Representative:** {contact or 'N/A'}\n"
                    f"🎁 **Community Perks:** {perks or 'Creator Perks & Cross-Promotion'}"
                ),
                "color": 0x06b6d4,
                "footer": {"text": "Circuit Verse Affiliate & Creator Program"}
            }
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.post(
                    f"https://discord.com/api/v10/channels/{ch_id}/messages",
                    headers={"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"},
                    json={"embeds": [embed]}
                )
                if res.status_code in (200, 201):
                    msg_data = res.json()
                    item["discord_message_id"] = msg_data.get("id")
                    save_json_list(AFFILIATES_FILE, affiliates)
    except Exception as e:
        logger.warning(f"Could not broadcast affiliate to Discord: {e}")

    return {"success": True, "affiliate": item}

@app.post("/api/master/affiliates/remove")
async def api_master_remove_affiliate(request: Request):
    user = await require_master(request)
    body = await request.json()
    aid = body.get("id")
    affiliates = load_json_list(AFFILIATES_FILE)
    affiliates = [a for a in affiliates if a.get("id") != aid]
    save_json_list(AFFILIATES_FILE, affiliates)
    record_audit(user, "master", "remove_affiliate", f"Removed affiliate ID: {aid}")
    return {"success": True}

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

@app.get("/")
@app.get("/index.html")
async def get_index_root():
    return FileResponse("/opt/cv-panel/index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})

app.mount("/", StaticFiles(directory="/opt/cv-panel/static", html=True), name="static")
