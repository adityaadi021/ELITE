import discord
from discord.ext import commands
from discord import ui
import json
from bot import modern_embed

class ThemeSelect(ui.Select):
    def __init__(self, callback):
        options = [
            discord.SelectOption(label="Blurple", value="blurple", emoji="🔵", description="Default Discord theme"),
            discord.SelectOption(label="Green", value="green", emoji="🟢", description="Success theme"),
            discord.SelectOption(label="Red", value="red", emoji="🔴", description="Error theme"),
            discord.SelectOption(label="Gold", value="gold", emoji="🟡", description="Premium theme"),
            discord.SelectOption(label="Purple", value="purple", emoji="🟣", description="Royal theme"),
            discord.SelectOption(label="Orange", value="orange", emoji="🟠", description="Warning theme")
        ]
        super().__init__(placeholder="Choose a theme...", min_values=1, max_values=1, options=options)
        self.callback_func = callback

    async def callback(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.values[0])

class LanguageSelect(ui.Select):
    def __init__(self, callback):
        options = [
            discord.SelectOption(label="English", value="en", emoji="🇬🇧", description="English"),
            discord.SelectOption(label="Hindi", value="hi", emoji="🇮🇳", description="Hindi"),
            discord.SelectOption(label="Spanish", value="es", emoji="🇪🇸", description="Spanish"),
            discord.SelectOption(label="French", value="fr", emoji="🇫🇷", description="French"),
            discord.SelectOption(label="German", value="de", emoji="🇩🇪", description="German"),
            discord.SelectOption(label="Japanese", value="ja", emoji="🇯🇵", description="Japanese")
        ]
        super().__init__(placeholder="Choose a language...", min_values=1, max_values=1, options=options)
        self.callback_func = callback

    async def callback(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.values[0])

class SettingsView(ui.View):
    def __init__(self, bot, ctx):
        super().__init__(timeout=60)
        self.bot = bot
        self.ctx = ctx
        self.add_item(ThemeSelect(self.theme_callback))
        self.add_item(LanguageSelect(self.language_callback))

    async def theme_callback(self, interaction, theme):
        # Save theme to database or config
        await interaction.response.send_message(embed=modern_embed(
            title="🎨 Theme Updated",
            description=f"Bot theme set to **{theme.title()}**",
            color=discord.Color.blurple(),
            ctx=interaction
        ), ephemeral=True)

    async def language_callback(self, interaction, language):
        # Save language to database or config
        await interaction.response.send_message(embed=modern_embed(
            title="🌐 Language Updated",
            description=f"Bot language set to **{language.upper()}**",
            color=discord.Color.blurple(),
            ctx=interaction
        ), ephemeral=True)

class WelcomeModal(ui.Modal, title="Welcome Message Setup"):
    message = ui.TextInput(label="Welcome Message", placeholder="Welcome {user} to {server}!", style=discord.TextStyle.paragraph, required=True, max_length=1000)
    channel = ui.TextInput(label="Channel ID", placeholder="123456789012345678", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=modern_embed(
            title="✅ Welcome Setup",
            description=f"Welcome message configured!\nChannel: <#{self.channel.value}>\nMessage: {self.message.value}",
            color=discord.Color.green(),
            ctx=interaction
        ), ephemeral=True)

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = {}

    @commands.command(name="settings", description="Configure bot settings.")
    @commands.has_permissions(administrator=True)
    async def settings(self, ctx):
        embed = modern_embed(
            title="⚙️ Bot Settings",
            description="Configure your bot settings using the buttons below.",
            color=discord.Color.blurple(),
            ctx=ctx,
            emoji="⚙️"
        )
        view = SettingsView(self.bot, ctx)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="welcome", description="Setup welcome messages.")
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx):
        await ctx.send_modal(WelcomeModal())

    @commands.command(name="prefix", description="Set custom prefix.")
    @commands.has_permissions(administrator=True)
    async def prefix(self, ctx, new_prefix: str):
        if len(new_prefix) > 5:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Prefix",
                description="Prefix must be 5 characters or less.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        # Save prefix to database
        await ctx.send(embed=modern_embed(
            title="✅ Prefix Updated",
            description=f"Server prefix set to `{new_prefix}`",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.command(name="autodelete", description="Set auto-delete for commands.")
    @commands.has_permissions(administrator=True)
    async def autodelete(self, ctx, seconds: int = 0):
        if seconds < 0 or seconds > 300:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Time",
                description="Auto-delete time must be between 0-300 seconds.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        await ctx.send(embed=modern_embed(
            title="✅ Auto-Delete Updated",
            description=f"Command messages will be deleted after {seconds} seconds." if seconds > 0 else "Auto-delete disabled.",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.command(name="logchannel", description="Set logging channel.")
    @commands.has_permissions(administrator=True)
    async def logchannel(self, ctx, channel: discord.TextChannel):
        await ctx.send(embed=modern_embed(
            title="✅ Log Channel Set",
            description=f"Logging channel set to {channel.mention}",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.command(name="serverconfig", description="Show server configuration.")
    async def serverconfig(self, ctx):
        embed = modern_embed(
            title=f"📊 {ctx.guild.name} Configuration",
            description="Current server settings:",
            color=discord.Color.blurple(),
            ctx=ctx
        )
        embed.add_field(name="👥 Members", value=ctx.guild.member_count, inline=True)
        embed.add_field(name="📅 Created", value=ctx.guild.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="👑 Owner", value=ctx.guild.owner.mention, inline=True)
        embed.add_field(name="🔧 Roles", value=len(ctx.guild.roles), inline=True)
        embed.add_field(name="💬 Channels", value=len(ctx.guild.channels), inline=True)
        embed.add_field(name="🎭 Emojis", value=len(ctx.guild.emojis), inline=True)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Settings(bot)) 