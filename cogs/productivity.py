import discord
from discord.ext import commands
from bot import modern_embed
import aiosqlite
import asyncio
import json
from datetime import datetime, timedelta
import re

class Productivity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminders = {}
        self.tasks = {}

    async def init_database(self):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS reminders 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER, guild_id INTEGER, message TEXT,
                                reminder_time TEXT, created_at TEXT, channel_id INTEGER)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS tasks 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER, guild_id INTEGER, title TEXT,
                                description TEXT, due_date TEXT, priority TEXT,
                                completed BOOLEAN DEFAULT FALSE, created_at TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS notes 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER, guild_id INTEGER, title TEXT,
                                content TEXT, created_at TEXT, updated_at TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS productivity_stats 
                               (user_id INTEGER PRIMARY KEY, guild_id INTEGER,
                                tasks_completed INTEGER DEFAULT 0, reminders_set INTEGER DEFAULT 0,
                                notes_created INTEGER DEFAULT 0, total_time_saved INTEGER DEFAULT 0)''')
            await db.commit()

    async def cog_load(self):
        """Async initialization when cog loads"""
        await self.init_database()

    @commands.command(name="remind", description="Set a reminder.")
    async def set_reminder(self, ctx, time: str, *, message: str):
        # Parse time (e.g., "2h", "30m", "1d", "2024-01-01 15:30")
        reminder_time = await self.parse_time(time)
        
        if not reminder_time:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Time Format",
                description="Use formats like: 2h, 30m, 1d, or 2024-01-01 15:30",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Store reminder
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT INTO reminders 
                               (user_id, guild_id, message, reminder_time, created_at, channel_id)
                               VALUES (?, ?, ?, ?, ?, ?)''',
                           (ctx.author.id, ctx.guild.id, message, reminder_time.isoformat(),
                            datetime.utcnow().isoformat(), ctx.channel.id))
            await db.commit()
        
        await ctx.send(embed=modern_embed(
            title="⏰ Reminder Set",
            description=f"**Message:** {message}\n"
                       f"**Time:** {reminder_time.strftime('%Y-%m-%d %H:%M UTC')}\n"
                       f"**Channel:** {ctx.channel.mention}",
            color=discord.Color.green(),
            ctx=ctx
        ))
        
        # Schedule reminder
        await self.schedule_reminder(ctx.author.id, ctx.guild.id, ctx.channel.id, message, reminder_time)

    async def parse_time(self, time_str: str) -> datetime:
        """Parse time string into datetime"""
        now = datetime.utcnow()
        
        # Relative time formats
        if time_str.endswith('s'):
            seconds = int(time_str[:-1])
            return now + timedelta(seconds=seconds)
        elif time_str.endswith('m'):
            minutes = int(time_str[:-1])
            return now + timedelta(minutes=minutes)
        elif time_str.endswith('h'):
            hours = int(time_str[:-1])
            return now + timedelta(hours=hours)
        elif time_str.endswith('d'):
            days = int(time_str[:-1])
            return now + timedelta(days=days)
        
        # Absolute time formats
        try:
            # Try different date formats
            formats = [
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d %H:%M:%S',
                '%d/%m/%Y %H:%M',
                '%m/%d/%Y %H:%M'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue
            
            return None
        except:
            return None

    async def schedule_reminder(self, user_id: int, guild_id: int, channel_id: int, message: str, reminder_time: datetime):
        """Schedule a reminder"""
        delay = (reminder_time - datetime.utcnow()).total_seconds()
        
        if delay > 0:
            await asyncio.sleep(delay)
            
            # Send reminder
            channel = self.bot.get_channel(channel_id)
            if channel:
                user = self.bot.get_user(user_id)
                await channel.send(embed=modern_embed(
                    title="⏰ Reminder",
                    description=f"{user.mention}\n\n**{message}**",
                    color=discord.Color.blue(),
                    ctx=None
                ))

    @commands.command(name="reminders", description="List your active reminders.")
    async def list_reminders(self, ctx):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT message, reminder_time, created_at
                                   FROM reminders WHERE user_id = ? AND guild_id = ?
                                   AND reminder_time > ? ORDER BY reminder_time''',
                                (ctx.author.id, ctx.guild.id, datetime.utcnow().isoformat())) as cursor:
                reminders = await cursor.fetchall()
        
        if not reminders:
            await ctx.send(embed=modern_embed(
                title="⏰ No Active Reminders",
                description="You don't have any active reminders.",
                color=discord.Color.blue(),
                ctx=ctx
            ))
            return
        
        embed = modern_embed(
            title="⏰ Your Reminders",
            description=f"You have {len(reminders)} active reminder(s):",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        for message, reminder_time, created_at in reminders:
            reminder_dt = datetime.fromisoformat(reminder_time)
            created_dt = datetime.fromisoformat(created_at)
            
            embed.add_field(
                name=f"⏰ {message[:30]}{'...' if len(message) > 30 else ''}",
                value=f"**Time:** {reminder_dt.strftime('%Y-%m-%d %H:%M UTC')}\n"
                      f"**Created:** {created_dt.strftime('%Y-%m-%d %H:%M')}",
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="task", description="Create a new task.")
    async def create_task(self, ctx, title: str, priority: str = "medium", due_date: str = None, *, description: str = ""):
        priorities = ["low", "medium", "high", "urgent"]
        if priority not in priorities:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Priority",
                description=f"Valid priorities: {', '.join(priorities)}",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        due_datetime = None
        if due_date:
            due_datetime = await self.parse_time(due_date)
            if not due_datetime:
                await ctx.send(embed=modern_embed(
                    title="❌ Invalid Due Date",
                    description="Use formats like: 2h, 30m, 1d, or 2024-01-01 15:30",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
        
        # Store task
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT INTO tasks 
                               (user_id, guild_id, title, description, due_date, priority, created_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?)''',
                           (ctx.author.id, ctx.guild.id, title, description,
                            due_datetime.isoformat() if due_datetime else None,
                            priority, datetime.utcnow().isoformat()))
            await db.commit()
        
        embed = modern_embed(
            title="✅ Task Created",
            description=f"**Title:** {title}\n"
                       f"**Priority:** {priority.title()}\n"
                       f"**Description:** {description or 'No description'}\n"
                       f"**Due Date:** {due_datetime.strftime('%Y-%m-%d %H:%M UTC') if due_datetime else 'No due date'}",
            color=discord.Color.green(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.command(name="tasks", description="List your tasks.")
    async def list_tasks(self, ctx, filter_type: str = "all"):
        filter_conditions = {
            "all": "",
            "completed": "AND completed = TRUE",
            "pending": "AND completed = FALSE",
            "urgent": "AND priority = 'urgent' AND completed = FALSE",
            "overdue": "AND due_date < ? AND completed = FALSE"
        }
        
        if filter_type not in filter_conditions:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Filter",
                description=f"Valid filters: {', '.join(filter_conditions.keys())}",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        condition = filter_conditions[filter_type]
        params = [ctx.author.id, ctx.guild.id]
        
        if filter_type == "overdue":
            params.append(datetime.utcnow().isoformat())
        
        async with aiosqlite.connect('database.db') as db:
            query = f'''SELECT title, description, due_date, priority, completed, created_at
                       FROM tasks WHERE user_id = ? AND guild_id = ? {condition}
                       ORDER BY due_date ASC, priority DESC'''
            
            async with db.execute(query, params) as cursor:
                tasks = await cursor.fetchall()
        
        if not tasks:
            await ctx.send(embed=modern_embed(
                title="📋 No Tasks",
                description=f"No {filter_type} tasks found.",
                color=discord.Color.blue(),
                ctx=ctx
            ))
            return
        
        embed = modern_embed(
            title=f"📋 Your Tasks ({filter_type.title()})",
            description=f"Found {len(tasks)} task(s):",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        for title, description, due_date, priority, completed, created_at in tasks:
            status = "✅ Completed" if completed else "⏳ Pending"
            priority_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "urgent": "🔴"}
            
            task_info = f"**Priority:** {priority_emoji.get(priority, '⚪')} {priority.title()}\n"
            task_info += f"**Status:** {status}\n"
            
            if due_date:
                due_dt = datetime.fromisoformat(due_date)
                task_info += f"**Due:** {due_dt.strftime('%Y-%m-%d %H:%M')}\n"
            
            if description:
                task_info += f"**Description:** {description[:50]}{'...' if len(description) > 50 else ''}"
            
            embed.add_field(
                name=f"📋 {title}",
                value=task_info,
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="complete", description="Mark a task as complete.")
    async def complete_task(self, ctx, task_id: int):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT title FROM tasks 
                                   WHERE id = ? AND user_id = ? AND guild_id = ?''',
                                (task_id, ctx.author.id, ctx.guild.id)) as cursor:
                task = await cursor.fetchone()
            
            if not task:
                await ctx.send(embed=modern_embed(
                    title="❌ Task Not Found",
                    description="Task not found or you don't have permission to complete it.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            await db.execute('''UPDATE tasks SET completed = TRUE
                               WHERE id = ? AND user_id = ? AND guild_id = ?''',
                           (task_id, ctx.author.id, ctx.guild.id))
            await db.commit()
        
        await ctx.send(embed=modern_embed(
            title="✅ Task Completed",
            description=f"Task **{task[0]}** has been marked as complete!",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.command(name="note", description="Create a note.")
    async def create_note(self, ctx, title: str, *, content: str):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT INTO notes 
                               (user_id, guild_id, title, content, created_at, updated_at)
                               VALUES (?, ?, ?, ?, ?, ?)''',
                           (ctx.author.id, ctx.guild.id, title, content,
                            datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
            await db.commit()
        
        await ctx.send(embed=modern_embed(
            title="📝 Note Created",
            description=f"**Title:** {title}\n\n**Content:** {content}",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.command(name="notes", description="List your notes.")
    async def list_notes(self, ctx):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT title, content, created_at, updated_at
                                   FROM notes WHERE user_id = ? AND guild_id = ?
                                   ORDER BY updated_at DESC''',
                                (ctx.author.id, ctx.guild.id)) as cursor:
                notes = await cursor.fetchall()
        
        if not notes:
            await ctx.send(embed=modern_embed(
                title="📝 No Notes",
                description="You don't have any notes yet.",
                color=discord.Color.blue(),
                ctx=ctx
            ))
            return
        
        embed = modern_embed(
            title="📝 Your Notes",
            description=f"You have {len(notes)} note(s):",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        for title, content, created_at, updated_at in notes:
            created_dt = datetime.fromisoformat(created_at)
            updated_dt = datetime.fromisoformat(updated_at)
            
            embed.add_field(
                name=f"📝 {title}",
                value=f"**Content:** {content[:100]}{'...' if len(content) > 100 else ''}\n"
                      f"**Created:** {created_dt.strftime('%Y-%m-%d %H:%M')}\n"
                      f"**Updated:** {updated_dt.strftime('%Y-%m-%d %H:%M')}",
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="calculator", description="Use the built-in calculator.")
    async def calculator(self, ctx, *, expression: str):
        # Remove any potentially dangerous characters
        expression = re.sub(r'[^0-9+\-*/().\s]', '', expression)
        
        try:
            result = eval(expression)
            await ctx.send(embed=modern_embed(
                title="🧮 Calculator",
                description=f"**Expression:** {expression}\n"
                           f"**Result:** {result}",
                color=discord.Color.green(),
                ctx=ctx
            ))
        except:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Expression",
                description="Please provide a valid mathematical expression.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.command(name="timer", description="Start a countdown timer.")
    async def start_timer(self, ctx, duration: str):
        # Parse duration
        total_seconds = 0
        
        if duration.endswith('s'):
            total_seconds = int(duration[:-1])
        elif duration.endswith('m'):
            total_seconds = int(duration[:-1]) * 60
        elif duration.endswith('h'):
            total_seconds = int(duration[:-1]) * 3600
        else:
            try:
                total_seconds = int(duration)
            except:
                await ctx.send(embed=modern_embed(
                    title="❌ Invalid Duration",
                    description="Use formats like: 30s, 5m, 2h, or just seconds",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
        
        if total_seconds <= 0 or total_seconds > 86400:  # Max 24 hours
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Duration",
                description="Duration must be between 1 second and 24 hours.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Start timer
        embed = modern_embed(
            title="⏱️ Timer Started",
            description=f"**Duration:** {duration}\n"
                       f"**Ends:** {(datetime.utcnow() + timedelta(seconds=total_seconds)).strftime('%H:%M:%S UTC')}",
            color=discord.Color.blue(),
            ctx=ctx
        )
        timer_msg = await ctx.send(embed=embed)
        
        # Countdown
        remaining = total_seconds
        while remaining > 0:
            await asyncio.sleep(1)
            remaining -= 1
            
            if remaining % 60 == 0 or remaining <= 10:  # Update every minute or last 10 seconds
                minutes = remaining // 60
                seconds = remaining % 60
                time_str = f"{minutes:02d}:{seconds:02d}"
                
                embed.description = f"**Time Remaining:** {time_str}\n"
                embed.description += f"**Ends:** {(datetime.utcnow() + timedelta(seconds=remaining)).strftime('%H:%M:%S UTC')}"
                
                await timer_msg.edit(embed=embed)
        
        # Timer finished
        embed.title = "⏰ Timer Finished!"
        embed.description = f"**Duration:** {duration}\n**Time's up!**"
        embed.color = discord.Color.green()
        await timer_msg.edit(embed=embed)
        
        # Ping the user
        await ctx.send(f"{ctx.author.mention} ⏰ Your timer has finished!")

    @commands.command(name="productivity", description="View your productivity statistics.")
    async def productivity_stats(self, ctx, user: discord.Member = None):
        if not user:
            user = ctx.author
        
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT tasks_completed, reminders_set, notes_created, total_time_saved
                                   FROM productivity_stats WHERE user_id = ? AND guild_id = ?''',
                                (user.id, ctx.guild.id)) as cursor:
                stats = await cursor.fetchone()
        
        if not stats:
            stats = (0, 0, 0, 0)
        
        tasks_completed, reminders_set, notes_created, time_saved = stats
        
        embed = modern_embed(
            title=f"📊 {user.display_name}'s Productivity Stats",
            description="Your productivity achievements",
            color=user.color if user.color != discord.Color.default() else discord.Color.blurple(),
            ctx=ctx,
            thumbnail=user.avatar.url if user.avatar else None
        )
        
        embed.add_field(
            name="✅ Tasks Completed",
            value=str(tasks_completed),
            inline=True
        )
        
        embed.add_field(
            name="⏰ Reminders Set",
            value=str(reminders_set),
            inline=True
        )
        
        embed.add_field(
            name="📝 Notes Created",
            value=str(notes_created),
            inline=True
        )
        
        embed.add_field(
            name="⏱️ Time Saved",
            value=f"{time_saved} minutes",
            inline=True
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Productivity(bot)) 