import discord
from discord.ext import commands
from discord import ui
from bot import modern_embed
import aiosqlite
import json
import asyncio
from datetime import datetime
import os

class Advanced(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.custom_commands = {}
        self.webhooks = {}
        self.backup_data = {}
        # Remove async initialization from __init__

    async def init_database(self):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS custom_commands 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                guild_id INTEGER, command_name TEXT, response TEXT,
                                created_by INTEGER, created_at TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS webhooks 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                guild_id INTEGER, channel_id INTEGER, webhook_id INTEGER,
                                name TEXT, created_at TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS backups 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                guild_id INTEGER, backup_name TEXT, backup_data TEXT,
                                created_by INTEGER, created_at TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS auto_responses 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                guild_id INTEGER, trigger TEXT, response TEXT,
                                created_by INTEGER, created_at TEXT)''')
            await db.commit()

    async def cog_load(self):
        """Async initialization when cog loads"""
        await self.init_database()

    @commands.hybrid_command(name="customcmd", description="Create a custom command.")
    async def create_custom_command(self, ctx, command_name: str, *, response: str):
        if len(command_name) < 2 or len(command_name) > 20:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Command Name",
                description="Command name must be between 2-20 characters.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Check if command already exists
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT id FROM custom_commands 
                                   WHERE guild_id = ? AND command_name = ?''',
                                (ctx.guild.id, command_name)) as cursor:
                existing = await cursor.fetchone()
            
            if existing:
                await ctx.send(embed=modern_embed(
                    title="❌ Command Exists",
                    description=f"Command `{command_name}` already exists!",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            # Create custom command
            await db.execute('''INSERT INTO custom_commands 
                               (guild_id, command_name, response, created_by, created_at)
                               VALUES (?, ?, ?, ?, ?)''',
                           (ctx.guild.id, command_name, response, ctx.author.id,
                            datetime.utcnow().isoformat()))
            await db.commit()
        
        # Store in memory for quick access
        self.custom_commands[f"{ctx.guild.id}_{command_name}"] = response
        
        await ctx.send(embed=modern_embed(
            title="✅ Custom Command Created",
            description=f"Command `{command_name}` created successfully!\n\n"
                       f"**Response:** {response}",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.hybrid_command(name="customcmds", description="List all custom commands.")
    async def list_custom_commands(self, ctx):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT command_name, response, created_at
                                   FROM custom_commands WHERE guild_id = ?''',
                                (ctx.guild.id,)) as cursor:
                commands = await cursor.fetchall()
        
        if not commands:
            await ctx.send(embed=modern_embed(
                title="📝 No Custom Commands",
                description="No custom commands have been created yet.",
                color=discord.Color.blue(),
                ctx=ctx
            ))
            return
        
        embed = modern_embed(
            title="📝 Custom Commands",
            description=f"Found {len(commands)} custom command(s):",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        for command_name, response, created_at in commands:
            created_date = datetime.fromisoformat(created_at)
            embed.add_field(
                name=f"⚡ {command_name}",
                value=f"**Response:** {response[:50]}{'...' if len(response) > 50 else ''}\n"
                      f"**Created:** {created_date.strftime('%Y-%m-%d')}",
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="delcmd", description="Delete a custom command.")
    async def delete_custom_command(self, ctx, command_name: str):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''DELETE FROM custom_commands 
                                   WHERE guild_id = ? AND command_name = ?''',
                                (ctx.guild.id, command_name)) as cursor:
                deleted = cursor.rowcount
            
            await db.commit()
        
        if deleted > 0:
            # Remove from memory
            key = f"{ctx.guild.id}_{command_name}"
            if key in self.custom_commands:
                del self.custom_commands[key]
            
            await ctx.send(embed=modern_embed(
                title="✅ Command Deleted",
                description=f"Custom command `{command_name}` has been deleted.",
                color=discord.Color.green(),
                ctx=ctx
            ))
        else:
            await ctx.send(embed=modern_embed(
                title="❌ Command Not Found",
                description=f"Custom command `{command_name}` not found.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.hybrid_command(name="webhook", description="Create a webhook for a channel.")
    async def create_webhook(self, ctx, channel: discord.TextChannel = None, name: str = "Nexus Elite"):
        if not channel:
            channel = ctx.channel
        
        if not ctx.author.guild_permissions.manage_webhooks:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Denied",
                description="You need 'Manage Webhooks' permission.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        try:
            webhook = await channel.create_webhook(name=name)
            
            # Store webhook
            async with aiosqlite.connect('database.db') as db:
                await db.execute('''INSERT INTO webhooks 
                                   (guild_id, channel_id, webhook_id, name, created_at)
                                   VALUES (?, ?, ?, ?, ?)''',
                               (ctx.guild.id, channel.id, webhook.id, name,
                                datetime.utcnow().isoformat()))
                await db.commit()
            
            await ctx.send(embed=modern_embed(
                title="✅ Webhook Created",
                description=f"Webhook `{name}` created in {channel.mention}",
                color=discord.Color.green(),
                ctx=ctx
            ))
        except discord.Forbidden:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Error",
                description="I don't have permission to create webhooks in that channel.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.hybrid_command(name="webhooks", description="List all webhooks.")
    async def list_webhooks(self, ctx):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT name, channel_id, webhook_id, created_at
                                   FROM webhooks WHERE guild_id = ?''',
                                (ctx.guild.id,)) as cursor:
                webhooks = await cursor.fetchall()
        
        if not webhooks:
            await ctx.send(embed=modern_embed(
                title="🔗 No Webhooks",
                description="No webhooks have been created yet.",
                color=discord.Color.blue(),
                ctx=ctx
            ))
            return
        
        embed = modern_embed(
            title="🔗 Webhooks",
            description=f"Found {len(webhooks)} webhook(s):",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        for name, channel_id, webhook_id, created_at in webhooks:
            channel = ctx.guild.get_channel(channel_id)
            created_date = datetime.fromisoformat(created_at)
            embed.add_field(
                name=f"🔗 {name}",
                value=f"**Channel:** {channel.mention if channel else 'Unknown'}\n"
                      f"**ID:** {webhook_id}\n"
                      f"**Created:** {created_date.strftime('%Y-%m-%d')}",
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="delwebhook", description="Delete a webhook.")
    async def delete_webhook(self, ctx, webhook_id: int):
        if not ctx.author.guild_permissions.manage_webhooks:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Denied",
                description="You need 'Manage Webhooks' permission.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Check if webhook exists in database
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT channel_id, name FROM webhooks 
                                   WHERE guild_id = ? AND webhook_id = ?''',
                                (ctx.guild.id, webhook_id)) as cursor:
                webhook_data = await cursor.fetchone()
        
        if not webhook_data:
            await ctx.send(embed=modern_embed(
                title="❌ Webhook Not Found",
                description=f"Webhook with ID {webhook_id} not found.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        channel_id, webhook_name = webhook_data
        channel = ctx.guild.get_channel(channel_id)
        
        try:
            # Get webhook from Discord
            webhook = await self.bot.fetch_webhook(webhook_id)
            
            # Delete webhook from Discord
            await webhook.delete()
            
            # Remove from database
            async with aiosqlite.connect('database.db') as db:
                await db.execute('''DELETE FROM webhooks 
                                   WHERE guild_id = ? AND webhook_id = ?''',
                               (ctx.guild.id, webhook_id))
                await db.commit()
            
            await ctx.send(embed=modern_embed(
                title="✅ Webhook Deleted",
                description=f"Webhook `{webhook_name}` has been deleted from {channel.mention if channel else 'Unknown Channel'}",
                color=discord.Color.green(),
                ctx=ctx
            ))
            
        except discord.NotFound:
            # Webhook doesn't exist on Discord, just remove from database
            async with aiosqlite.connect('database.db') as db:
                await db.execute('''DELETE FROM webhooks 
                                   WHERE guild_id = ? AND webhook_id = ?''',
                               (ctx.guild.id, webhook_id))
                await db.commit()
            
            await ctx.send(embed=modern_embed(
                title="✅ Webhook Removed",
                description=f"Webhook `{webhook_name}` was already deleted from Discord and has been removed from database.",
                color=discord.Color.green(),
                ctx=ctx
            ))
            
        except discord.Forbidden:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Error",
                description="I don't have permission to delete this webhook.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.hybrid_command(name="backup", description="Create a server backup.")
    async def create_backup(self, ctx, backup_name: str):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Denied",
                description="You need Administrator permission to create backups.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Create backup data
        backup_data = {
            "guild_name": ctx.guild.name,
            "guild_id": ctx.guild.id,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": ctx.author.id,
            "channels": [],
            "roles": [],
            "settings": {}
        }
        
        # Backup channels
        for channel in ctx.guild.channels:
            channel_data = {
                "name": channel.name,
                "type": str(channel.type),
                "position": channel.position,
                "permissions": {}
            }
            
            if hasattr(channel, 'topic'):
                channel_data["topic"] = channel.topic
            
            if hasattr(channel, 'slowmode_delay'):
                channel_data["slowmode"] = channel.slowmode_delay
            
            backup_data["channels"].append(channel_data)
        
        # Backup roles
        for role in ctx.guild.roles:
            if role.name != "@everyone":
                role_data = {
                    "name": role.name,
                    "color": role.color.value,
                    "hoist": role.hoist,
                    "mentionable": role.mentionable,
                    "permissions": role.permissions.value
                }
                backup_data["roles"].append(role_data)
        
        # Store backup
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT INTO backups 
                               (guild_id, backup_name, backup_data, created_by, created_at)
                               VALUES (?, ?, ?, ?, ?)''',
                           (ctx.guild.id, backup_name, json.dumps(backup_data),
                            ctx.author.id, datetime.utcnow().isoformat()))
            await db.commit()
        
        await ctx.send(embed=modern_embed(
            title="✅ Backup Created",
            description=f"Backup `{backup_name}` created successfully!\n\n"
                       f"**Channels:** {len(backup_data['channels'])}\n"
                       f"**Roles:** {len(backup_data['roles'])}",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.hybrid_command(name="backups", description="List all backups.")
    async def list_backups(self, ctx):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT backup_name, created_at
                                   FROM backups WHERE guild_id = ?''',
                                (ctx.guild.id,)) as cursor:
                backups = await cursor.fetchall()
        
        if not backups:
            await ctx.send(embed=modern_embed(
                title="💾 No Backups",
                description="No backups have been created yet.",
                color=discord.Color.blue(),
                ctx=ctx
            ))
            return
        
        embed = modern_embed(
            title="💾 Server Backups",
            description=f"Found {len(backups)} backup(s):",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        for backup_name, created_at in backups:
            created_date = datetime.fromisoformat(created_at)
            embed.add_field(
                name=f"💾 {backup_name}",
                value=f"**Created:** {created_date.strftime('%Y-%m-%d %H:%M')}",
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="autorole", description="Set up automatic role assignment.")
    async def setup_autorole(self, ctx, role: discord.Role, trigger: str = "join"):
        if not ctx.author.guild_permissions.manage_roles:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Denied",
                description="You need 'Manage Roles' permission.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Store autorole setting
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT OR REPLACE INTO auto_responses 
                               (guild_id, trigger, response, created_by, created_at)
                               VALUES (?, ?, ?, ?, ?)''',
                           (ctx.guild.id, f"autorole_{trigger}", str(role.id),
                            ctx.author.id, datetime.utcnow().isoformat()))
            await db.commit()
        
        await ctx.send(embed=modern_embed(
            title="✅ Auto-Role Set",
            description=f"Role {role.mention} will be automatically assigned on {trigger}.",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.hybrid_command(name="autoresponse", description="Set up automatic responses.")
    async def setup_autoresponse(self, ctx, trigger: str, *, response: str):
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Denied",
                description="You need 'Manage Messages' permission.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Store autoresponse
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT INTO auto_responses 
                               (guild_id, trigger, response, created_by, created_at)
                               VALUES (?, ?, ?, ?, ?)''',
                           (ctx.guild.id, trigger, response, ctx.author.id,
                            datetime.utcnow().isoformat()))
            await db.commit()
        
        await ctx.send(embed=modern_embed(
            title="✅ Auto-Response Set",
            description=f"Auto-response for `{trigger}` has been set.",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.hybrid_command(name="autoresponses", description="List all auto-responses.")
    async def list_autoresponses(self, ctx):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT trigger, response, created_at
                                   FROM auto_responses WHERE guild_id = ?''',
                                (ctx.guild.id,)) as cursor:
                responses = await cursor.fetchall()
        
        if not responses:
            await ctx.send(embed=modern_embed(
                title="🤖 No Auto-Responses",
                description="No auto-responses have been set up yet.",
                color=discord.Color.blue(),
                ctx=ctx
            ))
            return
        
        embed = modern_embed(
            title="🤖 Auto-Responses",
            description=f"Found {len(responses)} auto-response(s):",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        for trigger, response, created_at in responses:
            created_date = datetime.fromisoformat(created_at)
            embed.add_field(
                name=f"🤖 {trigger}",
                value=f"**Response:** {response[:50]}{'...' if len(response) > 50 else ''}\n"
                      f"**Created:** {created_date.strftime('%Y-%m-%d')}",
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="serverinfo", description="Get detailed server information.")
    async def detailed_server_info(self, ctx):
        guild = ctx.guild
        
        # Get detailed stats
        total_members = guild.member_count
        online_members = len([m for m in guild.members if m.status != discord.Status.offline])
        bot_count = len([m for m in guild.members if m.bot])
        human_count = total_members - bot_count
        
        # Channel counts
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        
        # Role counts
        total_roles = len(guild.roles)
        
        # Boost info
        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count
        
        embed = modern_embed(
            title=f"📊 {guild.name} - Detailed Info",
            description="Comprehensive server statistics",
            color=guild.owner.color if guild.owner.color != discord.Color.default() else discord.Color.blurple(),
            ctx=ctx,
            thumbnail=guild.icon.url if guild.icon else None
        )
        
        embed.add_field(
            name="👥 Members",
            value=f"**Total:** {total_members:,}\n"
                  f"**Online:** {online_members:,}\n"
                  f"**Humans:** {human_count:,}\n"
                  f"**Bots:** {bot_count:,}",
            inline=True
        )
        
        embed.add_field(
            name="📺 Channels",
            value=f"**Text:** {text_channels}\n"
                  f"**Voice:** {voice_channels}\n"
                  f"**Categories:** {categories}\n"
                  f"**Total:** {text_channels + voice_channels + categories}",
            inline=True
        )
        
        embed.add_field(
            name="🎭 Roles & Boosts",
            value=f"**Roles:** {total_roles}\n"
                  f"**Boost Level:** {boost_level}\n"
                  f"**Boosts:** {boost_count}\n"
                  f"**Created:** {guild.created_at.strftime('%Y-%m-%d')}",
            inline=True
        )
        
        embed.add_field(
            name="🔒 Verification",
            value=f"**Level:** {guild.verification_level.name}\n"
                  f"**2FA:** {'Required' if guild.mfa_level == discord.MFALevel.require_2fa else 'Optional'}\n"
                  f"**Explicit:** {'Yes' if guild.explicit_content_filter else 'No'}",
            inline=True
        )
        
        embed.add_field(
            name="🎨 Features",
            value=f"**Animated Icon:** {'Yes' if guild.icon.is_animated() else 'No'}\n"
                  f"**Banner:** {'Yes' if guild.banner else 'No'}\n"
                  f"**Splash:** {'Yes' if guild.splash else 'No'}\n"
                  f"**Vanity URL:** {'Yes' if guild.vanity_url_code else 'No'}",
            inline=True
        )
        
        embed.add_field(
            name="📈 Activity",
            value=f"**Owner:** {guild.owner.mention}\n"
                  f"**Chunked:** {'Yes' if guild.chunked else 'No'}\n"
                  f"**Large:** {'Yes' if guild.large else 'No'}\n"
                  f"**Widget:** {'Enabled' if guild.widget_enabled else 'Disabled'}",
            inline=True
        )
        
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        # Check for custom commands
        if message.content.startswith('!'):
            command_name = message.content[1:].split()[0]
            key = f"{message.guild.id}_{command_name}"
            
            if key in self.custom_commands:
                response = self.custom_commands[key]
                await message.channel.send(response)
                return
        
        # Check for auto-responses
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT response FROM auto_responses 
                                   WHERE guild_id = ? AND trigger = ?''',
                                (message.guild.id, message.content.lower())) as cursor:
                auto_response = await cursor.fetchone()
            
            if auto_response:
                await message.channel.send(auto_response[0])

async def setup(bot):
    await bot.add_cog(Advanced(bot)) 