import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import sys
import logging
import asyncio
import subprocess
from byond import ByondClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("CVNovaHelper")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Config file not found at {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

config = load_config()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.config = config
bot.byond = ByondClient(
    host=config.get("byond", {}).get("host", "127.0.0.1"),
    port=config.get("byond", {}).get("port", 7777),
    comms_key=config.get("byond", {}).get("comms_key", "")
)

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user.name} ({bot.user.id})")
    try:
        guild_id = config.get("guild_id")
        if guild_id:
            guild_obj = discord.Object(id=guild_id)
            bot.tree.copy_global_to(guild=guild_obj)
            synced_guild = await bot.tree.sync(guild=guild_obj)
            logger.info(f"Instantly synced {len(synced_guild)} slash commands to guild {guild_id}.")
        synced_global = await bot.tree.sync()
        logger.info(f"Synced {len(synced_global)} application slash commands globally.")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")

@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def sync_commands(ctx: commands.Context):
    """Force an instant sync of slash commands to this Discord guild"""
    msg = await ctx.send("⏳ Syncing slash commands directly to this server...")
    try:
        guild_obj = discord.Object(id=ctx.guild.id)
        bot.tree.copy_global_to(guild=guild_obj)
        synced = await bot.tree.sync(guild=guild_obj)
        await msg.edit(content=f"✅ Successfully synced **{len(synced)}** slash commands to this server! If they don't appear immediately, press `Ctrl+R` to refresh Discord.")
    except Exception as e:
        await msg.edit(content=f"❌ Failed to sync slash commands: {e}")

@bot.command(name="update")
@commands.has_permissions(administrator=True)
async def update_command(ctx: commands.Context):
    """Force an instant update of the bot, Discord roles, and slash commands"""
    msg = await ctx.send("🔄 Running CV-Nova-Helper update...")
    try:
        staff_cog = bot.get_cog("StaffManagementCog")
        if staff_cog:
            await staff_cog.sync_all_member_roles()
            await bot.byond.reload_admins(sender=ctx.author.display_name)
        guild_obj = discord.Object(id=ctx.guild.id)
        bot.tree.copy_global_to(guild=guild_obj)
        synced = await bot.tree.sync(guild=guild_obj)
        await msg.edit(content=f"✅ **Bot update complete!** In-game admin ranks reloaded and **{len(synced)}** commands synchronized to server.")
    except Exception as e:
        await msg.edit(content=f"❌ Update failed: {e}")

