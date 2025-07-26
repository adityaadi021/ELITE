import discord
from discord.ext import commands
from discord import app_commands, Interaction, ui
from datetime import datetime
import aiosqlite
import asyncio
from bot import modern_embed

OWNER_ID = 1201050377911554061

# Permission check
async def is_admin(ctx):
    if ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator:
        return True
    async with aiosqlite.connect('database.db') as db:
        async with db.execute('SELECT user_id FROM server_owners WHERE guild_id = ? AND user_id = ?', (ctx.guild.id, ctx.author.id)) as cursor:
            return await cursor.fetchone() is not None

def styled_embed(title, description, color, image_url=None, ctx=None):
    embed = discord.Embed(
        title=title or None,
        description=description or None,
        color=color or discord.Color.blurple(),
        timestamp=datetime.utcnow()
    )
    if image_url:
        embed.set_image(url=image_url)
    # Always show a professional moderation/support footer
    embed.set_footer(text="For support, contact the official server staff.")
    return embed

class ChannelSelectView(ui.View):
    def __init__(self, ctx, channels, timeout=60):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.selected_channel = None
        options = [discord.SelectOption(label=ch.name, value=str(ch.id)) for ch in channels]
        self.select = ui.Select(placeholder="Select a channel to announce in...", options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)
    async def select_callback(self, interaction: Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't select for this command.", ephemeral=True)
            return
        self.selected_channel = int(self.select.values[0])
        self.stop()
        await interaction.response.defer()

class AnnounceModal(ui.Modal, title="Send Announcement"):
    message_input = ui.TextInput(label="Announcement Text (optional)", style=discord.TextStyle.paragraph, required=False, max_length=2000)
    image_url = ui.TextInput(label="Image URL (optional)", required=False)
    # File upload not supported in modals, so will handle in followup
    def __init__(self, bot, interaction, channel_id):
        super().__init__()
        self.bot = bot
        self.interaction = interaction
        self.channel_id = channel_id
    async def on_submit(self, interaction: Interaction):
        channel = interaction.guild.get_channel(self.channel_id)
        text = self.message_input.value.strip()
        if text.lower() == 'skip':
            text = None
        image_url = self.image_url.value.strip() if self.image_url.value else None
        if image_url and image_url.lower() == 'skip':
            image_url = None
        # After modal, check for file upload in followup
        await interaction.response.send_message("If you want to upload an image, reply here with the file or type 'skip'.", ephemeral=True)
        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            file_url = msg.attachments[0].url if msg.attachments else None
            if msg.content and msg.content.strip().lower() == 'skip':
                file_url = None
        except asyncio.TimeoutError:
            file_url = None
        # Ask for mention
        await interaction.followup.send("Do you want to @everyone or @here mention? (type 'everyone', 'here', or 'no'):", ephemeral=True)
        try:
            mention_msg = await self.bot.wait_for('message', check=check, timeout=30)
            mention_choice = mention_msg.content.strip().lower()
            mention = ''
            if mention_choice == 'everyone':
                mention = '@everyone\n'
            elif mention_choice == 'here':
                mention = '@here\n'
        except asyncio.TimeoutError:
            mention = ''
        # At least one of text, image_url, or file_url must be present
        if not (text or image_url or file_url):
            await interaction.followup.send("❌ You must provide at least text or an image.", ephemeral=True)
            return
        embed = modern_embed(
            description=f"{mention}{text if text else ''}",
            color=discord.Color.blurple(),
            emoji="📢",
            thumbnail=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None,
            ctx=interaction
        )
        if image_url or file_url:
            embed.set_image(url=image_url or file_url)
        await channel.send(embed=embed)
        await interaction.followup.send("✅ Announcement sent!", ephemeral=True)

class DMUserModal(ui.Modal, title="DM a User"):
    user_id = ui.TextInput(label="User ID", required=True)
    message_input = ui.TextInput(label="Message", style=discord.TextStyle.paragraph, required=True)
    image_url = ui.TextInput(label="Image URL (optional)", required=False)

    def __init__(self, bot, interaction):
        super().__init__()
        self.bot = bot
        self.interaction = interaction

    async def on_submit(self, interaction: Interaction):
        user = await self.bot.fetch_user(int(self.user_id.value))
        embed = modern_embed(
            description=self.message_input.value,
            color=discord.Color.blurple(),
            emoji="✉️",
            thumbnail=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None,
            ctx=interaction
        )
        if self.image_url.value:
            embed.set_image(url=self.image_url.value)
        if interaction.guild:
            embed.set_author(name=f"Message from {interaction.guild.name} 📩")
        try:
            await user.send(embed=embed)
            await interaction.response.send_message(f"✅ DM sent to {user.mention}", ephemeral=True)
        except Exception:
            await interaction.response.send_message(f"❌ Could not DM user.", ephemeral=True)

class Announce(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Prefix command: announce
    @commands.hybrid_command(name="announce", description="Send an announcement as an embed.")
    async def announce(self, ctx):
        if not await is_admin(ctx):
            if isinstance(ctx, discord.Interaction):
                await ctx.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            else:
                await ctx.send("❌ You do not have permission to use this command.", reference=ctx.message, mention_author=True)
            return
        
        # List all text channels
        text_channels = [ch for ch in ctx.guild.text_channels if ch.permissions_for(ctx.author).send_messages]
        if not text_channels:
            if isinstance(ctx, discord.Interaction):
                await ctx.response.send_message("❌ No channels available to announce in.", ephemeral=True)
            else:
                await ctx.send("❌ No channels available to announce in.", reference=ctx.message, mention_author=True)
            return
        
        if isinstance(ctx, discord.Interaction):
            # Slash command - use modal
            class ChannelDropdown(ui.Select):
                def __init__(self, channels):
                    options = [discord.SelectOption(label=ch.name, value=str(ch.id)) for ch in channels]
                    super().__init__(placeholder="Select a channel...", options=options)
                async def callback(self2, i: Interaction):
                    await i.response.defer()
                    self2.view.selected_channel = int(self2.values[0])
                    self2.view.stop()
            class ChannelDropdownView(ui.View):
                def __init__(self, channels):
                    super().__init__(timeout=60)
                    self.selected_channel = None
                    self.add_item(ChannelDropdown(channels))
            view = ChannelDropdownView(text_channels)
            await ctx.response.send_message("Select a channel to send the announcement:", view=view, ephemeral=True)
            await view.wait()
            if not view.selected_channel:
                await ctx.followup.send("❌ No channel selected. Announcement cancelled.", ephemeral=True)
                return
            channel_id = view.selected_channel
            # Show modal for text and image URL
            await ctx.followup.send_modal(AnnounceModal(self.bot, ctx, channel_id))
        else:
            # Prefix command - use interactive prompt
            view = ChannelSelectView(ctx, text_channels)
            msg = await ctx.send("Select a channel to send the announcement:", view=view)
            await view.wait()
            await msg.edit(view=None)
            if not view.selected_channel:
                await ctx.send("❌ No channel selected. Announcement cancelled.", reference=ctx.message, mention_author=True)
                return
            channel = ctx.guild.get_channel(view.selected_channel)
            await ctx.send("Type the announcement text (or type 'skip' to leave blank):")
            def check(m): return m.author == ctx.author and m.channel == ctx.channel
            try:
                text_msg = await self.bot.wait_for('message', check=check, timeout=120)
                text_content = text_msg.content.strip().lower()
                text = None if text_content == 'skip' else text_msg.content
                await ctx.send("Upload an image or provide an image URL (or type 'skip' to leave blank):")
                img_msg = await self.bot.wait_for('message', check=check, timeout=60)
                image_url = None
                if img_msg.attachments:
                    image_url = img_msg.attachments[0].url
                elif img_msg.content and img_msg.content.strip().lower() == 'skip':
                    image_url = None
                elif img_msg.content:
                    image_url = img_msg.content.strip()
                await ctx.send("Do you want to @everyone or @here mention? (type 'everyone', 'here', or 'no'):")
                mention_msg = await self.bot.wait_for('message', check=check, timeout=30)
                mention_choice = mention_msg.content.strip().lower()
                mention = ''
                if mention_choice == 'everyone':
                    mention = '@everyone\n'
                elif mention_choice == 'here':
                    mention = '@here\n'
                # At least one of text or image_url must be present
                if not (text or image_url):
                    await ctx.send("❌ You must provide at least text or an image.", reference=ctx.message, mention_author=True)
                    return
                # Full-width embed: no title, just description and image
                embed = modern_embed(
                    description=f"{mention}{text if text else ''}",
                    color=discord.Color.blurple(),
                    emoji="📢",
                    thumbnail=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None,
                    ctx=ctx
                )
                if image_url:
                    embed.set_image(url=image_url)
                embed.set_footer(text="For support, contact the official server staff.")
                await channel.send(embed=embed)
                await ctx.send("✅ Announcement sent!", reference=ctx.message, mention_author=True)
            except asyncio.TimeoutError:
                await ctx.send("❌ Timed out. Announcement cancelled.", reference=ctx.message, mention_author=True)

    # Slash command: announce
    @app_commands.command(name="announce", description="Send an announcement as an embed.")
    async def announce_slash(self, interaction: Interaction):
        if not (interaction.user.id == interaction.guild.owner_id or interaction.user.guild_permissions.administrator):
            # Check server-level bot owner
            async with aiosqlite.connect('database.db') as db:
                async with db.execute('SELECT user_id FROM server_owners WHERE guild_id = ? AND user_id = ?', (interaction.guild.id, interaction.user.id)) as cursor:
                    if not await cursor.fetchone():
                        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
                        return
        # List all text channels
        text_channels = [ch for ch in interaction.guild.text_channels if ch.permissions_for(interaction.user).send_messages]
        if not text_channels:
            await interaction.response.send_message("❌ No channels available to announce in.", ephemeral=True)
            return
        # Show dropdown for channel selection
        class ChannelDropdown(ui.Select):
            def __init__(self, channels):
                options = [discord.SelectOption(label=ch.name, value=str(ch.id)) for ch in channels]
                super().__init__(placeholder="Select a channel...", options=options)
            async def callback(self2, i: Interaction):
                await i.response.defer()
                self2.view.selected_channel = int(self2.values[0])
                self2.view.stop()
        class ChannelDropdownView(ui.View):
            def __init__(self, channels):
                super().__init__(timeout=60)
                self.selected_channel = None
                self.add_item(ChannelDropdown(channels))
        view = ChannelDropdownView(text_channels)
        await interaction.response.send_message("Select a channel to send the announcement:", view=view, ephemeral=True)
        await view.wait()
        if not view.selected_channel:
            await interaction.followup.send("❌ No channel selected. Announcement cancelled.", ephemeral=True)
            return
        channel_id = view.selected_channel
        # Show modal for text and image URL
        await interaction.followup.send_modal(AnnounceModal(self.bot, interaction, channel_id))

    # Prefix command: dmuser
    @commands.command(name="dmuser", description="DM a user with a custom message.")
    async def dmuser(self, ctx, user: discord.User = None):
        if not await is_admin(ctx):
            await ctx.send("❌ You do not have permission to use this command.", reference=ctx.message, mention_author=True)
            return
        # Ask for user mention if not provided
        if not user:
            await ctx.send("Please mention the user you want to DM (e.g. @username):", reference=ctx.message, mention_author=True)
            def check_user(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.mentions
            try:
                user_msg = await self.bot.wait_for('message', check=check_user, timeout=60)
                user = user_msg.mentions[0]
            except asyncio.TimeoutError:
                await ctx.send("❌ Timed out waiting for user mention. DM cancelled.", reference=ctx.message, mention_author=True)
                return
            except Exception:
                await ctx.send("❌ Invalid user mention.", reference=ctx.message, mention_author=True)
                return
        await ctx.send("Now reply with the message to send:")
        def check_msg(m): return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg_msg = await self.bot.wait_for('message', check=check_msg, timeout=180)
            await ctx.send("Upload an image to include, or type 'skip' to send without an image:")
            def check_img(m):
                return m.author == ctx.author and m.channel == ctx.channel and (m.attachments or m.content.lower() == 'skip')
            img_msg = await self.bot.wait_for('message', check=check_img, timeout=60)
            image_url = None
            if img_msg.attachments:
                image_url = img_msg.attachments[0].url
            elif img_msg.content.lower() == 'skip':
                image_url = None
            else:
                await ctx.send("❌ Please upload an image file or type 'skip'. DM cancelled.", reference=ctx.message, mention_author=True)
                return
            embed = modern_embed(
                description=msg_msg.content,
                color=discord.Color.blurple(),
                emoji="✉️",
                thumbnail=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None,
                ctx=ctx
            )
            if image_url:
                embed.set_image(url=image_url)
            if ctx.guild:
                embed.set_author(name=f"Message from {ctx.guild.name} 📩")
            await user.send(embed=embed)
            await ctx.send(f"✅ DM sent to {user.mention}", reference=ctx.message, mention_author=True)
        except asyncio.TimeoutError:
            await ctx.send("❌ Timed out. DM cancelled.", reference=ctx.message, mention_author=True)
        except Exception:
            await ctx.send("❌ Could not DM user.", reference=ctx.message, mention_author=True)

    # Slash command: dmuser
    @app_commands.command(name="dmuser", description="DM a user with a custom message.")
    @app_commands.describe(
        user="User to DM",
        message="Message text (optional)",
        attachment="Image or file to include (optional)"
    )
    async def dmuser_slash(self, interaction: Interaction, user: discord.User, message: str = None, attachment: discord.Attachment = None):
        if not (interaction.user.id == interaction.guild.owner_id or interaction.user.guild_permissions.administrator):
            # Check server-level bot owner
            async with aiosqlite.connect('database.db') as db:
                async with db.execute('SELECT user_id FROM server_owners WHERE guild_id = ? AND user_id = ?', (interaction.guild.id, interaction.user.id)) as cursor:
                    if not await cursor.fetchone():
                        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
                        return
        if not message and not attachment:
            await interaction.response.send_message("❌ You must provide at least text or an attachment.", ephemeral=True)
            return
        embed = modern_embed(
            description=message or None,
            color=discord.Color.blurple(),
            emoji="✉️",
            thumbnail=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None,
            ctx=interaction
        )
        if attachment:
            embed.set_image(url=attachment.url)
        embed.set_footer(text=f"From {interaction.guild.name} • Requested by {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        try:
            await user.send(embed=embed)
            await interaction.response.send_message(f"✅ DM sent to {user.mention}", ephemeral=True)
        except Exception:
            await interaction.response.send_message(f"❌ Could not DM user.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Announce(bot)) 
