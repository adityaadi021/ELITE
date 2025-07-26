import discord
from discord.ext import commands
from datetime import datetime
import aiosqlite
from .utility import styled_embed, OWNER_ID

class Invites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description="Show how many users a member has invited.")
    async def invites(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        async with aiosqlite.connect('database.db') as db:
            row = await db.execute('SELECT invites FROM invite_tracker WHERE user_id = ? AND guild_id = ?', (member.id, ctx.guild.id))
            result = await row.fetchone()
        count = result[0] if result else 0
        embed = styled_embed(
            title="Invite Tracker",
            description=f"{member.mention} has invited **{count}** member(s) to this server!",
            color=discord.Color.blurple(),
            ctx=ctx,
            emoji="🔗"
        )
        await ctx.send(embed=embed, reference=ctx.message if hasattr(ctx, 'message') else None, mention_author=True)

    @commands.hybrid_command(description="Show the top inviters in this server.")
    async def inviteleaderboard(self, ctx):
        async with aiosqlite.connect('database.db') as db:
            rows = await db.execute('SELECT user_id, invites FROM invite_tracker WHERE guild_id = ? ORDER BY invites DESC LIMIT 10', (ctx.guild.id,))
            results = await rows.fetchall()
        if not results:
            await ctx.send(embed=styled_embed(
                title="Invite Leaderboard",
                description="No invite data found for this server.",
                color=discord.Color.orange(),
                ctx=ctx,
                emoji="🏆"
            ), reference=ctx.message if hasattr(ctx, 'message') else None, mention_author=True)
            return
        desc = ""
        for i, (user_id, invites) in enumerate(results, 1):
            member = ctx.guild.get_member(user_id)
            name = member.mention if member else f"<@{user_id}>"
            desc += f"**{i}.** {name} — `{invites}` invites\n"
        embed = styled_embed(
            title="Invite Leaderboard",
            description=desc,
            color=discord.Color.blurple(),
            ctx=ctx,
            emoji="🏆"
        )
        await ctx.send(embed=embed, reference=ctx.message if hasattr(ctx, 'message') else None, mention_author=True)

    @commands.hybrid_command(description="Show in how many servers a member has invited the bot.")
    async def botinviteservers(self, ctx, member: discord.Member = None):
        if member is None and ctx.author.id == OWNER_ID:
            invite_counts = {}
            for guild in ctx.bot.guilds:
                if guild.member_count >= 100:
                    async with aiosqlite.connect('database.db') as db:
                        rows = await db.execute('SELECT user_id, invites FROM invite_tracker WHERE guild_id = ?', (guild.id,))
                        results = await rows.fetchall()
                    for user_id, invites in results:
                        if invites > 0:
                            invite_counts[user_id] = invite_counts.get(user_id, 0) + 1
            if not invite_counts:
                await ctx.send(embed=styled_embed(
                    title="Bot Invite Servers Leaderboard",
                    description="No invite data found for any server.",
                    color=discord.Color.orange(),
                    ctx=ctx,
                    emoji="🌐"
                ), reference=ctx.message if hasattr(ctx, 'message') else None, mention_author=True)
                return
            sorted_counts = sorted(invite_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            desc = ""
            for i, (user_id, count) in enumerate(sorted_counts, 1):
                user = ctx.bot.get_user(user_id)
                name = user.mention if user else f"<@{user_id}>"
                desc += f"**{i}.** {name} — `{count}` servers\n"
            embed = styled_embed(
                title="Bot Invite Servers Leaderboard",
                description=desc,
                color=discord.Color.blurple(),
                ctx=ctx,
                emoji="🌐"
            )
            await ctx.send(embed=embed, reference=ctx.message if hasattr(ctx, 'message') else None, mention_author=True)
            return
        member = member or ctx.author
        count = 0
        for guild in ctx.bot.guilds:
            if guild.member_count >= 100:
                async with aiosqlite.connect('database.db') as db:
                    row = await db.execute('SELECT invites FROM invite_tracker WHERE user_id = ? AND guild_id = ?', (member.id, guild.id))
                    result = await row.fetchone()
                if result and result[0] > 0:
                    count += 1
        embed = styled_embed(
            title="Bot Invite Servers",
            description=f"{member.mention} has invited the bot in **{count}** server(s) with 100+ members.",
            color=discord.Color.blurple(),
            ctx=ctx,
            emoji="🌐"
        )
        await ctx.send(embed=embed, reference=ctx.message if hasattr(ctx, 'message') else None, mention_author=True)

async def setup(bot):
    await bot.add_cog(Invites(bot)) 