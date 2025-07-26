import discord
from discord.ext import commands
from discord import app_commands, Interaction, ui
from datetime import datetime, timedelta, timezone
import asyncio
import pytz
import re

OWNER_ID = 1201050377911554061
IST = pytz.timezone('Asia/Kolkata')

def parse_duration_with_gmt(duration_str):
    # Example: '1h GMT+5:30' or '30m GMT-2' or '2d'
    match = re.match(r'([\dhm ]+)(?:\s*GMT([+-]\d{1,2})(?::(\d{2}))?)?', duration_str.strip(), re.I)
    if not match:
        return 0, None
    dur_part, gmt_hour, gmt_min = match.groups()
    seconds = 0
    num = ''
    time_map = {'h': 3600, 'm': 60, 'd': 86400}
    for c in dur_part:
        if c.isdigit():
            num += c
        elif c in time_map and num:
            seconds += int(num) * time_map[c]
            num = ''
    tz = None
    if gmt_hour:
        offset_hours = int(gmt_hour)
        offset_minutes = int(gmt_min) if gmt_min else 0
        tz = timezone(timedelta(hours=offset_hours, minutes=offset_minutes))
    else:
        tz = IST  # Default to IST (GMT+5:30)
    return seconds, tz

async def run_giveaway(ctx_or_channel, duration_str, prize, winners_str, host_user):
    seconds, tz = parse_duration_with_gmt(duration_str)
    if seconds == 0:
        send = getattr(ctx_or_channel, 'send', None) or getattr(ctx_or_channel, 'channel', ctx_or_channel).send
        await send("❌ Invalid duration format. Use e.g. 1h GMT+5:30, 30m GMT-2, 2d.")
        return
    try:
        num_winners = int(winners_str)
        if num_winners < 1:
            raise ValueError
    except ValueError:
        send = getattr(ctx_or_channel, 'send', None) or getattr(ctx_or_channel, 'channel', ctx_or_channel).send
        await send("❌ Invalid number of winners. Giveaway cancelled.")
        return
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    end_time = now + timedelta(seconds=seconds)
    if tz:
        end_time = end_time.astimezone(tz)
    else:
        end_time = end_time.astimezone(IST)
    embed = discord.Embed(
        title="🎉 Giveaway!",
        description=f"**Prize:** {prize}\nReact with 🎉 to enter!\n**Hosted by:** {host_user.mention}\n**Ends:** <t:{int(end_time.timestamp())}:R>\n**Winners:** {num_winners}",
        color=discord.Color.gold(),
        timestamp=end_time
    )
    embed.set_footer(text="Nexus Manager Bot | Giveaway")
    channel = getattr(ctx_or_channel, 'channel', ctx_or_channel)
    msg = await channel.send(embed=embed)
    await msg.add_reaction("🎉")
    await asyncio.sleep(seconds)
    msg = await channel.fetch_message(msg.id)
    users = [user async for user in msg.reactions[0].users() if not user.bot]
    if not users:
        await channel.send("No valid entries. Giveaway cancelled.")
        return
    winners = []
    for _ in range(min(num_winners, len(users))):
        winner = users.pop(__import__('random').randint(0, len(users)-1))
        winners.append(winner)
    winner_mentions = ', '.join(w.mention for w in winners)
    await channel.send(f"🎉 Congratulations {winner_mentions}! You won the giveaway for **{prize}**!")

class GiveawayModal(ui.Modal, title="🎉 Start a Giveaway!"):
    duration = ui.TextInput(label="⏰ Duration (e.g. 1h GMT+5:30, 30m GMT-2, 2d)", placeholder="1h GMT+5:30", required=True)
    prize = ui.TextInput(label="🏆 Prize", placeholder="$10 Amazon Gift Card", required=True)
    winners = ui.TextInput(label="👥 Number of Winners", placeholder="1", required=True, min_length=1, max_length=2)

    def __init__(self, bot, interaction):
        super().__init__()
        self.bot = bot
        self.interaction = interaction

    async def on_submit(self, interaction: Interaction):
        await interaction.response.send_message("🎉 Giveaway started!", ephemeral=True)
        await run_giveaway(interaction.channel, self.duration.value, self.prize.value, self.winners.value, interaction.user)

def is_admin(ctx):
    return ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="giveaway", description="Start a giveaway (admin/owner only).")
    @commands.check(is_admin)
    async def giveaway(self, ctx):
        """Start a giveaway (admin/owner only)."""
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        template = (
            "**Please copy, fill, and send the following (all in one message):**\n"
            "```\n1h GMT+5:30 | $10 Amazon Gift Card | 2\n```\n"
            "Format: `<duration> | <prize> | <number of winners>`\n"
            "- Example: `30m GMT-2 | Nitro Classic | 1`"
        )
        await ctx.send(template)
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=120)
        except asyncio.TimeoutError:
            await ctx.send("❌ Timed out. Giveaway cancelled.")
            return
        parts = [p.strip() for p in msg.content.split('|')]
        if len(parts) != 3:
            await ctx.send("❌ Invalid format. Use: `<duration> | <prize> | <number of winners>`")
            return
        duration_str, prize, winners_str = parts
        await run_giveaway(ctx, duration_str, prize, winners_str, ctx.author)

    @app_commands.command(name="giveaway", description="Start a giveaway (admin/owner only)")
    async def giveaway_slash(self, interaction: Interaction):
        if not (interaction.user.id == OWNER_ID or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("❌ This is an admin command only.", ephemeral=True)
            return
        await interaction.response.send_modal(GiveawayModal(self.bot, interaction))

async def setup(bot):
    await bot.add_cog(Giveaway(bot)) 