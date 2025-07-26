# Import audioop compatibility first (for Python 3.13+)
import audioop_compat

import discord
from discord.ext import commands
import json
import aiosqlite
import os
from datetime import datetime
import asyncio
from datetime import datetime, timedelta
import pytz
from discord import ui
from cogs.membercount import update_membercount_channel
from dotenv import load_dotenv
from keep_alive import keep_alive

# Load environment variables
load_dotenv()

IST = pytz.timezone('Asia/Kolkata')
GUILD_ID = 1398674507992137880  # Your Discord server ID

# Load from environment variables (for production deployment)
TOKEN = os.getenv('TOKEN')
OWNER_ID = os.getenv('OWNER_ID')

# Only fallback to config.json if environment variables are not set (for local development)
if not TOKEN or not OWNER_ID:
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        TOKEN = config.get('token')
        OWNER_ID = config.get('owner_id')
        
        # Check if token is still placeholder
        if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("❌ Error: Bot token not found!")
            print("📝 Please set your bot token in one of these ways:")
            print("   1. Environment variable: TOKEN=your_token_here")
            print("   2. config.json file: Replace 'YOUR_BOT_TOKEN_HERE' with your actual token")
            exit(1)
            
    except FileNotFoundError:
        print("❌ Error: config.json not found and environment variables not set")
        print("📝 Please create config.json or set TOKEN environment variable")
        exit(1)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        exit(1)

# Convert OWNER_ID to int
try:
    OWNER_ID = int(OWNER_ID)
except ValueError:
    print("❌ Error: OWNER_ID must be a valid number")
    exit(1)
BOT_ADMINS = [OWNER_ID, 697811836040511498]
PREFIX = '-'

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.messages = True
intents.message_content = True

# Helper: Check if user is in no-prefix list
async def is_noprefix(user_id):
    if user_id in BOT_ADMINS:
        return True
    async with aiosqlite.connect('database.db') as db:
        async with db.execute('SELECT 1 FROM noprefix_users WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone() is not None

# Override get_prefix to allow no-prefix for owner/whitelisted users
async def get_prefix(bot, message):
    if message.author.id == OWNER_ID or await is_noprefix(message.author.id):
        return commands.when_mentioned_or(PREFIX, '')(bot, message)
    return commands.when_mentioned_or(PREFIX)(bot, message)

bot = commands.Bot(command_prefix=get_prefix, intents=intents, owner_id=OWNER_ID)
bot.remove_command('help')

# Invite tracker cache
invite_cache = {}

@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.watching, name=f"{PREFIX}help | Nexus Elite"))
    # Fast guild sync for instant slash command updates
    try:
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f'Slash commands synced to guild {GUILD_ID}')
    except Exception as e:
        print(f'Guild sync failed: {e}')
    await bot.tree.sync()
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    # Initialize database
    async with aiosqlite.connect('database.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS noprefix_users (user_id INTEGER PRIMARY KEY)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS invite_tracker (user_id INTEGER, guild_id INTEGER, invites INTEGER, PRIMARY KEY (user_id, guild_id))''')
        await db.commit()
    print('Database initialized.')
    print('Registered commands:')
    for command in bot.commands:
        print(f'- {command.qualified_name}')
    # Cache invites for all guilds
    for guild in bot.guilds:
        try:
            invite_cache[guild.id] = await guild.invites()
        except Exception:
            invite_cache[guild.id] = []

@bot.event
async def on_invite_create(invite):
    # Update cache when a new invite is created
    try:
        invite_cache[invite.guild.id] = await invite.guild.invites()
    except Exception:
        pass

@bot.event
async def on_invite_delete(invite):
    # Update cache when an invite is deleted
    try:
        invite_cache[invite.guild.id] = await invite.guild.invites()
    except Exception:
        pass

# Helper to send confirmation as a styled embed DM only
async def send_confirmation(ctx, message, title='Command Executed', color=discord.Color.green()):
    embed = discord.Embed(title=title, description=message, color=color)
    try:
        await ctx.author.send(embed=embed)
    except Exception:
        pass  # User DMs closed

# Helper for styled embeds

