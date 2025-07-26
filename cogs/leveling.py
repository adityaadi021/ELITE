import discord
from discord.ext import commands
from bot import modern_embed
import aiosqlite
import random
import asyncio
from datetime import datetime, timedelta
import json

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_cooldowns = {}
        self.achievements = {
            "first_message": {"name": "First Steps", "description": "Send your first message", "xp": 50, "icon": "👋"},
            "level_10": {"name": "Rising Star", "description": "Reach level 10", "xp": 100, "icon": "⭐"},
            "level_25": {"name": "Veteran", "description": "Reach level 25", "xp": 250, "icon": "🎖️"},
            "level_50": {"name": "Legend", "description": "Reach level 50", "xp": 500, "icon": "👑"},
            "daily_streak_7": {"name": "Dedicated", "description": "7-day daily streak", "xp": 200, "icon": "🔥"},
            "voice_hour": {"name": "Voice Master", "description": "Spend 1 hour in voice", "xp": 150, "icon": "🎤"},
            "invite_5": {"name": "Recruiter", "description": "Invite 5 people", "xp": 300, "icon": "📢"},
            "reaction_100": {"name": "Reactive", "description": "Use 100 reactions", "xp": 100, "icon": "😄"}
        }
        self.skill_trees = {
            "communication": {
                "name": "Communication",
                "skills": {
                    "eloquence": {"name": "Eloquence", "max_level": 5, "cost": 10, "effect": "Bonus XP for messages"},
                    "charisma": {"name": "Charisma", "max_level": 5, "cost": 15, "effect": "Better reaction rewards"},
                    "leadership": {"name": "Leadership", "max_level": 3, "cost": 25, "effect": "Team bonus XP"}
                }
            },
            "gaming": {
                "name": "Gaming",
                "skills": {
                    "strategy": {"name": "Strategy", "max_level": 5, "cost": 10, "effect": "Game win bonus"},
                    "luck": {"name": "Luck", "max_level": 5, "cost": 15, "effect": "Better gambling odds"},
                    "persistence": {"name": "Persistence", "max_level": 3, "cost": 25, "effect": "Daily streak bonus"}
                }
            }
        }


    async def init_database(self):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS user_levels 
                               (user_id INTEGER, guild_id INTEGER, xp INTEGER DEFAULT 0, 
                                level INTEGER DEFAULT 0, total_xp INTEGER DEFAULT 0,
                                daily_streak INTEGER DEFAULT 0, last_daily TEXT,
                                voice_time INTEGER DEFAULT 0, invites INTEGER DEFAULT 0,
                                reactions INTEGER DEFAULT 0, achievements TEXT DEFAULT '[]',
                                skill_points INTEGER DEFAULT 0, skills TEXT DEFAULT '{}',
                                PRIMARY KEY (user_id, guild_id))''')
            await db.execute('''CREATE TABLE IF NOT EXISTS guild_level_config 
                               (guild_id INTEGER PRIMARY KEY, xp_channel_id INTEGER,
                                level_up_messages BOOLEAN DEFAULT 1, xp_rate FLOAT DEFAULT 1.0)''')
            await db.commit()

    async def get_user_data(self, user_id, guild_id):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT xp, level, total_xp, daily_streak, last_daily,
                                   voice_time, invites, reactions, achievements, skill_points, skills
                                   FROM user_levels WHERE user_id = ? AND guild_id = ?''', 
                                (user_id, guild_id)) as cursor:
                result = await cursor.fetchone()
                if result:
                    return {
                        'xp': result[0], 'level': result[1], 'total_xp': result[2],
                        'daily_streak': result[3], 'last_daily': result[4],
                        'voice_time': result[5], 'invites': result[6], 'reactions': result[7],
                        'achievements': json.loads(result[8]), 'skill_points': result[9],
                        'skills': json.loads(result[10])
                    }
                return None

    async def update_user_data(self, user_id, guild_id, **kwargs):
        async with aiosqlite.connect('database.db') as db:
            if await self.get_user_data(user_id, guild_id):
                set_clause = ', '.join([f'{k} = ?' for k in kwargs.keys()])
                await db.execute(f'UPDATE user_levels SET {set_clause} WHERE user_id = ? AND guild_id = ?',
                               (*kwargs.values(), user_id, guild_id))
            else:
                await db.execute('''INSERT INTO user_levels (user_id, guild_id, xp, level, total_xp,
                                   daily_streak, last_daily, voice_time, invites, reactions, 
                                   achievements, skill_points, skills)
                                   VALUES (?, ?, 0, 0, 0, 0, ?, 0, 0, 0, '[]', 0, '{}')''',
                               (user_id, guild_id, datetime.utcnow().isoformat()))
            await db.commit()

    def calculate_level(self, xp):
        return int((xp ** 0.5) / 10)

    def calculate_xp_for_level(self, level):
        return int((level * 10) ** 2)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        user_id = message.author.id
        guild_id = message.guild.id
        
        # XP cooldown (1 minute)
        cooldown_key = f"{user_id}_{guild_id}"
        if cooldown_key in self.xp_cooldowns:
            if datetime.utcnow() - self.xp_cooldowns[cooldown_key] < timedelta(minutes=1):
                return
        
        self.xp_cooldowns[cooldown_key] = datetime.utcnow()
        
        # Get user data
        user_data = await self.get_user_data(user_id, guild_id)
        if not user_data:
            user_data = {
                'xp': 0, 'level': 0, 'total_xp': 0, 'daily_streak': 0,
                'last_daily': datetime.utcnow().isoformat(), 'voice_time': 0,
                'invites': 0, 'reactions': 0, 'achievements': [],
                'skill_points': 0, 'skills': {}
            }

        # Calculate XP gain
        base_xp = random.randint(15, 25)
        
        # Skill bonuses
        communication_level = user_data['skills'].get('eloquence', 0)
        base_xp += communication_level * 2

        # Update XP
        new_xp = user_data['xp'] + base_xp
        new_total_xp = user_data['total_xp'] + base_xp
        old_level = user_data['level']
        new_level = self.calculate_level(new_xp)

        # Check for level up
        level_up = new_level > old_level
        skill_points_gained = new_level - old_level

        # Update data
        await self.update_user_data(user_id, guild_id,
                                  xp=new_xp, level=new_level, total_xp=new_total_xp,
                                  skill_points=user_data['skill_points'] + skill_points_gained)

        # Level up message
        if level_up:
            embed = modern_embed(
                title="🎉 Level Up!",
                description=f"**{message.author.display_name}** reached level **{new_level}**!\n"
                           f"🎯 **XP:** {new_xp:,} | **Total:** {new_total_xp:,}\n"
                           f"⭐ **Skill Points:** +{skill_points_gained}",
                color=discord.Color.gold(),
                ctx=message
            )
            await message.channel.send(embed=embed)

        # Check achievements
        await self.check_achievements(user_id, guild_id, user_data)

    async def check_achievements(self, user_id, guild_id, user_data):
        new_achievements = []
        
        # First message achievement
        if "first_message" not in user_data['achievements']:
            new_achievements.append("first_message")

        # Level achievements
        if user_data['level'] >= 10 and "level_10" not in user_data['achievements']:
            new_achievements.append("level_10")
        if user_data['level'] >= 25 and "level_25" not in user_data['achievements']:
            new_achievements.append("level_25")
        if user_data['level'] >= 50 and "level_50" not in user_data['achievements']:
            new_achievements.append("level_50")

        # Award achievements
        if new_achievements:
            total_xp_gained = 0
            achievement_text = []
            
            for achievement_id in new_achievements:
                achievement = self.achievements[achievement_id]
                total_xp_gained += achievement['xp']
                achievement_text.append(f"{achievement['icon']} **{achievement['name']}** - {achievement['description']}")

            # Update achievements and XP
            all_achievements = user_data['achievements'] + new_achievements
            new_xp = user_data['xp'] + total_xp_gained
            new_total_xp = user_data['total_xp'] + total_xp_gained
            
            await self.update_user_data(user_id, guild_id,
                                      xp=new_xp, total_xp=new_total_xp,
                                      achievements=json.dumps(all_achievements))

            # Send achievement notification
            embed = modern_embed(
                title="🏆 Achievement Unlocked!",
                description=f"**Achievements:**\n" + "\n".join(achievement_text) + f"\n\n💰 **XP Gained:** +{total_xp_gained}",
                color=discord.Color.gold(),
                ctx=None
            )
            # Instead of DM, send to a channel if possible
            if hasattr(self, 'last_xp_channel') and self.last_xp_channel:
                try:
                    await self.last_xp_channel.send(embed=embed)
                except:
                    pass

    @commands.hybrid_command(name="level", description="Show your or another user's level.")
    async def level(self, ctx, user: discord.Member = None):
        if not user:
            user = ctx.author

        user_data = await self.get_user_data(user.id, ctx.guild.id)
        if not user_data:
            await ctx.send(embed=modern_embed(
                title="❌ No Data",
                description="This user hasn't earned any XP yet.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return

        # Calculate progress to next level
        current_level_xp = self.calculate_xp_for_level(user_data['level'])
        next_level_xp = self.calculate_xp_for_level(user_data['level'] + 1)
        progress = (user_data['xp'] - current_level_xp) / (next_level_xp - current_level_xp) * 100

        # Create progress bar
        bar_length = 20
        filled_length = int(bar_length * progress / 100)
        progress_bar = "█" * filled_length + "░" * (bar_length - filled_length)

        embed = modern_embed(
            title=f"📊 {user.display_name}'s Level",
            description=f"**Level:** {user_data['level']}\n"
                       f"**XP:** {user_data['xp']:,} / {next_level_xp:,}\n"
                       f"**Total XP:** {user_data['total_xp']:,}\n"
                       f"**Progress:** {progress:.1f}%\n"
                       f"**Progress Bar:** `{progress_bar}`\n\n"
                       f"**Stats:**\n"
                       f"🎤 **Voice Time:** {user_data['voice_time'] // 3600}h {(user_data['voice_time'] % 3600) // 60}m\n"
                       f"📢 **Invites:** {user_data['invites']}\n"
                       f"😄 **Reactions:** {user_data['reactions']}\n"
                       f"🔥 **Daily Streak:** {user_data['daily_streak']} days\n"
                       f"⭐ **Skill Points:** {user_data['skill_points']}\n"
                       f"🏆 **Achievements:** {len(user_data['achievements'])}/{len(self.achievements)}",
            color=user.color if user.color != discord.Color.default() else discord.Color.blurple(),
            ctx=ctx,
            thumbnail=user.avatar.url if user.avatar else None
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="levelleaderboard", description="Show the server's level leaderboard.")
    async def leaderboard(self, ctx):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT user_id, xp, level, total_xp 
                                   FROM user_levels WHERE guild_id = ? 
                                   ORDER BY level DESC, xp DESC LIMIT 10''', 
                                (ctx.guild.id,)) as cursor:
                results = await cursor.fetchall()

        if not results:
            await ctx.send(embed=modern_embed(
                title="❌ No Data",
                description="No one has earned XP yet.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return

        embed = modern_embed(
            title="🏆 Level Leaderboard",
            description="Top 10 members by level",
            color=discord.Color.gold(),
            ctx=ctx
        )

        for i, (user_id, xp, level, total_xp) in enumerate(results, 1):
            user = ctx.guild.get_member(user_id)
            if user:
                embed.add_field(
                    name=f"{'🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'#{i}'} {user.display_name}",
                    value=f"**Level:** {level} | **XP:** {xp:,} | **Total:** {total_xp:,}",
                    inline=False
                )

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="achievements", description="Show your achievements.")
    async def achievements(self, ctx, user: discord.Member = None):
        if not user:
            user = ctx.author

        user_data = await self.get_user_data(user.id, ctx.guild.id)
        if not user_data:
            await ctx.send(embed=modern_embed(
                title="❌ No Data",
                description="This user hasn't earned any achievements yet.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return

        embed = modern_embed(
            title=f"🏆 {user.display_name}'s Achievements",
            description=f"**Progress:** {len(user_data['achievements'])}/{len(self.achievements)} achievements unlocked",
            color=discord.Color.gold(),
            ctx=ctx,
            thumbnail=user.avatar.url if user.avatar else None
        )

        # Show unlocked achievements
        unlocked = []
        for achievement_id in user_data['achievements']:
            achievement = self.achievements[achievement_id]
            unlocked.append(f"{achievement['icon']} **{achievement['name']}** - {achievement['description']} (+{achievement['xp']} XP)")

        if unlocked:
            embed.add_field(name="✅ Unlocked", value="\n".join(unlocked), inline=False)

        # Show locked achievements
        locked = []
        for achievement_id, achievement in self.achievements.items():
            if achievement_id not in user_data['achievements']:
                locked.append(f"🔒 **{achievement['name']}** - {achievement['description']}")

        if locked:
            embed.add_field(name="🔒 Locked", value="\n".join(locked), inline=False)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="skills", description="Show and manage your skill tree.")
    async def skills(self, ctx):
        user_data = await self.get_user_data(ctx.author.id, ctx.guild.id)
        if not user_data:
            await ctx.send(embed=modern_embed(
                title="❌ No Data",
                description="You need to earn XP first to access skills.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return

        embed = modern_embed(
            title="🌳 Skill Tree",
            description=f"**Available Skill Points:** {user_data['skill_points']}\n\n"
                       f"Use `/skillup <tree> <skill>` to upgrade skills!",
            color=discord.Color.green(),
            ctx=ctx
        )

        for tree_id, tree in self.skill_trees.items():
            tree_text = []
            for skill_id, skill in tree['skills'].items():
                current_level = user_data['skills'].get(skill_id, 0)
                tree_text.append(f"**{skill['name']}** (Lv. {current_level}/{skill['max_level']}) - {skill['effect']}")
            
            embed.add_field(
                name=f"🌿 {tree['name']}",
                value="\n".join(tree_text),
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="skillup", description="Upgrade a skill.")
    async def skillup(self, ctx, tree: str, skill: str):
        user_data = await self.get_user_data(ctx.author.id, ctx.guild.id)
        if not user_data:
            await ctx.send(embed=modern_embed(
                title="❌ No Data",
                description="You need to earn XP first to access skills.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return

        if tree not in self.skill_trees:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Tree",
                description=f"Available trees: {', '.join(self.skill_trees.keys())}",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return

        if skill not in self.skill_trees[tree]['skills']:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Skill",
                description=f"Available skills in {tree}: {', '.join(self.skill_trees[tree]['skills'].keys())}",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return

        skill_info = self.skill_trees[tree]['skills'][skill]
        current_level = user_data['skills'].get(skill, 0)

        if current_level >= skill_info['max_level']:
            await ctx.send(embed=modern_embed(
                title="❌ Max Level",
                description=f"{skill_info['name']} is already at maximum level!",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return

        if user_data['skill_points'] < skill_info['cost']:
            await ctx.send(embed=modern_embed(
                title="❌ Insufficient Points",
                description=f"You need {skill_info['cost']} skill points to upgrade {skill_info['name']}.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return

        # Upgrade skill
        user_data['skills'][skill] = current_level + 1
        user_data['skill_points'] -= skill_info['cost']

        await self.update_user_data(ctx.author.id, ctx.guild.id,
                                  skill_points=user_data['skill_points'],
                                  skills=json.dumps(user_data['skills']))

        embed = modern_embed(
            title="⭐ Skill Upgraded!",
            description=f"**{skill_info['name']}** upgraded to level **{current_level + 1}**!\n"
                       f"**Effect:** {skill_info['effect']}\n"
                       f"**Remaining Points:** {user_data['skill_points']}",
            color=discord.Color.green(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="dailylevel", description="Claim your daily XP bonus.")
    async def daily(self, ctx):
        user_data = await self.get_user_data(ctx.author.id, ctx.guild.id)
        if not user_data:
            user_data = {
                'daily_streak': 0, 'last_daily': datetime.utcnow().isoformat(),
                'xp': 0, 'level': 0, 'total_xp': 0, 'voice_time': 0,
                'invites': 0, 'reactions': 0, 'achievements': [],
                'skill_points': 0, 'skills': {}
            }

        # Check if already claimed today
        last_daily = datetime.fromisoformat(user_data['last_daily'])
        if datetime.utcnow() - last_daily < timedelta(days=1):
            time_left = timedelta(days=1) - (datetime.utcnow() - last_daily)
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            await ctx.send(embed=modern_embed(
                title="❌ Already Claimed",
                description=f"You've already claimed your daily bonus today!\n"
                           f"Come back in {hours}h {minutes}m",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return

        # Calculate streak and bonus
        days_since_last = (datetime.utcnow() - last_daily).days
        if days_since_last == 1:
            new_streak = user_data['daily_streak'] + 1
        else:
            new_streak = 1

        # Calculate bonus XP
        base_bonus = 100
        streak_bonus = min(new_streak * 10, 100)  # Max 100 bonus from streak
        total_bonus = base_bonus + streak_bonus

        # Update data
        new_xp = user_data['xp'] + total_bonus
        new_total_xp = user_data['total_xp'] + total_bonus

        await self.update_user_data(ctx.author.id, ctx.guild.id,
                                  xp=new_xp, total_xp=new_total_xp,
                                  daily_streak=new_streak,
                                  last_daily=datetime.utcnow().isoformat())

        embed = modern_embed(
            title="💰 Daily Bonus Claimed!",
            description=f"**XP Gained:** +{total_bonus}\n"
                       f"**Current Streak:** {new_streak} days\n"
                       f"**Base Bonus:** +{base_bonus}\n"
                       f"**Streak Bonus:** +{streak_bonus}\n\n"
                       f"Come back tomorrow to keep your streak!",
            color=discord.Color.gold(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

async def setup(bot):
    cog = Leveling(bot)
    await cog.init_database()
    await bot.add_cog(cog) 