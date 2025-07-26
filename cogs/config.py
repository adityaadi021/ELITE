import discord
from discord.ext import commands
import aiosqlite
from .utility import styled_embed
from bot import modern_embed
from discord import ui, Interaction

class PrefixModal(ui.Modal, title="Set Custom Prefix"):
    prefix = ui.TextInput(label="New Prefix", placeholder="Enter new prefix", required=True, max_length=5)
    def __init__(self, callback):
        super().__init__()
        self.callback_func = callback
    async def on_submit(self, interaction: Interaction):
        await self.callback_func(interaction, self.prefix.value)

class LanguageSelect(ui.Select):
    def __init__(self, callback):
        options = [
            discord.SelectOption(label="English", value="en", emoji="🇬🇧"),
            discord.SelectOption(label="Hindi", value="hi", emoji="🇮🇳"),
            discord.SelectOption(label="Spanish", value="es", emoji="🇪🇸"),
            discord.SelectOption(label="French", value="fr", emoji="🇫🇷"),
            discord.SelectOption(label="German", value="de", emoji="🇩🇪"),
        ]
        super().__init__(placeholder="Choose a language...", min_values=1, max_values=1, options=options)
        self.callback_func = callback
    async def callback(self, interaction: Interaction):
        await self.callback_func(interaction, self.values[0])

class LanguageView(ui.View):
    def __init__(self, callback):
        super().__init__(timeout=60)
        self.add_item(LanguageSelect(callback))

