import discord
from discord.ext import commands
from bot import modern_embed
import aiosqlite
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import json
import io
import asyncio

class Analytics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.activity_trackers = {}


    async def init_database(self):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS server_analytics 
                               (guild_id INTEGER, date TEXT, member_count INTEGER,
                                message_count INTEGER, voice_minutes INTEGER,
                                join_count INTEGER, leave_count INTEGER,
                                command_usage INTEGER, PRIMARY KEY (guild_id, date))''')
            await db.execute('''CREATE TABLE IF NOT EXISTS user_activity 
                               (user_id INTEGER, guild_id INTEGER, date TEXT,
                                messages INTEGER, voice_minutes INTEGER, commands INTEGER,
                                reactions INTEGER, PRIMARY KEY (user_id, guild_id, date))''')
            await db.execute('''CREATE TABLE IF NOT EXISTS channel_stats 
                               (channel_id INTEGER, guild_id INTEGER, date TEXT,
                                message_count INTEGER, reaction_count INTEGER,
                                PRIMARY KEY (channel_id, date))''')
            await db.execute('''CREATE TABLE IF NOT EXISTS command_stats 
                               (command_name TEXT, guild_id INTEGER, date TEXT,
                                usage_count INTEGER, PRIMARY KEY (command_name, guild_id, date))''')
            await db.commit()

    async def track_activity(self, guild_id, user_id=None, channel_id=None, command_name=None):
        """Track various activity metrics"""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        
        async with aiosqlite.connect('database.db') as db:
            # Update server analytics
            await db.execute('''INSERT OR REPLACE INTO server_analytics 
                               (guild_id, date, member_count, message_count, voice_minutes,
                                join_count, leave_count, command_usage)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                           (guild_id, today, 0, 0, 0, 0, 0, 0))
            
            # Update user activity if user_id provided
            if user_id:
                await db.execute('''INSERT OR REPLACE INTO user_activity 
                                   (user_id, guild_id, date, messages, voice_minutes, commands, reactions)
                                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                               (user_id, guild_id, today, 0, 0, 0, 0))
            
            # Update channel stats if channel_id provided
            if channel_id:
                await db.execute('''INSERT OR REPLACE INTO channel_stats 
                                   (channel_id, guild_id, date, message_count, reaction_count)
                                   VALUES (?, ?, ?, ?, ?)''',
                               (channel_id, guild_id, today, 0, 0))
            
            # Update command stats if command_name provided
            if command_name:
                await db.execute('''INSERT OR REPLACE INTO command_stats 
                                   (command_name, guild_id, date, usage_count)
                                   VALUES (?, ?, ?, ?)''',
                               (command_name, guild_id, today, 0))
            
            await db.commit()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        
        guild_id = message.guild.id
        user_id = message.author.id
        channel_id = message.channel.id
        
        # Track message activity
        await self.track_activity(guild_id, user_id, channel_id)
        
        # Update message counts
        today = datetime.utcnow().strftime('%Y-%m-%d')
        async with aiosqlite.connect('database.db') as db:
            # Update server message count
            await db.execute('''UPDATE server_analytics SET message_count = message_count + 1
                               WHERE guild_id = ? AND date = ?''', (guild_id, today))
            
            # Update user message count
            await db.execute('''UPDATE user_activity SET messages = messages + 1
                               WHERE user_id = ? AND guild_id = ? AND date = ?''',
                           (user_id, guild_id, today))
            
            # Update channel message count
            await db.execute('''UPDATE channel_stats SET message_count = message_count + 1
                               WHERE channel_id = ? AND date = ?''', (channel_id, today))
            
            await db.commit()

    @commands.Cog.listener()
    async def on_command(self, ctx):
        if not ctx.guild:
            return
        
        guild_id = ctx.guild.id
        user_id = ctx.author.id
        command_name = ctx.command.qualified_name
        
        # Track command usage
        await self.track_activity(guild_id, user_id, command_name=command_name)
        
        # Update command counts
        today = datetime.utcnow().strftime('%Y-%m-%d')
        async with aiosqlite.connect('database.db') as db:
            # Update server command count
            await db.execute('''UPDATE server_analytics SET command_usage = command_usage + 1
                               WHERE guild_id = ? AND date = ?''', (guild_id, today))
            
            # Update user command count
            await db.execute('''UPDATE user_activity SET commands = commands + 1
                               WHERE user_id = ? AND guild_id = ? AND date = ?''',
                           (user_id, guild_id, today))
            
            # Update command stats
            await db.execute('''UPDATE command_stats SET usage_count = usage_count + 1
                               WHERE command_name = ? AND guild_id = ? AND date = ?''',
                           (command_name, guild_id, today))
            
            await db.commit()

    @commands.command(name="analytics", description="Show server analytics dashboard.")
    @commands.has_permissions(administrator=True)
    async def analytics_dashboard(self, ctx):
        guild_id = ctx.guild.id
        today = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Get current server stats
        async with aiosqlite.connect('database.db') as db:
            # Today's stats
            async with db.execute('''SELECT member_count, message_count, voice_minutes, 
                                   join_count, leave_count, command_usage
                                   FROM server_analytics WHERE guild_id = ? AND date = ?''',
                                (guild_id, today)) as cursor:
                today_stats = await cursor.fetchone()
            
            # Weekly stats
            week_ago = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
            async with db.execute('''SELECT SUM(message_count), SUM(command_usage), 
                                   SUM(join_count), SUM(leave_count)
                                   FROM server_analytics 
                                   WHERE guild_id = ? AND date >= ?''',
                                (guild_id, week_ago)) as cursor:
                weekly_stats = await cursor.fetchone()
            
            # Top channels
            async with db.execute('''SELECT channel_id, SUM(message_count) as total_messages
                                   FROM channel_stats 
                                   WHERE guild_id = ? AND date >= ?
                                   GROUP BY channel_id 
                                   ORDER BY total_messages DESC LIMIT 5''',
                                (guild_id, week_ago)) as cursor:
                top_channels = await cursor.fetchall()
            
            # Top commands
            async with db.execute('''SELECT command_name, SUM(usage_count) as total_usage
                                   FROM command_stats 
                                   WHERE guild_id = ? AND date >= ?
                                   GROUP BY command_name 
                                   ORDER BY total_usage DESC LIMIT 5''',
                                (guild_id, week_ago)) as cursor:
                top_commands = await cursor.fetchall()
        
        embed = modern_embed(
            title="📊 Server Analytics Dashboard",
            description=f"**Server:** {ctx.guild.name}\n**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        # Today's stats
        if today_stats:
            embed.add_field(
                name="📈 Today's Activity",
                value=f"**Messages:** {today_stats[1]:,}\n"
                      f"**Commands:** {today_stats[5]:,}\n"
                      f"**Joins:** {today_stats[3]}\n"
                      f"**Leaves:** {today_stats[4]}",
                inline=True
            )
        
        # Weekly stats
        if weekly_stats:
            embed.add_field(
                name="📅 This Week",
                value=f"**Messages:** {weekly_stats[0] or 0:,}\n"
                      f"**Commands:** {weekly_stats[1] or 0:,}\n"
                      f"**Net Growth:** {weekly_stats[2] or 0 - weekly_stats[3] or 0:+d}",
                inline=True
            )
        
        # Server info
        embed.add_field(
            name="🏠 Server Info",
            value=f"**Members:** {ctx.guild.member_count:,}\n"
                  f"**Channels:** {len(ctx.guild.channels)}\n"
                  f"**Roles:** {len(ctx.guild.roles)}\n"
                  f"**Created:** {ctx.guild.created_at.strftime('%Y-%m-%d')}",
            inline=True
        )
        
        # Top channels
        if top_channels:
            channel_text = []
            for channel_id, message_count in top_channels:
                channel = ctx.guild.get_channel(channel_id)
                if channel:
                    channel_text.append(f"#{channel.name}: {message_count:,}")
            
            embed.add_field(
                name="🔥 Top Channels (Week)",
                value="\n".join(channel_text) if channel_text else "No data",
                inline=False
            )
        
        # Top commands
        if top_commands:
            command_text = []
            for command_name, usage_count in top_commands:
                command_text.append(f"`{command_name}`: {usage_count:,}")
            
            embed.add_field(
                name="⚡ Top Commands (Week)",
                value="\n".join(command_text) if command_text else "No data",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="userstats", description="Show user activity statistics.")
    async def user_stats(self, ctx, user: discord.Member = None):
        if not user:
            user = ctx.author
        
        guild_id = ctx.guild.id
        user_id = user.id
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Get user stats
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT SUM(messages), SUM(voice_minutes), 
                                   SUM(commands), SUM(reactions)
                                   FROM user_activity 
                                   WHERE user_id = ? AND guild_id = ? AND date >= ?''',
                                (user_id, guild_id, week_ago)) as cursor:
                stats = await cursor.fetchone()
            
            # Get daily activity for the last 7 days
            async with db.execute('''SELECT date, messages, commands
                                   FROM user_activity 
                                   WHERE user_id = ? AND guild_id = ? AND date >= ?
                                   ORDER BY date DESC''',
                                (user_id, guild_id, week_ago)) as cursor:
                daily_activity = await cursor.fetchall()
        
        embed = modern_embed(
            title=f"📊 {user.display_name}'s Activity",
            description=f"**Period:** Last 7 days\n**Member since:** {user.joined_at.strftime('%Y-%m-%d') if user.joined_at else 'Unknown'}",
            color=user.color if user.color != discord.Color.default() else discord.Color.blurple(),
            ctx=ctx,
            thumbnail=user.avatar.url if user.avatar else None
        )
        
        if stats:
            embed.add_field(
                name="📈 Activity Summary",
                value=f"**Messages:** {stats[0] or 0:,}\n"
                      f"**Voice Time:** {stats[1] or 0 // 60}h {stats[1] or 0 % 60}m\n"
                      f"**Commands:** {stats[2] or 0:,}\n"
                      f"**Reactions:** {stats[3] or 0:,}",
                inline=True
            )
        
        # Daily activity breakdown
        if daily_activity:
            activity_text = []
            for date, messages, commands in daily_activity:
                activity_text.append(f"**{date}:** {messages} msgs, {commands} cmds")
            
            embed.add_field(
                name="📅 Daily Breakdown",
                value="\n".join(activity_text[:5]),  # Show last 5 days
                inline=False
            )
        
        # Member info
        embed.add_field(
            name="👤 Member Info",
            value=f"**Joined:** {user.joined_at.strftime('%Y-%m-%d') if user.joined_at else 'Unknown'}\n"
                  f"**Account Created:** {user.created_at.strftime('%Y-%m-%d')}\n"
                  f"**Roles:** {len(user.roles) - 1}\n"
                  f"**Status:** {str(user.status).title()}",
            inline=True
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="trends", description="Show activity trends with graphs.")
    @commands.has_permissions(administrator=True)
    async def activity_trends(self, ctx, days: int = 7):
        if days > 30:
            days = 30  # Limit to 30 days
        
        guild_id = ctx.guild.id
        start_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Get trend data
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT date, message_count, command_usage, join_count, leave_count
                                   FROM server_analytics 
                                   WHERE guild_id = ? AND date >= ?
                                   ORDER BY date''',
                                (guild_id, start_date)) as cursor:
                trend_data = await cursor.fetchall()
        
        if not trend_data:
            await ctx.send(embed=modern_embed(
                title="❌ No Data",
                description="No analytics data available for the specified period.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Create graph
        plt.figure(figsize=(12, 8))
        
        dates = [datetime.strptime(row[0], '%Y-%m-%d') for row in trend_data]
        messages = [row[1] for row in trend_data]
        commands = [row[2] for row in trend_data]
        joins = [row[3] for row in trend_data]
        leaves = [row[4] for row in trend_data]
        
        # Plot messages and commands
        plt.subplot(2, 1, 1)
        plt.plot(dates, messages, 'b-', label='Messages', linewidth=2)
        plt.plot(dates, commands, 'g-', label='Commands', linewidth=2)
        plt.title(f'Activity Trends - {ctx.guild.name} (Last {days} days)')
        plt.ylabel('Count')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Plot joins and leaves
        plt.subplot(2, 1, 2)
        plt.plot(dates, joins, 'r-', label='Joins', linewidth=2)
        plt.plot(dates, leaves, 'orange', label='Leaves', linewidth=2)
        plt.ylabel('Count')
        plt.xlabel('Date')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Format x-axis
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days//7)))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # Save to buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        
        # Send graph
        file = discord.File(buffer, filename='activity_trends.png')
        embed = modern_embed(
            title="📈 Activity Trends",
            description=f"**Server:** {ctx.guild.name}\n**Period:** Last {days} days\n**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            color=discord.Color.blue(),
            ctx=ctx
        )
        embed.set_image(url="attachment://activity_trends.png")
        
        await ctx.send(embed=embed, file=file)

    @commands.command(name="report", description="Generate a custom analytics report.")
    @commands.has_permissions(administrator=True)
    async def generate_report(self, ctx, report_type: str = "overview"):
        guild_id = ctx.guild.id
        today = datetime.utcnow().strftime('%Y-%m-%d')
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
        month_ago = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        if report_type == "overview":
            await self.generate_overview_report(ctx, guild_id, today, week_ago, month_ago)
        elif report_type == "engagement":
            await self.generate_engagement_report(ctx, guild_id, week_ago)
        elif report_type == "growth":
            await self.generate_growth_report(ctx, guild_id, month_ago)
        else:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Report Type",
                description="Available reports: `overview`, `engagement`, `growth`",
                color=discord.Color.red(),
                ctx=ctx
            ))

    async def generate_overview_report(self, ctx, guild_id, today, week_ago, month_ago):
        async with aiosqlite.connect('database.db') as db:
            # Get various stats
            async with db.execute('''SELECT SUM(message_count), SUM(command_usage), 
                                   SUM(join_count), SUM(leave_count)
                                   FROM server_analytics 
                                   WHERE guild_id = ? AND date >= ?''',
                                (guild_id, week_ago)) as cursor:
                weekly_stats = await cursor.fetchone()
            
            async with db.execute('''SELECT SUM(message_count), SUM(command_usage)
                                   FROM server_analytics 
                                   WHERE guild_id = ? AND date >= ?''',
                                (guild_id, month_ago)) as cursor:
                monthly_stats = await cursor.fetchone()
        
        embed = modern_embed(
            title="📋 Server Overview Report",
            description=f"**Server:** {ctx.guild.name}\n**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            color=discord.Color.green(),
            ctx=ctx
        )
        
        if weekly_stats:
            embed.add_field(
                name="📊 Weekly Metrics",
                value=f"**Messages:** {weekly_stats[0] or 0:,}\n"
                      f"**Commands:** {weekly_stats[1] or 0:,}\n"
                      f"**Net Growth:** {weekly_stats[2] or 0 - weekly_stats[3] or 0:+d}",
                inline=True
            )
        
        if monthly_stats:
            embed.add_field(
                name="📈 Monthly Metrics",
                value=f"**Messages:** {monthly_stats[0] or 0:,}\n"
                      f"**Commands:** {monthly_stats[1] or 0:,}\n"
                      f"**Avg Daily:** {(monthly_stats[0] or 0) // 30:,}",
                inline=True
            )
        
        embed.add_field(
            name="🏠 Server Status",
            value=f"**Members:** {ctx.guild.member_count:,}\n"
                  f"**Channels:** {len(ctx.guild.channels)}\n"
                  f"**Boost Level:** {ctx.guild.premium_tier}\n"
                  f"**Verification:** {ctx.guild.verification_level.name}",
            inline=True
        )
        
        await ctx.send(embed=embed)

    async def generate_engagement_report(self, ctx, guild_id, week_ago):
        async with aiosqlite.connect('database.db') as db:
            # Get top users by activity
            async with db.execute('''SELECT user_id, SUM(messages + commands) as total_activity
                                   FROM user_activity 
                                   WHERE guild_id = ? AND date >= ?
                                   GROUP BY user_id 
                                   ORDER BY total_activity DESC LIMIT 10''',
                                (guild_id, week_ago)) as cursor:
                top_users = await cursor.fetchall()
        
        embed = modern_embed(
            title="🎯 Engagement Report",
            description=f"**Server:** {ctx.guild.name}\n**Period:** Last 7 days",
            color=discord.Color.purple(),
            ctx=ctx
        )
        
        if top_users:
            user_text = []
            for i, (user_id, activity) in enumerate(top_users, 1):
                user = ctx.guild.get_member(user_id)
                if user:
                    user_text.append(f"{'🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'#{i}'} {user.display_name}: {activity:,}")
            
            embed.add_field(
                name="👥 Most Active Users",
                value="\n".join(user_text),
                inline=False
            )
        
        await ctx.send(embed=embed)

    async def generate_growth_report(self, ctx, guild_id, month_ago):
        async with aiosqlite.connect('database.db') as db:
            # Get growth data
            async with db.execute('''SELECT SUM(join_count), SUM(leave_count)
                                   FROM server_analytics 
                                   WHERE guild_id = ? AND date >= ?''',
                                (guild_id, month_ago)) as cursor:
                growth_data = await cursor.fetchone()
        
        embed = modern_embed(
            title="📈 Growth Report",
            description=f"**Server:** {ctx.guild.name}\n**Period:** Last 30 days",
            color=discord.Color.orange(),
            ctx=ctx
        )
        
        if growth_data:
            joins = growth_data[0] or 0
            leaves = growth_data[1] or 0
            net_growth = joins - leaves
            retention_rate = ((joins - leaves) / joins * 100) if joins > 0 else 0
            
            embed.add_field(
                name="📊 Growth Metrics",
                value=f"**Joins:** {joins:,}\n"
                      f"**Leaves:** {leaves:,}\n"
                      f"**Net Growth:** {net_growth:+d}\n"
                      f"**Retention Rate:** {retention_rate:.1f}%",
                inline=True
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    cog = Analytics(bot)
    await cog.init_database()
    await bot.add_cog(cog) 