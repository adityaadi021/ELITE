import discord
from discord.ext import commands
from bot import modern_embed
import aiosqlite
import random
import json
from datetime import datetime, timedelta

class Social(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.marriage_requests = {}
        self.friendships = {}

    async def init_database(self):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS user_profiles 
                               (user_id INTEGER PRIMARY KEY, guild_id INTEGER,
                                bio TEXT, age INTEGER, location TEXT, interests TEXT,
                                relationship_status TEXT, partner_id INTEGER,
                                reputation INTEGER DEFAULT 0, created_at TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS friendships 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user1_id INTEGER, user2_id INTEGER, guild_id INTEGER,
                                status TEXT, created_at TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS social_actions 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER, target_id INTEGER, guild_id INTEGER,
                                action TEXT, timestamp TEXT)''')
            await db.commit()

    @commands.hybrid_command(name="profile", description="View or edit your profile.")
    async def profile(self, ctx, user: discord.Member = None, action: str = "view", *, content: str = None):
        if not user:
            user = ctx.author
        
        if action == "view":
            await self.view_profile(ctx, user)
        elif action == "edit":
            if user.id != ctx.author.id:
                await ctx.send(embed=modern_embed(
                    title="❌ Permission Denied",
                    description="You can only edit your own profile.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            await self.edit_profile(ctx, content)
        else:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Action",
                description="Use `view` or `edit` as the action.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    async def view_profile(self, ctx, user):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT bio, age, location, interests, relationship_status,
                                   partner_id, reputation, created_at
                                   FROM user_profiles WHERE user_id = ? AND guild_id = ?''',
                                (user.id, ctx.guild.id)) as cursor:
                profile = await cursor.fetchone()
        
        embed = modern_embed(
            title=f"👤 {user.display_name}'s Profile",
            description="Social profile information",
            color=user.color if user.color != discord.Color.default() else discord.Color.blurple(),
            ctx=ctx,
            thumbnail=user.avatar.url if user.avatar else None
        )
        
        if profile:
            bio, age, location, interests, relationship_status, partner_id, reputation, created_at = profile
            
            embed.add_field(
                name="📝 Bio",
                value=bio or "No bio set",
                inline=False
            )
            
            if age:
                embed.add_field(name="🎂 Age", value=str(age), inline=True)
            if location:
                embed.add_field(name="📍 Location", value=location, inline=True)
            if interests:
                embed.add_field(name="🎯 Interests", value=interests, inline=True)
            
            embed.add_field(
                name="💕 Relationship",
                value=relationship_status or "Single",
                inline=True
            )
            
            if partner_id:
                partner = ctx.guild.get_member(partner_id)
                if partner:
                    embed.add_field(name="💑 Partner", value=partner.mention, inline=True)
            
            embed.add_field(
                name="⭐ Reputation",
                value=f"{reputation} points",
                inline=True
            )
            
            if created_at:
                created_date = datetime.fromisoformat(created_at)
                embed.add_field(
                    name="📅 Member Since",
                    value=created_date.strftime('%Y-%m-%d'),
                    inline=True
                )
        else:
            embed.add_field(
                name="❌ No Profile",
                value="This user hasn't set up their profile yet.",
                inline=False
            )
        
        await ctx.send(embed=embed)

    async def edit_profile(self, ctx, content):
        if not content:
            await ctx.send(embed=modern_embed(
                title="❌ Missing Content",
                description="Please provide content to edit your profile.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Simple bio editing for now
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT OR REPLACE INTO user_profiles 
                               (user_id, guild_id, bio, created_at)
                               VALUES (?, ?, ?, ?)''',
                           (ctx.author.id, ctx.guild.id, content, datetime.utcnow().isoformat()))
            await db.commit()
        
        await ctx.send(embed=modern_embed(
            title="✅ Profile Updated",
            description=f"Your bio has been updated to: **{content}**",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.hybrid_command(name="marry", description="Propose marriage to someone.")
    async def propose_marriage(self, ctx, user: discord.Member):
        if user.bot:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Target",
                description="You cannot marry a bot.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        if user == ctx.author:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Target",
                description="You cannot marry yourself.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Check if already married
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT relationship_status, partner_id 
                                   FROM user_profiles 
                                   WHERE user_id = ? AND guild_id = ?''',
                                (ctx.author.id, ctx.guild.id)) as cursor:
                author_profile = await cursor.fetchone()
            
            if author_profile and author_profile[0] == "Married":
                await ctx.send(embed=modern_embed(
                    title="❌ Already Married",
                    description="You are already married!",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
        
        # Send marriage proposal
        embed = modern_embed(
            title="💍 Marriage Proposal",
            description=f"{ctx.author.mention} has proposed to {user.mention}!\n\n"
                       f"**{user.name}**, do you accept this proposal?",
            color=discord.Color.magenta(),
            ctx=ctx
        )
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("💍")
        await message.add_reaction("❌")
        
        # Store proposal
        self.marriage_requests[message.id] = {
            'proposer': ctx.author.id,
            'target': user.id,
            'guild_id': ctx.guild.id
        }

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        
        if reaction.message.id in self.marriage_requests:
            request = self.marriage_requests[reaction.message.id]
            
            if user.id != request['target']:
                return
            
            if str(reaction.emoji) == "💍":
                # Accept marriage
                async with aiosqlite.connect('database.db') as db:
                    # Update both profiles
                    await db.execute('''INSERT OR REPLACE INTO user_profiles 
                                       (user_id, guild_id, relationship_status, partner_id, created_at)
                                       VALUES (?, ?, 'Married', ?, ?)''',
                                   (request['proposer'], request['guild_id'], request['target'],
                                    datetime.utcnow().isoformat()))
                    
                    await db.execute('''INSERT OR REPLACE INTO user_profiles 
                                       (user_id, guild_id, relationship_status, partner_id, created_at)
                                       VALUES (?, ?, 'Married', ?, ?)''',
                                   (request['target'], request['guild_id'], request['proposer'],
                                    datetime.utcnow().isoformat()))
                    
                    await db.commit()
                
                embed = modern_embed(
                    title="💒 Marriage Accepted!",
                    description=f"🎉 **Congratulations!** {user.mention} has accepted {reaction.message.guild.get_member(request['proposer']).mention}'s proposal!\n\n"
                               f"💕 They are now married!",
                    color=discord.Color.magenta(),
                    ctx=None
                )
                await reaction.message.edit(embed=embed)
                await reaction.message.clear_reactions()
                
            elif str(reaction.emoji) == "❌":
                # Reject marriage
                embed = modern_embed(
                    title="💔 Proposal Rejected",
                    description=f"{user.mention} has rejected the marriage proposal.",
                    color=discord.Color.red(),
                    ctx=None
                )
                await reaction.message.edit(embed=embed)
                await reaction.message.clear_reactions()
            
            del self.marriage_requests[reaction.message.id]

    @commands.hybrid_command(name="divorce", description="Divorce your partner.")
    async def divorce(self, ctx):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT partner_id FROM user_profiles 
                                   WHERE user_id = ? AND guild_id = ? AND relationship_status = 'Married' ''',
                                (ctx.author.id, ctx.guild.id)) as cursor:
                profile = await cursor.fetchone()
            
            if not profile:
                await ctx.send(embed=modern_embed(
                    title="❌ Not Married",
                    description="You are not currently married.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            partner_id = profile[0]
            partner = ctx.guild.get_member(partner_id)
            
            # Process divorce
            await db.execute('''UPDATE user_profiles SET relationship_status = 'Single', partner_id = NULL
                               WHERE user_id = ? AND guild_id = ?''', (ctx.author.id, ctx.guild.id))
            await db.execute('''UPDATE user_profiles SET relationship_status = 'Single', partner_id = NULL
                               WHERE user_id = ? AND guild_id = ?''', (partner_id, ctx.guild.id))
            await db.commit()
            
            embed = modern_embed(
                title="💔 Divorce Finalized",
                description=f"{ctx.author.mention} and {partner.mention if partner else 'Unknown'} are now divorced.",
                color=discord.Color.red(),
                ctx=ctx
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="friend", description="Send a friend request.")
    async def friend_request(self, ctx, user: discord.Member):
        if user.bot:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Target",
                description="You cannot send friend requests to bots.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        if user == ctx.author:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Target",
                description="You cannot send friend requests to yourself.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Check if already friends
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT status FROM friendships 
                                   WHERE ((user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?))
                                   AND guild_id = ?''',
                                (ctx.author.id, user.id, user.id, ctx.author.id, ctx.guild.id)) as cursor:
                friendship = await cursor.fetchone()
            
            if friendship:
                await ctx.send(embed=modern_embed(
                    title="❌ Already Friends",
                    description="You are already friends with this user.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            
            # Send friend request
            embed = modern_embed(
                title="🤝 Friend Request",
                description=f"{ctx.author.mention} wants to be friends with {user.mention}!\n\n"
                           f"**{user.name}**, do you accept this friend request?",
                color=discord.Color.blue(),
                ctx=ctx
            )
            
            message = await ctx.send(embed=embed)
            await message.add_reaction("✅")
            await message.add_reaction("❌")
            
            # Store friend request
            self.friendships[message.id] = {
                'requester': ctx.author.id,
                'target': user.id,
                'guild_id': ctx.guild.id
            }

    @commands.hybrid_command(name="friends", description="List your friends.")
    async def list_friends(self, ctx):
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT user1_id, user2_id FROM friendships 
                                   WHERE (user1_id = ? OR user2_id = ?) AND guild_id = ? AND status = 'accepted' ''',
                                (ctx.author.id, ctx.author.id, ctx.guild.id)) as cursor:
                friendships = await cursor.fetchall()
        
        if not friendships:
            await ctx.send(embed=modern_embed(
                title="👥 No Friends",
                description="You don't have any friends yet.",
                color=discord.Color.blue(),
                ctx=ctx
            ))
            return
        
        friends = []
        for user1_id, user2_id in friendships:
            friend_id = user2_id if user1_id == ctx.author.id else user1_id
            friend = ctx.guild.get_member(friend_id)
            if friend:
                friends.append(friend.display_name)
        
        embed = modern_embed(
            title="👥 Your Friends",
            description=f"You have {len(friends)} friend(s):",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        for i, friend in enumerate(friends, 1):
            embed.add_field(
                name=f"👤 Friend #{i}",
                value=friend,
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="hug", description="Hug someone.")
    async def hug(self, ctx, user: discord.Member):
        if user.bot:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Target",
                description="You cannot hug a bot.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        if user == ctx.author:
            await ctx.send(embed=modern_embed(
                title="🤗 Self Hug",
                description=f"{ctx.author.mention} gives themselves a big hug! 🤗",
                color=discord.Color.magenta(),
                ctx=ctx
            ))
            return
        
        hugs = [
            f"{ctx.author.mention} gives {user.mention} a warm hug! 🤗",
            f"{ctx.author.mention} hugs {user.mention} tightly! 💕",
            f"{ctx.author.mention} embraces {user.mention} with love! ❤️",
            f"{ctx.author.mention} gives {user.mention} a friendly hug! 🤝",
            f"{ctx.author.mention} hugs {user.mention} and doesn't let go! 🥰"
        ]
        
        embed = modern_embed(
            title="🤗 Hug",
            description=random.choice(hugs),
            color=discord.Color.magenta(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="kiss", description="Kiss someone.")
    async def kiss(self, ctx, user: discord.Member):
        if user.bot:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Target",
                description="You cannot kiss a bot.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        if user == ctx.author:
            await ctx.send(embed=modern_embed(
                title="💋 Self Kiss",
                description=f"{ctx.author.mention} blows themselves a kiss! 💋",
                color=discord.Color.magenta(),
                ctx=ctx
            ))
            return
        
        kisses = [
            f"{ctx.author.mention} gives {user.mention} a sweet kiss! 💋",
            f"{ctx.author.mention} kisses {user.mention} passionately! 💕",
            f"{ctx.author.mention} plants a gentle kiss on {user.mention}! 😘",
            f"{ctx.author.mention} gives {user.mention} a loving kiss! 💖",
            f"{ctx.author.mention} kisses {user.mention} with all their heart! 💝"
        ]
        
        embed = modern_embed(
            title="💋 Kiss",
            description=random.choice(kisses),
            color=discord.Color.magenta(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

async def setup(bot):
    cog = Social(bot)
    await cog.init_database()
    await bot.add_cog(cog) 