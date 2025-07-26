import discord
from discord.ext import commands
from bot import modern_embed
import asyncio

class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="join", description="Request to join a user's voice channel.")
    async def join(self, ctx, member: discord.Member):
        """Request to join a user's voice channel"""
        if not member.voice:
            await ctx.send(embed=modern_embed(
                title="❌ Error",
                description=f"{member.mention} is not in a voice channel.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return

        try:
            await member.voice.channel.connect()
            await ctx.send(embed=modern_embed(
                title="✅ Joined Voice Channel",
                description=f"Successfully joined {member.voice.channel.mention}",
                color=discord.Color.green(),
                ctx=ctx
            ))
        except discord.ClientException:
            await ctx.send(embed=modern_embed(
                title="❌ Error",
                description="I'm already connected to a voice channel.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.command(name="voicekick", description="Remove a user from a voice channel.")
    @commands.has_permissions(move_members=True)
    async def voicekick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Remove a user from their voice channel"""
        if not member.voice:
            await ctx.send(embed=modern_embed(
                title="❌ Error",
                description=f"{member.mention} is not in a voice channel.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return

        try:
            await member.move_to(None)
            await ctx.send(embed=modern_embed(
                title="✅ Voice Kick",
                description=f"Kicked {member.mention} from voice channel.\n**Reason:** {reason}",
                color=discord.Color.green(),
                ctx=ctx
            ))
        except discord.Forbidden:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Error",
                description="I don't have permission to move this user.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.command(name="voicemute", description="Mute a user in a voice channel.")
    @commands.has_permissions(mute_members=True)
    async def voicemute(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Mute a user in their voice channel"""
        if not member.voice:
            await ctx.send(embed=modern_embed(
                title="❌ Error",
                description=f"{member.mention} is not in a voice channel.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return

        try:
            await member.edit(mute=True, reason=reason)
            await ctx.send(embed=modern_embed(
                title="✅ Voice Mute",
                description=f"Muted {member.mention} in voice channel.\n**Reason:** {reason}",
                color=discord.Color.green(),
                ctx=ctx
            ))
        except discord.Forbidden:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Error",
                description="I don't have permission to mute this user.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.command(name="voiceunmute", description="Unmute a user in a voice channel.")
    @commands.has_permissions(mute_members=True)
    async def voiceunmute(self, ctx, member: discord.Member):
        """Unmute a user in their voice channel"""
        if not member.voice:
            await ctx.send(embed=modern_embed(
                title="❌ Error",
                description=f"{member.mention} is not in a voice channel.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return

        try:
            await member.edit(mute=False)
            await ctx.send(embed=modern_embed(
                title="✅ Voice Unmute",
                description=f"Unmuted {member.mention} in voice channel.",
                color=discord.Color.green(),
                ctx=ctx
            ))
        except discord.Forbidden:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Error",
                description="I don't have permission to unmute this user.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.command(name="voicemove", description="Move a user to another voice channel.")
    @commands.has_permissions(move_members=True)
    async def voicemove(self, ctx, member: discord.Member, channel: discord.VoiceChannel):
        """Move a user to another voice channel"""
        if not member.voice:
            await ctx.send(embed=modern_embed(
                title="❌ Error",
                description=f"{member.mention} is not in a voice channel.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return

        try:
            await member.move_to(channel)
            await ctx.send(embed=modern_embed(
                title="✅ Voice Move",
                description=f"Moved {member.mention} to {channel.mention}",
                color=discord.Color.green(),
                ctx=ctx
            ))
        except discord.Forbidden:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Error",
                description="I don't have permission to move this user.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.command(name="voicelock", description="Lock a voice channel (prevent joining).")
    @commands.has_permissions(manage_channels=True)
    async def voicelock(self, ctx, channel: discord.VoiceChannel = None):
        """Lock a voice channel to prevent new members from joining"""
        if channel is None:
            if not ctx.author.voice:
                await ctx.send(embed=modern_embed(
                    title="❌ Error",
                    description="Please specify a channel or be in a voice channel.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            channel = ctx.author.voice.channel

        try:
            await channel.set_permissions(ctx.guild.default_role, connect=False)
            await ctx.send(embed=modern_embed(
                title="🔒 Voice Channel Locked",
                description=f"{channel.mention} is now locked. New members cannot join.",
                color=discord.Color.orange(),
                ctx=ctx
            ))
        except discord.Forbidden:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Error",
                description="I don't have permission to manage this channel.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.command(name="voiceunlock", description="Unlock a voice channel (allow joining).")
    @commands.has_permissions(manage_channels=True)
    async def voiceunlock(self, ctx, channel: discord.VoiceChannel = None):
        """Unlock a voice channel to allow new members to join"""
        if channel is None:
            if not ctx.author.voice:
                await ctx.send(embed=modern_embed(
                    title="❌ Error",
                    description="Please specify a channel or be in a voice channel.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            channel = ctx.author.voice.channel

        try:
            await channel.set_permissions(ctx.guild.default_role, connect=None)
            await ctx.send(embed=modern_embed(
                title="🔓 Voice Channel Unlocked",
                description=f"{channel.mention} is now unlocked. New members can join.",
                color=discord.Color.green(),
                ctx=ctx
            ))
        except discord.Forbidden:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Error",
                description="I don't have permission to manage this channel.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.command(name="voiceprivate", description="Make a voice channel private (deny VIEW_CHANNEL to @everyone).")
    @commands.has_permissions(manage_channels=True)
    async def voiceprivate(self, ctx, channel: discord.VoiceChannel = None):
        """Make a voice channel private by denying VIEW_CHANNEL to @everyone"""
        if channel is None:
            if not ctx.author.voice:
                await ctx.send(embed=modern_embed(
                    title="❌ Error",
                    description="Please specify a channel or be in a voice channel.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            channel = ctx.author.voice.channel

        try:
            await channel.set_permissions(ctx.guild.default_role, view_channel=False)
            await ctx.send(embed=modern_embed(
                title="🔒 Voice Channel Private",
                description=f"{channel.mention} is now private. Only users with explicit permissions can see it.",
                color=discord.Color.orange(),
                ctx=ctx
            ))
        except discord.Forbidden:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Error",
                description="I don't have permission to manage this channel.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.command(name="voiceunprivate", description="Make a voice channel public (allow VIEW_CHANNEL to @everyone).")
    @commands.has_permissions(manage_channels=True)
    async def voiceunprivate(self, ctx, channel: discord.VoiceChannel = None):
        """Make a voice channel public by allowing VIEW_CHANNEL to @everyone"""
        if channel is None:
            if not ctx.author.voice:
                await ctx.send(embed=modern_embed(
                    title="❌ Error",
                    description="Please specify a channel or be in a voice channel.",
                    color=discord.Color.red(),
                    ctx=ctx
                ))
                return
            channel = ctx.author.voice.channel

        try:
            await channel.set_permissions(ctx.guild.default_role, view_channel=None)
            await ctx.send(embed=modern_embed(
                title="🔓 Voice Channel Public",
                description=f"{channel.mention} is now public. Everyone can see it.",
                color=discord.Color.green(),
                ctx=ctx
            ))
        except discord.Forbidden:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Error",
                description="I don't have permission to manage this channel.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.command(name="voice", description="Show all voice management commands and their descriptions.")
    async def voice_help(self, ctx):
        """Show voice management commands"""
        embed = modern_embed(
            title="🎤 Voice Management Commands",
            description="Here are all available voice management commands:",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        commands_list = [
            ("!join", "Request to join a user's voice channel"),
            ("!voicekick", "Remove a user from a voice channel"),
            ("!voicemute", "Mute a user in a voice channel"),
            ("!voiceunmute", "Unmute a user in a voice channel"),
            ("!voicemove", "Move a user to another voice channel"),
            ("!voicelock", "Lock a voice channel (prevent joining)"),
            ("!voiceunlock", "Unlock a voice channel (allow joining)"),
            ("!voiceprivate", "Make a voice channel private"),
            ("!voiceunprivate", "Make a voice channel public"),
            ("!textlock", "Lock a text channel (prevent sending messages)"),
            ("!textunlock", "Unlock a text channel (allow sending messages)")
        ]
        
        for cmd, desc in commands_list:
            embed.add_field(name=cmd, value=desc, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="textlock", description="Lock a text channel (prevent sending messages).")
    @commands.has_permissions(manage_channels=True)
    async def textlock(self, ctx, channel: discord.TextChannel = None):
        """Lock a text channel to prevent sending messages"""
        if channel is None:
            channel = ctx.channel

        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=False)
            await ctx.send(embed=modern_embed(
                title="🔒 Text Channel Locked",
                description=f"{channel.mention} is now locked. Members cannot send messages.",
                color=discord.Color.orange(),
                ctx=ctx
            ))
        except discord.Forbidden:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Error",
                description="I don't have permission to manage this channel.",
                color=discord.Color.red(),
                ctx=ctx
            ))

    @commands.command(name="textunlock", description="Unlock a text channel (allow sending messages).")
    @commands.has_permissions(manage_channels=True)
    async def textunlock(self, ctx, channel: discord.TextChannel = None):
        """Unlock a text channel to allow sending messages"""
        if channel is None:
            channel = ctx.channel

        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=None)
            await ctx.send(embed=modern_embed(
                title="🔓 Text Channel Unlocked",
                description=f"{channel.mention} is now unlocked. Members can send messages.",
                color=discord.Color.green(),
                ctx=ctx
            ))
        except discord.Forbidden:
            await ctx.send(embed=modern_embed(
                title="❌ Permission Error",
                description="I don't have permission to manage this channel.",
                color=discord.Color.red(),
                ctx=ctx
            ))

async def setup(bot):
    await bot.add_cog(Voice(bot)) 