# 🤖 Nexus Elite Discord Bot

A powerful, feature-rich Discord bot built with discord.py, optimized for Render deployment with QL and Discord database integration.

## 🚀 Features

- **24/7 Uptime** - Keep-alive system for Render deployment
- **Hybrid Commands** - Both prefix and slash commands
- **Advanced Moderation** - Comprehensive moderation tools
- **Economy System** - Virtual currency and shop
- **Leveling System** - User progression tracking
- **Automation** - Automated tasks and responses
- **Analytics** - Server statistics and insights
- **Entertainment** - Games and fun commands
- **Productivity** - Utility and management tools
- **Security** - Advanced security features

## 📋 Requirements

- Python 3.8+
- Discord Bot Token
- Render Account (for deployment)

## 🛠️ Installation

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd PROJECT-MANAGER
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   
   **Option A: Using .env file (for local development)**
   Create a `.env` file:
   ```
   TOKEN=your_discord_bot_token
   OWNER_ID=your_discord_user_id
   ```
   
   **Option B: Using config.json (for local development)**
   Update `config.json`:
   ```json
   {
     "token": "your_discord_bot_token",
     "owner_id": 1201050377911554061
   }
   ```
   
   **Option C: Environment variables (for production)**
   Set these in your deployment platform (Render, Heroku, etc.):
   - `TOKEN` - Your Discord bot token
   - `OWNER_ID` - Your Discord user ID

4. **Run the bot**
   ```bash
   python bot.py
   ```

### Render Deployment

1. **Connect your GitHub repository to Render**
2. **Set environment variables in Render:**
   - `TOKEN` - Your Discord bot token
   - `OWNER_ID` - Your Discord user ID
3. **Deploy automatically**

## 📁 Project Structure

```
PROJECT MANAGER/
├── bot.py                 # Main bot file
├── keep_alive.py          # Flask server for 24/7 uptime
├── requirements.txt       # Python dependencies
├── config.json           # Local configuration (not in git)
├── .env                  # Environment variables (not in git)
├── .gitignore           # Git ignore rules
├── README.md            # This file
└── cogs/                # Bot command modules
    ├── utility.py        # Utility commands
    ├── moderation.py     # Moderation commands
    ├── economy.py        # Economy system
    ├── leveling.py       # Leveling system
    ├── fun.py           # Entertainment commands
    ├── game.py          # Game commands
    ├── analytics.py     # Analytics and statistics
    ├── events.py        # Event management
    ├── ai.py            # AI-powered features
    ├── social.py        # Social features
    ├── weather.py       # Weather information
    ├── advanced.py      # Advanced features
    ├── entertainment.py # Entertainment features
    ├── security.py      # Security features
    ├── productivity.py  # Productivity tools
    ├── automation.py    # Automation features
    ├── announce.py      # Announcement system
    ├── giveaway.py      # Giveaway system
    ├── invites.py       # Invite tracking
    ├── config.py        # Configuration commands
    ├── voice.py         # Voice channel features
    ├── info.py          # Information commands
    ├── welcome.py       # Welcome system
    ├── logging.py       # Logging system
    ├── settings.py      # Settings management
    ├── automod.py       # Auto-moderation
    └── membercount.py   # Member count tracking
```

## 🔧 Configuration

## 🔒 Security

**⚠️ IMPORTANT: Never commit your bot token to Git!**

- ✅ **Environment Variables** - Use for production deployment
- ✅ **config.json** - Use for local development (not committed to Git)
- ✅ **.env file** - Use for local development (not committed to Git)
- ❌ **Never hardcode tokens** in your source code

**Safe token handling:**
1. **For Render/Production:** Set `TOKEN` and `OWNER_ID` as environment variables
2. **For Local Development:** Use `config.json` or `.env` file
3. **Git Safety:** Both `config.json` and `.env` are in `.gitignore`

### Environment Variables

- `TOKEN` - Discord bot token (required)
- `OWNER_ID` - Bot owner's Discord user ID (required)

### Local Development

Create a `config.json` file for local development:
```json
{
    "token": "your_discord_bot_token",
    "owner_id": "your_discord_user_id"
}
```

## 🎯 Commands

### Core Commands
- `-help` - Show help menu
- `-sync` - Sync slash commands
- `-info` - Bot information

### Moderation
- `-ban` - Ban a user
- `-kick` - Kick a user
- `-mute` - Mute a user
- `-clear` - Clear messages

### Economy
- `-balance` - Check balance
- `-daily` - Daily reward
- `-work` - Work for money
- `-shop` - View shop

### Fun
- `-8ball` - Magic 8-ball
- `-coinflip` - Flip a coin
- `-roll` - Roll dice
- `-joke` - Get a joke

## 🚀 Deployment

### Render Deployment

1. **Fork/Clone this repository**
2. **Connect to Render**
3. **Set environment variables:**
   - `TOKEN` - Your Discord bot token
   - `OWNER_ID` - Your Discord user ID
4. **Deploy**

The bot will automatically:
- Start the Flask keep-alive server
- Load all command modules
- Connect to Discord
- Stay online 24/7

## 📊 Database

This bot uses:
- **QL Database** - For persistent data storage
- **Discord** - For real-time data and caching
- **SQLite** - For local development

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

If you need help:
1. Check the documentation
2. Open an issue on GitHub
3. Contact the bot owner

---

**Made with ❤️ for the Discord community** 