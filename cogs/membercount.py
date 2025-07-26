import os

async def update_membercount_channel(guild):
    try:
        if not os.path.exists("membercount_channel.txt"):
            return
        with open("membercount_channel.txt", "r") as f:
            channel_id = int(f.read().strip())
        channel = guild.get_channel(channel_id)
        if channel:
            await channel.edit(name=f"Members: {guild.member_count}")
    except Exception:
        pass 