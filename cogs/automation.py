import discord
from discord.ext import commands
from bot import modern_embed
import aiosqlite
import json
import re
from datetime import datetime, timedelta
import asyncio

class Automation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.automations = {}
        self.triggers = {}

    async def init_database(self):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS automations 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                guild_id INTEGER, name TEXT, trigger_type TEXT,
                                trigger_condition TEXT, actions TEXT, enabled BOOLEAN DEFAULT TRUE,
                                created_by INTEGER, created_at TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS automation_logs 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                automation_id INTEGER, guild_id INTEGER, user_id INTEGER,
                                trigger_type TEXT, action_result TEXT, timestamp TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS custom_commands 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                guild_id INTEGER, name TEXT, response TEXT,
                                permissions TEXT, cooldown INTEGER DEFAULT 0,
                                created_by INTEGER, created_at TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS auto_responses 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                guild_id INTEGER, trigger TEXT, response TEXT,
                                chance INTEGER DEFAULT 100, enabled BOOLEAN DEFAULT TRUE,
                                created_by INTEGER, created_at TEXT)''')
            await db.commit()

    @commands.hybrid_command(name="automation", description="Create a new automation.")
    async def create_automation(self, ctx, name: str, trigger_type: str, *, trigger_condition: str):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Denied",
                description="You need Administrator permission to create automations.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        valid_triggers = ["message", "reaction", "member_join", "member_leave", "voice_join", "voice_leave"]
        
        if trigger_type not in valid_triggers:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Trigger",
                description=f"Valid triggers: {', '.join(valid_triggers)}",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Store automation
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT INTO automations 
                               (guild_id, name, trigger_type, trigger_condition, actions, created_by, created_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?)''',
                           (ctx.guild.id, name, trigger_type, trigger_condition, "[]",
                            ctx.author.id, datetime.utcnow().isoformat()))
            await db.commit()
        
        await ctx.send(embed=modern_embed(
            title="✅ Automation Created",
            description=f"**Name:** {name}\n"
                       f"**Trigger:** {trigger_type}\n"
                       f"**Condition:** {trigger_condition}\n\n"
                       f"Use `/automation_action` to add actions to this automation.",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.hybrid_command(name="automation_action", description="Add an action to an automation.")
    async def add_automation_action(self, ctx, automation_name: str, action_type: str, *, action_data: str):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Denied",
                description="You need Administrator permission.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        valid_actions = ["send_message", "add_role", "remove_role", "kick", "ban", "timeout", "log"]
        
        if action_type not in valid_actions:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Action",
                description=f"Valid actions: {', '.join(valid_actions)}",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Get automation
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT id, actions FROM automations 
                                   WHERE guild_id = ? AND name = ?''',
                                (ctx.guild.id, automation_name)) as cursor:
                automation = await cursor.fetchone()
            
            if not automation:
                await ctx.send(embed=modern_embed(
                    title="❌ Automation Not Found",
                    description=f"Automation '{automation_name}' not found.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            automation_id, current_actions = automation
            actions = json.loads(current_actions) if current_actions else []
            
            # Add new action
            new_action = {
                "type": action_type,
                "data": action_data,
                "created_at": datetime.utcnow().isoformat()
            }
            actions.append(new_action)
            
            # Update automation
            await db.execute('''UPDATE automations SET actions = ?
                               WHERE id = ?''', (json.dumps(actions), automation_id))
            await db.commit()
        
        await ctx.send(embed=modern_embed(
            title="✅ Action Added",
            description=f"**Action:** {action_type}\n"
                       f"**Data:** {action_data}\n"
                       f"**Automation:** {automation_name}",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.hybrid_command(name="automations", description="List all automations.")
    async def list_automations(self, ctx):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT name, trigger_type, trigger_condition, actions, enabled
                                   FROM automations WHERE guild_id = ? ORDER BY created_at DESC''',
                                (ctx.guild.id,)) as cursor:
                automations = await cursor.fetchall()
        
        if not automations:
            await ctx.send(embed=modern_embed(
                title="🤖 No Automations",
                description="No automations have been created yet.",
                color=discord.Color.blue(),
                ctx=ctx
            ))
            return
        
        embed = modern_embed(
            title="🤖 Server Automations",
            description=f"Found {len(automations)} automation(s):",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        for name, trigger_type, trigger_condition, actions, enabled in automations:
            actions_list = json.loads(actions) if actions else []
            status = "✅ Enabled" if enabled else "❌ Disabled"
            
            embed.add_field(
                name=f"🤖 {name}",
                value=f"**Trigger:** {trigger_type}\n"
                      f"**Condition:** {trigger_condition}\n"
                      f"**Actions:** {len(actions_list)}\n"
                      f"**Status:** {status}",
                inline=True
            )
        
        await ctx.send(embed=embed)

    # Removed duplicate customcmd and customcmds commands - use the advanced cog instead

    # Removed duplicate autorole command - use the advanced cog instead

    # Removed duplicate autoresponse and autoresponses commands - use the advanced cog instead

    @commands.hybrid_command(name="workflow", description="Create a workflow with multiple steps.")
    async def create_workflow(self, ctx, name: str, *, description: str):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Denied",
                description="You need Administrator permission.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Create workflow automation
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT INTO automations 
                               (guild_id, name, trigger_type, trigger_condition, actions, created_by, created_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?)''',
                           (ctx.guild.id, f"workflow_{name}", "workflow", description, "[]",
                            ctx.author.id, datetime.utcnow().isoformat()))
            await db.commit()
        
        await ctx.send(embed=modern_embed(
            title="🔄 Workflow Created",
            description=f"**Name:** {name}\n"
                       f"**Description:** {description}\n\n"
                       f"Use `/workflow_step` to add steps to this workflow.",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.hybrid_command(name="workflow_step", description="Add a step to a workflow.")
    async def add_workflow_step(self, ctx, workflow_name: str, step_type: str, *, step_data: str):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Denied",
                description="You need Administrator permission.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        valid_steps = ["send_message", "add_role", "remove_role", "create_channel", "delete_channel", "log"]
        
        if step_type not in valid_steps:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Step",
                description=f"Valid steps: {', '.join(valid_steps)}",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Add workflow step
        workflow_automation_name = f"workflow_{workflow_name}"
        
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT id, actions FROM automations 
                                   WHERE guild_id = ? AND name = ?''',
                                (ctx.guild.id, workflow_automation_name)) as cursor:
                automation = await cursor.fetchone()
            
            if not automation:
                await ctx.send(embed=modern_embed(
                    title="❌ Workflow Not Found",
                    description=f"Workflow '{workflow_name}' not found.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            automation_id, current_actions = automation
            actions = json.loads(current_actions) if current_actions else []
            
            # Add new step
            new_step = {
                "type": step_type,
                "data": step_data,
                "step_number": len(actions) + 1,
                "created_at": datetime.utcnow().isoformat()
            }
            actions.append(new_step)
            
            # Update workflow
            await db.execute('''UPDATE automations SET actions = ?
                               WHERE id = ?''', (json.dumps(actions), automation_id))
            await db.commit()
        
        await ctx.send(embed=modern_embed(
            title="✅ Workflow Step Added",
            description=f"**Step Type:** {step_type}\n"
                       f"**Step Data:** {step_data}\n"
                       f"**Workflow:** {workflow_name}\n"
                       f"**Step Number:** {len(actions)}",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        # Check for custom commands
        if message.content.startswith('!'):
            command_name = message.content[1:].split()[0]
            
            async with aiosqlite.connect('database.db') as db:
                async with db.execute('''SELECT response FROM custom_commands 
                                       WHERE guild_id = ? AND name = ?''',
                                    (message.guild.id, command_name)) as cursor:
                    custom_command = await cursor.fetchone()
                
                if custom_command:
                    await message.channel.send(custom_command[0])
                    return
        
        # Check for auto-responses
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT response, chance FROM auto_responses 
                                   WHERE guild_id = ? AND trigger = ? AND enabled = TRUE''',
                                (message.guild.id, message.content.lower())) as cursor:
                auto_response = await cursor.fetchone()
            
            if auto_response:
                response, chance = auto_response
                if chance == 100 or (chance > 0 and chance >= discord.utils.random.randint(1, 100)):
                    await message.channel.send(response)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Check for autorole
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT response FROM auto_responses 
                                   WHERE guild_id = ? AND trigger = 'autorole_join' AND enabled = TRUE''',
                                (member.guild.id,)) as cursor:
                autorole = await cursor.fetchone()
            
            if autorole:
                try:
                    role_id = int(autorole[0])
                    role = member.guild.get_role(role_id)
                    if role:
                        await member.add_roles(role)
                except:
                    pass

async def setup(bot):
    cog = Automation(bot)
    await cog.init_database()
    await bot.add_cog(cog) 