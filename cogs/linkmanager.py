import json
import re
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import Context

class LinkManager(commands.Cog, name="linkmanager"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.JSON_PATH = Path(__file__).parent / "forbidden_links.json"  # Initialize FIRST
        self.forbidden_links = self.load_links()  # Now can use self.JSON_PATH
        self.url_regex = re.compile(r"https?://\S+|www\.\S+")

    def normalize_domain(self, url: str) -> str:
        """Normalize the domain name by stripping schemes and 'www.'."""
        if not urlparse(url).scheme:
            url = 'http://' + url
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain

    def load_links(self):
        """Load forbidden links from JSON with per-guild storage."""
        if self.JSON_PATH.exists():
            with open(self.JSON_PATH, "r") as f:
                data = json.load(f)
                return {int(k): set(v) for k, v in data.items()}
        return {}

    def save_links(self):
        """Save forbidden links to JSON with per-guild storage."""
        with open(self.JSON_PATH, "w") as f:
            json.dump(
                {str(k): list(v) for k, v in self.forbidden_links.items()}, 
                f,
                indent=2
            )

    async def send_report(self, guild: discord.Guild, message: discord.Message, domain: str):
        """Send violation report to #reports channel."""
        report_channel = discord.utils.get(guild.text_channels, name="reports")
        if not report_channel:
            return

        embed = discord.Embed(
            title="Forbidden Link Detected",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.add_field(name="User", value=f"{message.author.mention}\n{message.author}", inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=False)
        embed.add_field(name="Forbidden Domain", value=f"`{domain}`", inline=False)
        embed.add_field(name="Message Content", value=f"```{message.content[:500]}```", inline=False)
        embed.add_field(name="Timestamp", value=f"<t:{int(message.created_at.timestamp())}:F>", inline=False)
        embed.set_footer(text=f"User ID: {message.author.id}")

        await report_channel.send(embed=embed)

    @commands.hybrid_command(name="addlink", description="Add a domain to the forbidden list")
    @commands.has_permissions(administrator=True)
    async def addlink(self, context: Context, link: str) -> None:
        guild_id = context.guild.id
        normalized = self.normalize_domain(link)
        
        if guild_id not in self.forbidden_links:
            self.forbidden_links[guild_id] = set()
            
        if normalized in self.forbidden_links[guild_id]:
            embed = discord.Embed(
                description=f"⚠️ `{normalized}` is already forbidden!",
                color=discord.Color.orange()
            )
            return await context.send(embed=embed, ephemeral=True)
            
        self.forbidden_links[guild_id].add(normalized)
        self.save_links()
        
        embed = discord.Embed(
            description=f"✅ Added `{normalized}` to forbidden domains",
            color=discord.Color.green()
        )
        await context.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="removelink", description="Remove a domain from the forbidden list")
    @commands.has_permissions(administrator=True)
    async def removelink(self, context: Context, link: str) -> None:
        guild_id = context.guild.id
        normalized = self.normalize_domain(link)
        
        if guild_id not in self.forbidden_links or normalized not in self.forbidden_links[guild_id]:
            embed = discord.Embed(
                description=f"⚠️ `{normalized}` isn't in the forbidden list!",
                color=discord.Color.orange()
            )
            return await context.send(embed=embed, ephemeral=True)
            
        self.forbidden_links[guild_id].remove(normalized)
        self.save_links()
        
        embed = discord.Embed(
            description=f"❌ Removed `{normalized}` from forbidden domains",
            color=discord.Color.red()
        )
        await context.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="listlinks", description="Show all forbidden domains for this server")
    async def listlinks(self, context: Context) -> None:
        guild_id = context.guild.id
        domains = self.forbidden_links.get(guild_id, set())
        
        if not domains:
            embed = discord.Embed(
                description="ℹ️ No forbidden domains set for this server!",
                color=discord.Color.blue()
            )
            return await context.send(embed=embed, ephemeral=True)
            
        embed = discord.Embed(
            title="Forbidden Domains",
            description="\n".join(f"• `{d}`" for d in sorted(domains)),
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Total domains: {len(domains)}")
        await context.send(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return
            
        guild_id = message.guild.id
        if guild_id not in self.forbidden_links:
            return
            
        forbidden_domains = self.forbidden_links[guild_id]
        found_urls = self.url_regex.findall(message.content)
        
        for url in found_urls:
            try:
                domain = self.normalize_domain(url)
                if domain in forbidden_domains:
                    await self.handle_forbidden_message(message, domain)
                    break  # Only process first violation
            except Exception as e:
                self.bot.logger.error(f"Error processing URL: {e}")

    async def handle_forbidden_message(self, message: discord.Message, domain: str):
        try:
            await message.delete()
            await self.send_report(message.guild, message, domain)
            
            # Send user warning
            embed = discord.Embed(
                description=f"⚠️ {message.author.mention}, forbidden domain `{domain}` detected!",
                color=discord.Color.orange()
            )
            warning = await message.channel.send(embed=embed, delete_after=10)
            
        except discord.Forbidden:
            self.bot.logger.error(f"Missing permissions in {message.guild.name}")
        except Exception as e:
            self.bot.logger.error(f"Error handling forbidden message: {e}")

async def setup(bot) -> None:
    await bot.add_cog(LinkManager(bot))
