import discord
from discord.ext import commands
from bot import modern_embed
import aiosqlite
import re
import asyncio
from datetime import datetime, timedelta
import json
import random

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_trackers = {}
        self.raid_protection = {}
        self.verification_sessions = {}
        
        # Content filters
        self.banned_words = {
            "spam": ["discord.gg/", "discord.gg/", "discord.gg/", "discord.gg/"],
            "inappropriate": ["bad_word1", "bad_word2"],  # Add actual words
            "scam": ["free nitro", "free discord", "hack", "cheat"]
        }
        
        # Raid detection patterns
        self.raid_patterns = {
            "mass_join": {"threshold": 5, "timeframe": 30},  # 5 joins in 30 seconds
            "mass_message": {"threshold": 10, "timeframe": 60},  # 10 messages in 60 seconds
            "mass_reaction": {"threshold": 20, "timeframe": 30}  # 20 reactions in 30 seconds
        }

    async def cog_load(self):
        await self.init_database()

    async def init_database(self):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS automod_config 
                               (guild_id INTEGER PRIMARY KEY, enabled BOOLEAN DEFAULT 1,
                                spam_protection BOOLEAN DEFAULT 1, raid_protection BOOLEAN DEFAULT 1,
                                content_filter BOOLEAN DEFAULT 1, verification_enabled BOOLEAN DEFAULT 0,
                                log_channel_id INTEGER, action_level INTEGER DEFAULT 1)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS automod_logs 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER,
                                user_id INTEGER, action TEXT, reason TEXT, timestamp TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS verification_sessions 
                               (user_id INTEGER, guild_id INTEGER, code TEXT, expires TEXT,
                                verified BOOLEAN DEFAULT 0, PRIMARY KEY (user_id, guild_id))''')
            await db.commit()

    async def get_automod_config(self, guild_id):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('SELECT * FROM automod_config WHERE guild_id = ?', (guild_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    return {
                        'enabled': bool(result[1]),
                        'spam_protection': bool(result[2]),
                        'raid_protection': bool(result[3]),
                        'content_filter': bool(result[4]),
                        'verification_enabled': bool(result[5]),
                        'log_channel_id': result[6],
                        'action_level': result[7]
                    }
                return None

    async def log_automod_action(self, guild_id, user_id, action, reason):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT INTO automod_logs (guild_id, user_id, action, reason, timestamp)
                               VALUES (?, ?, ?, ?, ?)''',
                           (guild_id, user_id, action, reason, datetime.utcnow().isoformat()))
            await db.commit()

    def detect_spam(self, message, guild_id):
        """Advanced spam detection using multiple criteria"""
        user_id = message.author.id
        content = message.content.lower()
        
        if guild_id not in self.spam_trackers:
            self.spam_trackers[guild_id] = {}
        
        if user_id not in self.spam_trackers[guild_id]:
            self.spam_trackers[guild_id][user_id] = {
                'messages': [],
                'similar_count': 0,
                'link_count': 0,
                'caps_ratio': 0
            }
        
        tracker = self.spam_trackers[guild_id][user_id]
        current_time = datetime.utcnow()
        
        # Clean old messages (older than 60 seconds)
        tracker['messages'] = [msg for msg in tracker['messages'] 
                             if current_time - msg['time'] < timedelta(seconds=60)]
        
        # Add current message
        tracker['messages'].append({
            'content': content,
            'time': current_time
        })
        
        # Check for repeated messages
        if len(tracker['messages']) >= 3:
            recent_messages = [msg['content'] for msg in tracker['messages'][-3:]]
            if len(set(recent_messages)) == 1:  # All messages are identical
                tracker['similar_count'] += 1
            else:
                tracker['similar_count'] = 0
        
        # Check for excessive links
        link_count = len(re.findall(r'https?://\S+', content))
        if link_count > 0:
            tracker['link_count'] += link_count
        
        # Check for excessive caps
        if len(content) > 10:
            caps_ratio = sum(1 for c in content if c.isupper()) / len(content)
            if caps_ratio > 0.7:  # More than 70% caps
                tracker['caps_ratio'] += 1
            else:
                tracker['caps_ratio'] = 0
        
        # Determine spam score
        spam_score = 0
        if len(tracker['messages']) > 5:  # Too many messages
            spam_score += 2
        if tracker['similar_count'] >= 2:  # Repeated messages
            spam_score += 3
        if tracker['link_count'] >= 3:  # Too many links
            spam_score += 2
        if tracker['caps_ratio'] >= 2:  # Excessive caps
            spam_score += 1
        
        return spam_score >= 3  # Threshold for spam detection

    def detect_raid(self, guild_id, event_type, user_id):
        """Detect potential raid activity"""
        if guild_id not in self.raid_protection:
            self.raid_protection[guild_id] = {
                'joins': [],
                'messages': [],
                'reactions': []
            }
        
        current_time = datetime.utcnow()
        raid_data = self.raid_protection[guild_id]
        
        # Add event to appropriate tracker
        if event_type == 'join':
            raid_data['joins'].append({'user_id': user_id, 'time': current_time})
        elif event_type == 'message':
            raid_data['messages'].append({'user_id': user_id, 'time': current_time})
        elif event_type == 'reaction':
            raid_data['reactions'].append({'user_id': user_id, 'time': current_time})
        
        # Clean old events
        for event_list in raid_data.values():
            event_list[:] = [event for event in event_list 
                           if current_time - event['time'] < timedelta(seconds=60)]
        
        # Check for raid patterns
        if len(raid_data['joins']) >= self.raid_patterns['mass_join']['threshold']:
            return 'mass_join'
        elif len(raid_data['messages']) >= self.raid_patterns['mass_message']['threshold']:
            return 'mass_message'
        elif len(raid_data['reactions']) >= self.raid_patterns['mass_reaction']['threshold']:
            return 'mass_reaction'
        
        return None

    def content_filter(self, content):
        """Advanced content filtering"""
        content_lower = content.lower()
        
        # Check for banned words
        for category, words in self.banned_words.items():
            for word in words:
                if word in content_lower:
                    return category, word
        
        # Check for excessive mentions
        mention_count = len(re.findall(r'<@!?\d+>', content))
        if mention_count > 5:
            return 'excessive_mentions', mention_count
        
        # Check for excessive emojis
        emoji_count = len(re.findall(r'<a?:.+?:\d+>|[\U0001F600-\U0001F64F]', content))
        if emoji_count > 10:
            return 'excessive_emojis', emoji_count
        
        return None, None

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        
        config = await self.get_automod_config(message.guild.id)
        if not config or not config['enabled']:
            return
        
        user_id = message.author.id
        guild_id = message.guild.id
        
        # Check permissions
        if message.author.guild_permissions.administrator:
            return
        
        # Content filtering
        if config['content_filter']:
            filter_result, details = self.content_filter(message.content)
            if filter_result:
                await self.handle_violation(message, filter_result, details)
                return
        
        # Spam protection
        if config['spam_protection']:
            if self.detect_spam(message, guild_id):
                await self.handle_violation(message, 'spam', 'Repeated messages/links')
                return
        
        # Raid detection
        if config['raid_protection']:
            raid_type = self.detect_raid(guild_id, 'message', user_id)
            if raid_type:
                await self.handle_raid(guild_id, raid_type)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = await self.get_automod_config(member.guild.id)
        if not config or not config['enabled'] or not config['raid_protection']:
            return
        
        raid_type = self.detect_raid(member.guild.id, 'join', member.id)
        if raid_type:
            await self.handle_raid(member.guild.id, raid_type)

    async def handle_violation(self, message, violation_type, details):
        """Handle automod violations"""
        config = await self.get_automod_config(message.guild.id)
        action_level = config.get('action_level', 1)
        
        # Log the violation
        await self.log_automod_action(message.guild.id, message.author.id, violation_type, str(details))
        
        # Take action based on level
        if action_level == 1:  # Warning
            embed = modern_embed(
                title="⚠️ AutoMod Warning",
                description=f"Your message was flagged for: **{violation_type}**\n"
                           f"Please follow the server rules.",
                color=discord.Color.orange(),
                ctx=message
            )
            await message.channel.send(embed=embed, delete_after=10)
            await message.delete()
        
        elif action_level == 2:  # Timeout
            try:
                await message.author.timeout(duration=300, reason=f"AutoMod: {violation_type}")
                embed = modern_embed(
                    title="🔇 User Timed Out",
                    description=f"{message.author.mention} was timed out for 5 minutes\n"
                               f"Reason: **{violation_type}**",
                    color=discord.Color.red(),
                    ctx=message
                )
                await message.channel.send(embed=embed)
                await message.delete()
            except:
                pass
        
        elif action_level == 3:  # Kick
            try:
                await message.author.kick(reason=f"AutoMod: {violation_type}")
                embed = modern_embed(
                    title="👢 User Kicked",
                    description=f"{message.author.mention} was kicked\n"
                               f"Reason: **{violation_type}**",
                    color=discord.Color.red(),
                    ctx=message
                )
                await message.channel.send(embed=embed)
            except:
                pass

    async def handle_raid(self, guild_id, raid_type):
        """Handle raid detection"""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        
        config = await self.get_automod_config(guild_id)
        
        # Emergency lockdown
        try:
            for channel in guild.text_channels:
                await channel.set_permissions(guild.default_role, send_messages=False)
            
            embed = modern_embed(
                title="🚨 RAID DETECTED",
                description=f"**Raid Type:** {raid_type}\n"
                           f"**Action:** Server locked down for 5 minutes\n"
                           f"**Status:** Emergency mode activated",
                color=discord.Color.red(),
                ctx=None
            )
            
            # Send to log channel if configured
            if config and config.get('log_channel_id'):
                log_channel = guild.get_channel(config['log_channel_id'])
                if log_channel:
                    await log_channel.send(embed=embed)
            
            # Unlock after 5 minutes
            await asyncio.sleep(300)
            for channel in guild.text_channels:
                await channel.set_permissions(guild.default_role, send_messages=None)
            
        except Exception as e:
            print(f"Error handling raid: {e}")

    @commands.hybrid_command(name="automodconfig", description="Configure AutoMod settings.")
    @commands.has_permissions(administrator=True)
    async def automod_config(self, ctx):
        config = await self.get_automod_config(ctx.guild.id)
        
        embed = modern_embed(
            title="🤖 AutoMod Configuration",
            description="Configure automated moderation settings",
            color=discord.Color.blurple(),
            ctx=ctx
        )
        
        if config:
            embed.add_field(
                name="📊 Current Settings",
                value=f"**Enabled:** {'✅' if config['enabled'] else '❌'}\n"
                      f"**Spam Protection:** {'✅' if config['spam_protection'] else '❌'}\n"
                      f"**Raid Protection:** {'✅' if config['raid_protection'] else '❌'}\n"
                      f"**Content Filter:** {'✅' if config['content_filter'] else '❌'}\n"
                      f"**Action Level:** {config['action_level']}",
                inline=False
            )
        else:
            embed.add_field(
                name="❌ Not Configured",
                value="Use `/automod setup` to configure AutoMod",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="automod_setup", description="Setup AutoMod for this server.")
    @commands.has_permissions(administrator=True)
    async def automod_setup(self, ctx):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT OR REPLACE INTO automod_config 
                               (guild_id, enabled, spam_protection, raid_protection, 
                                content_filter, verification_enabled, action_level)
                               VALUES (?, 1, 1, 1, 1, 0, 1)''', (ctx.guild.id,))
            await db.commit()
        
        embed = modern_embed(
            title="✅ AutoMod Setup Complete",
            description="AutoMod has been enabled with default settings:\n\n"
                       "**Features Enabled:**\n"
                       "• Spam Protection\n"
                       "• Raid Protection\n"
                       "• Content Filtering\n"
                       "• Action Level: Warning\n\n"
                       "Use `/automod` to view current settings",
            color=discord.Color.green(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="verification", description="Setup verification system.")
    @commands.has_permissions(administrator=True)
    async def verification_setup(self, ctx, channel: discord.TextChannel):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''UPDATE automod_config SET verification_enabled = 1 
                               WHERE guild_id = ?''', (ctx.guild.id,))
            await db.commit()
        
        embed = modern_embed(
            title="✅ Verification Setup",
            description=f"Verification system enabled for {channel.mention}\n\n"
                       "New members will need to verify before accessing the server.",
            color=discord.Color.green(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="verify", description="Complete verification.")
    async def verify(self, ctx):
        config = await self.get_automod_config(ctx.guild.id)
        if not config or not config['verification_enabled']:
            await ctx.send(embed=modern_embed(
                title="❌ Verification Not Required",
                description="Verification is not enabled in this server.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Generate verification code
        code = ''.join(random.choices('0123456789', k=6))
        
        # Store verification session
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT OR REPLACE INTO verification_sessions 
                               (user_id, guild_id, code, expires, verified)
                               VALUES (?, ?, ?, ?, 0)''',
                           (ctx.author.id, ctx.guild.id, code, 
                            (datetime.utcnow() + timedelta(minutes=5)).isoformat()))
            await db.commit()
        
        embed = modern_embed(
            title="🔐 Verification Required",
            description=f"Your verification code is: **{code}**\n\n"
                       "Please enter this code in the verification channel.\n"
                       "Code expires in 5 minutes.",
            color=discord.Color.blurple(),
            ctx=ctx
        )
        await ctx.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AutoMod(bot)) 