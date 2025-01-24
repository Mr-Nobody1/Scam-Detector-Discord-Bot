# Mod Radar Discord Bot

A feature-rich Discord bot with moderation tools, fun commands, AI chat capabilities, and cryptocurrency monitoring features.

## Features

- **AI-Powered Chat**: DeepSeek integration for intelligent conversation handling
- **Moderation Tools**:
  - Kick/Ban/Warn system
  - Message purging
  - Link management & filtering
  - Warning system with tracking
- **Cryptocurrency Support**:
  - Bitcoin price tracking
  - Automated crypto help threads
- **Fun Commands**:
  - Cat memes
  - 8ball predictions
  - Coin flip
  - Rock-paper-scissors
- **Utility Features**:
  - Server/user analytics
  - Feedback system
  - Thread archiving
  - Custom logging

## Prerequisites

- Python 3.9+
- Discord bot token
- DeepSeek API key (for chat features)
- [Required Discord Intents](https://discordpy.readthedocs.io/en/stable/intents.html):
  - Message Content
  - Members
  - Presences

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/mod-radar-bot.git
cd mod-radar-bot

# Install dependencies
pip install -r requirements.txt

# Configure bot
cp config.example.json config.json
```

## Configuration

1. Edit `config.json`:
```json
{
  "prefix": "!",
  "invite_link": "your-bot-invite-link"
}
```

2. Add your credentials to `.env`:
```
TOKEN=your-discord-token
```

3. For chat features, update the DeepSeek API key in `cogs/chat.py`

## Command Overview

### General Commands
- `help` - List all commands
- `ping` - Check bot latency
- `serverinfo` - Display server statistics
- `userinfo` - Get user details
- `bitcoin` - Show current BTC price

### Moderation Commands
- `kick` - Remove user from server
- `ban` - Permanently ban user
- `warn` - Issue user warning
- `purge` - Bulk delete messages
- `addlink` - Block malicious URLs

### Fun Commands
- `catmeme` - Random cat meme
- `coinflip` - Virtual coin toss
- `8ball` - Magic 8ball predictions
- `randomfact` - Interesting trivia

### Crypto Features
- Automatic thread creation for help requests
- Cost tracking for AI interactions
- Real-time price monitoring

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -m 'Add new feature'`)
4. Push to branch (`git push origin feature/improvement`)
5. Open Pull Request
