import discord
from discord.ext import commands, tasks
from discord import ui
import logging
import mysql.connector
import asyncio

logger = logging.getLogger("CVNovaHelper.tickets")

class TicketReplyModal(ui.Modal, title="Reply to In-Game Ticket"):
    def __init__(self, bot, ticket_id: int, system: str, ticket_channel_id: int):
        super().__init__()
        self.bot = bot
        self.ticket_id = ticket_id
        self.system = system
        self.ticket_channel_id = ticket_channel_id

        self.reply_text = ui.TextInput(
            label=f"Response to Ticket #{ticket_id}",
            style=discord.TextStyle.paragraph,
            placeholder="Type your message to send to the player in-game...",
            required=True,
            max_length=1000
        )
        self.add_item(self.reply_text)

    async def on_submit(self, interaction: discord.Interaction):
        staff_cog = self.bot.get_cog("StaffManagementCog")
        if staff_cog and not staff_cog.is_staff_member(interaction.user, system=self.system):
            await interaction.response.send_message("🚫 **Access Denied**: You do not have verified game staff permissions to reply to tickets.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        sender_name = interaction.user.display_name
        res = await self.bot.byond.handle_ticket(
            action="reply",
            ticket_id=self.ticket_id,
            system=self.system,
            sender=sender_name,
            msg=self.reply_text.value
        )
        if res and isinstance(res, dict) and res.get("success"):
            await interaction.followup.send(f"✅ Reply sent to player for Ticket #{self.ticket_id}!", ephemeral=True)
        else:
            await interaction.followup.send(f"⚠️ Failed to send reply (server might be rebooting or ticket ended): {res}", ephemeral=True)

class TicketView(ui.View):
    def __init__(self, bot, ticket_id: int, system: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_id = ticket_id
        self.system = system

    @ui.button(label="Claim Ticket", style=discord.ButtonStyle.primary, emoji="🙋", custom_id="ticket_claim")
    async def claim_button(self, interaction: discord.Interaction, button: ui.Button):
        staff_cog = self.bot.get_cog("StaffManagementCog")
        if staff_cog and not staff_cog.is_staff_member(interaction.user, system=self.system):
            await interaction.response.send_message("🚫 **Access Denied**: You must be a verified game staff member to claim tickets.", ephemeral=True)
            return

        await interaction.response.defer()
        sender_name = interaction.user.display_name
        res = await self.bot.byond.handle_ticket(
            action="claim",
            ticket_id=self.ticket_id,
            system=self.system,
            sender=sender_name
        )
        if res and isinstance(res, dict) and res.get("success"):
            button.disabled = True
            button.label = f"Claimed by {sender_name}"
            button.style = discord.ButtonStyle.secondary
            await interaction.message.edit(view=self)
            await interaction.followup.send(f"🙋 **{sender_name}** claimed Ticket #{self.ticket_id} in-game.")
        else:
            await interaction.followup.send(f"⚠️ Could not claim ticket: {res}", ephemeral=True)

    @ui.button(label="Reply", style=discord.ButtonStyle.success, emoji="💬", custom_id="ticket_reply")
    async def reply_button(self, interaction: discord.Interaction, button: ui.Button):
        staff_cog = self.bot.get_cog("StaffManagementCog")
        if staff_cog and not staff_cog.is_staff_member(interaction.user, system=self.system):
            await interaction.response.send_message("🚫 **Access Denied**: You must be a verified game staff member to reply to tickets.", ephemeral=True)
            return

        modal = TicketReplyModal(self.bot, self.ticket_id, self.system, interaction.channel.id)
        await interaction.response.send_modal(modal)

    @ui.button(label="Resolve", style=discord.ButtonStyle.green, emoji="✅", custom_id="ticket_resolve")
    async def resolve_button(self, interaction: discord.Interaction, button: ui.Button):
        staff_cog = self.bot.get_cog("StaffManagementCog")
        if staff_cog and not staff_cog.is_staff_member(interaction.user, system=self.system):
            await interaction.response.send_message("🚫 **Access Denied**: You must be a verified game staff member to resolve tickets.", ephemeral=True)
            return

        await interaction.response.defer()
        sender_name = interaction.user.display_name
        res = await self.bot.byond.handle_ticket(
            action="resolve",
            ticket_id=self.ticket_id,
            system=self.system,
            sender=sender_name
        )
        if res and isinstance(res, dict) and res.get("success"):
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
            await interaction.followup.send(f"✅ Ticket #{self.ticket_id} resolved by **{sender_name}**.")
        else:
            await interaction.followup.send(f"⚠️ Could not resolve ticket: {res}", ephemeral=True)

    @ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_close")
    async def close_button(self, interaction: discord.Interaction, button: ui.Button):
        staff_cog = self.bot.get_cog("StaffManagementCog")
        if staff_cog and not staff_cog.is_staff_member(interaction.user, system=self.system):
            await interaction.response.send_message("🚫 **Access Denied**: You must be a verified game staff member to close tickets.", ephemeral=True)
            return

        await interaction.response.defer()
        sender_name = interaction.user.display_name
        res = await self.bot.byond.handle_ticket(
            action="close",
            ticket_id=self.ticket_id,
            system=self.system,
            sender=sender_name
        )
        if res and isinstance(res, dict) and res.get("success"):
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
            await interaction.followup.send(f"🔒 Ticket #{self.ticket_id} closed by **{sender_name}**.")
        else:
            await interaction.followup.send(f"⚠️ Could not close ticket: {res}", ephemeral=True)

class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        self.byond = bot.byond
        self.seen_ticket_ids = set()
        self.ticket_threads = {}
        self.poll_tickets_task.start()

    def cog_unload(self):
        self.poll_tickets_task.cancel()

    def get_db_connection(self):
        db_conf = self.config.get("database", {})
        return mysql.connector.connect(
            host=db_conf.get("host", "127.0.0.1"),
            user=db_conf.get("user", "nova_station_app"),
            password=db_conf.get("password", ""),
            database=db_conf.get("database", "paradise_gamedb")
        )

    @tasks.loop(seconds=5.0)
    async def poll_tickets_task(self):
        try:
            conn = await asyncio.to_thread(self.get_db_connection)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, ticket_num, ticket_type, real_filetime, ticket_creator, ticket_topic, ticket_taker, end_round_state
                FROM tickets
                ORDER BY id DESC LIMIT 20
            """)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            for row in reversed(rows):
                db_id = row["id"]
                if db_id in self.seen_ticket_ids:
                    continue
                self.seen_ticket_ids.add(db_id)

                await self.post_new_ticket(row)
        except Exception as e:
            logger.debug(f"Ticket poll exception: {e}")

    async def post_new_ticket(self, row):
        ticket_type = row["ticket_type"] # 'ADMIN' or 'MENTOR'
        system_key = "admin" if ticket_type == "ADMIN" else "mentor"
        channel_id = self.config["channels"].get("adminhelp" if system_key == "admin" else "mentorhelp")
        if not channel_id:
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        ticket_num = row["ticket_num"]
        creator = row["ticket_creator"]
        topic = row["ticket_topic"]
        time_str = str(row["real_filetime"])

        embed = discord.Embed(
            title=f"📩 New {ticket_type.capitalize()} Help (Ticket #{ticket_num})",
            color=discord.Color.red() if system_key == "admin" else discord.Color.teal()
        )
        embed.add_field(name="Player CKey", value=f"`{creator}`", inline=True)
        embed.add_field(name="Ticket Number", value=f"#{ticket_num}", inline=True)
        embed.add_field(name="Time", value=time_str, inline=True)
        embed.add_field(name="Message", value=f"```\n{topic}\n```", inline=False)
        embed.set_footer(text="Click Claim to take ticket, or Reply to message player in-game")

        view = TicketView(self.bot, ticket_num, system_key)
        msg = await channel.send(embed=embed, view=view)

        # Create a thread for conversation
        try:
            thread = await msg.create_thread(name=f"Ticket #{ticket_num} - {creator}")
            self.ticket_threads[thread.id] = {
                "ticket_num": ticket_num,
                "system": system_key,
                "creator": creator
            }
            await thread.send(f"Staff discussion & direct replies for Ticket #{ticket_num}. Messages typed here by verified staff are forwarded directly to `{creator}` in-game.")
        except Exception as e:
            logger.debug(f"Could not create thread for ticket #{ticket_num}: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        thread_info = self.ticket_threads.get(message.channel.id)
        if thread_info:
            staff_cog = self.bot.get_cog("StaffManagementCog")
            if staff_cog and not staff_cog.is_staff_member(message.author, system=thread_info["system"]):
                # Silently ignore non-staff messages in ticket threads
                return

            ticket_num = thread_info["ticket_num"]
            system = thread_info["system"]
            sender = message.author.display_name
            res = await self.bot.byond.handle_ticket(
                action="reply",
                ticket_id=ticket_num,
                system=system,
                sender=sender,
                msg=message.content
            )
            if res and isinstance(res, dict) and res.get("success"):
                await message.add_reaction("✅")
            else:
                await message.add_reaction("❌")

async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
