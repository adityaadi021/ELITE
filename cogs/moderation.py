import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import re
from bot import modern_embed

class TimeoutModal(discord.ui.Modal, title="Timeout User"):
    time = discord.ui.TextInput(label="Duration (e.g. 10m, 2h, 7d)", placeholder="e.g. 10m", required=True)
    reason = discord.ui.TextInput(label="Reason", placeholder="Reason for timeout", required=False, style=discord.TextStyle.paragraph)
    def __init__(self, member, callback):
        super().__init__()
        self.member = member
        self.callback_func = callback
    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.member, self.time.value, self.reason.value)

class WarningsView(discord.ui.View):
    def __init__(self, warnings, page=0):
        super().__init__(timeout=60)
        self.warnings = warnings
        self.page = page
        self.max_page = max(0, (len(warnings) - 1) // 5)
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if self.page > 0:
            self.add_item(self.PrevButton(self))
        if self.page < self.max_page:
            self.add_item(self.NextButton(self))

    class PrevButton(discord.ui.Button):
        def __init__(self, parent):
            super().__init__(label="Previous", style=discord.ButtonStyle.secondary, emoji="⬅️")
            self.parent = parent
        async def callback(self, interaction):
            self.parent.page -= 1
            self.parent.update_buttons()
            await interaction.response.edit_message(embed=self.parent.get_embed(interaction), view=self.parent)

    class NextButton(discord.ui.Button):
        def __init__(self, parent):
            super().__init__(label="Next", style=discord.ButtonStyle.secondary, emoji="➡️")
            self.parent = parent
        async def callback(self, interaction):
            self.parent.page += 1
            self.parent.update_buttons()
            await interaction.response.edit_message(embed=self.parent.get_embed(interaction), view=self.parent)

    def get_embed(self, ctx):
        start = self.page * 5
        end = start + 5
        entries = self.warnings[start:end]
        desc = "\n".join(f"`{i+1}.` {w}" for i, w in enumerate(entries, start=start)) or "No warnings."
        return modern_embed(
            title="⚠️ User Warnings",
            description=desc,
            color=discord.Color.orange(),
            ctx=ctx
        )

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.automod_enabled = {}
        self.last_messages = {}

    @commands.command(description="Enable anti-spam automod for this server.")
    @commands.has_permissions(administrator=True)
    async def automodenable(self, ctx):
        self.automod_enabled[ctx.guild.id] = True
        await ctx.send(f"Automod enabled for this server! Spammers will be timed out for 7 days.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        guild_id = message.guild.id
        if not getattr(self, 'automod_enabled', {}).get(guild_id):
            return
        user_msgs = self.last_messages.setdefault(guild_id, {}).setdefault(message.author.id, [])
        user_msgs.append(message.content)
        if len(user_msgs) > 5:
            user_msgs.pop(0)
        if len(user_msgs) == 5:
            if all(m == user_msgs[0] for m in user_msgs):
                await self.timeout_action(message, reason="Spam: repeated messages")
                return
            if all(re.fullmatch(r'\W+', m) for m in user_msgs):
                await self.timeout_action(message, reason="Spam: repeated emojis")
                return
            if all(self.bot.user in m.mentions if hasattr(m, 'mentions') else False for m in user_msgs):
                await self.timeout_action(message, reason="Spam: repeated bot tags")
                return

    async def timeout_action(self, message, reason):
        try:
            until = discord.utils.utcnow() + timedelta(days=7)
            await message.author.timeout(until, reason=reason)
            await message.channel.send(embed=modern_embed(
                title="User Timed Out",
                description=f"{message.author.mention} has been timed out for 7 days. Reason: {reason}",
                color=discord.Color.orange(),
                emoji="⏳",
                ctx=message
            ))
        except Exception as e:
            await message.channel.send(embed=modern_embed(
                title="Timeout Failed",
                description=f"Failed to timeout {message.author.mention}: {e}",
                color=discord.Color.red(),
                emoji="❌",
                ctx=message
            ))

    @commands.command(description="Timeout a user for a given time and reason.")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, time: str = None, *, reason: str = "No reason provided"):
        if isinstance(ctx, commands.Context) and ctx.interaction:
            if time is None:
                modal = TimeoutModal(member, self.timeout_modal_callback)
                await ctx.interaction.response.send_modal(modal)
                return
        if time is None:
            await ctx.send("You must specify a time (e.g. 10m, 2h, 7d).", ephemeral=True)
            return
        seconds = self.parse_time(time)
        if seconds is None:
            await ctx.send("Invalid time format. Use 10m, 2h, 7d, etc.")
            return
        until = discord.utils.utcnow() + timedelta(seconds=seconds)
        try:
            await member.timeout(until, reason=reason)
            try:
                await member.send(f"You have been timed out in {ctx.guild.name} for {time}. Reason: {reason}")
            except Exception:
                pass
            await ctx.send(f"{member.mention} has been timed out for {time}. Reason: {reason}")
        except Exception as e:
            await ctx.send(f"Failed to timeout {member.mention}: {e}")

    async def timeout_modal_callback(self, interaction, member, time, reason):
        seconds = self.parse_time(time)
        if seconds is None:
            await interaction.response.send_message("Invalid time format. Use 10m, 2h, 7d, etc.", ephemeral=True)
            return
        until = discord.utils.utcnow() + timedelta(seconds=seconds)
        try:
            await member.timeout(until, reason=reason)
            try:
                await member.send(f"You have been timed out in {interaction.guild.name} for {time}. Reason: {reason}")
            except Exception:
                pass
            await interaction.response.send_message(f"{member.mention} has been timed out for {time}. Reason: {reason}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to timeout {member.mention}: {e}", ephemeral=True)

    @commands.command(description="Ban a user from the server.")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        try:
            await member.ban(reason=reason)
            await ctx.send(f"{member.mention} has been banned. Reason: {reason}")
        except Exception as e:
            await ctx.send(f"Failed to ban {member.mention}: {e}")

    @commands.command(description="Unban a user from the server.")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user: discord.User, *, reason: str = "No reason provided"):
        try:
            await ctx.guild.unban(user, reason=reason)
            await ctx.send(f"{user.mention} has been unbanned. Reason: {reason}")
        except Exception as e:
            await ctx.send(f"Failed to unban {user.mention}: {e}")

    @commands.command(description="Kick a user from the server.")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        try:
            await member.kick(reason=reason)
            await ctx.send(f"{member.mention} has been kicked. Reason: {reason}")
        except Exception as e:
            await ctx.send(f"Failed to kick {member.mention}: {e}")

    @commands.hybrid_command(name="warn", description="Warn a user.")
    @commands.has_permissions(administrator=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        # In a real bot, store warning in DB. Here, just show UI.
        embed = modern_embed(
            title="⚠️ Warn",
            description=f"{member.mention} has been warned. Reason: {reason}",
            color=discord.Color.orange(),
            ctx=ctx
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="View Warnings", style=discord.ButtonStyle.blurple, emoji="📋", custom_id="view_warnings"))
        async def button_callback(interaction):
            # In a real bot, fetch warnings from DB. Here, use dummy data.
            dummy_warnings = [f"Reason {i+1}" for i in range(12)]
            warnings_view = WarningsView(dummy_warnings)
            await interaction.response.send_message(embed=warnings_view.get_embed(ctx), view=warnings_view, ephemeral=True)
        view.children[0].callback = button_callback
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="warnings", description="Show warnings for a user.")
    @commands.has_permissions(administrator=True)
    async def warnings(self, ctx, member: discord.Member):
        # In a real bot, fetch warnings from DB. Here, use dummy data.
        dummy_warnings = [f"Reason {i+1}" for i in range(12)]
        warnings_view = WarningsView(dummy_warnings)
        await ctx.send(embed=warnings_view.get_embed(ctx), view=warnings_view)

    @commands.hybrid_command(name="mute", description="Mute a user in text channels.")
    @commands.has_permissions(administrator=True)
    async def mute(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        await ctx.send(embed=discord.Embed(title="Mute", description=f"{member.mention} has been muted. Reason: {reason}", color=discord.Color.red()))

    @commands.hybrid_command(name="unmute", description="Unmute a user in text channels.")
    @commands.has_permissions(administrator=True)
    async def unmute(self, ctx, member: discord.Member):
        await ctx.send(embed=discord.Embed(title="Unmute", description=f"{member.mention} has been unmuted.", color=discord.Color.green()))

    @commands.hybrid_command(name="slowmode", description="Set slowmode for a channel.")
    @commands.has_permissions(administrator=True)
    async def slowmode(self, ctx, seconds: int):
        await ctx.send(embed=discord.Embed(title="Slowmode", description=f"Slowmode set to {seconds} seconds.", color=discord.Color.blurple()))

    @commands.hybrid_command(name="lockdown", description="Lockdown the server (stub).")
    @commands.has_permissions(administrator=True)
    async def lockdown(self, ctx):
        await ctx.send(embed=discord.Embed(title="Lockdown", description="Server is now in lockdown mode (stub).", color=discord.Color.red()))

    @commands.hybrid_command(name="tempban", description="Temporarily ban a user.")
    @commands.has_permissions(ban_members=True)
    async def tempban(self, ctx, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
        seconds = self.parse_time(duration)
        if seconds is None:
            await ctx.send(embed=modern_embed(title="❌ Error", description="Invalid duration format. Use 10m, 2h, 7d, etc.", color=discord.Color.red(), ctx=ctx))
            return
        try:
            await member.ban(reason=f"Tempban: {reason}")
            await ctx.send(embed=modern_embed(
                title="🔨 Tempban",
                description=f"{member.mention} has been temporarily banned for {duration}. Reason: {reason}",
                color=discord.Color.orange(),
                ctx=ctx
            ))
            # In a real bot, schedule unban after duration
        except Exception as e:
            await ctx.send(embed=modern_embed(title="❌ Error", description=f"Failed to tempban {member.mention}: {e}", color=discord.Color.red(), ctx=ctx))

    @commands.hybrid_command(name="softban", description="Softban a user (ban then unban to delete messages).")
    @commands.has_permissions(ban_members=True)
    async def softban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        try:
            await member.ban(reason=f"Softban: {reason}")
            await ctx.guild.unban(member, reason="Softban completed")
            await ctx.send(embed=modern_embed(
                title="🧹 Softban",
                description=f"{member.mention} has been softbanned. All their messages have been deleted. Reason: {reason}",
                color=discord.Color.orange(),
                ctx=ctx
            ))
        except Exception as e:
            await ctx.send(embed=modern_embed(title="❌ Error", description=f"Failed to softban {member.mention}: {e}", color=discord.Color.red(), ctx=ctx))

    @commands.hybrid_command(name="purge", description="Delete multiple messages with filters.")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int, user: discord.Member = None, *, contains: str = None):
        if amount < 1 or amount > 100:
            await ctx.send(embed=modern_embed(title="❌ Error", description="Amount must be between 1 and 100.", color=discord.Color.red(), ctx=ctx))
            return
        try:
            def check(msg):
                if user and msg.author != user:
                    return False
                if contains and contains.lower() not in msg.content.lower():
                    return False
                return True
            deleted = await ctx.channel.purge(limit=amount, check=check)
            await ctx.send(embed=modern_embed(
                title="🗑️ Purge",
                description=f"Deleted {len(deleted)} messages.",
                color=discord.Color.green(),
                ctx=ctx
            ), delete_after=5)
        except Exception as e:
            await ctx.send(embed=modern_embed(title="❌ Error", description=f"Failed to purge messages: {e}", color=discord.Color.red(), ctx=ctx))

    def parse_time(self, time_str):
        match = re.match(r"(\d+)([smhd])", time_str)
        if not match:
            return None
        value, unit = match.groups()
        value = int(value)
        if unit == 's':
            return value
        if unit == 'm':
            return value * 60
        if unit == 'h':
            return value * 3600
        if unit == 'd':
            return value * 86400
        return None

async def setup(bot):
    await bot.add_cog(Moderation(bot)) 
