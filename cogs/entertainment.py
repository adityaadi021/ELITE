import discord
from discord.ext import commands
from bot import modern_embed
import aiosqlite
import random
import asyncio
import json
from datetime import datetime, timedelta

class Entertainment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        self.story_progress = {}
        self.daily_challenges = {}

    async def cog_load(self):
        await self.init_database()

    async def init_database(self):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS story_progress 
                               (user_id INTEGER PRIMARY KEY, guild_id INTEGER,
                                chapter INTEGER DEFAULT 1, progress INTEGER DEFAULT 0,
                                choices TEXT, created_at TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS daily_challenges 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER, guild_id INTEGER, challenge_type TEXT,
                                completed BOOLEAN DEFAULT FALSE, completed_at TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS entertainment_stats 
                               (user_id INTEGER PRIMARY KEY, guild_id INTEGER,
                                games_won INTEGER DEFAULT 0, stories_completed INTEGER DEFAULT 0,
                                challenges_completed INTEGER DEFAULT 0, total_score INTEGER DEFAULT 0)''')
            await db.commit()

    @commands.hybrid_command(name="minigame", description="Play a mini-game.")
    async def play_minigame(self, ctx, game_type: str = "random"):
        games = {
            "number": self.number_guessing,
            "word": self.word_scramble,
            "math": self.math_challenge,
            "riddle": self.riddle_game,
            "memory": self.memory_game
        }
        
        if game_type == "random":
            game_type = random.choice(list(games.keys()))
        
        if game_type not in games:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Game",
                description=f"Available games: {', '.join(games.keys())}",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        await games[game_type](ctx)

    async def number_guessing(self, ctx):
        number = random.randint(1, 100)
        attempts = 0
        max_attempts = 10
        
        embed = modern_embed(
            title="🎯 Number Guessing Game",
            description=f"I'm thinking of a number between 1 and 100!\n"
                       f"You have {max_attempts} attempts to guess it.",
            color=discord.Color.blue(),
            ctx=ctx
        )
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        
        while attempts < max_attempts:
            try:
                msg = await self.bot.wait_for('message', timeout=30.0, check=check)
                guess = int(msg.content)
                attempts += 1
                
                if guess < number:
                    await ctx.send(f"🔽 Too low! You have {max_attempts - attempts} attempts left.")
                elif guess > number:
                    await ctx.send(f"🔼 Too high! You have {max_attempts - attempts} attempts left.")
                else:
                    await ctx.send(embed=modern_embed(
                        title="🎉 Congratulations!",
                        description=f"You guessed the number {number} in {attempts} attempts!",
                        color=discord.Color.green(),
                        ctx=ctx
                    ))
                    await self.update_stats(ctx.author.id, ctx.guild.id, "games_won")
                    return
            except asyncio.TimeoutError:
                await ctx.send("⏰ Time's up! The game has ended.")
                return
        
        await ctx.send(embed=modern_embed(
            title="💔 Game Over",
            description=f"The number was {number}. Better luck next time!",
            color=discord.Color.red(),
            ctx=ctx
        ))

    async def word_scramble(self, ctx):
        words = ["python", "discord", "elite", "gaming", "modern", "bot", "server", "community"]
        word = random.choice(words)
        scrambled = ''.join(random.sample(word, len(word)))
        
        embed = modern_embed(
            title="🔤 Word Scramble",
            description=f"Unscramble this word: **{scrambled}**\n"
                       f"You have 30 seconds to guess!",
            color=discord.Color.blue(),
            ctx=ctx
        )
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=check)
            if msg.content.lower() == word:
                await ctx.send(embed=modern_embed(
                    title="🎉 Correct!",
                    description=f"You unscrambled '{scrambled}' to '{word}'!",
                    color=discord.Color.green(),
                    ctx=ctx
                ))
                await self.update_stats(ctx.author.id, ctx.guild.id, "games_won")
            else:
                await ctx.send(embed=modern_embed(
                    title="❌ Wrong!",
                    description=f"The correct word was '{word}'.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
        except asyncio.TimeoutError:
            await ctx.send(embed=modern_embed(
                title="⏰ Time's Up!",
                description=f"The correct word was '{word}'.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    async def math_challenge(self, ctx):
        operations = [
            ("+", lambda x, y: x + y),
            ("-", lambda x, y: x - y),
            ("*", lambda x, y: x * y)
        ]
        
        op_symbol, op_func = random.choice(operations)
        a = random.randint(1, 20)
        b = random.randint(1, 20)
        answer = op_func(a, b)
        
        embed = modern_embed(
            title="🧮 Math Challenge",
            description=f"What is {a} {op_symbol} {b}?\n"
                       f"You have 15 seconds to answer!",
            color=discord.Color.blue(),
            ctx=ctx
        )
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        
        try:
            msg = await self.bot.wait_for('message', timeout=15.0, check=check)
            if int(msg.content) == answer:
                await ctx.send(embed=modern_embed(
                    title="🎉 Correct!",
                    description=f"{a} {op_symbol} {b} = {answer}",
                    color=discord.Color.green(),
                    ctx=ctx
                ))
                await self.update_stats(ctx.author.id, ctx.guild.id, "games_won")
            else:
                await ctx.send(embed=modern_embed(
                    title="❌ Wrong!",
                    description=f"The correct answer was {answer}.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
        except asyncio.TimeoutError:
            await ctx.send(embed=modern_embed(
                title="⏰ Time's Up!",
                description=f"The correct answer was {answer}.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    async def riddle_game(self, ctx):
        riddles = [
            ("I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?", "echo"),
            ("What has keys, but no locks; space, but no room; and you can enter, but not go in?", "keyboard"),
            ("The more you take, the more you leave behind. What am I?", "footsteps"),
            ("What gets wetter and wetter the more it dries?", "towel"),
            ("What has a head and a tail but no body?", "coin")
        ]
        
        riddle, answer = random.choice(riddles)
        
        embed = modern_embed(
            title="🤔 Riddle Time",
            description=f"**{riddle}**\n\nYou have 30 seconds to solve it!",
            color=discord.Color.blue(),
            ctx=ctx
        )
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=check)
            if msg.content.lower() == answer:
                await ctx.send(embed=modern_embed(
                    title="🎉 Correct!",
                    description=f"You solved the riddle! The answer was '{answer}'.",
                    color=discord.Color.green(),
                    ctx=ctx
                ))
                await self.update_stats(ctx.author.id, ctx.guild.id, "games_won")
            else:
                await ctx.send(embed=modern_embed(
                    title="❌ Wrong!",
                    description=f"The correct answer was '{answer}'.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
        except asyncio.TimeoutError:
            await ctx.send(embed=modern_embed(
                title="⏰ Time's Up!",
                description=f"The correct answer was '{answer}'.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    async def memory_game(self, ctx):
        sequence = [random.randint(1, 9) for _ in range(4)]
        
        embed = modern_embed(
            title="🧠 Memory Game",
            description="I'll show you a sequence of numbers. Remember them!\n"
                       f"Sequence: {' '.join(map(str, sequence))}\n\n"
                       f"Type the numbers back in order (e.g., 1 2 3 4)",
            color=discord.Color.blue(),
            ctx=ctx
        )
        await ctx.send(embed=embed)
        
        # Wait 5 seconds then clear
        await asyncio.sleep(5)
        await ctx.send("🔍 Now type the sequence!")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=check)
            user_sequence = [int(x) for x in msg.content.split() if x.isdigit()]
            
            if user_sequence == sequence:
                await ctx.send(embed=modern_embed(
                    title="🎉 Perfect Memory!",
                    description=f"You remembered the sequence correctly!",
                    color=discord.Color.green(),
                    ctx=ctx
                ))
                await self.update_stats(ctx.author.id, ctx.guild.id, "games_won")
            else:
                await ctx.send(embed=modern_embed(
                    title="❌ Wrong Sequence",
                    description=f"Your answer: {user_sequence}\n"
                               f"Correct answer: {sequence}",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
        except asyncio.TimeoutError:
            await ctx.send(embed=modern_embed(
                title="⏰ Time's Up!",
                description=f"The correct sequence was {sequence}.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.hybrid_command(name="story", description="Start an interactive story adventure.")
    async def start_story(self, ctx):
        story_chapters = {
            1: {
                "title": "The Mysterious Forest",
                "description": "You find yourself at the edge of a dark forest. The trees whisper ancient secrets, and a path leads deeper into the unknown.",
                "choices": ["Enter the forest", "Stay at the edge", "Call for help"],
                "outcomes": {
                    "Enter the forest": "You venture into the forest and discover a hidden village.",
                    "Stay at the edge": "You wait and eventually meet a friendly traveler.",
                    "Call for help": "Your call echoes through the forest, attracting attention."
                }
            },
            2: {
                "title": "The Hidden Village",
                "description": "You discover a village hidden among the trees. The villagers seem friendly but cautious.",
                "choices": ["Introduce yourself", "Observe from afar", "Ask about the forest"],
                "outcomes": {
                    "Introduce yourself": "The villagers welcome you and share their stories.",
                    "Observe from afar": "You learn about the village's customs and traditions.",
                    "Ask about the forest": "The villagers tell you about the forest's magical properties."
                }
            }
        }
        
        # Get user's story progress
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT chapter, progress FROM story_progress 
                                   WHERE user_id = ? AND guild_id = ?''',
                                (ctx.author.id, ctx.guild.id)) as cursor:
                progress = await cursor.fetchone()
        
        if not progress:
            # Start new story
            chapter = 1
            progress_val = 0
            async with aiosqlite.connect('database.db') as db:
                await db.execute('''INSERT INTO story_progress 
                                   (user_id, guild_id, chapter, progress, created_at)
                                   VALUES (?, ?, ?, ?, ?)''',
                               (ctx.author.id, ctx.guild.id, chapter, progress_val,
                                datetime.utcnow().isoformat()))
                await db.commit()
        else:
            chapter, progress_val = progress
        
        if chapter in story_chapters:
            current_chapter = story_chapters[chapter]
            
            embed = modern_embed(
                title=f"📖 Chapter {chapter}: {current_chapter['title']}",
                description=current_chapter['description'],
                color=discord.Color.purple(),
                ctx=ctx
            )
            
            choices_text = ""
            for i, choice in enumerate(current_chapter['choices'], 1):
                choices_text += f"{i}. {choice}\n"
            
            embed.add_field(
                name="🎯 Your Choices",
                value=choices_text,
                inline=False
            )
            
            await ctx.send(embed=embed)
            
            # Store current chapter for interaction
            self.story_progress[ctx.author.id] = {
                'chapter': chapter,
                'choices': current_chapter['choices'],
                'outcomes': current_chapter['outcomes']
            }
        else:
            await ctx.send(embed=modern_embed(
                title="🏁 Story Complete",
                description="You have completed all available story chapters!",
                color=discord.Color.green(),
                ctx=ctx
            ))

    @commands.hybrid_command(name="storychoice", description="Make a choice in your story.")
    async def make_story_choice(self, ctx, choice_number: int):
        if ctx.author.id not in self.story_progress:
            await ctx.send(embed=modern_embed(
                title="❌ No Active Story",
                description="You don't have an active story. Use `/story` to start one!",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        story_data = self.story_progress[ctx.author.id]
        choices = story_data['choices']
        outcomes = story_data['outcomes']
        
        if choice_number < 1 or choice_number > len(choices):
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Choice",
                description=f"Please choose a number between 1 and {len(choices)}.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        choice = choices[choice_number - 1]
        outcome = outcomes[choice]
        
        embed = modern_embed(
            title="📖 Story Choice",
            description=f"**Your choice:** {choice}\n\n**Outcome:** {outcome}",
            color=discord.Color.purple(),
            ctx=ctx
        )
        await ctx.send(embed=embed)
        
        # Update story progress
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''UPDATE story_progress SET chapter = chapter + 1, progress = progress + 1
                               WHERE user_id = ? AND guild_id = ?''',
                           (ctx.author.id, ctx.guild.id))
            await db.commit()
        
        # Remove from active stories
        del self.story_progress[ctx.author.id]
        
        await self.update_stats(ctx.author.id, ctx.guild.id, "stories_completed")

    @commands.hybrid_command(name="dailychallenge", description="Get your daily challenge.")
    async def get_daily_challenge(self, ctx):
        challenges = [
            "Send 10 messages today",
            "React to 5 messages",
            "Join a voice channel",
            "Use 3 different commands",
            "Welcome a new member",
            "Share a joke",
            "Start a conversation",
            "Help someone with a question",
            "Share an interesting fact",
            "Create a poll"
        ]
        
        challenge = random.choice(challenges)
        
        # Check if user already has a daily challenge
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT challenge_type FROM daily_challenges 
                                   WHERE user_id = ? AND guild_id = ? AND completed = FALSE''',
                                (ctx.author.id, ctx.guild.id)) as cursor:
                existing = await cursor.fetchone()
            
            if existing:
                await ctx.send(embed=modern_embed(
                    title="📅 Daily Challenge",
                    description=f"Your current challenge: **{existing[0]}**\n\n"
                               f"Complete it to get a new one!",
                    color=discord.Color.blue(),
                    ctx=ctx
                ))
                return
            
            # Create new daily challenge
            await db.execute('''INSERT INTO daily_challenges 
                               (user_id, guild_id, challenge_type, created_at)
                               VALUES (?, ?, ?, ?)''',
                           (ctx.author.id, ctx.guild.id, challenge,
                            datetime.utcnow().isoformat()))
            await db.commit()
        
        embed = modern_embed(
            title="📅 Daily Challenge",
            description=f"**Your challenge:** {challenge}\n\n"
                       f"Complete this challenge to earn rewards!",
            color=discord.Color.blue(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="completechallenge", description="Mark your daily challenge as complete.")
    async def complete_challenge(self, ctx):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT challenge_type FROM daily_challenges 
                                   WHERE user_id = ? AND guild_id = ? AND completed = FALSE''',
                                (ctx.author.id, ctx.guild.id)) as cursor:
                challenge = await cursor.fetchone()
            
            if not challenge:
                await ctx.send(embed=modern_embed(
                    title="❌ No Active Challenge",
                    description="You don't have an active daily challenge.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            # Mark challenge as complete
            await db.execute('''UPDATE daily_challenges SET completed = TRUE, completed_at = ?
                               WHERE user_id = ? AND guild_id = ? AND completed = FALSE''',
                           (datetime.utcnow().isoformat(), ctx.author.id, ctx.guild.id))
            await db.commit()
        
        await ctx.send(embed=modern_embed(
            title="🎉 Challenge Complete!",
            description=f"Congratulations! You completed: **{challenge[0]}**\n\n"
                       f"You've earned rewards!",
            color=discord.Color.green(),
            ctx=ctx
        ))
        
        await self.update_stats(ctx.author.id, ctx.guild.id, "challenges_completed")

    async def update_stats(self, user_id: int, guild_id: int, stat_type: str):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT OR REPLACE INTO entertainment_stats 
                               (user_id, guild_id, games_won, stories_completed, challenges_completed, total_score)
                               VALUES (?, ?, 
                                       COALESCE((SELECT games_won FROM entertainment_stats WHERE user_id = ? AND guild_id = ?), 0) + ?,
                                       COALESCE((SELECT stories_completed FROM entertainment_stats WHERE user_id = ? AND guild_id = ?), 0) + ?,
                                       COALESCE((SELECT challenges_completed FROM entertainment_stats WHERE user_id = ? AND guild_id = ?), 0) + ?,
                                       COALESCE((SELECT total_score FROM entertainment_stats WHERE user_id = ? AND guild_id = ?), 0) + 10)''',
                           (user_id, guild_id, user_id, guild_id, 1 if stat_type == "games_won" else 0,
                            user_id, guild_id, 1 if stat_type == "stories_completed" else 0,
                            user_id, guild_id, 1 if stat_type == "challenges_completed" else 0,
                            user_id, guild_id))
            await db.commit()

    @commands.hybrid_command(name="entertainmentstats", description="View your entertainment statistics.")
    async def entertainment_stats(self, ctx, user: discord.Member = None):
        if not user:
            user = ctx.author
        
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT games_won, stories_completed, challenges_completed, total_score
                                   FROM entertainment_stats WHERE user_id = ? AND guild_id = ?''',
                                (user.id, ctx.guild.id)) as cursor:
                stats = await cursor.fetchone()
        
        if not stats:
            stats = (0, 0, 0, 0)
        
        games_won, stories_completed, challenges_completed, total_score = stats
        
        embed = modern_embed(
            title=f"🎮 {user.display_name}'s Entertainment Stats",
            description="Your entertainment achievements",
            color=user.color if user.color != discord.Color.default() else discord.Color.blurple(),
            ctx=ctx,
            thumbnail=user.avatar.url if user.avatar else None
        )
        
        embed.add_field(
            name="🎯 Games Won",
            value=str(games_won),
            inline=True
        )
        
        embed.add_field(
            name="📖 Stories Completed",
            value=str(stories_completed),
            inline=True
        )
        
        embed.add_field(
            name="📅 Challenges Completed",
            value=str(challenges_completed),
            inline=True
        )
        
        embed.add_field(
            name="🏆 Total Score",
            value=str(total_score),
            inline=True
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Entertainment(bot)) 