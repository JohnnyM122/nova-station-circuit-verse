import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
import datetime

logger = logging.getLogger("CVNovaHelper.utilities")

class PollButton(discord.ui.Button):
    def __init__(self, option_index: int, option_label: str):
        super().__init__(style=discord.ButtonStyle.secondary, label=f"{option_index + 1}. {option_label[:40]}", custom_id=f"poll_opt_{option_index}")
        self.option_index = option_index

    async def callback(self, interaction: discord.Interaction):
        view: PollView = self.view
        user_id = interaction.user.id

        # Toggle or switch vote
        if view.user_votes.get(user_id) == self.option_index:
            del view.user_votes[user_id]
            msg = "Removed your vote."
        else:
            view.user_votes[user_id] = self.option_index
            msg = f"Voted for: **{view.options[self.option_index]}**"

        await view.update_poll_message()
        await interaction.response.send_message(msg, ephemeral=True)

class PollView(discord.ui.View):
    def __init__(self, question: str, options: list[str], author: discord.User, timeout: int = 86400):
        super().__init__(timeout=timeout)
        self.question = question
        self.options = options
        self.author = author
        self.user_votes = {} # user_id -> option_index
        self.message: discord.Message = None

        for i, opt in enumerate(options):
            self.add_item(PollButton(i, opt))

    def make_progress_bar(self, percentage: float, length: int = 10) -> str:
        filled = int(round(length * (percentage / 100)))
        empty = length - filled
        return "▰" * filled + "▱" * empty

    def generate_embed(self) -> discord.Embed:
        total_votes = len(self.user_votes)
        counts = [0] * len(self.options)
        for opt_idx in self.user_votes.values():
            counts[opt_idx] += 1

        embed = discord.Embed(
            title=f"📊 {self.question}",
            color=discord.Color.from_rgb(0, 225, 255)
        )

        lines = []
        for i, (opt, count) in enumerate(zip(self.options, counts)):
            pct = (count / total_votes * 100) if total_votes > 0 else 0
            bar = self.make_progress_bar(pct)
            lines.append(f"**{i+1}. {opt}**\n`{bar}` **{pct:.1f}%** ({count} votes)")

        embed.description = "\n\n".join(lines)
        embed.set_footer(text=f"Total Votes: {total_votes} • Initiated by {self.author.display_name}")
        return embed

    async def update_poll_message(self):
        if self.message:
            try:
                await self.message.edit(embed=self.generate_embed(), view=self)
            except Exception as e:
                logger.debug(f"Failed to edit poll message: {e}")

class CopyAddressButton(discord.ui.Button):
    def __init__(self, address: str = "87.99.133.221:7777"):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="📋 Copy Server Address",
            custom_id="btn_copy_server_address"
        )
        self.address = address

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"**Nova Station 13 Connection Address:**\n```text\nbyond://{self.address}\n```\n"
            f"• Open your BYOND pager, press **`Ctrl + O`**, paste `byond://{self.address}`, and click **OK**.",
            ephemeral=True
        )

class ConnectView(discord.ui.View):
    def __init__(self, address: str = "87.99.133.221:7777"):
        super().__init__(timeout=None)
        self.add_item(CopyAddressButton(address=address))
        self.add_item(discord.ui.Button(
            label="🌐 Download BYOND",
            url="https://www.byond.com/download/",
            style=discord.ButtonStyle.link
        ))

class UtilitiesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.byond = bot.byond
        self.config = bot.config

    @commands.hybrid_command(name="connect", aliases=["join", "server"], description="Get direct one-click join links and instructions for Nova Station 13")
    async def cmd_connect(self, ctx: commands.Context):
        status_data = await self.byond.get_status()
        is_online = status_data and isinstance(status_data, dict)
        server_address = self.config.get("public_server_address", "87.99.133.221:7777")

        embed = discord.Embed(
            title="🚀 Join Nova Station 13",
            description=(
                f"**Server Address:**\n```text\nbyond://{server_address}\n```\n"
                "**How to Connect:**\n"
                "1. Open your BYOND pager.\n"
                "2. Press **`Ctrl + O`** (Open Location).\n"
                f"3. Paste `byond://{server_address}` and press **Enter**.\n"
                "4. Bookmark the address in your BYOND favorites for fast reconnects!\n\n"
                "*Click the **📋 Copy Server Address** button below for a fast tap-to-copy snippet.*"
            ),
            color=discord.Color.green() if is_online else discord.Color.gold()
        )

        if is_online:
            embed.add_field(name="🟢 Status", value="Online & Accepting Connections", inline=True)
            embed.add_field(name="👥 Players", value=str(status_data.get("players", 0)), inline=True)
            embed.add_field(name="🗺️ Current Map", value=status_data.get("map_name", "Unknown"), inline=True)
        else:
            embed.add_field(name="🟡 Status", value="Initializing or Rebooting", inline=True)

        guild_icon = ctx.guild.icon.url if (ctx.guild and ctx.guild.icon) else None
        embed.set_footer(text="Circuit Verse • Nova Station 13", icon_url=guild_icon)
        await ctx.send(embed=embed, view=ConnectView(address=server_address))

    @commands.hybrid_command(name="server_info", aliases=["serverinfo", "specs"], description="View technical health, performance metrics, and status of the game server")
    async def cmd_server_info(self, ctx: commands.Context):
        await ctx.defer()
        status_data = await self.byond.get_status()

        if not status_data or not isinstance(status_data, dict):
            await ctx.send("🔴 **Nova Station 13 is currently offline or unreachable.**")
            return

        embed = discord.Embed(
            title="⚡ Nova Station 13 — Technical Overview",
            description=f"**Host Address:** `87.99.133.221:7777` • **Round ID:** `#{status_data.get('round_id', 'N/A')}`",
            color=discord.Color.from_rgb(0, 225, 255)
        )

        embed.add_field(name="🗺️ Active Map", value=status_data.get("map_name", "Unknown"), inline=True)
        embed.add_field(name="🎲 Game Mode", value=str(status_data.get("mode", "Unknown")).capitalize(), inline=True)
        embed.add_field(name="⏱️ Station Time", value=status_data.get("stationtime", "00:00"), inline=True)
        embed.add_field(name="⏳ Elapsed Time", value=status_data.get("roundtime", "00:00:00"), inline=True)
        embed.add_field(name="👥 Players Online", value=f"**{status_data.get('players', 0)}**", inline=True)
        embed.add_field(name="🛡️ Staff Online", value=str(status_data.get("admins", 0)), inline=True)

        # Performance metrics
        perf = status_data.get("perfmetrics", {})
        if perf:
            cpu = perf.get("cpu", 0)
            mcpu = perf.get("mcpu", 0)
            embed.add_field(name="💻 Server CPU Load", value=f"{cpu:.1f}% (Map: {mcpu:.2f}%)", inline=True)

        # Shuttle status
        shuttle_mode = status_data.get("shuttle_mode")
        shuttle_timer = status_data.get("shuttle_timer")
        if shuttle_timer is not None:
            mins, secs = divmod(int(shuttle_timer), 60)
            shuttle_str = f"{mins:02d}:{secs:02d}"
            embed.add_field(name="🚀 Evacuation Shuttle", value=f"Timer: `{shuttle_str}`", inline=True)

        guild_icon = ctx.guild.icon.url if (ctx.guild and ctx.guild.icon) else None
        embed.set_footer(text="Nova Station 13 Diagnostics • Circuit Verse", icon_url=guild_icon)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="poll", description="Create an interactive voting poll with clickable button options")
    @app_commands.describe(
        question="The poll question to ask",
        option1="First option",
        option2="Second option",
        option3="Third option (optional)",
        option4="Fourth option (optional)",
        option5="Fifth option (optional)"
    )
    async def cmd_poll(
        self,
        ctx: commands.Context,
        question: str,
        option1: str,
        option2: str,
        option3: str = None,
        option4: str = None,
        option5: str = None
    ):
        raw_options = [option1, option2, option3, option4, option5]
        options = [opt.strip() for opt in raw_options if opt and opt.strip()]

        if len(options) < 2:
            await ctx.send("❌ A poll requires at least 2 distinct options.", ephemeral=True)
            return

        view = PollView(question=question, options=options, author=ctx.author)
        embed = view.generate_embed()

        msg = await ctx.send(embed=embed, view=view)
        if hasattr(msg, "edit"):
            view.message = msg
        elif ctx.interaction:
            try:
                view.message = await ctx.interaction.original_response()
            except Exception:
                pass

    @commands.hybrid_command(name="remind", description="Set a personal timer/reminder")
    @app_commands.describe(minutes="Minutes from now to remind you", reminder="What to remind you about")
    async def cmd_remind(self, ctx: commands.Context, minutes: app_commands.Range[int, 1, 1440], reminder: str):
        await ctx.send(f"⏰ Got it! I'll remind you in **{minutes} minutes**: `{reminder}`.", ephemeral=True)

        async def send_reminder():
            await asyncio.sleep(minutes * 60)
            embed = discord.Embed(
                title="⏰ Reminder!",
                description=f"{ctx.author.mention}, here is your reminder:\n\n>>> **{reminder}**",
                color=discord.Color.gold()
            )
            embed.set_footer(text=f"Set {minutes} minutes ago")
            try:
                await ctx.channel.send(content=ctx.author.mention, embed=embed)
            except Exception:
                try:
                    await ctx.author.send(embed=embed)
                except Exception:
                    pass

        asyncio.create_task(send_reminder())

async def setup(bot):
    await bot.add_cog(UtilitiesCog(bot))
