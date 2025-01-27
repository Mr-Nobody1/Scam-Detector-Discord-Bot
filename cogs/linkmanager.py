import json
import re
import logging
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
import discord
from discord.ext import commands
from discord.ext.commands import Context

# Configure logger for this cog
logger = logging.getLogger(__name__)

class LinkManager(commands.Cog, name="linkmanager"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.logger = logger
        self.JSON_PATH = Path(__file__).parent / "forbidden_links.json"
        self.forbidden_links = self.load_links()
        self.url_regex = re.compile(r"https?://\S+|www\.\S+")
        self.logger.info("LinkManager cog initialized successfully")

    def normalize_domain(self, url: str) -> str:
        """Normalize a URL to its base domain form."""
        try:
            if not urlparse(url).scheme:
                url = f'http://{url}'
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            self.logger.debug(f"Normalized domain: {url} -> {domain}")
            return domain
        except Exception as e:
            self.logger.error(f"Domain normalization failed for {url}: {str(e)}", exc_info=True)
            raise

    def load_links(self):
        """Load forbidden links from JSON file with guild-specific storage."""
        try:
            if self.JSON_PATH.exists():
                with open(self.JSON_PATH, 'r') as f:
                    data = json.load(f)
                    self.logger.info(f"Loaded forbidden links from {self.JSON_PATH}")
                    return {int(k): set(v) for k, v in data.items()}
            self.logger.info("No existing forbidden links file found, starting fresh")
            return {}
        except Exception as e:
            self.logger.critical(f"Failed to load links: {str(e)}", exc_info=True)
            return {}

    def save_links(self):
        """Save forbidden links to JSON file with guild-specific storage."""
        try:
            with open(self.JSON_PATH, 'w') as f:
                json.dump(
                    {str(k): list(v) for k, v in self.forbidden_links.items()},
                    f,
                    indent=2
                )
            self.logger.info(f"Successfully saved links to {self.JSON_PATH}")
        except Exception as e:
            self.logger.error(f"Failed to save links: {str(e)}", exc_info=True)
            raise

    async def send_report(self, guild: discord.Guild, message: discord.Message, domain: str):
        """Send violation report to the designated reports channel."""
        try:
            report_channel = discord.utils.get(guild.text_channels, name='reports')
            if not report_channel:
                self.logger.warning(f"Reports channel not found in {guild.name} (ID: {guild.id})")
                return

            embed = discord.Embed(
                title="🚨 Forbidden Link Detected",
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
            self.logger.info(f"Sent violation report for {domain} in {guild.name} (ID: {guild.id})")
        except Exception as e:
            self.logger.error(f"Failed to send report: {str(e)}", exc_info=True)
            raise

    @commands.hybrid_command(name="addlink", description="Add a domain to the forbidden list")
    @commands.has_permissions(administrator=True)
    async def addlink(self, context: Context, link: str) -> None:
        """Add a domain to the server's forbidden list."""
        try:
            guild_id = context.guild.id
            normalized = self.normalize_domain(link)
            self.logger.info(f"Addlink command invoked by {context.author} (ID: {context.author.id}) for domain: {normalized}")

            if guild_id not in self.forbidden_links:
                self.forbidden_links[guild_id] = set()
                self.logger.debug(f"Created new entry for guild ID: {guild_id}")

            if normalized in self.forbidden_links[guild_id]:
                embed = discord.Embed(
                    description=f"⚠️ `{normalized}` is already forbidden!",
                    color=discord.Color.orange()
                )
                self.logger.warning(f"Duplicate domain attempt: {normalized} in guild ID: {guild_id}")
                return await context.send(embed=embed, ephemeral=True)

            self.forbidden_links[guild_id].add(normalized)
            self.save_links()

            embed = discord.Embed(
                description=f"✅ Added `{normalized}` to forbidden domains",
                color=discord.Color.green()
            )
            self.logger.info(f"Successfully added domain: {normalized} to guild ID: {guild_id}")
            await context.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Addlink command failed: {str(e)}", exc_info=True)
            await context.send("❌ An error occurred while processing your request.", ephemeral=True)

    @commands.hybrid_command(name="removelink", description="Remove a domain from the forbidden list")
    @commands.has_permissions(administrator=True)
    async def removelink(self, context: Context, link: str) -> None:
        """Remove a domain from the server's forbidden list."""
        try:
            guild_id = context.guild.id
            normalized = self.normalize_domain(link)
            self.logger.info(f"Removelink command invoked by {context.author} (ID: {context.author.id}) for domain: {normalized}")

            if guild_id not in self.forbidden_links or normalized not in self.forbidden_links[guild_id]:
                embed = discord.Embed(
                    description=f"⚠️ `{normalized}` isn't in the forbidden list!",
                    color=discord.Color.orange()
                )
                self.logger.warning(f"Domain not found attempt: {normalized} in guild ID: {guild_id}")
                return await context.send(embed=embed, ephemeral=True)

            self.forbidden_links[guild_id].remove(normalized)
            self.save_links()

            embed = discord.Embed(
                description=f"❌ Removed `{normalized}` from forbidden domains",
                color=discord.Color.red()
            )
            self.logger.info(f"Successfully removed domain: {normalized} from guild ID: {guild_id}")
            await context.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Removelink command failed: {str(e)}", exc_info=True)
            await context.send("❌ An error occurred while processing your request.", ephemeral=True)

    @commands.hybrid_command(name="listlinks", description="Show all forbidden domains for this server")
    async def listlinks(self, context: Context) -> None:
        """List all forbidden domains for the current server."""
        try:
            guild_id = context.guild.id
            self.logger.info(f"Listlinks command invoked by {context.author} (ID: {context.author.id})")

            domains = self.forbidden_links.get(guild_id, set())
            if not domains:
                embed = discord.Embed(
                    description="ℹ️ No forbidden domains set for this server!",
                    color=discord.Color.blue()
                )
                self.logger.debug(f"No domains found for guild ID: {guild_id}")
                return await context.send(embed=embed, ephemeral=True)

            embed = discord.Embed(
                title="Forbidden Domains",
                description="\n".join(f"• `{d}`" for d in sorted(domains)),
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Total domains: {len(domains)}")
            self.logger.debug(f"Displayed {len(domains)} domains for guild ID: {guild_id}")
            await context.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Listlinks command failed: {str(e)}", exc_info=True)
            await context.send("❌ An error occurred while fetching the domain list.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Automatically scan messages for forbidden domains."""
        try:
            if message.author.bot or not message.guild:
                return

            guild_id = message.guild.id
            self.logger.debug(f"Scanning message from {message.author} (ID: {message.author.id}) in guild ID: {guild_id}")

            if guild_id not in self.forbidden_links:
                return

            forbidden_domains = self.forbidden_links[guild_id]
            found_urls = self.url_regex.findall(message.content)
            self.logger.debug(f"Found {len(found_urls)} URLs in message from {message.author}")

            for url in found_urls:
                try:
                    domain = self.normalize_domain(url)
                    self.logger.debug(f"Checking URL: {url} → Normalized: {domain}")

                    if domain in forbidden_domains:
                        self.logger.warning(f"Found forbidden domain {domain} in message from {message.author}")
                        await self.handle_forbidden_message(message, domain)
                        break  # Only process first violation

                except Exception as e:
                    self.logger.error(f"URL processing error: {str(e)}", exc_info=True)

        except Exception as e:
            self.logger.error(f"Message scanning failed: {str(e)}", exc_info=True)

    async def handle_forbidden_message(self, message: discord.Message, domain: str):
        """Handle messages containing forbidden domains."""
        try:
            self.logger.info(f"Deleting forbidden message containing {domain} from {message.author}")
            await message.delete()

            self.logger.debug(f"Sending report for {domain} violation by {message.author}")
            await self.send_report(message.guild, message, domain)

            # Send user warning
            embed = discord.Embed(
                description=f"⚠️ {message.author.mention}, forbidden domain `{domain}` detected!",
                color=discord.Color.orange()
            )
            await message.channel.send(embed=embed, delete_after=10)
            self.logger.info(f"Sent user warning for {domain} violation to {message.author}")

        except discord.Forbidden:
            self.logger.error(f"Missing permissions in {message.guild.name} (ID: {message.guild.id})")
        except Exception as e:
            self.logger.error(f"Forbidden message handling failed: {str(e)}", exc_info=True)

async def setup(bot) -> None:
    """Cog setup function."""
    await bot.add_cog(LinkManager(bot))
    