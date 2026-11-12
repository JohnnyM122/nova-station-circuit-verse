import subprocess, os

with open("c:\\Users\\SysAdmin\\Documents\\nova-station-circuit-verse-main\\local_audit_logger.py", "r", encoding="utf-8") as f:
    content = f.read()

edit_and_delete_code = '''
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Log message edits across the entire server to discord-logs."""
        if not after.guild or after.author.bot:
            return
        if before.content == after.content:
            return

        log_ch = self.get_log_channel(after.guild)
        if not log_ch:
            return

        embed = discord.Embed(
            title="✏️ Message Edited",
            description=f"Message edited in {after.channel.mention} by {after.author.mention}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(
            name=f"{after.author} ({after.author.id})",
            icon_url=after.author.display_avatar.url if after.author.display_avatar else None
        )
        embed.add_field(name="📍 Channel", value=after.channel.mention, inline=True)
        embed.add_field(name="🔗 Jump Link", value=f"[Go to Message]({after.jump_url})", inline=True)

        b_text = before.content if before.content else "*[Empty or Embed/Attachment]*"
        a_text = after.content if after.content else "*[Empty or Embed/Attachment]*"

        if len(b_text) > 1000:
            b_text = b_text[:997] + "..."
        if len(a_text) > 1000:
            a_text = a_text[:997] + "..."

        embed.add_field(name="📄 Original Content", value=f"```\n{b_text}\n```", inline=False)
        embed.add_field(name="📝 Edited Content", value=f"```\n{a_text}\n```", inline=False)
        embed.set_footer(text=f"User ID: {after.author.id} • Message ID: {after.id}")

        try:
            await log_ch.send(embed=embed)
        except Exception as e:
            logger.error(f"Error logging message edit: {e}")

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Log message deletions across the entire server to discord-logs."""
        if not message.guild or message.author.bot:
            return

        log_ch = self.get_log_channel(message.guild)
        if not log_ch:
            return

        # Check audit log if a staff member deleted it
        entry = await self.get_audit_entry(
            message.guild,
            discord.AuditLogAction.message_delete,
            target_id=message.author.id,
            max_age_seconds=8
        )
        deleter = entry.user if entry else None

        embed = discord.Embed(
            title="🗑️ Message Deleted",
            description=f"Message deleted in {message.channel.mention} by {deleter.mention if deleter and deleter != message.author else message.author.mention}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(
            name=f"{message.author} ({message.author.id})",
            icon_url=message.author.display_avatar.url if message.author.display_avatar else None
        )
        embed.add_field(name="📍 Channel", value=message.channel.mention, inline=True)
        embed.add_field(
            name="🗑️ Deleted By",
            value=f"{deleter.mention} (`{deleter.name}`)" if deleter and deleter != message.author else "*Author (Self-Delete)*",
            inline=True
        )

        m_text = message.content if message.content else "*[No text content]*"
        if len(m_text) > 1000:
            m_text = m_text[:997] + "..."
        embed.add_field(name="📄 Content", value=f"```\n{m_text}\n```", inline=False)

        if message.attachments:
            att_list = [f"• `{a.filename}`" for a in message.attachments]
            embed.add_field(name="📎 Attachments", value="\n".join(att_list[:5]), inline=False)

        embed.set_footer(text=f"Author ID: {message.author.id} • Message ID: {message.id}")

        try:
            await log_ch.send(embed=embed)
        except Exception as e:
            logger.error(f"Error logging message delete: {e}")

async def setup(bot):
'''

target = "async def setup(bot):"
if target in content and "on_message_edit" not in content:
    content = content.replace(target, edit_and_delete_code)
    with open("c:\\Users\\SysAdmin\\Documents\\nova-station-circuit-verse-main\\local_audit_logger.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Added message edit and delete listeners to local_audit_logger.py")

SSH_KEY = os.path.expanduser('~/.ssh/id_ed25519_tailscale')
DED_IP = '62.238.81.224'

cmd = ['scp', '-i', SSH_KEY, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new', 'c:\\Users\\SysAdmin\\Documents\\nova-station-circuit-verse-main\\local_audit_logger.py', f'root@{DED_IP}:/home/ubuntu/CV-Nova-Helper/cogs/discord_audit_logger.py']
res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
print("SCP discord_audit_logger.py status:", res.returncode)
