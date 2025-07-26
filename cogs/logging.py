import discord
from discord.ext import commands
from bot import modern_embed

class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="logmessage", description="Show message logs (stub).")
    @commands.has_permissions(administrator=True)
    async def logmessage(self, ctx):
        await ctx.send(embed=modern_embed(title="📝 Message Logs", description="Message logs (stub).", color=discord.Color.blurple(), ctx=ctx))

    @commands.command(name="logrole", description="Show role change logs (stub).")
    @commands.has_permissions(administrator=True)
    async def logrole(self, ctx):
        await ctx.send(embed=modern_embed(title="🔄 Role Logs", description="Role change logs (stub).", color=discord.Color.blurple(), ctx=ctx))

    @commands.command(name="logvoice", description="Show voice activity logs (stub).")
    @commands.has_permissions(administrator=True)
    async def logvoice(self, ctx):
        await ctx.send(embed=modern_embed(title="🎤 Voice Logs", description="Voice activity logs (stub).", color=discord.Color.blurple(), ctx=ctx))

    @commands.command(name="logmod", description="Show moderation action logs (stub).")
    @commands.has_permissions(administrator=True)
    async def logmod(self, ctx):
        await ctx.send(embed=modern_embed(title="🛡️ Mod Logs", description="Moderation action logs (stub).", color=discord.Color.blurple(), ctx=ctx))

async def setup(bot):
    await bot.add_cog(Logging(bot)) 