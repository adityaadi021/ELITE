import discord
from discord.ext import commands
from discord import ui
import random
import asyncio
import aiosqlite
from bot import modern_embed

class TicTacToeButton(ui.Button):
    def __init__(self, x, y, parent):
        super().__init__(style=discord.ButtonStyle.secondary, label=" ", row=y)
        self.x = x
        self.y = y
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        view = self.parent
        if view.finished or interaction.user != view.current_player:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        if view.board[self.y][self.x] != " ":
            await interaction.response.send_message("That spot is already taken!", ephemeral=True)
            return
        view.board[self.y][self.x] = view.symbols[view.turn]
        self.label = view.symbols[view.turn]
        self.style = discord.ButtonStyle.success if view.turn == 0 else discord.ButtonStyle.danger
        self.disabled = True
        view.turn = 1 - view.turn
        view.current_player = view.players[view.turn]
        winner = view.check_winner()
        if winner or view.is_full():
            view.finished = True
            for child in view.children:
                child.disabled = True
            if winner:
                # Award coins to winner
                coins_earned = 50
                await view.add_coins(winner.id, coins_earned)
                await interaction.response.edit_message(embed=modern_embed(
                    title="🎮 Tic-Tac-Toe",
                    description=f"{winner.mention} wins! 🎉\n**+{coins_earned} coins earned!**",
                    color=discord.Color.green(),
                    ctx=interaction
                ), view=view)
            else:
                await interaction.response.edit_message(embed=modern_embed(
                    title="🎮 Tic-Tac-Toe",
                    description="It's a draw! 🤝",
                    color=discord.Color.blurple(),
                    ctx=interaction
                ), view=view)
        else:
            await interaction.response.edit_message(embed=modern_embed(
                title="🎮 Tic-Tac-Toe",
                description=f"{view.current_player.mention}'s turn ({view.symbols[view.turn]})",
                color=discord.Color.blurple(),
                ctx=interaction
            ), view=view)

class TicTacToeView(ui.View):
    def __init__(self, player1, player2, game_cog):
        super().__init__(timeout=120)
        self.players = [player1, player2]
        self.current_player = player1
        self.symbols = ["X", "O"]
        self.turn = 0
        self.finished = False
        self.board = [[" " for _ in range(3)] for _ in range(3)]
        self.game_cog = game_cog
        for y in range(3):
            for x in range(3):
                self.add_item(TicTacToeButton(x, y, self))

    async def add_coins(self, user_id, amount):
        await self.game_cog.add_coins(user_id, amount)

    def check_winner(self):
        for i in range(3):
            if self.board[i][0] == self.board[i][1] == self.board[i][2] != " ":
                return self.players[0] if self.board[i][0] == "X" else self.players[1]
            if self.board[0][i] == self.board[1][i] == self.board[2][i] != " ":
                return self.players[0] if self.board[0][i] == "X" else self.players[1]
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != " ":
            return self.players[0] if self.board[0][0] == "X" else self.players[1]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != " ":
            return self.players[0] if self.board[0][2] == "X" else self.players[1]
        return None

    def is_full(self):
        return all(cell != " " for row in self.board for cell in row)

class ConnectFourButton(ui.Button):
    def __init__(self, x, parent):
        super().__init__(style=discord.ButtonStyle.secondary, label=f"{x+1}", row=0)
        self.x = x
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        view = self.parent
        if view.finished or interaction.user != view.current_player:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        
        # Find the lowest empty position in this column
        for y in range(5, -1, -1):
            if view.board[y][self.x] == " ":
                view.board[y][self.x] = view.symbols[view.turn]
                view.update_display()
                view.turn = 1 - view.turn
                view.current_player = view.players[view.turn]
                winner = view.check_winner()
                if winner or view.is_full():
                    view.finished = True
                    for child in view.children:
                        child.disabled = True
                    if winner:
                        # Award coins to winner
                        coins_earned = 75
                        await view.add_coins(winner.id, coins_earned)
                        await interaction.response.edit_message(embed=modern_embed(
                            title="🎮 Connect Four",
                            description=f"{winner.mention} wins! 🎉\n**+{coins_earned} coins earned!**",
                            color=discord.Color.green(),
                            ctx=interaction
                        ), view=view)
                    else:
                        await interaction.response.edit_message(embed=modern_embed(
                            title="🎮 Connect Four",
                            description="It's a draw! 🤝",
                            color=discord.Color.blurple(),
                            ctx=interaction
                        ), view=view)
                else:
                    await interaction.response.edit_message(embed=modern_embed(
                        title="🎮 Connect Four",
                        description=f"{view.current_player.mention}'s turn ({view.symbols[view.turn]})",
                        color=discord.Color.blurple(),
                        ctx=interaction
                    ), view=view)
                break
        else:
            await interaction.response.send_message("This column is full!", ephemeral=True)

