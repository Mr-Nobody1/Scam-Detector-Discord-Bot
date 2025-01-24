from discord.ext import commands
from discord.ext.commands import Context
import random

# Here we name the cog and create a new class for the cog.
class CatMeme(commands.Cog, name="cat_meme"):
    def __init__(self, bot) -> None:
        self.bot = bot

    # Here you can just add your own commands, you'll always need to provide "self" as first parameter.

    @commands.hybrid_command(
        name="catmeme",
        description="Sends a random cat meme.",
    )
    async def catmeme(self, context: Context) -> None:
        """
        Sends a random cat meme.

        :param context: The application command context.
        """
        self.bot.logger.info(f"{context.author} (ID: {context.author.id}) used catmeme command")
        
        cat_memes = [
            "https://i.imgur.com/Jf0XJ.gif",
            "https://i.imgur.com/4M7IWwP.gif",
            "https://i.imgur.com/5J5Z.gif",
            "https://i.imgur.com/6J6Z.gif",
            "https://i.imgur.com/7J7Z.gif"
        ]
        meme = random.choice(cat_memes)
        await context.send(meme)
        
        self.bot.logger.info(f"Sent cat meme: {meme}")

# And then we finally add the cog to the bot so that it can load, unload, reload and use its content.
async def setup(bot) -> None:
    await bot.add_cog(CatMeme(bot))
