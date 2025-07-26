import discord
from discord.ext import commands
from bot import modern_embed
import random
import asyncio
from datetime import datetime

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.truth_dares = {
            "truth": [
                "What's your biggest fear?",
                "What's the most embarrassing thing that happened to you?",
                "What's your biggest regret?",
                "What's your biggest dream?",
                "What's your biggest secret?",
                "What's your biggest weakness?",
                "What's your biggest strength?",
                "What's your biggest pet peeve?",
                "What's your biggest accomplishment?",
                "What's your biggest failure?"
            ],
            "dare": [
                "Send a selfie to the channel",
                "Say something embarrassing about yourself",
                "Tell a joke",
                "Do your best impression of someone",
                "Sing a song",
                "Dance for 30 seconds",
                "Tell a story",
                "Make a funny face",
                "Do a cartwheel",
                "Tell a secret"
            ]
        }

    @commands.hybrid_command(name="8ball", description="Ask the magic 8ball a question.")
    async def eightball(self, ctx, *, question: str):
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.",
            "Yes - definitely.", "You may rely on it.", "As I see it, yes.",
            "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful."
        ]
        
        embed = modern_embed(
            title="🎱 Magic 8-Ball",
            description=f"**Question:** {question}\n\n**Answer:** {random.choice(responses)}",
            color=discord.Color.purple(),
            ctx=ctx,
            emoji="🎱"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="coinflip", description="Flip a coin.")
    async def coinflip(self, ctx):
        result = random.choice(["Heads", "Tails"])
        emoji = "🪙" if result == "Heads" else "🪙"
        
        embed = modern_embed(
            title="🪙 Coin Flip",
            description=f"The coin landed on **{result}**!",
            color=discord.Color.gold(),
            ctx=ctx,
            emoji=emoji
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="dice", description="Roll a dice.")
    async def dice(self, ctx, sides: int = 6):
        if sides < 2:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Dice",
                description="Dice must have at least 2 sides.",
                color=discord.Color.red(),
                ctx=ctx,
                emoji="❌"
            ))
            return
        
        result = random.randint(1, sides)
        embed = modern_embed(
            title="🎲 Dice Roll",
            description=f"You rolled a **{result}** on a {sides}-sided die!",
            color=discord.Color.green(),
            ctx=ctx,
            emoji="🎲"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="rps", description="Play rock, paper, scissors.")
    async def rps(self, ctx, choice: str):
        choice = choice.lower()
        if choice not in ["rock", "paper", "scissors", "r", "p", "s"]:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Choice",
                description="Please choose: rock, paper, or scissors",
                color=discord.Color.red(),
                ctx=ctx,
                emoji="❌"
            ))
            return
        
        # Convert short forms
        if choice == "r": choice = "rock"
        elif choice == "p": choice = "paper"
        elif choice == "s": choice = "scissors"
        
        bot_choice = random.choice(["rock", "paper", "scissors"])
        
        # Determine winner
        if choice == bot_choice:
            result = "It's a tie!"
            color = discord.Color.blue()
        elif (choice == "rock" and bot_choice == "scissors") or \
             (choice == "paper" and bot_choice == "rock") or \
             (choice == "scissors" and bot_choice == "paper"):
            result = "You win!"
            color = discord.Color.green()
        else:
            result = "You lose!"
            color = discord.Color.red()
        
        emojis = {"rock": "✊", "paper": "🖐️", "scissors": "✌️"}
        
        embed = modern_embed(
            title="✊🖐️✌️ Rock, Paper, Scissors",
            description=f"You chose: {emojis[choice]} {choice.title()}\nI chose: {emojis[bot_choice]} {bot_choice.title()}\n\n**{result}**",
            color=color,
            ctx=ctx,
            emoji="✊"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="truth", description="Get a random truth question.")
    async def truth(self, ctx):
        question = random.choice(self.truth_dares["truth"])
        embed = modern_embed(
            title="🤔 Truth",
            description=f"**{question}**",
            color=discord.Color.blue(),
            ctx=ctx,
            emoji="🤔"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="dare", description="Get a random dare.")
    async def dare(self, ctx):
        dare = random.choice(self.truth_dares["dare"])
        embed = modern_embed(
            title="😈 Dare",
            description=f"**{dare}**",
            color=discord.Color.red(),
            ctx=ctx,
            emoji="😈"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="joke", description="Tell a random joke.")
    async def joke(self, ctx):
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "Why did the scarecrow win an award? He was outstanding in his field!",
            "Why don't eggs tell jokes? They'd crack each other up!",
            "Why did the math book look so sad? Because it had too many problems!",
            "What do you call a fake noodle? An impasta!",
            "Why did the cookie go to the doctor? Because it was feeling crumbly!",
            "What do you call a bear with no teeth? A gummy bear!",
            "Why don't skeletons fight each other? They don't have the guts!",
            "What do you call a fish wearing a bowtie? So-fish-ticated!",
            "Why did the golfer bring two pairs of pants? In case he got a hole in one!"
        ]
        
        embed = modern_embed(
            title="😄 Random Joke",
            description=random.choice(jokes),
            color=discord.Color.yellow(),
            ctx=ctx,
            emoji="😄"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="choose", description="Let the bot choose for you.")
    async def choose(self, ctx, *, options: str):
        if "|" not in options:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Format",
                description="Please separate options with | (e.g., pizza|burger|salad)",
                color=discord.Color.red(),
                ctx=ctx,
                emoji="❌"
            ))
            return
        
        choices = [choice.strip() for choice in options.split("|")]
        if len(choices) < 2:
            await ctx.send(embed=modern_embed(
                title="❌ Not Enough Options",
                description="Please provide at least 2 options.",
                color=discord.Color.red(),
                ctx=ctx,
                emoji="❌"
            ))
            return
        
        chosen = random.choice(choices)
        embed = modern_embed(
            title="🎯 Choice Made",
            description=f"I choose: **{chosen}**",
            color=discord.Color.green(),
            ctx=ctx,
            emoji="🎯"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="reverse", description="Reverse your text.")
    async def reverse(self, ctx, *, text: str):
        reversed_text = text[::-1]
        embed = modern_embed(
            title="🔄 Text Reversed",
            description=f"**Original:** {text}\n**Reversed:** {reversed_text}",
            color=discord.Color.blurple(),
            ctx=ctx,
            emoji="🔄"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="emojify", description="Convert text to emoji.")
    async def emojify(self, ctx, *, text: str):
        emoji_map = {
            'a': '🅰️', 'b': '🅱️', 'c': '©️', 'd': '🇩', 'e': '📧', 'f': '🎏',
            'g': '🇬', 'h': '♓', 'i': 'ℹ️', 'j': '🗾', 'k': '🇰', 'l': '🇱',
            'm': 'Ⓜ️', 'n': '🇳', 'o': '⭕', 'p': '🅿️', 'q': '🇶', 'r': '🇷',
            's': '💲', 't': '✝️', 'u': '⛎', 'v': '♈', 'w': '🇼', 'x': '❌',
            'y': '🇾', 'z': '💤', '0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣',
            '4': '4️⃣', '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣'
        }
        
        emojified = ""
        for char in text.lower():
            if char in emoji_map:
                emojified += emoji_map[char] + " "
            elif char == " ":
                emojified += "  "
            else:
                emojified += char + " "
        
        embed = modern_embed(
            title="😀 Emojified Text",
            description=f"**Original:** {text}\n**Emojified:** {emojified}",
            color=discord.Color.yellow(),
            ctx=ctx,
            emoji="😀"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="ascii", description="Convert text to ASCII art.")
    async def ascii(self, ctx, *, text: str):
        if len(text) > 10:
            await ctx.send(embed=modern_embed(
                title="❌ Text Too Long",
                description="Please use 10 characters or less for ASCII art.",
                color=discord.Color.red(),
                ctx=ctx,
                emoji="❌"
            ))
            return
        
        # Simple ASCII art (you can expand this)
        ascii_art = f"""
```
  ___  ___  ___  ___  ___  ___  ___  ___
 /   \\/   \\/   \\/   \\/   \\/   \\/   \\/   \\
| {text.upper().center(8)} |
 \\___/\\___/\\___/\\___/\\___/\\___/\\___/\\___/
```
        """
        
        embed = modern_embed(
            title="🎨 ASCII Art",
            description=f"```{ascii_art}```",
            color=discord.Color.teal(),
            ctx=ctx,
            emoji="🎨"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="fortune", description="Get your fortune.")
    async def fortune(self, ctx):
        fortunes = [
            "A beautiful, smart, and loving person will be coming into your life.",
            "A dubious friend may be an enemy in camouflage.",
            "A faithful friend is a strong defense.",
            "A fresh start will put you on your way.",
            "A golden egg of opportunity falls into your lap this month.",
            "A lifetime friend shall soon be made.",
            "A light heart carries you through all the hard times.",
            "A new perspective will come with the new year.",
            "A pleasant surprise is waiting for you.",
            "A short pencil is usually better than a long memory any day.",
            "A small donation is call for. It's the right thing to do.",
            "A smile is your personal welcome mat.",
            "A smooth long journey! Great expectations.",
            "A soft voice may be awfully persuasive.",
            "A truly rich life contains love and art in abundance."
        ]
        
        embed = modern_embed(
            title="🔮 Fortune Cookie",
            description=f"**{random.choice(fortunes)}**",
            color=discord.Color.orange(),
            ctx=ctx,
            emoji="🔮"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="compliment", description="Get a random compliment.")
    async def compliment(self, ctx):
        compliments = [
            "You're absolutely amazing!",
            "Your smile brightens up the room!",
            "You have such a kind heart!",
            "You're incredibly talented!",
            "Your positive energy is contagious!",
            "You're a true inspiration!",
            "You have such a beautiful soul!",
            "You're absolutely stunning!",
            "Your creativity knows no bounds!",
            "You're a ray of sunshine!",
            "You have such a wonderful personality!",
            "You're absolutely perfect just the way you are!",
            "Your kindness makes the world a better place!",
            "You're incredibly intelligent!",
            "You have such a beautiful mind!"
        ]
        
        embed = modern_embed(
            title="💝 Compliment",
            description=f"**{random.choice(compliments)}**",
            color=discord.Color.magenta(),
            ctx=ctx,
            emoji="💝"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="roast", description="Get roasted by the bot.")
    async def roast(self, ctx):
        roasts = [
            "You're so slow, you could win a race against a statue!",
            "Your jokes are so bad, even dad jokes feel embarrassed!",
            "You're so unlucky, even your shadow leaves you!",
            "Your fashion sense is so unique, even blind people cringe!",
            "You're so forgetful, you probably forgot to read this!",
            "Your cooking is so bad, even rats order takeout!",
            "You're so clumsy, you could trip over a wireless charger!",
            "Your singing is so bad, even karaoke machines have standards!",
            "You're so slow at typing, even dial-up internet feels fast!",
            "Your dance moves are so unique, even robots feel embarrassed!"
        ]
        
        embed = modern_embed(
            title="🔥 Roast",
            description=f"**{random.choice(roasts)}**",
            color=discord.Color.red(),
            ctx=ctx,
            emoji="🔥"
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Fun(bot)) 