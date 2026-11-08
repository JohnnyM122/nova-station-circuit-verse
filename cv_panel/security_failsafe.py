import asyncio
import datetime
import hashlib
import json
import logging
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger("cv-panel.security")

DB_PATH = "/etc/cv-panel/audit.db"

# =====================================================================
# BOT INTRUSION DETECTION & AUTONOMOUS QUARANTINE SENTINEL
# =====================================================================

BOT_REGISTRY = {
    "cv_nova_helper": {
        "id": "1566602346715160716",
        "name": "Circuit Verse Helper",
        "service": "cv-nova-helper.service",
        "proc_pattern": "CV-Nova-Helper",
        "invite_url": "https://discord.com/oauth2/authorize?client_id=1566602346715160716&permissions=8&scope=bot%20applications.commands"
    },
    "cv_radio_helper": {
        "id": "1568619465434857695",
        "name": "CV Radio Helper",
        "service": "cv-radio-helper.service",
        "proc_pattern": "CV-Radio-Helper",
        "invite_url": "https://discord.com/oauth2/authorize?client_id=1568619465434857695&permissions=37080384&scope=bot%20applications.commands"
    }
}

def init_bot_defense_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS bot_quarantine_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_key TEXT,
            bot_id TEXT,
            action TEXT,
            reason TEXT,
            triggered_by TEXT,
            ts REAL
        )
    """)
    conn.commit()
    conn.close()

init_bot_defense_db()

async def execute_bot_quarantine(cfg: Dict[str, Any], bot_key: str, action: str, reason: str, triggered_by: str, run_ssh_fn) -> Dict[str, Any]:
    bot_info = BOT_REGISTRY.get(bot_key)
    if not bot_info:
        raise HTTPException(400, f"Unknown bot key: {bot_key}")

    bot_id = bot_info["id"]
    bot_name = bot_info["name"]
    service = bot_info["service"]
    proc = bot_info["proc_pattern"]
    token = cfg.get("discord_bot_token", "")
    guild_id = cfg.get("guild_id", "1564605314752585797")

    results = []

    if action == "kill":
        # 1. SSH to 2.31.173.113 and mask/kill systemd service immediately
        try:
            cmd = f"sudo systemctl mask --now {service} && sudo pkill -9 -f '{proc}' || true"
            await run_ssh_fn("2.31.173.113", "root", cmd, timeout=15)
            results.append(f"Host service {service} masked and process terminated.")
        except Exception as e:
            results.append(f"Host SSH action error: {e}")

        # 2. Kick/Leave Discord Guild
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                if bot_key == "cv_radio_helper":
                    # Circuit Verse Helper kicks CV Radio Helper
                    kick_url = f"https://discord.com/api/v10/guilds/{guild_id}/members/{bot_id}"
                    resp = await client.delete(kick_url, headers={
                        "Authorization": f"Bot {token}",
                        "X-Audit-Log-Reason": f"EMERGENCY BOT KILLSWITCH: {reason} (By: {triggered_by})"
                    })
                    if resp.status_code in (200, 204):
                        results.append(f"Bot {bot_name} kicked from Discord server.")
                    else:
                        results.append(f"Discord kick returned HTTP {resp.status_code}")
                elif bot_key == "cv_nova_helper":
                    # Force bot to leave guild via DELETE /users/@me/guilds/{guild_id}
                    leave_url = f"https://discord.com/api/v10/users/@me/guilds/{guild_id}"
                    resp = await client.delete(leave_url, headers={
                        "Authorization": f"Bot {token}"
                    })
                    if resp.status_code in (200, 204):
                        results.append(f"Bot {bot_name} evicted (forced leave) from Discord server.")
                    else:
                        results.append(f"Discord leave returned HTTP {resp.status_code}")
            except Exception as e:
                results.append(f"Discord API kick error: {e}")

        # 3. Log quarantine event
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO bot_quarantine_events (bot_key, bot_id, action, reason, triggered_by, ts) VALUES (?, ?, ?, ?, ?, ?)",
                  (bot_key, bot_id, "kill", reason, triggered_by, time.time()))
        conn.commit()
        conn.close()

        # 4. Emergency Discord Dispatch
        dispatch_desc = "\n".join([
            f"**Target Bot:** `{bot_name}` (ID: `{bot_id}`)",
            f"**Reason:** {reason}",
            f"**Triggered By:** `{triggered_by}`",
            "",
            "**Protective Containment Actions Taken:**"
        ] + [f"• {r}" for r in results] + [
            "",
            "⚠️ *The host service is permanently masked on 2.31.173.113 and cannot restart until manually unmasked.*"
        ])
        await broadcast_discord_security_alert(
            cfg,
            f"🚨 EMERGENCY BOT KILLSWITCH EXECUTED: {bot_name.upper()}",
            dispatch_desc,
            color=0x991b1b
        )

        return {"success": True, "message": f"Bot {bot_name} neutralized and kicked from Discord server.", "details": results}

    elif action == "restore":
        # Unmask and restart service
        try:
            cmd = f"sudo systemctl unmask {service} && sudo systemctl restart {service}"
            await run_ssh_fn("2.31.173.113", "root", cmd, timeout=15)
            results.append(f"Service {service} unmasked and restarted.")
        except Exception as e:
            results.append(f"Host SSH action error: {e}")

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO bot_quarantine_events (bot_key, bot_id, action, reason, triggered_by, ts) VALUES (?, ?, ?, ?, ?, ?)",
                  (bot_key, bot_id, "restore", reason, triggered_by, time.time()))
        conn.commit()
        conn.close()

        restore_desc = "\n".join([
            f"**Bot:** `{bot_name}` (ID: `{bot_id}`)",
            f"**Restored By:** `{triggered_by}`",
            f"**Notes:** {reason}",
            "",
            "Host service unmasked and restarted.",
            f"*(If the bot was kicked from Discord, authorize it again via its invite URL: [Click here to re-invite]({bot_info['invite_url']}))*"
        ])
        await broadcast_discord_security_alert(
            cfg,
            f"🟢 BOT SERVICE RESTORED: {bot_name.upper()}",
            restore_desc,
            color=0x10b981
        )

        return {"success": True, "message": f"Service {service} unmasked and restarted.", "details": results, "invite_url": bot_info["invite_url"]}

    else:
        raise HTTPException(400, "Invalid action (expected 'kill' or 'restore')")


def load_panel_config() -> Dict[str, Any]:
    try:
        with open("/etc/cv-panel/config.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}

def get_ip_subnet(ip: str) -> str:
    if not ip or ip == "unknown":
        return "unknown"
    if "." in ip:
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    elif ":" in ip:
        parts = ip.split(":")
        if len(parts) >= 4:
            return ":".join(parts[:4]) + "::/64"
    return ip

def get_client_ip(request: Request) -> str:
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"

def get_ua_hash(request: Request) -> str:
    ua = request.headers.get("user-agent", "unknown")
    return hashlib.sha256(ua.encode("utf-8")).hexdigest()[:16]

def get_security_setting(key: str, default: str = "") -> str:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM panel_security_settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def set_security_setting(key: str, value: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO panel_security_settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def is_account_locked(discord_id: str) -> Tuple[bool, Optional[str]]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT active, reason FROM staff_lockouts WHERE discord_id = ?", (str(discord_id),))
    row = c.fetchone()
    conn.close()
    if row and row[0] == 1:
        return True, row[1]
    return False, None

def is_defcon_active() -> bool:
    return get_security_setting("defcon_emergency_freeze", "false").lower() == "true"

def verify_session_security(request: Request, user: Dict[str, Any]) -> Tuple[bool, str]:
    now = time.time()
    sid = user.get("session_id", "")
    did = str(user.get("discord_id", ""))

    # 1. Check Global Emergency DEFCON 1
    if is_defcon_active():
        role_ids = set(user.get("role_ids", []))
        # Founder (1564610713216098394) is the only role allowed during DEFCON 1
        if "1564610713216098394" not in role_ids:
            return False, "DEFCON 1 Emergency Freeze is active. Panel access temporarily locked."

    # 2. Check Staff Account Lockout Failsafe
    locked, reason = is_account_locked(did)
    if locked:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM sessions WHERE discord_id = ?", (did,))
        conn.commit()
        conn.close()
        logger.warning(f"?? Terminated session for emergency locked staff account {did} ({reason})")
        return False, f"Account Frozen: {reason}"

    # 3. Check Session Max Lifetime (24h)
    max_lifetime = int(get_security_setting("max_session_seconds", "86400"))
    created_at = user.get("created_at") or user.get("updated_at", now)
    if now - created_at > max_lifetime:
        return False, "Session expired (max lifetime reached). Please sign in again."

    # 4. Check Idle Timeout (2h default)
    idle_limit = int(get_security_setting("idle_timeout_seconds", "7200"))
    last_active = user.get("last_active_at") or user.get("updated_at", now)
    if now - last_active > idle_limit:
        return False, "Session expired due to inactivity. Please sign in again."

    # 5. Check User-Agent Fingerprint & IP Subnet Binding (Infostealer / Session Hijacking Defense)
    ua_binding = get_security_setting("ua_binding_enabled", "true") == "true"
    ip_binding = get_security_setting("ip_binding_enabled", "true") == "true"
    strict_ip = get_security_setting("strict_ip_binding", "false") == "true"

    req_ua_hash = get_ua_hash(request)
    req_ip = get_client_ip(request)
    stored_ua = user.get("user_agent_hash", "")
    stored_ip = user.get("ip_address", "")

    ua_mismatch = bool(stored_ua and stored_ua != req_ua_hash) if ua_binding else False
    stored_subnet = get_ip_subnet(stored_ip)
    req_subnet = get_ip_subnet(req_ip)
    ip_mismatch = bool(stored_ip and stored_subnet != "unknown" and req_subnet != "unknown" and stored_subnet != req_subnet) if ip_binding else False

    # Scenario 1: Critical Infostealer Token Replay (Both UA and IP changed)
    if ua_mismatch and ip_mismatch:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
        conn.commit()
        conn.close()
        logger.critical(f"🚨 CRITICAL SESSION HIJACK INTERCEPTED: Stolen session {sid[:8]} for user '{user.get('username')}' attempted from {req_ip} (Stored: {stored_ip}). Session purged.")
        try:
            loop = asyncio.get_running_loop()
            cfg = load_panel_config()
            loop.create_task(broadcast_discord_security_alert(
                cfg,
                "🚨 CRITICAL SESSION HIJACK INTERCEPTED (Infostealer Defense)",
                f"**User:** `{user.get('username')}` (<@{did}>)\n"
                f"**Original Login:** `{stored_ip}` (Subnet: `{stored_subnet}`)\n"
                f"**Hijack Attempt IP:** `{req_ip}` (Subnet: `{req_subnet}`)\n"
                f"**User-Agent:** Mismatch (`{req_ua_hash}` != `{stored_ua}`)\n\n"
                f"**Protective Action Taken:** The session token was permanently deleted across all panels immediately.",
                color=0x991b1b
            ))
        except Exception:
            pass
        return False, "Session terminated: Unauthorized device and network connection detected (Infostealer defense trigger)."

    # Scenario 2: UA mismatch on same IP
    if ua_mismatch:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
        conn.commit()
        conn.close()
        logger.warning(f"⚠️ Potential session hijack: UA mismatch for user {user.get('username')}")
        return False, "Session invalidated due to device fingerprint mismatch."

    # Scenario 3: IP changed outside subnet with same UA (User network transition)
    if ip_mismatch:
        if strict_ip:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
            conn.commit()
            conn.close()
            return False, f"Session invalidated due to network change from {stored_ip} to {req_ip} (Strict IP Binding enabled)."
        else:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("UPDATE sessions SET ip_address = ? WHERE session_id = ?", (req_ip, sid))
            conn.commit()
            conn.close()
            logger.info(f"Session {sid[:8]} ({user.get('username')}) subnet roaming permitted ({stored_ip} -> {req_ip}).")

    # 6. Check Staff MFA/2FA Requirement
    if get_security_setting("require_mfa_for_staff", "true") == "true":
        access = user.get("access", {})
        if access.get("any_staff") and not user.get("mfa_enabled", 1):
            return False, "Discord 2FA is strictly required for Circuit Verse staff panel access."

    # Update last_active_at
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE sessions SET last_active_at = ? WHERE session_id = ?", (now, sid))
    conn.commit()
    conn.close()

    return True, "OK"

async def broadcast_discord_security_alert(cfg: Dict[str, Any], title: str, description: str, color: int = 0xef4444):
    token = cfg.get("discord_bot_token")
    if not token:
        return
    channels = [
        cfg.get("channels", {}).get("discord_logs", 1566986370910654517),
        1567474488059363418  # ????executives
    ]
    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "footer": {"text": "Circuit Verse ? Security & Account Failsafe System"}
        }]
    }
    async with httpx.AsyncClient(timeout=10) as client:
        for cid in channels:
            try:
                await client.post(
                    f"https://discord.com/api/v10/channels/{cid}/messages",
                    headers={"Authorization": f"Bot {token}", "Content-Type": "application/json"},
                    json=payload
                )
            except Exception as e:
                logger.error(f"Failed to post security alert to channel {cid}: {e}")

def setup_security_failsafe(app: FastAPI, helpers: Dict[str, Any]):
    load_config = helpers["load_config"]
    get_current_user = helpers["get_current_user"]
    run_rcon = helpers["run_rcon"]
    run_ssh = helpers["run_ssh"]
    record_audit = helpers["record_audit"]
    asyncio.create_task(bot_sentinel_watchdog_loop(app, load_config, run_ssh))

    async def require_master(request: Request) -> Dict[str, Any]:
        cfg = load_config()
        bot_token = request.headers.get("x-bot-token", "")
        if bot_token and bot_token == cfg.get("discord_bot_token"):
            return {
                "username": request.headers.get("x-executor-name", "Circuit Verse Bot"),
                "discord_id": request.headers.get("x-executor-id", "BOT"),
                "role_ids": ["1564610713216098394"],
                "access": {"master_unlocked": True, "any_staff": True}
            }
        user = await get_current_user(request)
        if not user or not user.get("access", {}).get("master_unlocked"):
            raise HTTPException(403, "Secondary Master Password required")
        return user

    @app.get("/api/master/security/overview")
    async def api_security_overview(request: Request):
        await require_master(request)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Get active sessions
        c.execute("SELECT session_id, discord_id, username, global_name, avatar, ip_address, user_agent_hash, mfa_enabled, created_at, last_active_at, updated_at FROM sessions ORDER BY updated_at DESC")
        sessions = [dict(r) for r in c.fetchall()]

        # Get lockouts
        c.execute("SELECT * FROM staff_lockouts WHERE active = 1 ORDER BY locked_at DESC")
        lockouts = [dict(r) for r in c.fetchall()]
        conn.close()

        cfg = load_config()
        return {
            "defcon_active": is_defcon_active(),
            "require_mfa": get_security_setting("require_mfa_for_staff", "true") == "true",
            "idle_timeout": int(get_security_setting("idle_timeout_seconds", "7200")),
            "max_lifetime": int(get_security_setting("max_session_seconds", "86400")),
            "active_sessions_count": len(sessions),
            "sessions": sessions,
            "active_lockouts_count": len(lockouts),
            "lockouts": lockouts,
        }

    @app.post("/api/master/security/lockout")
    async def api_security_lockout(request: Request):
        user = await require_master(request)
        body = await request.json()
        target_id = str(body.get("target_discord_id", "")).strip()
        action = body.get("action", "freeze")  # "freeze" or "unfreeze"
        reason = body.get("reason", "Suspected Account Compromise / Unauthorized Activity").strip()

        if not target_id:
            raise HTTPException(400, "Target Discord ID is required")

        cfg = load_config()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        if action == "freeze":
            now = time.time()
            # 1. Register lockout
            c.execute("""
                INSERT OR REPLACE INTO staff_lockouts (discord_id, username, reason, locked_by, locked_at, active)
                VALUES (?, (SELECT username FROM sessions WHERE discord_id = ? LIMIT 1), ?, ?, ?, 1)
            """, (target_id, target_id, reason, user.get("username", "admin"), now))
            
            # 2. Terminate all active sessions for target
            c.execute("DELETE FROM sessions WHERE discord_id = ?", (target_id,))
            conn.commit()
            conn.close()

            # 3. Strip in-game staff ranks (Zero-Trust Mitigation)
            # Minecraft: demote LuckPerms to default if linked
            try:
                await run_rcon("2.31.101.63", 25575, cfg.get("mc_server", {}).get("rcon_password", ""), f"lp user {target_id} parent set default")
            except Exception:
                pass

            # 4. Broadcast emergency Discord alert
            await broadcast_discord_security_alert(
                cfg,
                "?? EMERGENCY STAFF ACCOUNT LOCKOUT EXECUTED",
                f"**Target Staff Discord ID:** `{target_id}` (<@{target_id}>)\n"
                f"**Reason:** {reason}\n"
                f"**Executed By:** <@{user.get('discord_id')}> (`{user.get('username')}`)\n\n"
                f"**Automated Protective Measures Taken:**\n"
                f"? All active web panel sessions instantly terminated.\n"
                f"? SSO login permanently blocked until manual identity verification.\n"
                f"? In-game staff permissions demoted to default player.",
                color=0xef4444
            )

            record_audit(user, "security", "emergency_lockout", f"Frozen staff Discord ID {target_id}: {reason}")
            return {"success": True, "message": f"Successfully frozen staff account {target_id} across all services!"}

        elif action == "unfreeze":
            c.execute("UPDATE staff_lockouts SET active = 0 WHERE discord_id = ?", (target_id,))
            conn.commit()
            conn.close()

            await broadcast_discord_security_alert(
                cfg,
                "?? STAFF ACCOUNT LOCKOUT LIFTED",
                f"**Staff Discord ID:** `{target_id}` (<@{target_id}>)\n"
                f"**Unlocked By:** <@{user.get('discord_id')}> (`{user.get('username')}`)\n"
                f"Account has been verified and restored to regular status.",
                color=0x10b981
            )

            record_audit(user, "security", "unfreeze_account", f"Unlocked staff Discord ID {target_id}")
            return {"success": True, "message": f"Account {target_id} has been restored."}

        else:
            conn.close()
            raise HTTPException(400, "Unknown action")

    @app.post("/api/master/security/terminate-session")
    async def api_security_terminate_session(request: Request):
        user = await require_master(request)
        body = await request.json()
        sid = body.get("session_id", "").strip()
        if not sid:
            raise HTTPException(400, "session_id required")
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
        conn.commit()
        conn.close()

        record_audit(user, "security", "terminate_session", f"Force terminated session {sid[:8]}")
        return {"success": True, "message": f"Session {sid[:8]} terminated."}

    @app.get("/api/master/security/bots")
    async def api_security_bots(request: Request):
        await require_master(request)
        cfg = load_config()
        token = cfg.get("discord_bot_token", "")
        guild_id = cfg.get("guild_id", "1564605314752585797")

        # 1. Query host systemd status on 2.31.173.113
        service_statuses = {}
        try:
            ssh_res = await run_ssh("2.31.173.113", "root", "systemctl is-active cv-nova-helper cv-radio-helper 2>/dev/null; echo '---'; systemctl is-enabled cv-nova-helper cv-radio-helper 2>/dev/null", timeout=8)
            out = ssh_res.get("stdout", "") if isinstance(ssh_res, dict) else str(ssh_res)
            parts = out.split('---')
            actives = parts[0].strip().split() if len(parts) > 0 else []
            enableds = parts[1].strip().split() if len(parts) > 1 else []
            service_statuses["cv_nova_helper"] = {
                "active": actives[0] if len(actives) > 0 else "unknown",
                "enabled": enableds[0] if len(enableds) > 0 else "unknown"
            }
            service_statuses["cv_radio_helper"] = {
                "active": actives[1] if len(actives) > 1 else "unknown",
                "enabled": enableds[1] if len(enableds) > 1 else "unknown"
            }
        except Exception as e:
            service_statuses["error"] = str(e)

        # 2. Query Discord membership for both bots
        discord_statuses = {}
        async with httpx.AsyncClient(timeout=8) as client:
            for bkey, binfo in BOT_REGISTRY.items():
                try:
                    url = f"https://discord.com/api/v10/guilds/{guild_id}/members/{binfo['id']}"
                    resp = await client.get(url, headers={"Authorization": f"Bot {token}"})
                    discord_statuses[bkey] = resp.status_code == 200
                except Exception:
                    discord_statuses[bkey] = False

        # 3. Query quarantine events
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT bot_key, bot_id, action, reason, triggered_by, ts FROM bot_quarantine_events ORDER BY ts DESC LIMIT 15")
        events = [dict(r) for r in c.fetchall()]
        conn.close()

        bots_data = []
        for bkey, binfo in BOT_REGISTRY.items():
            sst = service_statuses.get(bkey, {})
            is_masked = sst.get("enabled") == "masked"
            is_active = sst.get("active") == "active"
            in_discord = discord_statuses.get(bkey, False)
            bots_data.append({
                "key": bkey,
                "id": binfo["id"],
                "name": binfo["name"],
                "service": binfo["service"],
                "active": is_active,
                "masked": is_masked,
                "in_discord": in_discord,
                "invite_url": binfo["invite_url"]
            })

        return {
            "bots": bots_data,
            "events": events,
            "sentinel_active": True
        }

    @app.post("/api/master/security/bot-killswitch")
    async def api_security_bot_killswitch(request: Request):
        user = await require_master(request)
        body = await request.json()
        bot_key = body.get("bot_key", "").strip()
        action = body.get("action", "kill").strip()
        reason = body.get("reason", "Suspected token compromise or unauthorized activity").strip()
        cfg = load_config()

        triggered_by = f"{user.get('username')} ({user.get('discord_id')})"

        if bot_key == "all":
            results = []
            for bk in ["cv_radio_helper", "cv_nova_helper"]:
                res = await execute_bot_quarantine(cfg, bk, action, reason, triggered_by, run_ssh)
                results.append(res)
            record_audit(user, "security", "bot_killswitch_all", f"{action.upper()} all bots: {reason}")
            return {"success": True, "message": f"Successfully executed {action} across all bots!", "results": results}
        else:
            res = await execute_bot_quarantine(cfg, bot_key, action, reason, triggered_by, run_ssh)
            record_audit(user, "security", f"bot_killswitch_{bot_key}", f"{action.upper()} {bot_key}: {reason}")
            return res

    @app.post("/api/master/security/defcon")
    async def api_security_defcon(request: Request):
        user = await require_master(request)
        body = await request.json()
        enable = bool(body.get("enable", False))
        reason = body.get("reason", "Executive Emergency Defcon 1 Lock").strip()

        set_security_setting("defcon_emergency_freeze", "true" if enable else "false")
        cfg = load_config()

        if enable:
            # Terminate all non-founder sessions immediately
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM sessions WHERE discord_id != '1564610713216098394'")
            conn.commit()
            conn.close()

            await broadcast_discord_security_alert(
                cfg,
                "?? DEFCON 1 GLOBAL EMERGENCY LOCKDOWN ACTIVATED",
                f"**All staff control panels have been frozen globally.**\n"
                f"**Reason:** {reason}\n"
                f"**Activated By:** <@{user.get('discord_id')}> (`{user.get('username')}`)\n\n"
                f"Only the Founder retains emergency console authority until this lockdown is deactivated.",
                color=0x991b1b
            )
            record_audit(user, "security", "defcon_activate", f"DEFCON 1 activated: {reason}")
            return {"success": True, "message": "DEFCON 1 Global Emergency Lockdown ACTIVATED!"}
        else:
            await broadcast_discord_security_alert(
                cfg,
                "?? DEFCON 1 GLOBAL EMERGENCY LOCKDOWN DEACTIVATED",
                f"**Normal operations and staff panel logins have been restored.**\n"
                f"**Deactivated By:** <@{user.get('discord_id')}> (`{user.get('username')}`)",
                color=0x10b981
            )
            record_audit(user, "security", "defcon_deactivate", "DEFCON 1 deactivated")
            return {"success": True, "message": "DEFCON 1 Lockdown lifted. Normal operations restored."}

# Background Sentinel Watchdog
SENTINEL_RUNNING = False

async def bot_sentinel_watchdog_loop(app_instance, cfg_loader, run_ssh_fn):
    global SENTINEL_RUNNING
    if SENTINEL_RUNNING:
        return
    SENTINEL_RUNNING = True
    logger.info("🛡️ Bot Intrusion Detection Sentinel Watchdog started (15s poll).")

    last_checked_id = None
    recent_strikes = {} # bot_id -> list of (timestamp, action_type, entry_id)
    seen_entry_ids = set()

    while True:
        try:
            await asyncio.sleep(15)
            cfg = cfg_loader()
            token = cfg.get("discord_bot_token")
            guild_id = cfg.get("guild_id", "1564605314752585797")
            if not token:
                continue

            # Fetch last 20 audit log entries
            async with httpx.AsyncClient(timeout=8) as client:
                url = f"https://discord.com/api/v10/guilds/{guild_id}/audit-logs?limit=20"
                resp = await client.get(url, headers={"Authorization": f"Bot {token}"})
                if resp.status_code != 200:
                    continue
                data = resp.json()
                entries = data.get("audit_log_entries", [])

            now = time.time()
            # Check maintenance flag
            import os
            if os.path.exists("/tmp/sentinel_maintenance"):
                await asyncio.sleep(60)
                continue

            bot_ids = {b["id"]: bkey for bkey, b in BOT_REGISTRY.items()}

            for e in entries:
                entry_id = str(e.get("id"))
                if entry_id in seen_entry_ids:
                    continue
                seen_entry_ids.add(entry_id)
                # Keep seen_entry_ids bounded
                if len(seen_entry_ids) > 500:
                    seen_entry_ids = set(list(seen_entry_ids)[-250:])

                user_id = str(e.get("user_id", ""))
                action_type = e.get("action_type") # 12=CHANNEL_DELETE, 20=MEMBER_KICK, 22=MEMBER_BAN_ADD, 32=ROLE_DELETE

                if user_id in bot_ids and action_type in (12, 20, 22, 32):
                    strikes = recent_strikes.setdefault(user_id, [])
                    # Record strike if within 60s
                    strikes.append((now, action_type))
                    # Purge strikes older than 60s
                    recent_strikes[user_id] = [s for s in strikes if now - s[0] < 60]

                    # Anomaly thresholds (significantly adjusted for realistic administration):
                    # - Mass kicks/bans (20, 22): >= 10 in 60s
                    # - Total destructive actions (including channel/role maintenance): >= 15 in 60s
                    kicks_bans = [s for s in recent_strikes[user_id] if s[1] in (20, 22)]
                    total_actions = len(recent_strikes[user_id])

                    if len(kicks_bans) >= 10 or total_actions >= 15:
                        bot_key = bot_ids[user_id]
                        logger.critical(f"🚨 SENTINEL ANOMALY TRIGGERED: Bot {bot_key} exceeded destructive action threshold ({total_actions} actions, {len(kicks_bans)} kicks/bans)! Engaging automatic killswitch!")
                        recent_strikes[user_id] = [] # reset strikes
                        asyncio.create_task(execute_bot_quarantine(
                            cfg,
                            bot_key,
                            "kill",
                            f"AUTOMATIC DEFENSE: Detected {total_actions} mass destructive actions ({len(kicks_bans)} kicks/bans) in 60 seconds. Rogue activity contained.",
                            "Autonomous Sentinel Daemon",
                            run_ssh_fn
                        ))

        except Exception as err:
            logger.error(f"Sentinel watchdog loop error: {err}")
