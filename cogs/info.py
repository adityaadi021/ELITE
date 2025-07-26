import discord
from discord.ext import commands
from datetime import datetime
import pytz
from bot import modern_embed

IST = pytz.timezone('Asia/Kolkata')

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ui", description="Get user information.")
    async def ui(self, ctx, *, user: discord.User = None):
        if not user:
            user = ctx.author
        member = ctx.guild.get_member(user.id) if ctx.guild else None
        embed = modern_embed(
            title=f"{user} — User Info",
            color=user.color if hasattr(user, 'color') and user.color != discord.Color.default() else discord.Color.blurple(),
            ctx=ctx,
            emoji="👤",
            thumbnail=user.avatar.url if user.avatar else None
        )
        # Avatar
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        # General Info
        embed.add_field(
            name="🆔 ID",
            value=f"{user.id}",
            inline=True
        )
        embed.add_field(
            name="🏷️ Username",
            value=f"{user.name}#{user.discriminator}",
            inline=True
        )
        embed.add_field(
            name="🤖 Bot?",
            value="Yes" if user.bot else "No",
            inline=True
        )
        # Divider
        embed.add_field(name="\u200b", value="───────────────", inline=False)
        # Badges
        badge_map = {
            "hypesquad_bravery": "🦁",
            "hypesquad_brilliance": "🧠",
            "hypesquad_balance": "⚖️",
            "active_developer": "👨‍💻",
            "bug_hunter": "🐛",
            "bug_hunter_level_2": "🐞",
            "early_supporter": "🌟",
            "verified_bot_developer": "👨‍💻",
            "discord_certified_moderator": "🛡️",
            "bot_http_interactions": "🌐"
        }
        flags = [badge_map[name] for name, val in user.public_flags if val and name in badge_map]
        badges = " ".join(flags) if flags else "None"
        embed.add_field(name="🏆 Badges", value=badges, inline=False)
        # Account Created
        created = user.created_at.astimezone(IST)
        embed.add_field(
            name="🗓️ Joined Discord",
            value=f"{created.strftime('%Y-%m-%d %H:%M:%S')}\n({discord.utils.format_dt(created, 'R')})",
            inline=True
        )
        # Server Info
        if member:
            joined = member.joined_at.astimezone(IST) if member.joined_at else None
            embed.add_field(
                name="🏠 Joined Server",
                value=f"{joined.strftime('%Y-%m-%d %H:%M:%S')}\n({discord.utils.format_dt(joined, 'R')})" if joined else "Unknown",
                inline=True
            )
            embed.add_field(
                name="🔝 Highest Role",
                value=member.top_role.mention if member.top_role != ctx.guild.default_role else "@everyone",
                inline=True
            )
            # Divider
            embed.add_field(name="\u200b", value="───────────────", inline=False)
            # Nickname
            embed.add_field(name="📝 Nickname", value=member.nick or "None", inline=True)
            # Roles
            roles = [role.mention for role in member.roles if role != ctx.guild.default_role]
            roles_display = ", ".join(roles[:6]) + (f" +{len(roles)-6} more" if len(roles) > 6 else "") if roles else "None"
            embed.add_field(name=f"📜 Roles [{len(roles)}]", value=roles_display, inline=False)
            # Boosting
            embed.add_field(name="🚀 Boosting", value="Yes" if member.premium_since else "No", inline=True)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed, reference=ctx.message, mention_author=True)

    @commands.hybrid_command(name="si", description="Get server information.")
    async def si(self, ctx):
        guild = ctx.guild
        
        embed = modern_embed(
            title=f"{guild.name}",
            color=discord.Color.blurple(),
            ctx=ctx,
            emoji="🏠",
            thumbnail=guild.icon.url if guild.icon else None
        )
        
        # About section
        about_info = f"**Name:** {guild.name}\n"
        about_info += f"**ID:** {guild.id}\n"
        about_info += f"**Owner:** 👑 {guild.owner.mention}\n"
        about_info += f"**Created At:** {guild.created_at.astimezone(IST).strftime('%Y-%m-%d %H:%M:%S')}\n"
        about_info += f"**Members:** {guild.member_count:,}\n"
        
        embed.add_field(name="__About__", value=about_info, inline=False)
        
        # General Stats
        stats_info = f"**Verification Level:** {str(guild.verification_level).title()}\n"
        stats_info += f"**Channels:** {len(guild.channels)}\n"
        stats_info += f"**Roles:** {len(guild.roles)}\n"
        stats_info += f"**Emojis:** {len(guild.emojis)}\n"
        stats_info += f"**Boost Status:** Level {guild.premium_tier} (Boosts: {guild.premium_subscription_count})\n"
        
        embed.add_field(name="__General Stats__", value=stats_info, inline=False)
        
        # Features
        features = []
        if guild.features:
            for feature in guild.features:
                features.append(f"✔ {feature.replace('_', ' ').title()}")
        
        if features:
            features_text = '\n'.join(features)
            embed.add_field(name="__Features__", value=features_text, inline=False)
        
        # Channels
        text_channels = len([c for c in guild.channels if isinstance(c, discord.TextChannel)])
        voice_channels = len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])
        category_channels = len([c for c in guild.channels if isinstance(c, discord.CategoryChannel)])
        
        channels_info = f"**Total:** {len(guild.channels)}\n"
        channels_info += f"**Channels:** {text_channels} text, {voice_channels} voice, {category_channels} categories\n"
        
        embed.add_field(name="__Channels__", value=channels_info, inline=False)
        
        # Emoji Info
        regular_emojis = len([e for e in guild.emojis if not e.animated])
        animated_emojis = len([e for e in guild.emojis if e.animated])
        
        emoji_info = f"**Regular:** {regular_emojis}/50\n"
        emoji_info += f"**Animated:** {animated_emojis}/50\n"
        emoji_info += f"**Total Emoji:** {len(guild.emojis)}/100\n"
        
        embed.add_field(name="__Emoji Info__", value=emoji_info, inline=False)
        
        # Boost Status
        boost_info = f"**Level:** {guild.premium_tier} [{guild.premium_subscription_count} boosts]\n"
        
        embed.add_field(name="__Boost Status__", value=boost_info, inline=False)
        
        # Server Roles
        roles = [role.mention for role in sorted(guild.roles, key=lambda r: r.position, reverse=True) if role != guild.default_role]
        if roles:
            roles_text = ', '.join(roles[:10])
            if len(roles) > 10:
                roles_text += f"\n...and {len(roles) - 10} more"
            embed.add_field(name=f"__Server Roles [{len(roles)}]__", value=roles_text, inline=False)
        
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed, reference=ctx.message, mention_author=True)

async def setup(bot):
    await bot.add_cog(Info(bot)) 