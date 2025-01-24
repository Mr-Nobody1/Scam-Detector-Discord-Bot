import json
import os
from discord.ext import commands
from discord.ext.commands import Context

class LinkManager(commands.Cog, name="linkmanager"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.forbidden_links = self.load_links()

    def load_links(self):
        if os.path.exists("forbidden_links.json"):
            with open("forbidden_links.json", "r") as f:
                return set(json.load(f))
        else:
            return set()

    def save_links(self):
        with open("forbidden_links.json", "w") as f:
            json.dump(list(self.forbidden_links), f)

    @commands.hybrid_command(
        name="addlink",
        description="Adds a link to the forbidden links database.",
    )
    @commands.has_permissions(administrator=True)
    async def addlink(self, context: Context, link: str) -> None:
        if link in self.forbidden_links:
            await context.send("This link is already forbidden.")
            return
        self.forbidden_links.add(link)
        self.save_links()
        self.bot.logger.info(f"{context.author} (ID: {context.author.id}) added forbidden link: {link}")
        await context.send(f"Link {link} has been added to the forbidden list.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return  # Ignore messages from the bot itself

        # Check if any forbidden links are in the message content
        for link in self.forbidden_links:
            if link in message.content:
                try:
                    await message.delete()
                    self.bot.logger.info(f"Deleted message from {message.author} (ID: {message.author.id}) containing forbidden link: {link}")
                    await message.channel.send(f"{message.author.mention}, please do not share forbidden links.", delete_after=5)
                except Exception as e:
                    self.bot.logger.error(f"Error deleting message: {e}")
                break  # No need to check other links if one is found

async def setup(bot) -> None:
    await bot.add_cog(LinkManager(bot))
