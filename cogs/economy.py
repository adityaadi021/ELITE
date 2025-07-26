import discord
from discord.ext import commands
from bot import modern_embed
import random
import asyncio
from datetime import datetime, timedelta

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Simple in-memory storage (in production, use database)
        self.balances = {}
        self.daily_cooldowns = {}
        self.shop_items = {
            "role_color": {"name": "Custom Role Color", "price": 1000, "description": "Get a custom colored role"},
            "xp_boost": {"name": "XP Boost", "price": 500, "description": "2x XP for 24 hours"},
            "vip": {"name": "VIP Status", "price": 2000, "description": "Exclusive VIP perks"},
            "custom_emoji": {"name": "Custom Emoji", "price": 1500, "description": "Create a custom server emoji"}
        }

    def get_balance(self, user_id):
        return self.balances.get(user_id, 0)

    def add_balance(self, user_id, amount):
        if user_id not in self.balances:
            self.balances[user_id] = 0
        self.balances[user_id] += amount
        return self.balances[user_id]

    @commands.hybrid_command(name="balance", description="Check your balance.")
    async def balance(self, ctx):
        balance = self.get_balance(ctx.author.id)
        embed = modern_embed(
            title="💰 Balance",
            description=f"**{ctx.author.display_name}**'s balance: **{balance:,}** coins",
            color=discord.Color.gold(),
            ctx=ctx,
            emoji="💰"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="dailyreward", description="Claim your daily reward.")
    async def daily(self, ctx):
        user_id = ctx.author.id
        now = datetime.now()
        
        if user_id in self.daily_cooldowns:
            last_claim = self.daily_cooldowns[user_id]
            if now - last_claim < timedelta(days=1):
                remaining = timedelta(days=1) - (now - last_claim)
                hours, remainder = divmod(remaining.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                await ctx.send(embed=modern_embed(
                    title="⏰ Daily Cooldown",
                    description=f"You can claim again in **{hours}h {minutes}m**",
                    color=discord.Color.red(),
                    ctx=ctx,
                    emoji="⏰"
                ))
                return

        reward = random.randint(100, 500)
        self.add_balance(user_id, reward)
        self.daily_cooldowns[user_id] = now
        
        embed = modern_embed(
            title="🎁 Daily Reward",
            description=f"You claimed **{reward:,}** coins!\nNew balance: **{self.get_balance(user_id):,}** coins",
            color=discord.Color.green(),
            ctx=ctx,
            emoji="🎁"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="work", description="Work to earn coins.")
    async def work(self, ctx):
        user_id = ctx.author.id
        earnings = random.randint(50, 200)
        self.add_balance(user_id, earnings)
        
        jobs = [
            "worked as a developer", "delivered packages", "worked at a restaurant",
            "did freelance work", "worked as a teacher", "worked as a designer"
        ]
        job = random.choice(jobs)
        
        embed = modern_embed(
            title="💼 Work",
            description=f"You {job} and earned **{earnings:,}** coins!\nNew balance: **{self.get_balance(user_id):,}** coins",
            color=discord.Color.green(),
            ctx=ctx,
            emoji="💼"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="shop", description="View the shop.")
    async def shop(self, ctx):
        items_text = ""
        for item_id, item in self.shop_items.items():
            items_text += f"**{item['name']}** - {item['price']:,} coins\n{item['description']}\n\n"
        
        embed = modern_embed(
            title="🛒 Shop",
            description=items_text + "Use `/buy <item>` to purchase items!",
            color=discord.Color.blurple(),
            ctx=ctx,
            emoji="🛒"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="buy", description="Buy an item from the shop.")
    async def buy(self, ctx, item: str):
        item = item.lower()
        if item not in self.shop_items:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Item",
                description="That item doesn't exist in the shop.",
                color=discord.Color.red(),
                ctx=ctx,
                emoji="❌"
            ))
            return
        
        user_id = ctx.author.id
        balance = self.get_balance(user_id)
        price = self.shop_items[item]["price"]
        
        if balance < price:
            await ctx.send(embed=modern_embed(
                title="❌ Insufficient Funds",
                description=f"You need **{price:,}** coins but have **{balance:,}** coins.",
                color=discord.Color.red(),
                ctx=ctx,
                emoji="❌"
            ))
            return
        
        self.add_balance(user_id, -price)
        embed = modern_embed(
            title="✅ Purchase Successful",
            description=f"You bought **{self.shop_items[item]['name']}** for **{price:,}** coins!\nNew balance: **{self.get_balance(user_id):,}** coins",
            color=discord.Color.green(),
            ctx=ctx,
            emoji="✅"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="gamble", description="Gamble your coins.")
    async def gamble(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Amount",
                description="Please specify a positive amount.",
                color=discord.Color.red(),
                ctx=ctx,
                emoji="❌"
            ))
            return
        
        user_id = ctx.author.id
        balance = self.get_balance(user_id)
        
        if balance < amount:
            await ctx.send(embed=modern_embed(
                title="❌ Insufficient Funds",
                description=f"You don't have enough coins to gamble **{amount:,}**.",
                color=discord.Color.red(),
                ctx=ctx,
                emoji="❌"
            ))
            return
        
        # 40% chance to win
        if random.random() < 0.4:
            winnings = int(amount * 1.5)
            self.add_balance(user_id, winnings - amount)
            embed = modern_embed(
                title="🎉 You Won!",
                description=f"You won **{winnings:,}** coins!\nNew balance: **{self.get_balance(user_id):,}** coins",
                color=discord.Color.green(),
                ctx=ctx,
                emoji="🎉"
            )
        else:
            self.add_balance(user_id, -amount)
            embed = modern_embed(
                title="💸 You Lost!",
                description=f"You lost **{amount:,}** coins.\nNew balance: **{self.get_balance(user_id):,}** coins",
                color=discord.Color.red(),
                ctx=ctx,
                emoji="💸"
            )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="slots", description="Play slots machine.")
    async def slots(self, ctx, bet: int):
        if bet <= 0:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Bet",
                description="Please specify a positive bet amount.",
                color=discord.Color.red(),
                ctx=ctx,
                emoji="❌"
            ))
            return
        
        user_id = ctx.author.id
        balance = self.get_balance(user_id)
        
        if balance < bet:
            await ctx.send(embed=modern_embed(
                title="❌ Insufficient Funds",
                description=f"You don't have enough coins to bet **{bet:,}**.",
                color=discord.Color.red(),
                ctx=ctx,
                emoji="❌"
            ))
            return
        
        emojis = ["🍎", "🍊", "🍇", "🍒", "💎", "7️⃣"]
        slots = [random.choice(emojis) for _ in range(3)]
        
        embed = modern_embed(
            title="🎰 Slots",
            description=f"[ {' | '.join(slots)} ]",
            color=discord.Color.purple(),
            ctx=ctx,
            emoji="🎰"
        )
        
        if len(set(slots)) == 1:  # All same
            winnings = bet * 3
            self.add_balance(user_id, winnings - bet)
            embed.description += f"\n\n🎉 **JACKPOT!** You won **{winnings:,}** coins!"
            embed.color = discord.Color.gold()
        elif len(set(slots)) == 2:  # Two same
            winnings = int(bet * 1.5)
            self.add_balance(user_id, winnings - bet)
            embed.description += f"\n\n✅ **WIN!** You won **{winnings:,}** coins!"
            embed.color = discord.Color.green()
        else:
            self.add_balance(user_id, -bet)
            embed.description += f"\n\n💸 **LOSE!** You lost **{bet:,}** coins."
            embed.color = discord.Color.red()
        
        embed.description += f"\nNew balance: **{self.get_balance(user_id):,}** coins"
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="economyleaderboard", description="View the richest users.")
    async def leaderboard(self, ctx):
        if not self.balances:
            await ctx.send(embed=modern_embed(
                title="📊 Leaderboard",
                description="No users have any coins yet!",
                color=discord.Color.blurple(),
                ctx=ctx,
                emoji="📊"
            ))
            return
        
        sorted_users = sorted(self.balances.items(), key=lambda x: x[1], reverse=True)[:10]
        
        leaderboard_text = ""
        for i, (user_id, balance) in enumerate(sorted_users, 1):
            user = self.bot.get_user(user_id)
            username = user.display_name if user else f"User {user_id}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            leaderboard_text += f"{medal} **{username}** - {balance:,} coins\n"
        
        embed = modern_embed(
            title="📊 Richest Users",
            description=leaderboard_text,
            color=discord.Color.gold(),
            ctx=ctx,
            emoji="📊"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="giveeconomy", description="Give coins to another user.")
    async def give(self, ctx, user: discord.Member, amount: int):
        if amount <= 0:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Amount",
                description="Please specify a positive amount.",
                color=discord.Color.red(),
                ctx=ctx,
                emoji="❌"
            ))
            return
        
        if user.bot:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Target",
                description="You cannot give coins to bots.",
                color=discord.Color.red(),
                ctx=ctx,
                emoji="❌"
            ))
            return
        
        user_id = ctx.author.id
        balance = self.get_balance(user_id)
        
        if balance < amount:
            await ctx.send(embed=modern_embed(
                title="❌ Insufficient Funds",
                description=f"You don't have enough coins to give **{amount:,}**.",
                color=discord.Color.red(),
                ctx=ctx,
                emoji="❌"
            ))
            return
        
        self.add_balance(user_id, -amount)
        self.add_balance(user.id, amount)
        
        embed = modern_embed(
            title="💸 Gift Sent",
            description=f"You gave **{amount:,}** coins to {user.mention}!\nYour new balance: **{self.get_balance(user_id):,}** coins",
            color=discord.Color.green(),
            ctx=ctx,
            emoji="💸"
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot)) 