def styled_embed(title, description, color, ctx=None, emoji=None):
    embed = discord.Embed(
        title=f"{emoji + ' ' if emoji else ''}{title}",
        description=description,
        color=color,
        timestamp=datetime.utcnow().astimezone(IST)
    )
    if ctx:
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    return embed

def modern_embed(
    title: str = None,
    description: str = None,
    color: discord.Color = discord.Color.blurple(),
    ctx=None,
    emoji: str = None,
    thumbnail: str = None,
    footer: str = None,
    timestamp=None
):
    embed = discord.Embed(
        title=(f"{emoji} {title}" if emoji and title else title or None),
        description=description,
        color=color,
        timestamp=timestamp or discord.utils.utcnow()
    )
    if ctx and hasattr(ctx, 'author') and ctx.author.avatar:
        embed.set_footer(
            text=footer or f"Requested by {ctx.author}",
            icon_url=ctx.author.avatar.url
        )
    elif footer:
        embed.set_footer(text=footer)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    return embed

# DM auto-reply for bot (more professional)
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    # Respond with self-info ONLY if the message is exactly a mention of the bot
    if message.guild and len(message.mentions) == 1 and bot.user in message.mentions and message.content.strip() in [f'<@{bot.user.id}>', f'<@!{bot.user.id}>']:
        invite_url = discord.utils.oauth_url(
            bot.user.id,
            permissions=discord.Permissions(administrator=True)
        )
        support_url = "https://discord.gg/xPGJCWpMbM"  # Official support server link
        prefix = PREFIX
        total_commands = len(bot.commands)
        help_cmd = f"{prefix}help"
        # Only show features/modules the bot actually supports
        features = (
            "🛠️ Utility\n"
            "💬 General\n"
            "🤖 Automoderation\n"
            "🔨 Moderation"
        )
        modules = (
            "🎉 Giveaway\n"
            "👋 Welcome\n"
            "📋 Logging"
        )
        # Use the bot's Discord profile banner as the main image if available
        banner_url = bot.user.banner.url if hasattr(bot.user, 'banner') and bot.user.banner else None
        embed = discord.Embed(
            title=f"NEXUS ELITE",
            description=(
                f"**Server Prefix:** `{prefix}`\n"
                f"**Total Commands:** `{total_commands}`\n"
                f"Type `{help_cmd}` to get started\n\n"
                f"[Invite]({invite_url}) | [Support]({support_url})"
            ),
            color=discord.Color.from_rgb(34, 139, 34)
        )
        embed.add_field(name="Developer", value=f"<@{OWNER_ID}>", inline=False)
        if bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        embed.add_field(name="★ My Features", value=features, inline=True)
        embed.add_field(name="★ My Modules", value=modules, inline=True)
        if banner_url:
            embed.set_image(url=banner_url)
        embed.set_footer(text=f"Requested by: {message.author}")
        # Modern UI buttons for Invite and Support
        class InfoView(discord.ui.View):
            def __init__(self):
                super().__init__()
                self.add_item(discord.ui.Button(label="Invite", url=invite_url, style=discord.ButtonStyle.link))
                self.add_item(discord.ui.Button(label="Support", url=support_url, style=discord.ButtonStyle.link))
        view = InfoView()
        await message.channel.send(embed=embed, view=view, reference=message)
        return
    # DM auto-reply
    if isinstance(message.channel, discord.DMChannel):
        try:
            embed = discord.Embed(
                title="Need Help?",
                description=(
                    "Thank you for reaching out to **Nexus Elite Bot**!\n\n"
                    "For support, please contact a server admin or join our official server.\n\n"
                    f"**Admin Contact:** <@{OWNER_ID}>\n"
                    f"**Official Server:** [Join Here](https://discord.gg/xPGJCWpMbM)"
                ),
                color=discord.Color.blurple()
            )
            embed.set_footer(text="Nexus Elite Bot | Professional Support")
            await message.channel.send(embed=embed)
        except Exception:
            pass
        return
    # React with emoji if owner is mentioned
    if any(user.id == OWNER_ID for user in message.mentions):
        try:
            emoji = bot.get_emoji(1397943669666873344)
            if emoji:
                await message.add_reaction(emoji)
        except Exception:
            pass
    # React with 👀 if owner is mentioned
    if any(user.id == OWNER_ID for user in message.mentions):
        try:
            await message.add_reaction('👀')
        except Exception:
            pass
    # React with 🫣 if user 1201173322843566140 is mentioned
    if any(user.id == 1201173322843566140 for user in message.mentions):
        try:
            await message.add_reaction('🫣')
        except Exception:
            pass
    # React with ⚔️ if user 697811836040511498 is mentioned
    if any(user.id == 697811836040511498 for user in message.mentions):
        try:
            await message.add_reaction('⚡')
        except Exception:
            pass
    # Load registration channel
    
    # Process commands
    await bot.process_commands(message)
    async with aiosqlite.connect('database.db') as db:
        async with db.execute('SELECT value FROM bot_config WHERE key = ?', ('registration_channel',)) as cursor:
            reg_row = await cursor.fetchone()
            if not reg_row:
                await bot.process_commands(message)
                return  # Registration channel not set
            registration_channel_id = int(reg_row[0])
    if message.channel.id != registration_channel_id:
        await bot.process_commands(message)
        return  # Only allow registration in the set channel
    # Load tag check player count
    async with aiosqlite.connect('database.db') as db:
        async with db.execute('SELECT player_count FROM scrim_config WHERE id = 1') as cursor:
            row = await cursor.fetchone()
            if not row:
                await bot.process_commands(message)
                return  # Tag check is disabled, do nothing
            player_count = row[0]
    # Simplified format: first word/line is team name, rest are tags
    content = message.content.strip()
    if not content:
        await message.add_reaction('❌')
        await bot.process_commands(message)
        return
    lines = content.split('\n')
    if len(lines) == 1:
        parts = lines[0].split()
        if len(parts) < 1 + player_count:
            await message.add_reaction('❌')
            await bot.process_commands(message)
            return
        team_name = parts[0]
        tags = parts[1:]
    else:
        team_name = lines[0].strip()
        tags = []
        for line in lines[1:]:
            tags.extend(line.strip().split())
    tags = [tag for tag in tags if tag]
    # Ensure each tag is a single word (no spaces)
    if any(' ' in tag for tag in tags):
        await message.add_reaction('❌')
        await bot.process_commands(message)
        return
    if len(tags) != player_count:
        await message.add_reaction('❌')
        await bot.process_commands(message)
        return
    # Check that each tag is a valid member and not already registered
    member_ids = set()
    for tag in tags:
        user_id = None
        if tag.startswith('<@') and tag.endswith('>'):
            # Mention format
            tag_id = tag.replace('<@!', '').replace('<@', '').replace('>', '')
            if tag_id.isdigit():
                user_id = int(tag_id)
        elif tag.isdigit():
            user_id = int(tag)
        else:
            # Try username#discriminator
            if '#' in tag:
                name, discrim = tag.rsplit('#', 1)
                member = discord.utils.get(message.guild.members, name=name, discriminator=discrim)
                if member:
                    user_id = member.id
        if user_id is None:
            await message.add_reaction('❌')
            await bot.process_commands(message)
            return
        member = message.guild.get_member(user_id)
        if not member:
            await message.add_reaction('❌')
            await bot.process_commands(message)
            return
        member_ids.add(user_id)
    if len(member_ids) != player_count:
        await message.add_reaction('❌')
        await bot.process_commands(message)
        return
    # Check for duplicate registrations in DB
    async with aiosqlite.connect('database.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS scrim_tags (id INTEGER PRIMARY KEY AUTOINCREMENT, team_name TEXT, tag TEXT, user_id INTEGER)''')
        for user_id in member_ids:
            async with db.execute('SELECT team_name FROM scrim_tags WHERE tag = ?', (str(user_id),)) as cursor:
                if await cursor.fetchone():
                    await message.add_reaction('❌')
                    await bot.process_commands(message)
                    return
        for user_id in member_ids:
            await db.execute('INSERT INTO scrim_tags (team_name, tag, user_id) VALUES (?, ?, ?)', (team_name, str(user_id), message.author.id))
        await db.commit()
    await message.add_reaction('✅')
    # After successful registration:
    async with aiosqlite.connect('database.db') as db:
        async with db.execute('SELECT value FROM bot_config WHERE key = ?', ('show_channel',)) as cursor:
            show_row = await cursor.fetchone()
    if show_row:
        show_channel_mention = f'<#{show_row[0]}>'
        await message.channel.send(embed=discord.Embed(title='Registration Successful', description=f'Your team has been registered!\nView all registered teams in {show_channel_mention}.', color=discord.Color.green()), reference=message)
    else:
        await message.channel.send(embed=discord.Embed(title='Registration Successful', description='Your team has been registered!', color=discord.Color.green()), reference=message)
    await bot.process_commands(message)

