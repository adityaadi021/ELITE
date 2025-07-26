import discord
from discord.ext import commands
from datetime import datetime
import json
import os
import aiosqlite
from discord import ui
from bot import modern_embed

OWNER_ID = 1201050377911554061

def styled_embed(title, description, color, ctx=None, emoji=None):
    embed = discord.Embed(
        title=f"{emoji + ' ' if emoji else ''}{title}",
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    if ctx:
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    return embed

def is_owner(ctx):
    return ctx.author.id == OWNER_ID

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.afk_status = {}  # user_id: (message, timestamp)

    @commands.hybrid_command(description="Check the bot's latency.")
    @commands.check(is_owner)
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        embed = styled_embed(
            title="Pong!",
            description=f'🏓 Latency: {latency}ms',
            color=discord.Color.blurple(),
            ctx=ctx,
            emoji="🏓"
        )
        await ctx.send(embed=embed, reference=getattr(ctx, 'message', None), mention_author=True)

    @commands.hybrid_command(name="serverstat", description="Create or update a member count voice channel.")
    @commands.check(is_owner)
    async def serverstat(self, ctx):
        guild = ctx.guild
        channel_name = f"Members: {guild.member_count}"
        channel = None
        if os.path.exists("membercount_channel.txt"):
            try:
                with open("membercount_channel.txt", "r") as f:
                    channel_id = int(f.read().strip())
                channel = guild.get_channel(channel_id)
            except Exception:
                channel = None
        if not channel:
            channel = discord.utils.get(guild.voice_channels, name=channel_name)
        if channel:
            await channel.edit(name=channel_name)
            await ctx.send(embed=styled_embed(
                title="Member Count Channel Updated",
                description=f"Updated {channel.mention} to current member count.",
                color=discord.Color.green(),
                ctx=ctx,
                emoji="✅"
            ), reference=getattr(ctx, 'message', None), mention_author=True)
            with open("membercount_channel.txt", "w") as f:
                f.write(str(channel.id))
            return
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True)
        }
        channel = await guild.create_voice_channel(channel_name, overwrites=overwrites, reason="Member count channel")
        with open("membercount_channel.txt", "w") as f:
            f.write(str(channel.id))
        await ctx.send(embed=styled_embed(
            title="Member Count Channel Created",
            description=f"Created {channel.mention}. It will update automatically!",
            color=discord.Color.green(),
            ctx=ctx,
            emoji="✅"
        ), reference=getattr(ctx, 'message', None), mention_author=True)

    @commands.hybrid_command(name="afk", description="Set your AFK status.")
    async def afk(self, ctx, *, message: str = "AFK"):
        self.afk_status[ctx.author.id] = (message, datetime.utcnow())
        embed = modern_embed(
            title="AFK Set",
            description=f"You are now AFK: {message}",
            color=discord.Color.blurple(),
            ctx=ctx,
            emoji="💤"
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        # Clear AFK if user sends a message
        if message.author.id in self.afk_status:
            del self.afk_status[message.author.id]
            embed = modern_embed(
                title="AFK Removed",
                description="Welcome back! Your AFK status has been cleared.",
                color=discord.Color.green(),
                ctx=message,
                emoji="✅"
            )
            await message.channel.send(embed=embed)
        # Notify if mentioned user is AFK
        for user in message.mentions:
            if user.id in self.afk_status:
                afk_msg, since = self.afk_status[user.id]
                embed = modern_embed(
                    title=f"{user.display_name} is AFK",
                    description=afk_msg,
                    color=discord.Color.orange(),
                    ctx=message,
                    emoji="🚧"
                )
                await message.channel.send(embed=embed)
        # Don't break other listeners
        # await self.bot.process_commands(message)  # Removed to prevent double replies

    @commands.hybrid_command(name="poll", description="Create a poll.")
    async def poll(self, ctx, *, question: str):
        view = PollView(question)
        await ctx.send(embed=modern_embed(title="📊 Poll", description=question, color=discord.Color.blurple(), ctx=ctx), view=view)

    @commands.command(name="reminder", description="Set a reminder.")
    async def reminder(self, ctx, *, reminder: str):
        await ctx.send(embed=modern_embed(title="⏰ Reminder", description="This is a stub for reminder.", color=discord.Color.blurple(), ctx=ctx))

    @commands.command(name="translate", description="Translate text.")
    async def translate(self, ctx, *, text: str):
        await ctx.send(embed=modern_embed(title="🌐 Translate", description="This is a stub for translate.", color=discord.Color.blurple(), ctx=ctx))

    # Removed duplicate weather command - use the weather cog instead

class PollView(ui.View):
    def __init__(self, question):
        super().__init__(timeout=300)
        self.question = question
        self.votes = {"Yes": set(), "No": set(), "Maybe": set()}
        self.add_item(self.YesButton(self))
        self.add_item(self.NoButton(self))
        self.add_item(self.MaybeButton(self))
        self.add_item(self.ResultsButton(self))

    class YesButton(ui.Button):
        def __init__(self, parent):
            super().__init__(label="Yes", style=discord.ButtonStyle.success, emoji="👍")
            self.parent = parent
        async def callback(self, interaction):
            self.parent._vote(interaction.user, "Yes")
            await interaction.response.send_message("You voted Yes!", ephemeral=True)
    class NoButton(ui.Button):
        def __init__(self, parent):
            super().__init__(label="No", style=discord.ButtonStyle.danger, emoji="👎")
            self.parent = parent
        async def callback(self, interaction):
            self.parent._vote(interaction.user, "No")
            await interaction.response.send_message("You voted No!", ephemeral=True)
    class MaybeButton(ui.Button):
        def __init__(self, parent):
            super().__init__(label="Maybe", style=discord.ButtonStyle.secondary, emoji="🤔")
            self.parent = parent
        async def callback(self, interaction):
            self.parent._vote(interaction.user, "Maybe")
            await interaction.response.send_message("You voted Maybe!", ephemeral=True)
    class ResultsButton(ui.Button):
        def __init__(self, parent):
            super().__init__(label="View Results", style=discord.ButtonStyle.blurple, emoji="📊")
            self.parent = parent
        async def callback(self, interaction):
            await interaction.response.send_message(embed=self.parent.get_results_embed(interaction), ephemeral=True)
    def _vote(self, user, choice):
        for k in self.votes:
            self.votes[k].discard(user.id)
        self.votes[choice].add(user.id)
    def get_results_embed(self, ctx):
        total = sum(len(v) for v in self.votes.values())
        desc = "\n".join(f"{emoji} **{k}:** {len(v)}" for k, v, emoji in zip(self.votes.keys(), self.votes.values(), ["👍", "👎", "🤔"]))
        return modern_embed(
            title="📊 Poll Results",
            description=f"**{self.question}**\n\n{desc}\n\n**Total votes:** {total}",
            color=discord.Color.blurple(),
            ctx=ctx
        )

class RoleMenuView(ui.View):
    def __init__(self, roles):
        super().__init__(timeout=300)
        self.roles = roles
        for role in roles:
            self.add_item(RoleButton(role))

class RoleButton(ui.Button):
    def __init__(self, role):
        super().__init__(label=role.name, style=discord.ButtonStyle.secondary, emoji="🎭")
        self.role = role
    async def callback(self, interaction):
        member = interaction.user
        if self.role in member.roles:
            await member.remove_roles(self.role)
            await interaction.response.send_message(f"Removed role {self.role.mention}!", ephemeral=True)
        else:
            await member.add_roles(self.role)
            await interaction.response.send_message(f"Added role {self.role.mention}!", ephemeral=True)

    @commands.hybrid_command(name="rolesetup", description="Setup self-assignable roles (admin only).")
    @commands.has_permissions(administrator=True)
    async def rolesetup(self, ctx, role1: discord.Role, role2: discord.Role = None, role3: discord.Role = None):
        roles = [role for role in [role1, role2, role3] if role]
        if not roles:
            await ctx.send(embed=modern_embed(title="❌ Error", description="Please specify at least one role.", color=discord.Color.red(), ctx=ctx))
            return
        # In a real bot, store in DB. Here, just show success.
        role_list = ", ".join(role.mention for role in roles)
        await ctx.send(embed=modern_embed(title="🎭 Role Setup", description=f"Self-assignable roles set: {role_list}", color=discord.Color.green(), ctx=ctx))

    @commands.hybrid_command(name="rolemenu", description="Post a role menu for users to assign roles.")
    @commands.has_permissions(administrator=True)
    async def rolemenu(self, ctx):
        # In a real bot, fetch from DB. Here, use dummy roles.
        roles = [role for role in ctx.guild.roles if role.name in ["Member", "Verified", "VIP"] and role != ctx.guild.default_role]
        if not roles:
            await ctx.send(embed=modern_embed(title="❌ Error", description="No self-assignable roles configured. Use `/rolesetup` first.", color=discord.Color.red(), ctx=ctx))
            return
        view = RoleMenuView(roles)
        await ctx.send(embed=modern_embed(title="🎭 Role Menu", description="Click a button to assign or remove a role.", color=discord.Color.blurple(), ctx=ctx), view=view)

async def setup(bot):
    await bot.add_cog(Utility(bot)) 