class ConnectFourView(ui.View):
    def __init__(self, player1, player2, game_cog):
        super().__init__(timeout=120)
        self.players = [player1, player2]
        self.current_player = player1
        self.symbols = ["🔴", "🟡"]
        self.turn = 0
        self.finished = False
        self.board = [[" " for _ in range(7)] for _ in range(6)]
        self.game_cog = game_cog
        for x in range(7):
            self.add_item(ConnectFourButton(x, self))

    async def add_coins(self, user_id, amount):
        await self.game_cog.add_coins(user_id, amount)

    def update_display(self):
        for i, child in enumerate(self.children):
            child.label = f"{i+1}"

    def check_winner(self):
        # Check horizontal, vertical, and diagonal
        for y in range(6):
            for x in range(4):
                if (self.board[y][x] != " " and 
                    self.board[y][x] == self.board[y][x+1] == self.board[y][x+2] == self.board[y][x+3]):
                    return self.players[0] if self.board[y][x] == "🔴" else self.players[1]
        
        for y in range(3):
            for x in range(7):
                if (self.board[y][x] != " " and 
                    self.board[y][x] == self.board[y+1][x] == self.board[y+2][x] == self.board[y+3][x]):
                    return self.players[0] if self.board[y][x] == "🔴" else self.players[1]
        
        # Diagonal checks
        for y in range(3):
            for x in range(4):
                if (self.board[y][x] != " " and 
                    self.board[y][x] == self.board[y+1][x+1] == self.board[y+2][x+2] == self.board[y+3][x+3]):
                    return self.players[0] if self.board[y][x] == "🔴" else self.players[1]
        
        for y in range(3):
            for x in range(3, 7):
                if (self.board[y][x] != " " and 
                    self.board[y][x] == self.board[y+1][x-1] == self.board[y+2][x-2] == self.board[y+3][x-3]):
                    return self.players[0] if self.board[y][x] == "🔴" else self.players[1]
        
        return None

    def is_full(self):
        return all(cell != " " for row in self.board for cell in row)

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        self.game_themes = {
            "classic": {"primary": discord.Color.blurple(), "secondary": discord.Color.dark_theme()},
            "neon": {"primary": discord.Color.purple(), "secondary": discord.Color.dark_purple()},
            "sunset": {"primary": discord.Color.orange(), "secondary": discord.Color.red()},
            "ocean": {"primary": discord.Color.blue(), "secondary": discord.Color.dark_blue()},
            "forest": {"primary": discord.Color.green(), "secondary": discord.Color.dark_green()}
        }
        self.trivia_questions = {
            "general": [
                {"question": "What is the capital of France?", "answer": "paris"},
                {"question": "What is 2 + 2?", "answer": "4"},
                {"question": "What is the largest planet in our solar system?", "answer": "jupiter"},
                {"question": "What is the chemical symbol for gold?", "answer": "au"},
                {"question": "What year did World War II end?", "answer": "1945"}
            ],
            "science": [
                {"question": "What is the atomic number of carbon?", "answer": "6"},
                {"question": "What is the speed of light in m/s?", "answer": "300000000"},
                {"question": "What is the largest organ in the human body?", "answer": "skin"},
                {"question": "What is the chemical formula for water?", "answer": "h2o"},
                {"question": "What is the closest star to Earth?", "answer": "sun"}
            ]
        }
        self.hangman_words = ["python", "discord", "modern", "elite", "hangman", "bot", "cog", "command", "gaming", "interactive"]
        self.stats = {}

    async def init_database(self):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS game_coins 
                               (user_id INTEGER PRIMARY KEY, coins INTEGER DEFAULT 1000)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS game_stats 
                               (user_id INTEGER PRIMARY KEY, games_played INTEGER DEFAULT 0,
                                games_won INTEGER DEFAULT 0, total_earnings INTEGER DEFAULT 0)''')
            await db.commit()

    async def cog_load(self):
        """Async initialization when cog loads"""
        await self.init_database()

    async def get_coins(self, user_id):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('SELECT coins FROM game_coins WHERE user_id = ?', (user_id,)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0

    async def add_coins(self, user_id, amount):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT OR REPLACE INTO game_coins (user_id, coins) 
                               VALUES (?, COALESCE((SELECT coins FROM game_coins WHERE user_id = ?), 0) + ?)''', 
                           (user_id, user_id, amount))
            await db.commit()

    async def remove_coins(self, user_id, amount):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''UPDATE game_coins SET coins = coins - ? WHERE user_id = ? AND coins >= ?''', 
                           (amount, user_id, amount))
            await db.commit()

    async def update_stats(self, user_id, won=False):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT OR REPLACE INTO game_stats (user_id, games_played, games_won, total_earnings) 
                               VALUES (?, COALESCE((SELECT games_played FROM game_stats WHERE user_id = ?), 0) + 1, 
                                       COALESCE((SELECT games_won FROM game_stats WHERE user_id = ?), 0) + ?,
                                       COALESCE((SELECT total_earnings FROM game_stats WHERE user_id = ?), 0) + ?)''', 
                           (user_id, user_id, 1 if won else 0, user_id, user_id, 50 if won else 0))
            await db.commit()

    @commands.command(name="tictactoe", description="Play Tic-Tac-Toe with another user.")
    async def tictactoe(self, ctx, opponent: discord.Member, theme: str = "classic"):
        if opponent.bot or opponent == ctx.author:
            await ctx.send(embed=modern_embed(title="❌ Invalid Opponent", description="You cannot play against yourself or bots.", color=discord.Color.red(), ctx=ctx))
            return
        
        if theme not in self.game_themes:
            theme = "classic"
        
        theme_info = self.game_themes[theme]
        view = TicTacToeView(ctx.author, opponent, self)
        embed = modern_embed(
            title=f"{theme_info['emoji']} Tic-Tac-Toe - {theme_info['name']}",
            description=f"{ctx.author.mention} vs {opponent.mention}\n{ctx.author.mention}'s turn (X)\n\n**Prize: 50 coins for winner!**",
            color=theme_info['color'],
            ctx=ctx
        )
        await ctx.send(embed=embed, view=view)

    @commands.command(name="connect4", description="Play Connect Four with another user.")
    async def connect4(self, ctx, opponent: discord.Member, theme: str = "classic"):
        if opponent.bot or opponent == ctx.author:
            await ctx.send(embed=modern_embed(title="❌ Invalid Opponent", description="You cannot play against yourself or bots.", color=discord.Color.red(), ctx=ctx))
            return
        
        if theme not in self.game_themes:
            theme = "classic"
        
        theme_info = self.game_themes[theme]
        view = ConnectFourView(ctx.author, opponent, self)
        embed = modern_embed(
            title=f"{theme_info['emoji']} Connect Four - {theme_info['name']}",
            description=f"{ctx.author.mention} vs {opponent.mention}\n{ctx.author.mention}'s turn (🔴)\n\n**Prize: 75 coins for winner!**",
            color=theme_info['color'],
            ctx=ctx
        )
        await ctx.send(embed=embed, view=view)

    @commands.command(name="trivia", description="Answer a random trivia question.")
    async def trivia(self, ctx, category: str = "general", theme: str = "classic"):
        if category not in self.trivia_questions:
            category = "general"
        if theme not in self.game_themes:
            theme = "classic"
        
        question, answer = random.choice(self.trivia_questions[category])
        theme_info = self.game_themes[theme]
        
        embed = modern_embed(
            title=f"{theme_info['emoji']} Trivia - {category.title()} ({theme_info['name']})",
            description=f"**{question}**\n\n**Prize: 25 coins for correct answer!**",
            color=theme_info['color'],
            ctx=ctx
        )
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=20)
        except asyncio.TimeoutError:
            await ctx.send(embed=modern_embed(
                title="⏰ Time's up!",
                description=f"The answer was **{answer}**.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        if msg.content.strip().lower() == answer.lower():
            await self.add_coins(ctx.author.id, 25)
            await self.update_stats(ctx.author.id, won=True)
            await ctx.send(embed=modern_embed(
                title="✅ Correct!",
                description=f"You earned **25 coins**!\nNew balance: **{await self.get_coins(ctx.author.id)} coins**",
                color=discord.Color.green(),
                ctx=ctx
            ))
        else:
            await ctx.send(embed=modern_embed(
                title="❌ Wrong!",
                description=f"The answer was **{answer}**.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.command(name="hangman", description="Play Hangman.")
    async def hangman(self, ctx, theme: str = "classic"):
        if theme not in self.game_themes:
            theme = "classic"
        
        word = random.choice(self.hangman_words)
        display = ["_" for _ in word]
        attempts = 6
        guessed = set()
        theme_info = self.game_themes[theme]
        
        embed = modern_embed(
            title=f"{theme_info['emoji']} Hangman - {theme_info['name']}",
            description=f"Word: {' '.join(display)}\nAttempts left: {attempts}\n\n**Prize: 30 coins for winning!**",
            color=theme_info['color'],
            ctx=ctx
        )
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and len(m.content) == 1 and m.content.isalpha()
        
        while attempts > 0 and "_" in display:
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send(embed=modern_embed(
                    title="⏰ Time's up!",
                    description=f"The word was **{word}**.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            letter = msg.content.lower()
            if letter in guessed:
                await ctx.send(embed=modern_embed(
                    title="Already Guessed",
                    description="You already guessed that letter!",
                    color=discord.Color.orange(),
                    ctx=ctx
                ))
                continue
            
            guessed.add(letter)
            if letter in word:
                for i, c in enumerate(word):
                    if c == letter:
                        display[i] = letter
                await ctx.send(embed=modern_embed(
                    title="✅ Correct!",
                    description=f"Word: {' '.join(display)}\nAttempts left: {attempts}",
                    color=discord.Color.green(),
                    ctx=ctx
                ))
            else:
                attempts -= 1
                await ctx.send(embed=modern_embed(
                    title="❌ Wrong!",
                    description=f"Attempts left: {attempts}\nWord: {' '.join(display)}",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
        
        if "_" not in display:
            await self.add_coins(ctx.author.id, 30)
            await self.update_stats(ctx.author.id, won=True)
            await ctx.send(embed=modern_embed(
                title="🎉 You Won!",
                description=f"You guessed the word: **{word}**!\n**+30 coins earned!**\nNew balance: **{await self.get_coins(ctx.author.id)} coins**",
                color=discord.Color.green(),
                ctx=ctx
            ))
        else:
            await ctx.send(embed=modern_embed(
                title="Game Over",
                description=f"The word was **{word}**.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.command(name="scramble", description="Unscramble the word.")
    async def scramble(self, ctx, theme: str = "classic"):
        if theme not in self.game_themes:
            theme = "classic"
        
        words = ["python", "discord", "modern", "elite", "gaming", "interactive", "button", "command"]
        word = random.choice(words)
        scrambled = ''.join(random.sample(word, len(word)))
        theme_info = self.game_themes[theme]
        
        embed = modern_embed(
            title=f"{theme_info['emoji']} Word Scramble - {theme_info['name']}",
            description=f"Unscramble: **{scrambled}**\n\n**Prize: 20 coins for correct answer!**",
            color=theme_info['color'],
            ctx=ctx
        )
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send(embed=modern_embed(
                title="⏰ Time's up!",
                description=f"The word was **{word}**.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        if msg.content.strip().lower() == word.lower():
            await self.add_coins(ctx.author.id, 20)
            await self.update_stats(ctx.author.id, won=True)
            await ctx.send(embed=modern_embed(
                title="✅ Correct!",
                description=f"You earned **20 coins**!\nNew balance: **{await self.get_coins(ctx.author.id)} coins**",
                color=discord.Color.green(),
                ctx=ctx
            ))
        else:
            await ctx.send(embed=modern_embed(
                title="❌ Wrong!",
                description=f"The word was **{word}**.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.command(name="guess", description="Guess the number (1-100).")
    async def guess(self, ctx, theme: str = "classic"):
        if theme not in self.game_themes:
            theme = "classic"
        
        number = random.randint(1, 100)
        theme_info = self.game_themes[theme]
        
        embed = modern_embed(
            title=f"{theme_info['emoji']} Guess the Number - {theme_info['name']}",
            description=f"I'm thinking of a number between 1 and 100. Try to guess it!\n\n**Prize: 15 coins for correct answer!**",
            color=theme_info['color'],
            ctx=ctx
        )
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        
        attempts = 0
        while True:
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=20)
            except asyncio.TimeoutError:
                await ctx.send(embed=modern_embed(
                    title="⏰ Time's up!",
                    description=f"The number was **{number}**.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            guess = int(msg.content)
            attempts += 1
            
            if guess == number:
                await self.add_coins(ctx.author.id, 15)
                await self.update_stats(ctx.author.id, won=True)
                await ctx.send(embed=modern_embed(
                    title="✅ Correct!",
                    description=f"You guessed it in {attempts} tries!\n**+15 coins earned!**\nNew balance: **{await self.get_coins(ctx.author.id)} coins**",
                    color=discord.Color.green(),
                    ctx=ctx
                ))
                break
            elif guess < number:
                await ctx.send(embed=modern_embed(
                    title="Too Low!",
                    description="Try a higher number.",
                    color=discord.Color.orange(),
                    ctx=ctx
                ))
            else:
                await ctx.send(embed=modern_embed(
                    title="Too High!",
                    description="Try a lower number.",
                    color=discord.Color.orange(),
                    ctx=ctx
                ))

    # BETTING GAMES

    async def remove_coins(self, user_id, amount):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''UPDATE game_coins SET coins = coins - ? WHERE user_id = ? AND coins >= ?''', 
                           (amount, user_id, amount))
            await db.commit()

    @commands.command(name="betcoinflip", description="Bet on coin flip (2x payout).")
    async def betcoinflip(self, ctx, bet: int, choice: str = "heads"):
        if bet <= 0:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Bet",
                description="Bet amount must be positive.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        user_coins = await self.get_coins(ctx.author.id)
        if user_coins < bet:
            await ctx.send(embed=modern_embed(
                title="❌ Insufficient Funds",
                description=f"You only have {user_coins} coins but want to bet {bet} coins.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        choice = choice.lower()
        if choice not in ["heads", "tails", "h", "t"]:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Choice",
                description="Choose 'heads' or 'tails'.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Convert short forms
        if choice == "h": choice = "heads"
        elif choice == "t": choice = "tails"
        
        result = random.choice(["heads", "tails"])
        won = choice == result
        
        if won:
            winnings = bet * 2
            await self.add_coins(ctx.author.id, bet)  # Return original bet + winnings
            await ctx.send(embed=modern_embed(
                title="🎉 You Won!",
                description=f"The coin landed on **{result}**!\n**+{winnings} coins earned!**\nNew balance: **{await self.get_coins(ctx.author.id)} coins**",
                color=discord.Color.green(),
                ctx=ctx
            ))
        else:
            await self.remove_coins(ctx.author.id, bet)
            await ctx.send(embed=modern_embed(
                title="💸 You Lost!",
                description=f"The coin landed on **{result}**.\n**-{bet} coins lost.**\nNew balance: **{await self.get_coins(ctx.author.id)} coins**",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.command(name="betdice", description="Bet on dice roll (6x payout for exact match).")
    async def betdice(self, ctx, bet: int, prediction: int):
        if bet <= 0:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Bet",
                description="Bet amount must be positive.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        if prediction < 1 or prediction > 6:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Prediction",
                description="Prediction must be between 1 and 6.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        user_coins = await self.get_coins(ctx.author.id)
        if user_coins < bet:
            await ctx.send(embed=modern_embed(
                title="❌ Insufficient Funds",
                description=f"You only have {user_coins} coins but want to bet {bet} coins.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        result = random.randint(1, 6)
        won = prediction == result
        
        if won:
            winnings = bet * 6
            await self.add_coins(ctx.author.id, bet)  # Return original bet + winnings
            await ctx.send(embed=modern_embed(
                title="🎉 Jackpot!",
                description=f"The dice rolled **{result}**!\n**+{winnings} coins earned!**\nNew balance: **{await self.get_coins(ctx.author.id)} coins**",
                color=discord.Color.green(),
                ctx=ctx
            ))
        else:
            await self.remove_coins(ctx.author.id, bet)
            await ctx.send(embed=modern_embed(
                title="💸 You Lost!",
                description=f"The dice rolled **{result}**.\n**-{bet} coins lost.**\nNew balance: **{await self.get_coins(ctx.author.id)} coins**",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.command(name="betslots", description="Play slots with betting (3x for 3 same, 1.5x for 2 same).")
    async def betslots(self, ctx, bet: int):
        if bet <= 0:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Bet",
                description="Bet amount must be positive.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        user_coins = await self.get_coins(ctx.author.id)
        if user_coins < bet:
            await ctx.send(embed=modern_embed(
                title="❌ Insufficient Funds",
                description=f"You only have {user_coins} coins but want to bet {bet} coins.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        emojis = ["🍎", "🍊", "🍇", "🍒", "💎", "7️⃣"]
        slots = [random.choice(emojis) for _ in range(3)]
        
        embed = modern_embed(
            title="🎰 Slots",
            description=f"[ {' | '.join(slots)} ]",
            color=discord.Color.purple(),
            ctx=ctx
        )
        
        if len(set(slots)) == 1:  # All same
            winnings = bet * 3
            await self.add_coins(ctx.author.id, bet)  # Return original bet + winnings
            embed.description += f"\n\n🎉 **JACKPOT!** You won **{winnings} coins**!"
            embed.color = discord.Color.gold()
        elif len(set(slots)) == 2:  # Two same
            winnings = int(bet * 1.5)
            await self.add_coins(ctx.author.id, bet)  # Return original bet + winnings
            embed.description += f"\n\n✅ **WIN!** You won **{winnings} coins**!"
            embed.color = discord.Color.green()
        else:
            await self.remove_coins(ctx.author.id, bet)
            embed.description += f"\n\n💸 **LOSE!** You lost **{bet} coins**."
            embed.color = discord.Color.red()
        
        embed.description += f"\nNew balance: **{await self.get_coins(ctx.author.id)} coins**"
        await ctx.send(embed=embed)

    @commands.command(name="betblackjack", description="Play Blackjack with betting (2x payout).")
    async def betblackjack(self, ctx, bet: int):
        if bet <= 0:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Bet",
                description="Bet amount must be positive.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        user_coins = await self.get_coins(ctx.author.id)
        if user_coins < bet:
            await ctx.send(embed=modern_embed(
                title="❌ Insufficient Funds",
                description=f"You only have {user_coins} coins but want to bet {bet} coins.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Simple Blackjack implementation
        deck = list(range(1, 11)) * 4  # 1-10, each 4 times
        random.shuffle(deck)
        
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        
        player_total = sum(player_hand)
        dealer_total = sum(dealer_hand)
        
        embed = modern_embed(
            title="🃏 Blackjack",
            description=f"Your hand: {player_hand} (Total: {player_total})\nDealer's hand: [{dealer_hand[0]}, ?]\n\n**Hit or Stand?**",
            color=discord.Color.blurple(),
            ctx=ctx
        )
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["hit", "stand", "h", "s"]
        
        while player_total < 21:
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send(embed=modern_embed(
                    title="⏰ Time's up!",
                    description="You stood.",
                    color=discord.Color.orange(),
                    ctx=ctx
                ))
                break
            
            if msg.content.lower() in ["hit", "h"]:
                player_hand.append(deck.pop())
                player_total = sum(player_hand)
                await ctx.send(embed=modern_embed(
                    title="🃏 Blackjack",
                    description=f"Your hand: {player_hand} (Total: {player_total})\nDealer's hand: [{dealer_hand[0]}, ?]",
                    color=discord.Color.blurple(),
                    ctx=ctx
                ))
                
                if player_total > 21:
                    await self.remove_coins(ctx.author.id, bet)
                    await ctx.send(embed=modern_embed(
                        title="💥 Bust!",
                        description=f"Your total: {player_total}\n**-{bet} coins lost.**\nNew balance: **{await self.get_coins(ctx.author.id)} coins**",
                        color=discord.Color.red(),
                        ctx=ctx
                    ))
                    return
            else:
                break
        
        # Dealer's turn
        while dealer_total < 17:
            dealer_hand.append(deck.pop())
            dealer_total = sum(dealer_hand)
        
        # Determine winner
        if dealer_total > 21:
            winnings = bet * 2
            await self.add_coins(ctx.author.id, bet)
            await ctx.send(embed=modern_embed(
                title="🎉 Dealer Bust!",
                description=f"Your total: {player_total}\nDealer's total: {dealer_total}\n**+{winnings} coins earned!**\nNew balance: **{await self.get_coins(ctx.author.id)} coins**",
                color=discord.Color.green(),
                ctx=ctx
            ))
        elif player_total > dealer_total:
            winnings = bet * 2
            await self.add_coins(ctx.author.id, bet)
            await ctx.send(embed=modern_embed(
                title="🎉 You Win!",
                description=f"Your total: {player_total}\nDealer's total: {dealer_total}\n**+{winnings} coins earned!**\nNew balance: **{await self.get_coins(ctx.author.id)} coins**",
                color=discord.Color.green(),
                ctx=ctx
            ))
        elif player_total < dealer_total:
            await self.remove_coins(ctx.author.id, bet)
            await ctx.send(embed=modern_embed(
                title="💸 Dealer Wins!",
                description=f"Your total: {player_total}\nDealer's total: {dealer_total}\n**-{bet} coins lost.**\nNew balance: **{await self.get_coins(ctx.author.id)} coins**",
                color=discord.Color.red(),
                ctx=ctx
            ))
        else:
            await ctx.send(embed=modern_embed(
                title="🤝 Push!",
                description=f"Your total: {player_total}\nDealer's total: {dealer_total}\n**Bet returned.**\nBalance: **{await self.get_coins(ctx.author.id)} coins**",
                color=discord.Color.blurple(),
                ctx=ctx
            ))

    @commands.command(name="games", description="List all available games.")
    async def games(self, ctx):
        games = ["tictactoe", "connect4", "trivia", "hangman", "scramble", "guess"]
        betting_games = ["betcoinflip", "betdice", "betslots", "betblackjack"]
        themes = list(self.game_themes.keys())
        embed = modern_embed(
            title="🎮 Available Games",
            description=f"**Free Games:** {', '.join(games)}\n**Betting Games:** {', '.join(betting_games)}\n**Themes:** {', '.join(themes)}\n\nUse `/game theme` to specify a theme!",
            color=discord.Color.blurple(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.command(name="gamebalance", description="Check your game coin balance.")
    async def balance(self, ctx):
        coins = await self.get_coins(ctx.author.id)
        embed = modern_embed(
            title="💰 Game Balance",
            description=f"**{ctx.author.display_name}**'s balance: **{coins:,} coins**",
            color=discord.Color.gold(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.command(name="gameleaderboard", description="Show global game leaderboard.")
    async def leaderboard(self, ctx):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT user_id, coins FROM game_coins 
                                   ORDER BY coins DESC LIMIT 10''') as cursor:
                results = await cursor.fetchall()
        
        if not results:
            await ctx.send(embed=modern_embed(
                title="📊 Leaderboard",
                description="No players have earned coins yet!",
                color=discord.Color.blurple(),
                ctx=ctx
            ))
            return
        
        leaderboard_text = ""
        for i, (user_id, coins) in enumerate(results, 1):
            user = self.bot.get_user(user_id)
            username = user.display_name if user else f"User {user_id}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            leaderboard_text += f"{medal} **{username}** - {coins:,} coins\n"
        
        embed = modern_embed(
            title="🏆 Global Game Leaderboard",
            description=leaderboard_text,
            color=discord.Color.gold(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.command(name="stats", description="Show your game statistics.")
    async def stats(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        coins = await self.get_coins(member.id)
        
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('SELECT games_played, games_won, total_earnings FROM game_stats WHERE user_id = ?', (member.id,)) as cursor:
                result = await cursor.fetchone()
        
        if result:
            games_played, games_won, total_earnings = result
            win_rate = (games_won / games_played * 100) if games_played > 0 else 0
        else:
            games_played, games_won, total_earnings, win_rate = 0, 0, 0, 0
        
        embed = modern_embed(
            title=f"📊 {member.display_name}'s Game Stats",
            description=f"**Current Balance:** {coins:,} coins\n**Games Played:** {games_played}\n**Wins:** {games_won}\n**Win Rate:** {win_rate:.1f}%\n**Total Coins Earned:** {total_earnings:,}",
            color=discord.Color.blurple(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.command(name="addcoins", description="Add coins to a user (Owner only).")
    async def addcoins(self, ctx, user: discord.Member, amount: int):
        # Check if user is the bot owner
        if ctx.author.id != 1201050377911554061:  # Replace with your owner ID
            await ctx.send(embed=modern_embed(
                title="❌ Permission Denied",
                description="Only the bot owner can use this command.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        if amount <= 0:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Amount",
                description="Amount must be positive.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        old_balance = await self.get_coins(user.id)
        await self.add_coins(user.id, amount)
        new_balance = await self.get_coins(user.id)
        
        embed = modern_embed(
            title="💰 Coins Added",
            description=f"**{user.display_name}** received **{amount:,} coins**!\n\n**Old Balance:** {old_balance:,} coins\n**New Balance:** {new_balance:,} coins",
            color=discord.Color.green(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.command(name="removecoins", description="Remove coins from a user (Owner only).")
    async def removecoins(self, ctx, user: discord.Member, amount: int):
        # Check if user is the bot owner
        if ctx.author.id != 1201050377911554061:  # Replace with your owner ID
            await ctx.send(embed=modern_embed(
                title="❌ Permission Denied",
                description="Only the bot owner can use this command.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        if amount <= 0:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Amount",
                description="Amount must be positive.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        current_balance = await self.get_coins(user.id)
        if current_balance < amount:
            await ctx.send(embed=modern_embed(
                title="❌ Insufficient Balance",
                description=f"**{user.display_name}** only has **{current_balance:,} coins** but you want to remove **{amount:,} coins**.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        await self.remove_coins(user.id, amount)
        new_balance = await self.get_coins(user.id)
        
        embed = modern_embed(
            title="💰 Coins Removed",
            description=f"**{amount:,} coins** removed from **{user.display_name}**!\n\n**Old Balance:** {current_balance:,} coins\n**New Balance:** {new_balance:,} coins",
            color=discord.Color.orange(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.command(name="setcoins", description="Set a user's coin balance (Owner only).")
    async def setcoins(self, ctx, user: discord.Member, amount: int):
        # Check if user is the bot owner
        if ctx.author.id != 1201050377911554061:  # Replace with your owner ID
            await ctx.send(embed=modern_embed(
                title="❌ Permission Denied",
                description="Only the bot owner can use this command.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        if amount < 0:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Amount",
                description="Amount cannot be negative.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        old_balance = await self.get_coins(user.id)
        
        # Set the exact amount
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT OR REPLACE INTO game_coins (user_id, coins) VALUES (?, ?)''', (user.id, amount))
            await db.commit()
        
        embed = modern_embed(
            title="💰 Balance Set",
            description=f"**{user.display_name}**'s balance set to **{amount:,} coins**!\n\n**Old Balance:** {old_balance:,} coins\n**New Balance:** {amount:,} coins",
            color=discord.Color.green(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.command(name="resetcoins", description="Reset a user's coin balance to 0 (Owner only).")
    async def resetcoins(self, ctx, user: discord.Member):
        # Check if user is the bot owner
        if ctx.author.id != 1201050377911554061:  # Replace with your owner ID
            await ctx.send(embed=modern_embed(
                title="❌ Permission Denied",
                description="Only the bot owner can use this command.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        old_balance = await self.get_coins(user.id)
        
        # Reset to 0
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT OR REPLACE INTO game_coins (user_id, coins) VALUES (?, 0)''', (user.id,))
            await db.commit()
        
        embed = modern_embed(
            title="💰 Balance Reset",
            description=f"**{user.display_name}**'s balance has been reset!\n\n**Old Balance:** {old_balance:,} coins\n**New Balance:** 0 coins",
            color=discord.Color.orange(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    # COIN TRANSFER SYSTEM

    @commands.command(name="givecoins", description="Give coins to another player.")
    async def give(self, ctx, user: discord.Member, amount: int):
        if user.bot:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Target",
                description="You cannot give coins to bots.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        if user == ctx.author:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Target",
                description="You cannot give coins to yourself.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        if amount <= 0:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Amount",
                description="Amount must be positive.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        sender_balance = await self.get_coins(ctx.author.id)
        if sender_balance < amount:
            await ctx.send(embed=modern_embed(
                title="❌ Insufficient Balance",
                description=f"You only have **{sender_balance:,} coins** but want to give **{amount:,} coins**.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Transfer coins
        await self.remove_coins(ctx.author.id, amount)
        await self.add_coins(user.id, amount)
        
        new_sender_balance = await self.get_coins(ctx.author.id)
        receiver_balance = await self.get_coins(user.id)
        
        embed = modern_embed(
            title="💸 Gift Sent",
            description=f"**{ctx.author.display_name}** gave **{amount:,} coins** to **{user.display_name}**!\n\n**Your new balance:** {new_sender_balance:,} coins\n**{user.display_name}'s balance:** {receiver_balance:,} coins",
            color=discord.Color.green(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    # NEW INTERESTING GAMES

    @commands.command(name="memory", description="Play memory card game.")
    async def memory(self, ctx, theme: str = "classic"):
        if theme not in self.game_themes:
            theme = "classic"
        
        theme_info = self.game_themes[theme]
        
        # Create memory cards (pairs of emojis)
        emojis = ["🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐮"]
        cards = emojis[:6] * 2  # 6 pairs
        random.shuffle(cards)
        
        # Create board display
        board = ["🃏" for _ in range(12)]
        revealed = [False for _ in range(12)]
        
        embed = modern_embed(
            title=f"{theme_info['emoji']} Memory Game - {theme_info['name']}",
            description=f"Find matching pairs!\n\n**Board:** {' '.join(board)}\n\n**Prize: 40 coins for completing!**",
            color=theme_info['color'],
            ctx=ctx
        )
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        
        moves = 0
        pairs_found = 0
        
        while pairs_found < 6:
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send(embed=modern_embed(
                    title="⏰ Time's up!",
                    description="Game ended due to timeout.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            try:
                card1 = int(msg.content) - 1
                if card1 < 0 or card1 >= 12 or revealed[card1]:
                    await ctx.send(embed=modern_embed(
                        title="❌ Invalid Card",
                        description="Choose a valid unrevealed card (1-12).",
                        color=discord.Color.orange(),
                        ctx=ctx
                    ))
                    continue
                
                # Show first card
                temp_board = board.copy()
                temp_board[card1] = cards[card1]
                revealed[card1] = True
                
                await ctx.send(embed=modern_embed(
                    title="🃏 Memory Game",
                    description=f"First card: **{cards[card1]}**\n\n**Board:** {' '.join(temp_board)}\n\nChoose second card (1-12):",
                    color=theme_info['color'],
                    ctx=ctx
                ))
                
                # Get second card
                try:
                    msg2 = await self.bot.wait_for('message', check=check, timeout=20)
                except asyncio.TimeoutError:
                    revealed[card1] = False
                    await ctx.send(embed=modern_embed(
                        title="⏰ Time's up!",
                        description="First card hidden again.",
                        color=discord.Color.red(),
                        ctx=ctx
                    ))
                    continue
                
                card2 = int(msg2.content) - 1
                if card2 < 0 or card2 >= 12 or revealed[card2] or card2 == card1:
                    revealed[card1] = False
                    await ctx.send(embed=modern_embed(
                        title="❌ Invalid Card",
                        description="Choose a different valid unrevealed card.",
                        color=discord.Color.orange(),
                        ctx=ctx
                    ))
                    continue
                
                moves += 1
                revealed[card2] = True
                
                # Show both cards
                temp_board[card2] = cards[card2]
                
                if cards[card1] == cards[card2]:
                    # Match found
                    pairs_found += 1
                    board[card1] = cards[card1]
                    board[card2] = cards[card2]
                    
                    await ctx.send(embed=modern_embed(
                        title="✅ Match Found!",
                        description=f"**{cards[card1]}** matches **{cards[card2]}**!\n\n**Board:** {' '.join(board)}\n**Pairs found:** {pairs_found}/6",
                        color=discord.Color.green(),
                        ctx=ctx
                    ))
                else:
                    # No match
                    await ctx.send(embed=modern_embed(
                        title="❌ No Match",
                        description=f"**{cards[card1]}** and **{cards[card2]}** don't match.\n\n**Board:** {' '.join(temp_board)}",
                        color=discord.Color.red(),
                        ctx=ctx
                    ))
                    
                    # Hide cards after delay
                    await asyncio.sleep(2)
                    revealed[card1] = False
                    revealed[card2] = False
                    
                    await ctx.send(embed=modern_embed(
                        title="🃏 Memory Game",
                        description=f"Cards hidden again.\n\n**Board:** {' '.join(board)}\n**Pairs found:** {pairs_found}/6",
                        color=theme_info['color'],
                        ctx=ctx
                    ))
                    
            except ValueError:
                await ctx.send(embed=modern_embed(
                    title="❌ Invalid Input",
                    description="Please enter a number between 1 and 12.",
                    color=discord.Color.orange(),
                    ctx=ctx
                ))
        
        # Game completed
        await self.add_coins(ctx.author.id, 40)
        await self.update_stats(ctx.author.id, won=True)
        
        embed = modern_embed(
            title="🎉 Memory Game Complete!",
            description=f"You found all pairs in **{moves} moves**!\n**+40 coins earned!**\nNew balance: **{await self.get_coins(ctx.author.id)} coins**",
            color=discord.Color.green(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.command(name="wordchain", description="Play word chain game.")
    async def wordchain(self, ctx, theme: str = "classic"):
        if theme not in self.game_themes:
            theme = "classic"
        
        theme_info = self.game_themes[theme]
        
        words = ["python", "discord", "modern", "elite", "gaming", "interactive", "button", "command", "server", "channel", "message", "embed"]
        current_word = random.choice(words)
        
        embed = modern_embed(
            title=f"{theme_info['emoji']} Word Chain - {theme_info['name']}",
            description=f"**Starting word:** {current_word}\n\n**Rules:** Your word must start with the last letter of the previous word.\n**Prize: 25 coins for each correct word!**",
            color=theme_info['color'],
            ctx=ctx
        )
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        score = 0
        used_words = [current_word]
        
        for round_num in range(1, 6):  # 5 rounds
            last_letter = current_word[-1].lower()
            
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=20)
            except asyncio.TimeoutError:
                await ctx.send(embed=modern_embed(
                    title="⏰ Time's up!",
                    description=f"Round {round_num} ended. Final score: {score}",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                break
            
            word = msg.content.strip().lower()
            
            if len(word) < 3:
                await ctx.send(embed=modern_embed(
                    title="❌ Too Short",
                    description="Word must be at least 3 letters long.",
                    color=discord.Color.orange(),
                    ctx=ctx
                ))
                continue
            
            if not word.startswith(last_letter):
                await ctx.send(embed=modern_embed(
                    title="❌ Invalid Word",
                    description=f"Word must start with '{last_letter}'.",
                    color=discord.Color.orange(),
                    ctx=ctx
                ))
                continue
            
            if word in used_words:
                await ctx.send(embed=modern_embed(
                    title="❌ Word Already Used",
                    description="That word has already been used.",
                    color=discord.Color.orange(),
                    ctx=ctx
                ))
                continue
            
            # Valid word
            score += 1
            used_words.append(word)
            current_word = word
            
            await ctx.send(embed=modern_embed(
                title="✅ Correct!",
                description=f"**{word}** is valid!\n**Score:** {score}/5\n**Next word must start with:** {word[-1]}",
                color=discord.Color.green(),
                ctx=ctx
            ))
        
        # Game completed
        coins_earned = score * 5
        await self.add_coins(ctx.author.id, coins_earned)
        await self.update_stats(ctx.author.id, won=True)
        
        embed = modern_embed(
            title="🎉 Word Chain Complete!",
            description=f"**Final Score:** {score}/5\n**+{coins_earned} coins earned!**\nNew balance: **{await self.get_coins(ctx.author.id)} coins**",
            color=discord.Color.green(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.command(name="lottery", description="Buy lottery tickets and win big!")
    async def lottery(self, ctx, tickets: int = 1):
        if tickets <= 0 or tickets > 10:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Tickets",
                description="You can buy 1-10 tickets at once.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        ticket_cost = 50 * tickets
        user_balance = await self.get_coins(ctx.author.id)
        
        if user_balance < ticket_cost:
            await ctx.send(embed=modern_embed(
                title="❌ Insufficient Funds",
                description=f"Tickets cost {ticket_cost} coins but you have {user_balance} coins.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Deduct ticket cost
        await self.remove_coins(ctx.author.id, ticket_cost)
        
        # Generate lottery numbers
        winning_numbers = [random.randint(1, 99) for _ in range(6)]
        user_numbers = [random.randint(1, 99) for _ in range(6 * tickets)]
        
        # Check matches
        matches = 0
        for i in range(0, len(user_numbers), 6):
            ticket_numbers = user_numbers[i:i+6]
            ticket_matches = len(set(ticket_numbers) & set(winning_numbers))
            matches = max(matches, ticket_matches)
        
        # Calculate winnings
        winnings = 0
        if matches == 6:
            winnings = 10000  # Jackpot
        elif matches == 5:
            winnings = 1000
        elif matches == 4:
            winnings = 100
        elif matches == 3:
            winnings = 25
        elif matches == 2:
            winnings = 5
        
        if winnings > 0:
            await self.add_coins(ctx.author.id, winnings)
        
        new_balance = await self.get_coins(ctx.author.id)
        
        embed = modern_embed(
            title="🎰 Lottery Results",
            description=f"**Winning Numbers:** {', '.join(map(str, winning_numbers))}\n**Your Numbers:** {', '.join(map(str, user_numbers))}\n**Matches:** {matches}/6\n\n**Winnings:** {winnings} coins\n**New Balance:** {new_balance} coins",
            color=discord.Color.gold() if winnings > 0 else discord.Color.red(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.command(name="games", description="List all available games.")
    async def games(self, ctx):
        games = ["tictactoe", "connect4", "trivia", "hangman", "scramble", "guess", "memory", "wordchain"]
        betting_games = ["betcoinflip", "betdice", "betslots", "betblackjack"]
        special_games = ["lottery"]
        themes = list(self.game_themes.keys())
        embed = modern_embed(
            title="🎮 Available Games",
            description=f"**Free Games:** {', '.join(games)}\n**Betting Games:** {', '.join(betting_games)}\n**Special Games:** {', '.join(special_games)}\n**Themes:** {', '.join(themes)}\n\nUse `/game theme` to specify a theme!",
            color=discord.Color.blurple(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

async def setup(bot):
    cog = Game(bot)
    await cog.init_database()
    await bot.add_cog(cog) 