async def is_server_owner(ctx):
    # True if server owner or admin or in custom owner list
    if ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator:
        return True
    async with aiosqlite.connect('database.db') as db:
        async with db.execute('SELECT user_id FROM server_owners WHERE guild_id = ? AND user_id = ?', (ctx.guild.id, ctx.author.id)) as cursor:
            return await cursor.fetchone() is not None

def is_owner(ctx):
    return ctx.author.id in BOT_ADMINS

def is_guild_owner(ctx):
    return ctx.author.id == ctx.guild.owner_id or ctx.author.id in BOT_ADMINS

def is_admin(ctx):
    return ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator or ctx.author.id in BOT_ADMINS

@bot.command()
@commands.check(is_guild_owner)
async def addowner(ctx, user: discord.User):
    """Add a user as a server-level bot owner (server owner or bot owner only)."""
    async with aiosqlite.connect('database.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS server_owners (guild_id INTEGER, user_id INTEGER, PRIMARY KEY (guild_id, user_id))''')
        await db.execute('INSERT OR IGNORE INTO server_owners (guild_id, user_id) VALUES (?, ?)', (ctx.guild.id, user.id))
        await db.commit()
    embed = discord.Embed(
        title="Server Owner Added",
        description=f"{user.mention} is now a server-level bot owner and can use all admin/server owner commands in this server.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, reference=ctx.message, mention_author=True)

# Update is_admin to use is_server_owner

@bot.command()
@commands.check(is_admin)
async def addnoprefix_timed(ctx, user: discord.User):
    """Add a user to the no-prefix list for a specified duration (supports months and lifetime)."""
    await ctx.send("How long should no-prefix be enabled for this user? (e.g. 1h, 30m, 2d, 2mo, lifetime)")
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    try:
        msg = await bot.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        await ctx.send("❌ Timed out. Command cancelled.")
        return
    duration_str = msg.content.strip().lower()
    if duration_str in ["lifetime", "permanent"]:
        async with aiosqlite.connect('database.db') as db:
            await db.execute('INSERT OR IGNORE INTO noprefix_users (user_id) VALUES (?)', (user.id,))
            await db.commit()
        await ctx.send(f'Added {user.mention} to no-prefix list for lifetime.')
        return
    def parse_duration(duration_str):
        duration_str = duration_str.lower().strip()
        time_map = {'h': 3600, 'm': 60, 'd': 86400, 'mo': 2592000}  # 30 days per month
        seconds = 0
        num = ''
        i = 0
        while i < len(duration_str):
            if duration_str[i].isdigit():
                num += duration_str[i]
            else:
                # Check for 'mo' (months)
                if duration_str[i:i+2] == 'mo' and num:
                    seconds += int(num) * time_map['mo']
                    num = ''
                    i += 1  # skip extra char
                elif duration_str[i] in time_map and num:
                    seconds += int(num) * time_map[duration_str[i]]
                    num = ''
            i += 1
        return seconds
    seconds = parse_duration(duration_str)
    if seconds == 0:
        await ctx.send("❌ Invalid duration format. Use e.g. 1h, 30m, 2d, 2mo, lifetime.")
        return
    async with aiosqlite.connect('database.db') as db:
        await db.execute('INSERT OR IGNORE INTO noprefix_users (user_id) VALUES (?)', (user.id,))
        await db.commit()
    await ctx.send(f'Added {user.mention} to no-prefix list for {duration_str} ({seconds//60} minutes).')
    await asyncio.sleep(seconds)
    async with aiosqlite.connect('database.db') as db:
        await db.execute('DELETE FROM noprefix_users WHERE user_id = ?', (user.id,))
        await db.commit()
    try:
        await ctx.send(f'Removed {user.mention} from no-prefix list after {duration_str}.')
    except Exception:
        pass

@bot.command(name='np')
@commands.check(is_owner)
async def np(ctx, user: discord.User):
    """Give no-prefix access to a user (owner only, can be used without prefix)."""
    async with aiosqlite.connect('database.db') as db:
        await db.execute('INSERT OR IGNORE INTO noprefix_users (user_id) VALUES (?)', (user.id,))
        await db.commit()
    embed = discord.Embed(
        title="No-Prefix Granted",
        description=f"{user.mention} can now use commands without a prefix.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='removenp')
@commands.check(is_owner)
async def removenp(ctx, user: discord.User):
    """Remove no-prefix access from a user (owner only, can be used without prefix)."""
    async with aiosqlite.connect('database.db') as db:
        await db.execute('DELETE FROM noprefix_users WHERE user_id = ?', (user.id,))
        await db.commit()
    embed = discord.Embed(
        title="No-Prefix Revoked",
        description=f"{user.mention} can no longer use commands without a prefix.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

@bot.command(name='listnp')
@commands.check(is_owner)
async def listnp(ctx):
    """List all users with no-prefix access (owner only, can be used without prefix)."""
    async with aiosqlite.connect('database.db') as db:
        async with db.execute('SELECT user_id FROM noprefix_users') as cursor:
            rows = await cursor.fetchall()
    if not rows:
        await ctx.send('No users have no-prefix access.')
        return
    user_mentions = []
    for row in rows:
        user = bot.get_user(row[0])
        if user:
            user_mentions.append(user.mention)
        else:
            user_mentions.append(f'`{row[0]}`')
    embed = discord.Embed(
        title="No-Prefix Users",
        description='\n'.join(user_mentions),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.check(is_guild_owner)
async def removeowner(ctx, user: discord.User):
    """Remove a user as a server-level bot owner (server owner or bot owner only)."""
    async with aiosqlite.connect('database.db') as db:
        await db.execute('DELETE FROM server_owners WHERE guild_id = ? AND user_id = ?', (ctx.guild.id, user.id))
        await db.commit()
    embed = discord.Embed(
        title="Server Owner Removed",
        description=f"{user.mention} is no longer a server-level bot owner in this server.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed, reference=ctx.message, mention_author=True)

@bot.command()
@commands.check(is_guild_owner)
async def listowners(ctx):
    """List all server-level bot owners for this server (server owner or bot owner only)."""
    async with aiosqlite.connect('database.db') as db:
        async with db.execute('SELECT user_id FROM server_owners WHERE guild_id = ?', (ctx.guild.id,)) as cursor:
            rows = await cursor.fetchall()
    if not rows:
        await ctx.send('No server-level bot owners set for this server.')
        return
    user_mentions = []
    for row in rows:
        user = ctx.guild.get_member(row[0]) or ctx.guild.get_member_named(str(row[0]))
        if user:
            user_mentions.append(user.mention)
        else:
            user_mentions.append(f'`{row[0]}`')
    embed = discord.Embed(
        title="Server-Level Bot Owners",
        description='\n'.join(user_mentions),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, reference=ctx.message, mention_author=True)

@commands.hybrid_command(description="Sync all slash commands globally.")
@commands.check(is_owner)
async def sync(ctx):
    await ctx.bot.tree.sync()
    await ctx.send("Synced all slash commands globally.")

bot.add_command(sync)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        # Do not reply anything for unknown commands
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: `{error.param.name}`. Please check the command usage.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have permission to use this command.")
    else:
        await ctx.send(f"❌ An error occurred: {error}")

class BackButton(ui.Button):
    def __init__(self, bot, ctx, categories):
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, emoji="⬅️")
        self.bot = bot
        self.ctx = ctx
        self.categories = categories

    async def callback(self, interaction: discord.Interaction):
        # Re-show the main help menu with category select
        embed = discord.Embed(
            title="✨ Nexus Elite Bot Help",
            description=(
                'Welcome to **Nexus Elite Bot**!\n\n'
                '• **Prefix:** `-`\n'
                '• **Slash:** `/`\n'
                '• **Navigation:** Select a category below to view its commands.'
            ),
            color=discord.Color.purple(),
            timestamp=datetime.utcnow().astimezone(IST)
        )
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.set_footer(
            text=f"Nexus Elite Bot • Requested by {self.ctx.author}",
            icon_url=self.ctx.author.avatar.url if self.ctx.author.avatar else None
        )
        await interaction.response.edit_message(embed=embed, view=HelpCategoryView(self.bot, self.ctx, self.categories))

class CategoryCommandView(ui.View):
    def __init__(self, bot, ctx, categories):
        super().__init__(timeout=60)
        self.add_item(BackButton(bot, ctx, categories))

class HelpCategorySelect(ui.Select):
    def __init__(self, bot, ctx, categories):
        options = [discord.SelectOption(label=cat, value=cat) for cat in categories]
        super().__init__(placeholder="Choose a command category...", min_values=1, max_values=1, options=options)
        self.bot = bot
        self.ctx = ctx
        self.categories = categories

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        commands_in_cat = [cmd for cmd in self.bot.commands if (cmd.cog_name or "Other") == category and not cmd.hidden]
        
        # Create clean command list without descriptions
        command_list = []
        for command in commands_in_cat:
            command_list.append(f"`{command.qualified_name}`")
        
        command_text = ", ".join(command_list)
        
        embed = discord.Embed(
            title=f"✨ {category} Commands",
            description=f"**{category}:**\n{command_text}",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow().astimezone(IST)
        )
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.set_footer(
            text=f"Nexus Elite Bot • Requested by {self.ctx.author}",
            icon_url=self.ctx.author.avatar.url if self.ctx.author.avatar else None
        )
        await interaction.response.edit_message(embed=embed, view=CategoryCommandView(self.bot, self.ctx, self.categories))

class HelpCategoryView(ui.View):
    def __init__(self, bot, ctx, categories):
        super().__init__(timeout=60)
        self.add_item(HelpCategorySelect(bot, ctx, categories))

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='help')
    async def help_command(self, ctx):
        # Define your categories (could be dynamic or static)
        categories = sorted(set(cmd.cog_name or "Other" for cmd in self.bot.commands if not cmd.hidden))
        
        # Create category list
        category_list = []
        for category in categories:
            category_list.append(f"`{category}`")
        
        category_text = ", ".join(category_list)
        
        embed = discord.Embed(
            title="✨ Nexus Elite Bot Help",
            description=(
                'Welcome to **Nexus Elite Bot**!\n\n'
                '• **Prefix:** `-`\n'
                '• **Slash:** `/`\n'
                f'• **Developer:** <@{OWNER_ID}>\n'
                '• **Available Categories:**\n'
                f'{category_text}\n\n'
                '• **Navigation:** Select a category below to view its commands.'
            ),
            color=discord.Color.purple(),
            timestamp=datetime.utcnow().astimezone(IST)
        )
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.set_footer(
            text=f"Nexus Elite Bot • Requested by {ctx.author}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        await ctx.send(embed=embed, view=HelpCategoryView(self.bot, ctx, categories))

async def setup_help(bot):
    await bot.add_cog(HelpCog(bot))

# Auto-load all cogs from cogs directory
async def load_cogs():
    await bot.load_extension('cogs.utility')
    await bot.load_extension('cogs.invites')
    await bot.load_extension('cogs.config')
    await bot.load_extension('cogs.voice')
    await bot.load_extension('cogs.moderation')
    await bot.load_extension('cogs.info')
    await bot.load_extension('cogs.welcome')
    await bot.load_extension('cogs.logging')
    await bot.load_extension('cogs.economy')
    await bot.load_extension('cogs.fun')
    await bot.load_extension('cogs.game')
    await bot.load_extension('cogs.settings')
    await bot.load_extension('cogs.leveling')
    await bot.load_extension('cogs.automod')
    await bot.load_extension('cogs.analytics')
    await bot.load_extension('cogs.events')
    await bot.load_extension('cogs.ai')
    await bot.load_extension('cogs.social')
    await bot.load_extension('cogs.weather')
    await bot.load_extension('cogs.advanced')
    await bot.load_extension('cogs.entertainment')
    await bot.load_extension('cogs.security')
    await bot.load_extension('cogs.productivity')
    await bot.load_extension('cogs.automation')
    await bot.load_extension('cogs.announce')
    await bot.load_extension('cogs.giveaway')
    # Add more cogs here if needed
    await setup_help(bot)

if __name__ == "__main__":
    import asyncio
    # Start keep-alive server for Render
    keep_alive()
    print("🚀 Keep-alive server started!")
    
    # Load cogs and run bot
    asyncio.run(load_cogs())
    print("✅ All cogs loaded successfully!")
    print("🤖 Starting Nexus Elite Bot...")
    bot.run(TOKEN)

@bot.event
async def on_member_join(member):
    await update_membercount_channel(member.guild)
    # Invite tracker logic
    try:
        old_invites = invite_cache.get(member.guild.id, [])
        new_invites = await member.guild.invites()
        used = None
        for old in old_invites:
            match = next((n for n in new_invites if n.code == old.code), None)
            if match and match.uses > old.uses:
                used = match
                break
        inviter = None
        invite_count = None
        if used:
            inviter = used.inviter
            async with aiosqlite.connect('database.db') as db:
                row = await db.execute('SELECT invites FROM invite_tracker WHERE user_id = ? AND guild_id = ?', (inviter.id, member.guild.id))
                result = await row.fetchone()
                invite_count = result[0] if result else 1
        invite_cache[member.guild.id] = new_invites
        # Announce in invite log channel if set
        async with aiosqlite.connect('database.db') as db:
            row = await db.execute('SELECT value FROM bot_config WHERE key = ?', (f'invite_log_channel_{member.guild.id}',))
            result = await row.fetchone()
        if result:
            channel = member.guild.get_channel(int(result[0]))
            if channel:
                if inviter:
                    await channel.send(f"{member.mention} has joined {member.guild.name}, invited by {inviter.mention}, who now has {invite_count} invites.")
                else:
                    await channel.send(f"{member.mention} has joined {member.guild.name}, but I don't know who invited them.")
    except Exception:
        pass

@bot.event
async def on_member_remove(member):
    await update_membercount_channel(member.guild)
    # Find inviter for leave log
    inviter = None
    async with aiosqlite.connect('database.db') as db:
        row = await db.execute('SELECT value FROM bot_config WHERE key = ?', (f'leave_log_channel_{member.guild.id}',))
        result = await row.fetchone()
        inviter_row = await db.execute('SELECT user_id FROM invite_tracker WHERE guild_id = ? AND user_id IN (SELECT user_id FROM invite_tracker WHERE guild_id = ?)', (member.guild.id, member.guild.id))
        inviter_result = await inviter_row.fetchone()
    if result:
        channel = member.guild.get_channel(int(result[0]))
        if channel:
            # Try to find the inviter by checking the invite_tracker table for the member's inviter
            # (This is a best-effort guess, as Discord does not provide a direct way to track who invited a user after they leave)
            # We'll use the last known inviter if available
            inviter_id = None
            async with aiosqlite.connect('database.db') as db:
                row = await db.execute('SELECT user_id FROM invite_tracker WHERE guild_id = ? ORDER BY invites DESC LIMIT 1', (member.guild.id,))
                inviter_row = await row.fetchone()
                if inviter_row:
                    inviter_id = inviter_row[0]
            inviter_mention = f'<@{inviter_id}>' if inviter_id else 'Unknown'
            await channel.send(f'**{member.display_name}** left the server, they were invited by {inviter_mention}.') 