@bot.command(name="botshutdown", aliases=["bot_shutdown", "shutdownbot"])
@commands.has_permissions(administrator=True)
async def prefix_shutdown(ctx: commands.Context, *, reason: str = "Administrator requested shutdown"):
    """Safely shut down the Discord bot service"""
    embed = discord.Embed(
        title="🛑 CV-Nova-Helper Shutting Down",
        description=f"Bot shutdown initiated by {ctx.author.mention}.\n**Reason:** `{reason}`\n\nThe Discord bot service (`cv-nova-helper.service`) is now terminating and will remain offline until manually restarted on the host.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

    async def execute_shutdown():
        await asyncio.sleep(1.5)
        logger.warning(f"Bot shutdown by {ctx.author} (Reason: {reason})")
        try:
            subprocess.Popen(["sudo", "systemctl", "stop", "cv-nova-helper.service"])
        except Exception as e:
            logger.error(f"Error calling systemctl stop: {e}")
        await bot.close()
        sys.exit(0)

    asyncio.create_task(execute_shutdown())

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return  # Gracefully ignore unknown ! commands
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have permission to execute this command.")
        return
    logger.error(f"Error in prefix command '{ctx.command}': {error}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    logger.error(f"Command error in {interaction.command.name if interaction.command else 'unknown'}: {error}")
    try:
        msg = f"❌ An error occurred while executing this command: `{error}`"
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass

@bot.tree.command(name="setup_channels", description="Configure channels for CV-Nova-Helper")
@app_commands.describe(
    status_channel="Status channel (reboots, rounds, manifest, player/staff counts)",
    adminhelp_channel="Admin help / tickets channel",
    mentorhelp_channel="Mentor help / tickets channel",
    admin_logs_channel="Admin logs channel (management)",
    server_logs_channel="Server logs & runtimes channel (management)",
    announcements_channel="Announcements channel"
)
async def setup_channels(
    interaction: discord.Interaction,
    status_channel: discord.TextChannel = None,
    adminhelp_channel: discord.TextChannel = None,
    mentorhelp_channel: discord.TextChannel = None,
    admin_logs_channel: discord.TextChannel = None,
    server_logs_channel: discord.TextChannel = None,
    announcements_channel: discord.TextChannel = None
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only server administrators can configure channels.", ephemeral=True)
        return

    updated = []
    if status_channel:
        bot.config["channels"]["status"] = status_channel.id
        updated.append(f"• **Status**: {status_channel.mention}")
    if adminhelp_channel:
        bot.config["channels"]["adminhelp"] = adminhelp_channel.id
        updated.append(f"• **Adminhelp**: {adminhelp_channel.mention}")
    if mentorhelp_channel:
        bot.config["channels"]["mentorhelp"] = mentorhelp_channel.id
        updated.append(f"• **Mentorhelp**: {mentorhelp_channel.mention}")
    if admin_logs_channel:
        bot.config["channels"]["admin_logs"] = admin_logs_channel.id
        updated.append(f"• **Admin Logs**: {admin_logs_channel.mention}")
    if server_logs_channel:
        bot.config["channels"]["server_logs"] = server_logs_channel.id
        updated.append(f"• **Server Logs**: {server_logs_channel.mention}")
    if announcements_channel:
        bot.config["channels"]["announcements"] = announcements_channel.id
        updated.append(f"• **Announcements**: {announcements_channel.mention}")

    save_config(bot.config)

    embed = discord.Embed(
        title="⚙️ Channels Configured",
        description="\n".join(updated) if updated else "No channels were changed.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setup_roles", description="Assign staff roles for bot authorization and auto-sync")
@app_commands.describe(
    admin_role="Role with full Admin ban & ticket permissions",
    moderator_role="Role with Moderator ban (up to 14 days) & ticket permissions",
    chief_mentor_role="Role with Chief Mentor ban (up to 14 days) & ticket permissions",
    mentor_role="Role with Mentor ticket permissions",
    founder_role="Role with Community Founder permissions"
)
async def setup_roles(
    interaction: discord.Interaction,
    admin_role: discord.Role = None,
    moderator_role: discord.Role = None,
    chief_mentor_role: discord.Role = None,
    mentor_role: discord.Role = None,
    founder_role: discord.Role = None
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only server administrators can configure roles.", ephemeral=True)
        return

    updated = []
    sync_map = bot.config.setdefault("auto_role_sync", {}).setdefault("rank_to_role", {})

    if admin_role:
        bot.config["roles"]["admin"] = [admin_role.id]
        sync_map["Admin"] = admin_role.id
        sync_map["Head Admin"] = admin_role.id
        updated.append(f"• **Admin**: {admin_role.mention}")
    if moderator_role:
        bot.config["roles"]["moderator"] = [moderator_role.id]
        sync_map["Moderator"] = moderator_role.id
        updated.append(f"• **Moderator**: {moderator_role.mention}")
    if chief_mentor_role:
        bot.config["roles"]["chief_mentor"] = [chief_mentor_role.id]
        sync_map["Chief Mentor"] = chief_mentor_role.id
        updated.append(f"• **Chief Mentor**: {chief_mentor_role.mention}")
    if mentor_role:
        bot.config["roles"]["mentor"] = [mentor_role.id]
        sync_map["Mentor"] = mentor_role.id
        updated.append(f"• **Mentor**: {mentor_role.mention}")
    if founder_role:
        bot.config["roles"]["founder"] = [founder_role.id]
        sync_map["Community Founder"] = founder_role.id
        updated.append(f"• **Founder**: {founder_role.mention}")

    save_config(bot.config)

    embed = discord.Embed(
        title="🛡️ Staff Roles Configured",
        description="\n".join(updated) if updated else "No roles were changed.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def main():
    extensions = [
        "cogs.status",
        "cogs.tickets",
        "cogs.bans",
        "cogs.logs",
        "cogs.staff_management",
        "cogs.helpdesk",
        "cogs.welcome",
        "cogs.reaction_roles",
        "cogs.moderation",
        "cogs.voice_channels",
        "cogs.player_stats",
        "cogs.utilities"
    ]
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            logger.info(f"Loaded extension: {ext}")
        except Exception as e:
            logger.error(f"Failed to load extension {ext}: {e}")

    token = config.get("bot_token")
    if not token or token == "YOUR_DISCORD_BOT_TOKEN":
        logger.warning("Bot token not configured! Set 'bot_token' in config.json to run.")
        return

    await bot.start(token)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
