import discord
from discord.ext import commands
from bot import modern_embed
import aiosqlite
from datetime import datetime, timedelta
import json
import asyncio
import random

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_events = {}
        self.event_reminders = {}
        # Remove async initialization from __init__

    async def init_database(self):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS events 
                               (event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                guild_id INTEGER, title TEXT, description TEXT,
                                start_time TEXT, end_time TEXT, channel_id INTEGER,
                                max_participants INTEGER, created_by INTEGER,
                                status TEXT DEFAULT 'upcoming', participants TEXT DEFAULT '[]')''')
            await db.execute('''CREATE TABLE IF NOT EXISTS event_reminders 
                               (event_id INTEGER, user_id INTEGER, reminder_time TEXT,
                                PRIMARY KEY (event_id, user_id))''')
            await db.commit()

    async def cog_load(self):
        """Async initialization when cog loads"""
        await self.init_database()
        # Start background task after a short delay to ensure bot is ready
        asyncio.create_task(self.delayed_start())

    async def delayed_start(self):
        """Start background tasks after a delay"""
        await asyncio.sleep(5)  # Wait 5 seconds for bot to be fully ready
        asyncio.create_task(self.check_event_status())

    @commands.command(name="event", description="Create a new event.")
    @commands.has_permissions(manage_events=True)
    async def create_event(self, ctx, title: str, description: str, start_time: str, 
                          end_time: str = None, max_participants: int = 0):
        """Create a new event with interactive setup"""
        
        # Parse time (accepts formats like "2024-01-15 14:30" or "2h" for relative time)
        try:
            if start_time.startswith(('+', '-')):
                # Relative time
                if start_time.startswith('+'):
                    hours = int(start_time[1:])
                    start_datetime = datetime.utcnow() + timedelta(hours=hours)
                else:
                    hours = int(start_time[1:])
                    start_datetime = datetime.utcnow() - timedelta(hours=hours)
            else:
                # Absolute time
                start_datetime = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
            
            if end_time:
                if end_time.startswith(('+', '-')):
                    if end_time.startswith('+'):
                        hours = int(end_time[1:])
                        end_datetime = start_datetime + timedelta(hours=hours)
                    else:
                        hours = int(end_time[1:])
                        end_datetime = start_datetime - timedelta(hours=hours)
                else:
                    end_datetime = datetime.strptime(end_time, '%Y-%m-%d %H:%M')
            else:
                end_datetime = start_datetime + timedelta(hours=1)
                
        except ValueError:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Time Format",
                description="Please use format: `YYYY-MM-DD HH:MM` or `+2h` for relative time",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return

        # Create event in database
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT INTO events 
                               (guild_id, title, description, start_time, end_time,
                                channel_id, max_participants, created_by, participants)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (ctx.guild.id, title, description, start_datetime.isoformat(),
                            end_datetime.isoformat(), ctx.channel.id, max_participants,
                            ctx.author.id, json.dumps([])))
            await db.commit()
            
            # Get the event ID
            async with db.execute('SELECT last_insert_rowid()') as cursor:
                event_id = (await cursor.fetchone())[0]

        # Create event embed
        embed = modern_embed(
            title=f"🎉 New Event: {title}",
            description=description,
            color=discord.Color.green(),
            ctx=ctx
        )
        
        embed.add_field(
            name="📅 Event Details",
            value=f"**Start:** {start_datetime.strftime('%Y-%m-%d %H:%M UTC')}\n"
                  f"**End:** {end_datetime.strftime('%Y-%m-%d %H:%M UTC')}\n"
                  f"**Duration:** {(end_datetime - start_datetime).total_seconds() / 3600:.1f}h\n"
                  f"**Max Participants:** {max_participants if max_participants > 0 else 'Unlimited'}",
            inline=False
        )
        
        embed.add_field(
            name="👥 Participants",
            value="No participants yet",
            inline=False
        )
        
        embed.set_footer(text=f"Event ID: {event_id} • Created by {ctx.author.display_name}")
        
        # Create view with buttons
        view = EventView(self.bot, event_id, ctx.author.id)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="events", description="List all upcoming events.")
    async def list_events(self, ctx):
        """List all upcoming events"""
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT event_id, title, description, start_time, 
                                   end_time, max_participants, participants, created_by
                                   FROM events 
                                   WHERE guild_id = ? AND status = 'upcoming'
                                   ORDER BY start_time''', (ctx.guild.id,)) as cursor:
                events = await cursor.fetchall()
        
        if not events:
            await ctx.send(embed=modern_embed(
                title="📅 No Events",
                description="No upcoming events found.",
                color=discord.Color.blue(),
                ctx=ctx
            ))
            return
        
        embed = modern_embed(
            title="📅 Upcoming Events",
            description=f"Found {len(events)} upcoming event(s):",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        for event in events:
            event_id, title, description, start_time, end_time, max_participants, participants, created_by = event
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time)
            participants_list = json.loads(participants)
            
            embed.add_field(
                name=f"🎉 {title} (ID: {event_id})",
                value=f"**Description:** {description}\n"
                      f"**Start:** {start_dt.strftime('%Y-%m-%d %H:%M UTC')}\n"
                      f"**End:** {end_dt.strftime('%Y-%m-%d %H:%M UTC')}\n"
                      f"**Participants:** {len(participants_list)}/{max_participants if max_participants > 0 else '∞'}",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="joinevent", description="Join an event.")
    async def join_event(self, ctx, event_id: int):
        """Join an event by ID"""
        async with aiosqlite.connect('database.db') as db:
            # Get event details
            async with db.execute('''SELECT title, max_participants, participants, created_by
                                   FROM events WHERE event_id = ? AND guild_id = ? AND status = 'upcoming' ''',
                               (event_id, ctx.guild.id)) as cursor:
                event = await cursor.fetchone()
            
            if not event:
                await ctx.send(embed=modern_embed(
                    title="❌ Event Not Found",
                    description="Event not found or has already ended.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            title, max_participants, participants_json, created_by = event
            participants = json.loads(participants_json)
            
            if ctx.author.id in participants:
                await ctx.send(embed=modern_embed(
                    title="❌ Already Joined",
                    description="You are already registered for this event.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            if max_participants > 0 and len(participants) >= max_participants:
                await ctx.send(embed=modern_embed(
                    title="❌ Event Full",
                    description="This event has reached its maximum capacity.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            # Add participant
            participants.append(ctx.author.id)
            await db.execute('UPDATE events SET participants = ? WHERE event_id = ?',
                           (json.dumps(participants), event_id))
            await db.commit()
            
            await ctx.send(embed=modern_embed(
                title="✅ Joined Event",
                description=f"You have successfully joined **{title}**!",
                color=discord.Color.green(),
                ctx=ctx
            ))

    @commands.command(name="leaveevent", description="Leave an event.")
    async def leave_event(self, ctx, event_id: int):
        """Leave an event by ID"""
        async with aiosqlite.connect('database.db') as db:
            # Get event details
            async with db.execute('''SELECT title, participants
                                   FROM events WHERE event_id = ? AND guild_id = ? AND status = 'upcoming' ''',
                               (event_id, ctx.guild.id)) as cursor:
                event = await cursor.fetchone()
            
            if not event:
                await ctx.send(embed=modern_embed(
                    title="❌ Event Not Found",
                    description="Event not found or has already ended.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            title, participants_json = event
            participants = json.loads(participants_json)
            
            if ctx.author.id not in participants:
                await ctx.send(embed=modern_embed(
                    title="❌ Not Registered",
                    description="You are not registered for this event.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            # Remove participant
            participants.remove(ctx.author.id)
            await db.execute('UPDATE events SET participants = ? WHERE event_id = ?',
                           (json.dumps(participants), event_id))
            await db.commit()
            
            await ctx.send(embed=modern_embed(
                title="✅ Left Event",
                description=f"You have left **{title}**.",
                color=discord.Color.orange(),
                ctx=ctx
            ))

    @commands.command(name="eventreminder", description="Set a reminder for an event.")
    async def set_event_reminder(self, ctx, event_id: int, minutes: int = 30):
        """Set a reminder for an event"""
        async with aiosqlite.connect('database.db') as db:
            # Check if event exists
            async with db.execute('''SELECT title, start_time
                                   FROM events WHERE event_id = ? AND guild_id = ? AND status = 'upcoming' ''',
                               (event_id, ctx.guild.id)) as cursor:
                event = await cursor.fetchone()
            
            if not event:
                await ctx.send(embed=modern_embed(
                    title="❌ Event Not Found",
                    description="Event not found or has already ended.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            title, start_time = event
            start_dt = datetime.fromisoformat(start_time)
            reminder_time = start_dt - timedelta(minutes=minutes)
            
            if reminder_time <= datetime.utcnow():
                await ctx.send(embed=modern_embed(
                    title="❌ Invalid Reminder Time",
                    description="The reminder time has already passed.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            # Save reminder
            await db.execute('''INSERT OR REPLACE INTO event_reminders 
                               (event_id, user_id, reminder_time) VALUES (?, ?, ?)''',
                           (event_id, ctx.author.id, reminder_time.isoformat()))
            await db.commit()
            
            await ctx.send(embed=modern_embed(
                title="⏰ Reminder Set",
                description=f"Reminder set for **{title}** {minutes} minutes before start.",
                color=discord.Color.green(),
                ctx=ctx
            ))

    @commands.command(name="cancelevent", description="Cancel an event.")
    @commands.has_permissions(manage_events=True)
    async def cancel_event(self, ctx, event_id: int):
        """Cancel an event (admin only)"""
        async with aiosqlite.connect('database.db') as db:
            # Get event details
            async with db.execute('''SELECT title, created_by, participants
                                   FROM events WHERE event_id = ? AND guild_id = ? AND status = 'upcoming' ''',
                               (event_id, ctx.guild.id)) as cursor:
                event = await cursor.fetchone()
            
            if not event:
                await ctx.send(embed=modern_embed(
                    title="❌ Event Not Found",
                    description="Event not found or has already ended.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            title, created_by, participants_json = event
            participants = json.loads(participants_json)
            
            # Check permissions
            if ctx.author.id != created_by and not ctx.author.guild_permissions.administrator:
                await ctx.send(embed=modern_embed(
                    title="❌ Permission Denied",
                    description="Only the event creator or administrators can cancel events.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            # Cancel event
            await db.execute('UPDATE events SET status = ? WHERE event_id = ?',
                           ('cancelled', event_id))
            await db.commit()
            
            # Notify participants
            if participants:
                participant_mentions = [f"<@{user_id}>" for user_id in participants]
                await ctx.send(embed=modern_embed(
                    title="❌ Event Cancelled",
                    description=f"**{title}** has been cancelled.\n\n**Participants:** {' '.join(participant_mentions)}",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
            else:
                await ctx.send(embed=modern_embed(
                    title="❌ Event Cancelled",
                    description=f"**{title}** has been cancelled.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))

    async def check_event_status(self):
        """Background task to check event status and send reminders"""
        while True:
            try:
                async with aiosqlite.connect('database.db') as db:
                    # Check for events that have started
                    now = datetime.utcnow()
                    async with db.execute('''SELECT event_id, title, channel_id, participants
                                           FROM events 
                                           WHERE status = 'upcoming' AND start_time <= ?''',
                                       (now.isoformat(),)) as cursor:
                        started_events = await cursor.fetchall()
                    
                    for event_id, title, channel_id, participants_json in started_events:
                        participants = json.loads(participants_json)
                        channel = self.bot.get_channel(channel_id)
                        
                        if channel:
                            participant_mentions = [f"<@{user_id}>" for user_id in participants]
                            embed = modern_embed(
                                title="🎉 Event Starting!",
                                description=f"**{title}** is starting now!",
                                color=discord.Color.green(),
                                ctx=None
                            )
                            if participant_mentions:
                                embed.add_field(
                                    name="👥 Participants",
                                    value=" ".join(participant_mentions),
                                    inline=False
                                )
                            await channel.send(embed=embed)
                        
                        # Mark event as active
                        await db.execute('UPDATE events SET status = ? WHERE event_id = ?',
                                       ('active', event_id))
                    
                    # Check for reminders
                    async with db.execute('''SELECT er.event_id, er.user_id, e.title
                                           FROM event_reminders er
                                           JOIN events e ON er.event_id = e.event_id
                                           WHERE er.reminder_time <= ? AND e.status = 'upcoming' ''',
                                       (now.isoformat(),)) as cursor:
                        reminders = await cursor.fetchall()
                    
                    for event_id, user_id, title in reminders:
                        user = self.bot.get_user(user_id)
                        # Find the event's channel
                        async with db.execute('SELECT channel_id FROM events WHERE event_id = ?', (event_id,)) as ch_cursor:
                            ch_row = await ch_cursor.fetchone()
                        channel = self.bot.get_channel(ch_row[0]) if ch_row else None
                        if channel:
                            await channel.send(embed=modern_embed(
                                title="⏰ Event Reminder",
                                description=f"<@{user_id}> **{title}** is starting soon!",
                                color=discord.Color.blue(),
                                ctx=None
                            ))
                        # Remove reminder
                        await db.execute('DELETE FROM event_reminders WHERE event_id = ? AND user_id = ?', (event_id, user_id))
                    
                    await db.commit()
                    
            except Exception as e:
                print(f"Error in event status check: {e}")
            
            await asyncio.sleep(60)  # Check every minute

class EventView(discord.ui.View):
    def __init__(self, bot, event_id, creator_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.event_id = event_id
        self.creator_id = creator_id

    @discord.ui.button(label="Join Event", style=discord.ButtonStyle.green, emoji="✅")
    async def join_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Join the event via button"""
        async with aiosqlite.connect('database.db') as db:
            # Get event details
            async with db.execute('''SELECT title, max_participants, participants
                                   FROM events WHERE event_id = ? AND status = 'upcoming' ''',
                               (self.event_id,)) as cursor:
                event = await cursor.fetchone()
            
            if not event:
                await interaction.response.send_message("Event not found or has ended.", ephemeral=True)
                return
            
            title, max_participants, participants_json = event
            participants = json.loads(participants_json)
            
            if interaction.user.id in participants:
                await interaction.response.send_message("You are already registered for this event.", ephemeral=True)
                return
            
            if max_participants > 0 and len(participants) >= max_participants:
                await interaction.response.send_message("This event has reached its maximum capacity.", ephemeral=True)
                return
            
            # Add participant
            participants.append(interaction.user.id)
            await db.execute('UPDATE events SET participants = ? WHERE event_id = ?',
                           (json.dumps(participants), self.event_id))
            await db.commit()
            
            await interaction.response.send_message(f"You have joined **{title}**!", ephemeral=True)

    @discord.ui.button(label="Leave Event", style=discord.ButtonStyle.red, emoji="❌")
    async def leave_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Leave the event via button"""
        async with aiosqlite.connect('database.db') as db:
            # Get event details
            async with db.execute('''SELECT title, participants
                                   FROM events WHERE event_id = ? AND status = 'upcoming' ''',
                               (self.event_id,)) as cursor:
                event = await cursor.fetchone()
            
            if not event:
                await interaction.response.send_message("Event not found or has ended.", ephemeral=True)
                return
            
            title, participants_json = event
            participants = json.loads(participants_json)
            
            if interaction.user.id not in participants:
                await interaction.response.send_message("You are not registered for this event.", ephemeral=True)
                return
            
            # Remove participant
            participants.remove(interaction.user.id)
            await db.execute('UPDATE events SET participants = ? WHERE event_id = ?',
                           (json.dumps(participants), self.event_id))
            await db.commit()
            
            await interaction.response.send_message(f"You have left **{title}**.", ephemeral=True)

    @discord.ui.button(label="Cancel Event", style=discord.ButtonStyle.gray, emoji="🚫")
    async def cancel_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the event via button (creator only)"""
        if interaction.user.id != self.creator_id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only the event creator or administrators can cancel events.", ephemeral=True)
            return
        
        async with aiosqlite.connect('database.db') as db:
            # Get event details
            async with db.execute('''SELECT title, participants
                                   FROM events WHERE event_id = ? AND status = 'upcoming' ''',
                               (self.event_id,)) as cursor:
                event = await cursor.fetchone()
            
            if not event:
                await interaction.response.send_message("Event not found or has ended.", ephemeral=True)
                return
            
            title, participants_json = event
            participants = json.loads(participants_json)
            
            # Cancel event
            await db.execute('UPDATE events SET status = ? WHERE event_id = ?',
                           ('cancelled', self.event_id))
            await db.commit()
            
            # Disable all buttons
            for child in self.children:
                child.disabled = True
            
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(f"**{title}** has been cancelled.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Events(bot)) 