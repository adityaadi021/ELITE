import discord
from discord.ext import commands
from bot import modern_embed
import aiosqlite
import asyncio
import random
import json
from datetime import datetime

class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.chat_history = {}
        self.ai_personalities = {
            "assistant": "You are a helpful AI assistant. Be friendly and informative.",
            "sarcastic": "You are a sarcastic AI. Be witty and slightly mocking.",
            "professional": "You are a professional AI. Be formal and business-like.",
            "creative": "You are a creative AI. Be imaginative and artistic.",
            "philosopher": "You are a philosophical AI. Be deep and thought-provoking."
        }
        # Remove async initialization from __init__

    async def init_database(self):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS ai_conversations 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER, guild_id INTEGER, message TEXT,
                                response TEXT, personality TEXT, timestamp TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS ai_images 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER, guild_id INTEGER, prompt TEXT,
                                image_url TEXT, created_at TEXT)''')
            await db.commit()

    async def cog_load(self):
        """Async initialization when cog loads"""
        await self.init_database()

    @commands.command(name="chat", description="Chat with AI assistant.")
    async def chat_with_ai(self, ctx, personality: str = "assistant", *, message: str):
        """Chat with AI assistant using different personalities"""
        if personality not in self.ai_personalities:
            personality = "assistant"
        
        # Simulate AI response based on personality
        response = await self.generate_ai_response(message, personality)
        
        # Store conversation
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT INTO ai_conversations 
                               (user_id, guild_id, message, response, personality, timestamp)
                               VALUES (?, ?, ?, ?, ?, ?)''',
                           (ctx.author.id, ctx.guild.id, message, response, personality,
                            datetime.utcnow().isoformat()))
            await db.commit()
        
        embed = modern_embed(
            title=f"🤖 AI Assistant ({personality.title()})",
            description=f"**You:** {message}\n\n**AI:** {response}",
            color=discord.Color.purple(),
            ctx=ctx
        )
        await ctx.send(embed=embed)

    async def generate_ai_response(self, message: str, personality: str) -> str:
        """Generate AI response based on personality"""
        message_lower = message.lower()
        
        # Personality-based responses
        if personality == "sarcastic":
            responses = [
                "Oh wow, what a groundbreaking question. *slow clap*",
                "Let me think... actually, no. I don't want to.",
                "That's the kind of question that makes me question humanity.",
                "I'm not saying you're wrong, but you're definitely not right.",
                "Fascinating. Said no one ever."
            ]
        elif personality == "professional":
            responses = [
                "Based on my analysis, I would recommend considering all available options.",
                "Thank you for your inquiry. I'll process this information accordingly.",
                "I understand your question and will provide a comprehensive response.",
                "Let me address your concerns in a systematic manner.",
                "I appreciate your input and will take it under advisement."
            ]
        elif personality == "creative":
            responses = [
                "Imagine if we could paint with the colors of your imagination...",
                "In a world where dreams dance with reality, your question becomes art.",
                "Let's weave a tapestry of possibilities from your words.",
                "Your question is like a seed that could grow into a beautiful garden.",
                "In the symphony of life, your inquiry adds a unique melody."
            ]
        elif personality == "philosopher":
            responses = [
                "What is existence but a fleeting moment in the grand tapestry of time?",
                "Your question touches upon the fundamental nature of reality itself.",
                "In the vast cosmos, we are but specks of consciousness seeking meaning.",
                "The answer you seek lies not in words, but in the spaces between them.",
                "What is truth, but a reflection of our own perceptions?"
            ]
        else:  # assistant
            responses = [
                "I'd be happy to help you with that!",
                "That's an interesting question. Let me think about it.",
                "I understand what you're asking. Here's what I think...",
                "That's a great question! Let me explain...",
                "I'm here to help! Here's my response to your question."
            ]
        
        # Add some context-aware responses
        if "hello" in message_lower or "hi" in message_lower:
            return f"Hello! How can I assist you today?"
        elif "how are you" in message_lower:
            return "I'm functioning perfectly, thank you for asking!"
        elif "bye" in message_lower or "goodbye" in message_lower:
            return "Goodbye! Feel free to chat with me again anytime!"
        elif "thank" in message_lower:
            return "You're welcome! I'm glad I could help."
        elif "help" in message_lower:
            return "I'm here to help! You can ask me questions, chat with me, or use other AI features."
        
        return random.choice(responses)

    @commands.command(name="generate", description="Generate an AI image.")
    async def generate_image(self, ctx, *, prompt: str):
        """Generate an AI image based on prompt"""
        # Simulate image generation (in real implementation, connect to DALL-E or similar)
        await ctx.send(embed=modern_embed(
            title="🎨 AI Image Generation",
            description=f"**Prompt:** {prompt}\n\n*Image generation would happen here in a real implementation.*",
            color=discord.Color.blue(),
            ctx=ctx
        ))
        
        # Store image generation request
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT INTO ai_images 
                               (user_id, guild_id, prompt, image_url, created_at)
                               VALUES (?, ?, ?, ?, ?)''',
                           (ctx.author.id, ctx.guild.id, prompt, "simulated_url",
                            datetime.utcnow().isoformat()))
            await db.commit()

    @commands.command(name="personality", description="Change AI personality.")
    async def change_personality(self, ctx, personality: str):
        """Change AI personality for future conversations"""
        if personality not in self.ai_personalities:
            available = ", ".join(self.ai_personalities.keys())
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Personality",
                description=f"Available personalities: {available}",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        # Store user's preferred personality (in a real implementation)
        await ctx.send(embed=modern_embed(
            title="✅ Personality Changed",
            description=f"Your AI personality has been set to: **{personality.title()}**",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.command(name="aihelp", description="Show AI features help.")
    async def ai_help(self, ctx):
        """Show AI features help"""
        embed = modern_embed(
            title="🤖 AI Features Help",
            description="Here are all available AI commands:",
            color=discord.Color.purple(),
            ctx=ctx
        )
        
        commands_list = [
            ("!chat [personality] [message]", "Chat with AI assistant"),
            ("!generate [prompt]", "Generate an AI image"),
            ("!personality [type]", "Change AI personality"),
            ("!aihelp", "Show this help message")
        ]
        
        personalities_list = [
            ("assistant", "Friendly and helpful"),
            ("sarcastic", "Witty and mocking"),
            ("professional", "Formal and business-like"),
            ("creative", "Imaginative and artistic"),
            ("philosopher", "Deep and thought-provoking")
        ]
        
        for cmd, desc in commands_list:
            embed.add_field(name=cmd, value=desc, inline=False)
        
        embed.add_field(
            name="🎭 Available Personalities",
            value="\n".join([f"**{name}:** {desc}" for name, desc in personalities_list]),
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AI(bot)) 