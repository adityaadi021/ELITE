import discord
from discord.ext import commands
from bot import modern_embed
import aiosqlite
import random
from datetime import datetime

class Weather(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def init_database(self):
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS weather_favorites 
                               (user_id INTEGER, guild_id INTEGER, city TEXT,
                                PRIMARY KEY (user_id, guild_id))''')
            await db.execute('''CREATE TABLE IF NOT EXISTS weather_alerts 
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER, guild_id INTEGER, city TEXT,
                                alert_type TEXT, threshold TEXT, created_at TEXT)''')
            await db.commit()

    async def cog_load(self):
        """Async initialization when cog loads"""
        await self.init_database()

    async def get_weather_data(self, city: str):
        """Simulate weather data (in real implementation, connect to weather API)"""
        # Simulate weather data
        weather_conditions = ["Sunny", "Cloudy", "Rainy", "Snowy", "Stormy", "Foggy", "Clear"]
        temp = random.randint(10, 30)
        
        return {
            "city": city.title(),
            "condition": random.choice(weather_conditions),
            "temperature": temp,
            "humidity": random.randint(40, 90),
            "wind_speed": random.randint(5, 25),
            "pressure": random.randint(1000, 1020),
            "visibility": random.randint(5, 15),
            "sunrise": "06:30",
            "sunset": "18:45",
            "forecast": [
                {"day": "Today", "condition": random.choice(weather_conditions), "temp": temp},
                {"day": "Tomorrow", "condition": random.choice(weather_conditions), "temp": temp + random.randint(-3, 3)},
                {"day": "Day 3", "condition": random.choice(weather_conditions), "temp": temp + random.randint(-5, 5)},
                {"day": "Day 4", "condition": random.choice(weather_conditions), "temp": temp + random.randint(-7, 7)},
                {"day": "Day 5", "condition": random.choice(weather_conditions), "temp": temp + random.randint(-10, 10)}
            ]
        }

    @commands.command(name="weather", description="Get weather information for a city.")
    async def get_weather(self, ctx, *, city: str):
        """Get weather information for a specific city"""
        # Get weather data
        weather_data = await self.get_weather_data(city)
        
        # Create weather embed
        embed = modern_embed(
            title=f"🌤️ Weather in {weather_data['city']}",
            description=f"Current weather conditions",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        # Current weather
        condition_emoji = {
            "Sunny": "☀️",
            "Cloudy": "☁️",
            "Rainy": "🌧️",
            "Snowy": "❄️",
            "Stormy": "⛈️",
            "Foggy": "🌫️",
            "Clear": "🌙"
        }
        
        emoji = condition_emoji.get(weather_data['condition'], "🌤️")
        
        embed.add_field(
            name=f"{emoji} Current Weather",
            value=f"**Condition:** {weather_data['condition']}\n"
                  f"**Temperature:** {weather_data['temperature']}°C\n"
                  f"**Humidity:** {weather_data['humidity']}%\n"
                  f"**Wind Speed:** {weather_data['wind_speed']} km/h\n"
                  f"**Pressure:** {weather_data['pressure']} hPa\n"
                  f"**Visibility:** {weather_data['visibility']} km",
            inline=True
        )
        
        # Sun times
        embed.add_field(
            name="🌅 Sun Times",
            value=f"**Sunrise:** {weather_data['sunrise']}\n"
                  f"**Sunset:** {weather_data['sunset']}",
            inline=True
        )
        
        # 5-day forecast
        forecast_text = ""
        for day in weather_data['forecast'][:3]:  # Show next 3 days
            day_emoji = condition_emoji.get(day['condition'], "🌤️")
            forecast_text += f"{day_emoji} **{day['day']}:** {day['condition']}, {day['temp']}°C\n"
        
        embed.add_field(
            name="📅 3-Day Forecast",
            value=forecast_text,
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="forecast", description="Get detailed weather forecast.")
    async def get_forecast(self, ctx, *, city: str):
        """Get detailed weather forecast for a city"""
        weather_data = await self.get_weather_data(city)
        
        embed = modern_embed(
            title=f"📅 5-Day Forecast for {weather_data['city']}",
            description="Detailed weather forecast",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        condition_emoji = {
            "Sunny": "☀️",
            "Cloudy": "☁️",
            "Rainy": "🌧️",
            "Snowy": "❄️",
            "Stormy": "⛈️",
            "Foggy": "🌫️",
            "Clear": "🌙"
        }
        
        for day in weather_data['forecast']:
            emoji = condition_emoji.get(day['condition'], "🌤️")
            embed.add_field(
                name=f"{emoji} {day['day']}",
                value=f"**Condition:** {day['condition']}\n"
                      f"**Temperature:** {day['temp']}°C",
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="setweather", description="Set your favorite city for weather.")
    async def set_favorite_city(self, ctx, *, city: str):
        """Set your favorite city for weather"""
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT OR REPLACE INTO weather_favorites 
                               (user_id, guild_id, city)
                               VALUES (?, ?, ?)''',
                           (ctx.author.id, ctx.guild.id, city))
            await db.commit()
        
        await ctx.send(embed=modern_embed(
            title="✅ Favorite City Set",
            description=f"Your favorite city has been set to **{city}**\n\n"
                       f"Use `!myweather` to get weather for your favorite city.",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.command(name="myweather", description="Get weather for your favorite city.")
    async def get_favorite_weather(self, ctx):
        """Get weather for your favorite city"""
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT city FROM weather_favorites 
                                   WHERE user_id = ? AND guild_id = ?''',
                                (ctx.author.id, ctx.guild.id)) as cursor:
                result = await cursor.fetchone()
        
        if not result:
            await ctx.send(embed=modern_embed(
                title="❌ No Favorite City",
                description="You haven't set a favorite city yet.\n\n"
                           f"Use `!setweather [city]` to set your favorite city.",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        city = result[0]
        weather_data = await self.get_weather_data(city)
        
        embed = modern_embed(
            title=f"🌤️ Weather in {weather_data['city']} (Your Favorite)",
            description="Current weather for your favorite city",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        condition_emoji = {
            "Sunny": "☀️",
            "Cloudy": "☁️",
            "Rainy": "🌧️",
            "Snowy": "❄️",
            "Stormy": "⛈️",
            "Foggy": "🌫️",
            "Clear": "🌙"
        }
        
        emoji = condition_emoji.get(weather_data['condition'], "🌤️")
        
        embed.add_field(
            name=f"{emoji} Current Weather",
            value=f"**Condition:** {weather_data['condition']}\n"
                  f"**Temperature:** {weather_data['temperature']}°C\n"
                  f"**Humidity:** {weather_data['humidity']}%\n"
                  f"**Wind Speed:** {weather_data['wind_speed']} km/h",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="weatheralert", description="Set a weather alert.")
    async def set_weather_alert(self, ctx, city: str, alert_type: str, threshold: str):
        """Set a weather alert for a city"""
        valid_types = ["temperature", "humidity", "wind", "rain"]
        if alert_type.lower() not in valid_types:
            await ctx.send(embed=modern_embed(
                title="❌ Invalid Alert Type",
                description=f"Valid alert types: {', '.join(valid_types)}",
                color=discord.Color.red(),
                ctx=ctx
            ))
            return
        
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''INSERT INTO weather_alerts 
                               (user_id, guild_id, city, alert_type, threshold, created_at)
                               VALUES (?, ?, ?, ?, ?, ?)''',
                           (ctx.author.id, ctx.guild.id, city, alert_type.lower(),
                            threshold, datetime.utcnow().isoformat()))
            await db.commit()
        
        await ctx.send(embed=modern_embed(
            title="⏰ Weather Alert Set",
            description=f"Alert set for **{city}**\n"
                       f"**Type:** {alert_type.title()}\n"
                       f"**Threshold:** {threshold}",
            color=discord.Color.green(),
            ctx=ctx
        ))

    @commands.command(name="weatheralerts", description="List your weather alerts.")
    async def list_weather_alerts(self, ctx):
        """List all your weather alerts"""
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('''SELECT city, alert_type, threshold, created_at
                                   FROM weather_alerts 
                                   WHERE user_id = ? AND guild_id = ?
                                   ORDER BY created_at DESC''',
                                (ctx.author.id, ctx.guild.id)) as cursor:
                alerts = await cursor.fetchall()
        
        if not alerts:
            await ctx.send(embed=modern_embed(
                title="📋 No Weather Alerts",
                description="You don't have any weather alerts set.",
                color=discord.Color.blue(),
                ctx=ctx
            ))
            return
        
        embed = modern_embed(
            title="⏰ Your Weather Alerts",
            description=f"Found {len(alerts)} alert(s):",
            color=discord.Color.blue(),
            ctx=ctx
        )
        
        for city, alert_type, threshold, created_at in alerts:
            created_dt = datetime.fromisoformat(created_at)
            embed.add_field(
                name=f"🌤️ {city.title()}",
                value=f"**Type:** {alert_type.title()}\n"
                      f"**Threshold:** {threshold}\n"
                      f"**Set:** {created_dt.strftime('%Y-%m-%d %H:%M')}",
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="weathermap", description="Get weather map information.")
    async def get_weather_map(self, ctx, *, city: str):
        """Get weather map information for a city"""
        # Simulate weather map data
        await ctx.send(embed=modern_embed(
            title="🗺️ Weather Map",
            description=f"Weather map data for **{city.title()}**\n\n"
                       f"*Weather map functionality would be implemented here in a real application.*",
            color=discord.Color.blue(),
            ctx=ctx
        ))

    @commands.command(name="airquality", description="Get air quality information.")
    async def get_air_quality(self, ctx, *, city: str):
        """Get air quality information for a city"""
        # Simulate air quality data
        aqi = random.randint(1, 500)
        
        if aqi <= 50:
            quality = "Good"
            color = discord.Color.green()
            emoji = "🟢"
        elif aqi <= 100:
            quality = "Moderate"
            color = discord.Color.yellow()
            emoji = "🟡"
        elif aqi <= 150:
            quality = "Unhealthy for Sensitive Groups"
            color = discord.Color.orange()
            emoji = "🟠"
        elif aqi <= 200:
            quality = "Unhealthy"
            color = discord.Color.red()
            emoji = "🔴"
        elif aqi <= 300:
            quality = "Very Unhealthy"
            color = discord.Color.purple()
            emoji = "🟣"
        else:
            quality = "Hazardous"
            color = discord.Color.dark_red()
            emoji = "🟤"
        
        embed = modern_embed(
            title=f"🌬️ Air Quality in {city.title()}",
            description=f"Current air quality information",
            color=color,
            ctx=ctx
        )
        
        embed.add_field(
            name=f"{emoji} Air Quality Index",
            value=f"**AQI:** {aqi}\n"
                  f"**Quality:** {quality}\n"
                  f"**Status:** {emoji}",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Weather(bot)) 