class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="Set the invite log channel.")
    @commands.has_permissions(administrator=True)
    async def setinvitelog(self, ctx, channel: discord.TextChannel):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('REPLACE INTO bot_config (key, value) VALUES (?, ?)', (f'invite_log_channel_{ctx.guild.id}', str(channel.id)))
            await db.commit()
        await ctx.send(embed=styled_embed(
            title="Invite Log Channel Set",
            description=f"Invite join events will be announced in {channel.mention}.",
            color=discord.Color.green(),
            ctx=ctx,
            emoji="📢"
        ), reference=ctx.message if hasattr(ctx, 'message') else None, mention_author=True)

    @commands.command(description="Set the leave log channel.")
    @commands.has_permissions(administrator=True)
    async def setleavelog(self, ctx, channel: discord.TextChannel):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('REPLACE INTO bot_config (key, value) VALUES (?, ?)', (f'leave_log_channel_{ctx.guild.id}', str(channel.id)))
            await db.commit()
        await ctx.send(embed=styled_embed(
            title="Leave Log Channel Set",
            description=f"Member leave events will be announced in {channel.mention}.",
            color=discord.Color.green(),
            ctx=ctx,
            emoji="📤"
        ), reference=ctx.message if hasattr(ctx, 'message') else None, mention_author=True)

    @commands.command(description="Set the drag command channel.")
    @commands.has_permissions(administrator=True)
    async def setdragchannel(self, ctx, channel: discord.TextChannel):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('REPLACE INTO bot_config (key, value) VALUES (?, ?)', (f'drag_channel_{ctx.guild.id}', str(channel.id)))
            await db.commit()
        await ctx.send(embed=styled_embed(
            title="Drag Command Channel Set",
            description=f"Drag command can now only be used in {channel.mention}.",
            color=discord.Color.green(),
            ctx=ctx,
            emoji="🔗"
        ), reference=ctx.message if hasattr(ctx, 'message') else None, mention_author=True)

    @commands.command(description="Show all log channels set for this server.")
    async def logchannellist(self, ctx):
        keys = [
            (f'invite_log_channel_{ctx.guild.id}', 'Invite Log'),
            (f'leave_log_channel_{ctx.guild.id}', 'Leave Log'),
            (f'drag_channel_{ctx.guild.id}', 'Drag Command'),
        ]
        desc = ""
        async with aiosqlite.connect('database.db') as db:
            for key, label in keys:
                row = await db.execute('SELECT value FROM bot_config WHERE key = ?', (key,))
                result = await row.fetchone()
                if result:
                    channel = ctx.guild.get_channel(int(result[0]))
                    mention = channel.mention if channel else f'<#{result[0]}>'
                    desc += f'**{label}:** {mention}\n'
                else:
                    desc += f'**{label}:** Not set\n'
        embed = styled_embed(
            title="Log Channel List",
            description=desc,
            color=discord.Color.blurple(),
            ctx=ctx,
            emoji="📋"
        )
        await ctx.send(embed=embed, reference=ctx.message if hasattr(ctx, 'message') else None, mention_author=True)

    @commands.command(name="automod", description="Configure auto-moderation (stub).")
    @commands.has_permissions(administrator=True)
    async def automod(self, ctx):
        await ctx.send(embed=modern_embed(title="🤖 AutoMod", description="Auto-moderation settings (stub).", color=discord.Color.blurple(), ctx=ctx))

    @commands.hybrid_command(name="setprefix", description="Set a custom prefix (interactive).")
    @commands.has_permissions(administrator=True)
    async def setprefix(self, ctx):
        async def modal_callback(interaction, prefix):
            await interaction.response.send_message(embed=modern_embed(title="🔤 Prefix", description=f"Prefix set to `{prefix}` (stub).", color=discord.Color.blurple(), ctx=interaction), ephemeral=True)
        await ctx.interaction.response.send_modal(PrefixModal(modal_callback))

    @commands.hybrid_command(name="setlang", description="Set the bot language (interactive).")
    @commands.has_permissions(administrator=True)
    async def setlang(self, ctx):
        async def select_callback(interaction, lang):
            await interaction.response.send_message(embed=modern_embed(title="🌐 Language", description=f"Language set to `{lang}` (stub).", color=discord.Color.blurple(), ctx=interaction), ephemeral=True)
        await ctx.send(embed=modern_embed(title="🌐 Language", description="Select a language for the bot.", color=discord.Color.blurple(), ctx=ctx), view=LanguageView(select_callback))

    @commands.hybrid_command(name="setwelcomeformat", description="Set the welcome message format (stub).")
    @commands.has_permissions(administrator=True)
    async def setwelcomeformat(self, ctx, *, fmt: str):
        await ctx.send(embed=modern_embed(title="📝 Welcome Format", description="Welcome message format set (stub).", color=discord.Color.blurple(), ctx=ctx))

    @commands.hybrid_command(name="setupdatabase", description="Setup Discord server as hybrid database system (SQLite + Discord).")
    @commands.has_permissions(administrator=True)
    async def setupdatabase(self, ctx):
        """Setup Discord server as hybrid database system"""
        
        # Create required channels if they don't exist
        channels_to_create = {
            'bot-logs': '📊 Bot Logs',
            'verification': '✅ Verification',
            'welcome': '👋 Welcome',
            'announcements': '📢 Announcements',
            'database-stats': '📈 Database Stats',
            'bot-config': '⚙️ Bot Config'
        }
        
        created_channels = []
        existing_channels = []
        
        for channel_name, display_name in channels_to_create.items():
            # Check if channel exists
            existing_channel = discord.utils.get(ctx.guild.channels, name=channel_name)
            if existing_channel:
                existing_channels.append(f"#{channel_name}")
            else:
                # Create channel
                try:
                    new_channel = await ctx.guild.create_text_channel(
                        name=channel_name,
                        topic=f"Database channel for {display_name}",
                        reason="Bot database setup"
                    )
                    created_channels.append(f"#{channel_name}")
                except discord.Forbidden:
                    await ctx.send(f"❌ Cannot create #{channel_name} - missing permissions")
                    continue
        
        # Setup database configuration
        async with aiosqlite.connect('database.db') as db:
            # Create bot_config table if not exists
            await db.execute('''CREATE TABLE IF NOT EXISTS bot_config 
                               (key TEXT PRIMARY KEY, value TEXT)''')
            
            # Set up channel configurations
            configs = [
                (f'invite_log_channel_{ctx.guild.id}', 'bot-logs'),
                (f'leave_log_channel_{ctx.guild.id}', 'bot-logs'),
                (f'verification_channel_{ctx.guild.id}', 'verification'),
                (f'welcome_channel_{ctx.guild.id}', 'welcome'),
                (f'announcements_channel_{ctx.guild.id}', 'announcements'),
                (f'database_stats_channel_{ctx.guild.id}', 'database-stats'),
                (f'bot_config_channel_{ctx.guild.id}', 'bot-config')
            ]
            
            for key, channel_name in configs:
                channel = discord.utils.get(ctx.guild.channels, name=channel_name)
                if channel:
                    await db.execute('REPLACE INTO bot_config (key, value) VALUES (?, ?)', 
                                   (key, str(channel.id)))
            
            await db.commit()
        
        # Create comprehensive embed
        embed = modern_embed(
            title="🗄️ Hybrid Database Setup Complete",
            description="Your Discord server is now configured as a hybrid database system!",
            color=discord.Color.green(),
            ctx=ctx,
            emoji="🗄️"
        )
        
        # Add fields for created and existing channels
        if created_channels:
            embed.add_field(
                name="✅ Created Channels",
                value="\n".join(created_channels),
                inline=True
            )
        
        if existing_channels:
            embed.add_field(
                name="📋 Existing Channels",
                value="\n".join(existing_channels),
                inline=True
            )
        
        # Add database info
        embed.add_field(
            name="🗄️ Database System",
            value="**SQLite + Discord Hybrid**\n"
                  "• SQLite: Persistent data storage\n"
                  "• Discord: Real-time data & caching",
            inline=False
        )
        
        embed.add_field(
            name="📊 Data Storage",
            value="**SQLite:** User levels, settings, analytics\n"
                  "**Discord:** Real-time events, member data",
            inline=False
        )
        
        embed.add_field(
            name="🔧 Next Steps",
            value="• Use `-automod_setup` for AutoMod\n"
                  "• Use `-welcome` for welcome system\n"
                  "• Use `-settings` for general config\n"
                  "• Use `-logchannellist` to verify setup",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="databasestatus", description="Show hybrid database status and data distribution.")
    @commands.has_permissions(administrator=True)
    async def databasestatus(self, ctx):
        """Show database status and data distribution"""
        
        async with aiosqlite.connect('database.db') as db:
            # Get table counts
            tables = [
                'noprefix_users', 'server_owners', 'invite_tracker', 'bot_config',
                'user_levels', 'guild_level_config', 'automod_config', 'automod_logs',
                'verification_sessions', 'server_analytics', 'user_activity',
                'channel_stats', 'command_stats', 'events', 'event_reminders',
                'game_coins', 'game_stats'
            ]
            
            table_counts = {}
            for table in tables:
                try:
                    async with db.execute(f'SELECT COUNT(*) FROM {table}') as cursor:
                        result = await cursor.fetchone()
                        table_counts[table] = result[0] if result else 0
                except:
                    table_counts[table] = 0
            
            # Get channel configurations
            configs = [
                (f'invite_log_channel_{ctx.guild.id}', 'Invite Log'),
                (f'leave_log_channel_{ctx.guild.id}', 'Leave Log'),
                (f'verification_channel_{ctx.guild.id}', 'Verification'),
                (f'welcome_channel_{ctx.guild.id}', 'Welcome'),
                (f'announcements_channel_{ctx.guild.id}', 'Announcements'),
                (f'database_stats_channel_{ctx.guild.id}', 'Database Stats'),
                (f'bot_config_channel_{ctx.guild.id}', 'Bot Config')
            ]
            
            channel_status = {}
            for key, label in configs:
                async with db.execute('SELECT value FROM bot_config WHERE key = ?', (key,)) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        channel = ctx.guild.get_channel(int(result[0]))
                        channel_status[label] = channel.mention if channel else f"<#{result[0]}>"
                    else:
                        channel_status[label] = "❌ Not set"
        
        embed = modern_embed(
            title="📊 Hybrid Database Status",
            description="Current status of SQLite + Discord hybrid database system",
            color=discord.Color.blurple(),
            ctx=ctx,
            emoji="📊"
        )
        
        # SQLite Data
        sqlite_data = "\n".join([
            f"• **{table}:** {count} records" 
            for table, count in table_counts.items() if count > 0
        ]) or "No data yet"
        
        embed.add_field(
            name="🗄️ SQLite Database",
            value=sqlite_data,
            inline=False
        )
        
        # Discord Channels
        discord_channels = "\n".join([
            f"• **{label}:** {status}"
            for label, status in channel_status.items()
        ])
        
        embed.add_field(
            name="🤖 Discord Integration",
            value=discord_channels,
            inline=False
        )
        
        # Data Distribution
        embed.add_field(
            name="📈 Data Distribution",
            value="**SQLite Stores:**\n"
                  "• User levels & XP\n"
                  "• Server settings\n"
                  "• Analytics data\n"
                  "• Game statistics\n"
                  "• Event data\n\n"
                  "**Discord Stores:**\n"
                  "• Real-time member data\n"
                  "• Channel configurations\n"
                  "• Role assignments\n"
                  "• Message history\n"
                  "• Voice activity",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Config(bot)) 