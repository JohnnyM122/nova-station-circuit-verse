import asyncio
import json
import os
import sys
import discord

CONFIG_PATH = "/home/ubuntu/CV-Nova-Helper/config.json"

async def main():
    if not os.path.exists(CONFIG_PATH):
        print(f"Error: {CONFIG_PATH} not found.")
        return

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    token = config.get("bot_token")
    if not token:
        print("Error: No bot_token in config.json")
        return

    COMMUNITY_INFO_CH_ID = config.get("channels", {}).get("community_info", 1567434275928809544)

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Logged in as {client.user} ({client.user.id})")
        channel = client.get_channel(COMMUNITY_INFO_CH_ID)
        if not channel:
            try:
                channel = await client.fetch_channel(COMMUNITY_INFO_CH_ID)
            except Exception as e:
                print(f"Error fetching channel {COMMUNITY_INFO_CH_ID}: {e}")
                await client.close()
                return

        print(f"Posting announcement to #{channel.name} ({channel.id})...")

        embed = discord.Embed(
            title="🛡️ Circuit Verse Community Safety & Auto-Moderation System",
            description=(
                "Welcome to **Circuit Verse**! To ensure a fair, respectful, and safe environment "
                "for all members across our gaming network, our automated safety suite (**Circuit Verse Helper**) "
                "operates 24/7 alongside our staff team. As a dedicated subpart of our network DDoS and security "
                "infrastructure, this system actively maintains community integrity for our **13+ gaming community**."
            ),
            color=0x00c0ff,
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="🤖 Real-Time Automated Defense",
            value=(
                "• **Phishing & Malicious Links:** Instant automatic removal of suspicious URLs, token-grabbers, and scam domains.\n"
                "• **Raid & Spam Prevention:** Immediate suppression of mass mentions, copy-paste flooding, and rapid bot raids.\n"
                "• **Invite Shield:** Unapproved server invite links are filtered to prevent unauthorized advertising.\n"
                "• **Content Standards:** Automated filtering of severe slurs, hate speech, and explicit material."
            ),
            inline=False
        )

        embed.add_field(
            name="⚠️ Warning & Timeout Progression",
            value=(
                "• **Progressive Warning System:** Minor or first-time policy violations trigger official warnings.\n"
                "• **Automatic Timeouts:** Accumulating **3 warnings** automatically places the user on a 1-hour timeout.\n"
                "• **Severity Scaling:** More severe or repeated disruptions result in immediate dynamic timeouts (from 10 minutes up to 24 hours).\n"
                "• **Tracked History:** Warning records and past infraction histories are maintained to ensure repeat offenders face appropriate escalations."
            ),
            inline=False
        )

        embed.add_field(
            name="🛡️ Human Staff Oversight & Fair Play",
            value=(
                "• **Staff-Reviewed Incidents:** Major disciplinary actions (kicks & bans) require human review and approval by Community Staff, ensuring fair decisions.\n"
                "• **Incident Response Desk:** Complex situations are forwarded to staff channels (`general-incidents-chat` & `administration`) for interactive evaluation.\n"
                "• **Full Transparency:** All moderation actions, timeouts, message edits, and deletions are permanently logged in our staff audit logs (`discord-logs`)."
            ),
            inline=False
        )

        embed.add_field(
            name="🤝 Community Guidelines & Support",
            value=(
                "• Please keep chat discussions respectful and adhere to standard **Discord Terms of Service & Community Guidelines**.\n"
                "• Avoid attempting to bypass filters or spamming alternative channels.\n"
                "• If you have questions regarding a warning or require assistance from our moderators, feel free to open a ticket in <#1567433895912407223>!"
            ),
            inline=False
        )

        embed.set_footer(
            text="Circuit Verse Network • Community Safety Suite",
            icon_url=client.user.display_avatar.url if client.user.display_avatar else None
        )

        msg = await channel.send(embed=embed)
        print(f"Announcement posted successfully! Message ID: {msg.id}")
        await client.close()

    await client.start(token)

if __name__ == "__main__":
    asyncio.run(main())
