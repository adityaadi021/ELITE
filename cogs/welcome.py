import discord
from discord.ext import commands
from bot import modern_embed

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setwelcome", description="Set the welcome message (stub).")
    @commands.has_permissions(administrator=True)
    async def setwelcome(self, ctx, *, message: str):
        await ctx.send(embed=modern_embed(title="👋 Welcome Message", description="Welcome message set (stub).", color=discord.Color.blurple(), ctx=ctx))

    @commands.command(name="setautorole", description="Set the autorole for new members (stub).")
    @commands.has_permissions(administrator=True)
    async def setautorole(self, ctx, role: discord.Role):
        await ctx.send(embed=modern_embed(title="🦸 Autorole", description=f"Autorole set to {role.mention} (stub).", color=discord.Color.blurple(), ctx=ctx))

    @commands.command(name="welcomeconfig", description="Show welcome system config (stub).")
    @commands.has_permissions(administrator=True)
    async def welcomeconfig(self, ctx):
        await ctx.send(embed=modern_embed(title="⚙️ Welcome Config", description="Welcome system config (stub).", color=discord.Color.blurple(), ctx=ctx))

async def setup(bot):
    await bot.add_cog(Welcome(bot)) 