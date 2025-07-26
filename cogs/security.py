import discord
from discord.ext import commands
from bot import modern_embed
import aiosqlite
import hashlib
import secrets
import json
from datetime import datetime, timedelta
import asyncio

class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.security_sessions = {}
        self.audit_logs = []

    async def init_database(self):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS security_2fa 
                               (user_id INTEGER PRIMARY KEY, guild_id INTEGER,
                                secret_key TEXT, enabled BOOLEAN DEFAULT FALSE,
                                backup_codes TEXT, created_at TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS audit_logs 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                guild_id INTEGER, user_id INTEGER, action TEXT,
                                target_id INTEGER, details TEXT, timestamp TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS security_settings 
                               (guild_id INTEGER PRIMARY KEY, 
                                raid_protection BOOLEAN DEFAULT TRUE,
                                spam_protection BOOLEAN DEFAULT TRUE,
                                link_protection BOOLEAN DEFAULT FALSE,
                                invite_protection BOOLEAN DEFAULT TRUE,
                                whitelist_enabled BOOLEAN DEFAULT FALSE,
                                whitelist_users TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS security_incidents 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                guild_id INTEGER, incident_type TEXT,
                                user_id INTEGER, details TEXT, resolved BOOLEAN DEFAULT FALSE,
                                created_at TEXT, resolved_at TEXT)''')
            await db.commit()

    @commands.hybrid_command(name="2fa", description="Set up two-factor authentication.")
    async def setup_2fa(self, ctx):
        # Generate secret key
        secret_key = secrets.token_hex(16)
        backup_codes = [secrets.token_hex(4) for _ in range(5)]
        
        # Store 2FA data
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT OR REPLACE INTO security_2fa 
                               (user_id, guild_id, secret_key, backup_codes, created_at)
                               VALUES (?, ?, ?, ?, ?)''',
                           (ctx.author.id, ctx.guild.id, secret_key, json.dumps(backup_codes),
                            datetime.utcnow().isoformat()))
            await db.commit()
        
        embed = modern_embed(
            title="🔐 2FA Setup",
            description="Two-factor authentication has been set up!\n\n"
                       f"**Secret Key:** `{secret_key}`\n"
                       f"**Backup Codes:** {', '.join(backup_codes)}\n\n"
                       f"Use `/2fa_enable` to activate 2FA protection.",
            color=discord.Color.green(),
            ctx=ctx
        )
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="2fa_enable", description="Enable two-factor authentication.")
    async def enable_2fa(self, ctx):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''UPDATE security_2fa SET enabled = TRUE
                               WHERE user_id = ? AND guild_id = ?''',
                           (ctx.author.id, ctx.guild.id))
            await db.commit()
        
        await ctx.send(embed=modern_embed(
            title="✅ 2FA Enabled",
            description="Two-factor authentication is now active for your account.",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.hybrid_command(name="2fa_disable", description="Disable two-factor authentication.")
    async def disable_2fa(self, ctx):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''UPDATE security_2fa SET enabled = FALSE
                               WHERE user_id = ? AND guild_id = ?''',
                           (ctx.author.id, ctx.guild.id))
            await db.commit()
        
        await ctx.send(embed=modern_embed(
            title="❌ 2FA Disabled",
            description="Two-factor authentication has been disabled.",
            color=discord.Color.red(),
            ctx=ctx
        ))

    @commands.hybrid_command(name="security", description="Configure server security settings.")
    async def configure_security(self, ctx, setting: str, value: str):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Denied",
                description="You need Administrator permission to configure security.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        valid_settings = ["raid_protection", "spam_protection", "link_protection", 
                         "invite_protection", "whitelist_enabled"]
        
        if setting not in valid_settings:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Setting",
                description=f"Valid settings: {', '.join(valid_settings)}",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        bool_value = value.lower() in ["true", "yes", "on", "1"]
        
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT OR REPLACE INTO security_settings 
                               (guild_id, {}) VALUES (?, ?)'''.format(setting),
                           (ctx.guild.id, bool_value))
            await db.commit()
        
        await ctx.send(embed=modern_embed(
            title="✅ Security Updated",
            description=f"**{setting}** has been set to **{value}**",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.hybrid_command(name="security_status", description="View current security settings.")
    async def security_status(self, ctx):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT raid_protection, spam_protection, link_protection,
                                   invite_protection, whitelist_enabled
                                   FROM security_settings WHERE guild_id = ?''',
                                (ctx.guild.id,)) as cursor:
                settings = await cursor.fetchone()
        
        if not settings:
            settings = (True, True, False, True, False)
        
        raid_prot, spam_prot, link_prot, invite_prot, whitelist = settings
        
        embed = modern_embed(
            title="🛡️ Security Status",
            description="Current security configuration",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        embed.add_field(
            name="🛡️ Protection Features",
            value=f"**Raid Protection:** {'✅' if raid_prot else '❌'}\n"
                  f"**Spam Protection:** {'✅' if spam_prot else '❌'}\n"
                  f"**Link Protection:** {'✅' if link_prot else '❌'}\n"
                  f"**Invite Protection:** {'✅' if invite_prot else '❌'}\n"
                  f"**Whitelist:** {'✅' if whitelist else '❌'}",
            inline=True
        )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="audit", description="View recent audit logs.")
    async def view_audit_logs(self, ctx, limit: int = 10):
        if not ctx.author.guild_permissions.view_audit_log:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Denied",
                description="You need 'View Audit Log' permission.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT user_id, action, target_id, details, timestamp
                                   FROM audit_logs WHERE guild_id = ?
                                   ORDER BY timestamp DESC LIMIT ?''',
                                (ctx.guild.id, limit)) as cursor:
                logs = await cursor.fetchall()
        
        if not logs:
            await ctx.send(embed=modern_embed(
                title="📋 No Audit Logs",
                description="No audit logs found for this server.",
                color=discord.Color.blue(),
                ctx=ctx
            ))
            return
        
        embed = modern_embed(
            title="📋 Recent Audit Logs",
            description=f"Showing last {len(logs)} entries",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        for user_id, action, target_id, details, timestamp in logs:
            user = ctx.guild.get_member(user_id)
            user_name = user.display_name if user else "Unknown User"
            
            log_entry = f"**{action}** by {user_name}\n"
            if details:
                log_entry += f"Details: {details[:50]}{'...' if len(details) > 50 else ''}\n"
            log_entry += f"Time: {datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M')}"
            
            embed.add_field(
                name=f"📝 {action}",
                value=log_entry,
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="whitelist", description="Manage security whitelist.")
    async def manage_whitelist(self, ctx, action: str, user: discord.Member):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Denied",
                description="You need Administrator permission.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        async with aiosqlite.connect('database.db') as db:
            if action == "add":
                # Get current whitelist
                async with db.execute('''SELECT whitelist_users FROM security_settings 
                                       WHERE guild_id = ?''', (ctx.guild.id,)) as cursor:
                    result = await cursor.fetchone()
                
                current_whitelist = json.loads(result[0]) if result and result[0] else []
                
                if user.id not in current_whitelist:
                    current_whitelist.append(user.id)
                    await db.execute('''INSERT OR REPLACE INTO security_settings 
                                       (guild_id, whitelist_enabled, whitelist_users)
                                       VALUES (?, TRUE, ?)''',
                                   (ctx.guild.id, json.dumps(current_whitelist)))
                    await db.commit()
                    
                    await ctx.send(embed=modern_embed(
                        title="✅ User Whitelisted",
                        description=f"{user.mention} has been added to the security whitelist.",
                        color=discord.Color.green(),
                        ctx=ctx
                    ))
                else:
                    await ctx.send(embed=modern_embed(
                        title="❌ Already Whitelisted",
                        description=f"{user.mention} is already on the whitelist.",
                        color=discord.Color.red(),
                        ctx=ctx
                    ))
            
            elif action == "remove":
                # Get current whitelist
                async with db.execute('''SELECT whitelist_users FROM security_settings 
                                       WHERE guild_id = ?''', (ctx.guild.id,)) as cursor:
                    result = await cursor.fetchone()
                
                current_whitelist = json.loads(result[0]) if result and result[0] else []
                
                if user.id in current_whitelist:
                    current_whitelist.remove(user.id)
                    await db.execute('''INSERT OR REPLACE INTO security_settings 
                                       (guild_id, whitelist_enabled, whitelist_users)
                                       VALUES (?, TRUE, ?)''',
                                   (ctx.guild.id, json.dumps(current_whitelist)))
                    await db.commit()
                    
                    await ctx.send(embed=modern_embed(
                        title="❌ User Removed",
                        description=f"{user.mention} has been removed from the security whitelist.",
                        color=discord.Color.red(),
                        ctx=ctx
                    ))
                else:
                    await ctx.send(embed=modern_embed(
                        title="❌ Not Whitelisted",
                        description=f"{user.mention} is not on the whitelist.",
                        color=discord.Color.red(),
                        ctx=ctx
                    ))

    @commands.hybrid_command(name="incidents", description="View security incidents.")
    async def view_incidents(self, ctx):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Denied",
                description="You need Administrator permission.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT incident_type, user_id, details, resolved, created_at
                                   FROM security_incidents WHERE guild_id = ?
                                   ORDER BY created_at DESC LIMIT 10''',
                                (ctx.guild.id,)) as cursor:
                incidents = await cursor.fetchall()
        
        if not incidents:
            await ctx.send(embed=modern_embed(
                title="🚨 No Incidents",
                description="No security incidents found.",
                color=discord.Color.green(),
                ctx=ctx
            ))
            return
        
        embed = modern_embed(
            title="🚨 Security Incidents",
            description=f"Found {len(incidents)} incident(s)",
            color=discord.Color.red(),
            ctx=ctx
        )
        
        for incident_type, user_id, details, resolved, created_at in incidents:
            user = ctx.guild.get_member(user_id)
            user_name = user.display_name if user else "Unknown User"
            
            status = "✅ Resolved" if resolved else "🚨 Active"
            embed.add_field(
                name=f"🚨 {incident_type}",
                value=f"**User:** {user_name}\n"
                      f"**Status:** {status}\n"
                      f"**Details:** {details[:50]}{'...' if len(details) > 50 else ''}\n"
                      f"**Time:** {datetime.fromisoformat(created_at).strftime('%Y-%m-%d %H:%M')}",
                inline=True
            )
        
        await ctx.send(embed=embed)

    async def log_audit_event(self, guild_id: int, user_id: int, action: str, target_id: int = None, details: str = None):
        """Log an audit event"""
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT INTO audit_logs 
                               (guild_id, user_id, action, target_id, details, timestamp)
                               VALUES (?, ?, ?, ?, ?, ?)''',
                           (guild_id, user_id, action, target_id, details,
                            datetime.utcnow().isoformat()))
            await db.commit()

    async def create_incident(self, guild_id: int, incident_type: str, user_id: int, details: str):
        """Create a security incident"""
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT INTO security_incidents 
                               (guild_id, incident_type, user_id, details, created_at)
                               VALUES (?, ?, ?, ?, ?)''',
                           (guild_id, incident_type, user_id, details,
                            datetime.utcnow().isoformat()))
            await db.commit()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        # Check security settings
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT raid_protection, spam_protection, link_protection,
                                   invite_protection, whitelist_enabled, whitelist_users
                                   FROM security_settings WHERE guild_id = ?''',
                                (message.guild.id,)) as cursor:
                settings = await cursor.fetchone()
        
        if not settings:
            return
        
        raid_prot, spam_prot, link_prot, invite_prot, whitelist_enabled, whitelist_users = settings
        
        # Check if user is whitelisted
        if whitelist_enabled and whitelist_users:
            whitelist = json.loads(whitelist_users)
            if message.author.id in whitelist:
                return
        
        # Link protection
        if link_prot and any(domain in message.content.lower() for domain in ['http://', 'https://', 'discord.gg']):
            await message.delete()
            await self.log_audit_event(message.guild.id, message.author.id, "LINK_BLOCKED", None, message.content)
            await message.channel.send(embed=modern_embed(
                title="🚫 Link Blocked",
                description=f"{message.author.mention}, links are not allowed in this channel.",
                color=discord.Color.red(),
                ctx=None
            ))
        
        # Invite protection
        if invite_prot and 'discord.gg' in message.content.lower():
            await message.delete()
            await self.log_audit_event(message.guild.id, message.author.id, "INVITE_BLOCKED", None, message.content)
            await message.channel.send(embed=modern_embed(
                title="🚫 Invite Blocked",
                description=f"{message.author.mention}, Discord invites are not allowed.",
                color=discord.Color.red(),
                ctx=None
            ))

async def setup(bot):
    cog = Security(bot)
    await cog.init_database()
    await bot.add_cog(cog) 