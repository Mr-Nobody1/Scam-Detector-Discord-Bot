from discord.ext import commands
from discord import Message, Thread
import discord
import json
import os
import asyncio
from openai import OpenAI
from discord.ext.commands import Context
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

# Cost configuration (update with your rates)
DEEPSEEK_INPUT_COST = 0.01  # $ per 1k tokens
DEEPSEEK_OUTPUT_COST = 0.02  # $ per 1k tokens

# Persistent storage files
DATA_FILE = "active_channels.json"
HISTORY_FILE = "message_history.json"
COST_FILE = "cost_tracking.json"

class ChatCog(commands.Cog, name="chat"):
    def __init__(self, bot):
        self.bot = bot
        self.active_channels = {}
        self.message_history = {}
        self.thread_costs = {}
        self.total_costs = {
            "decisions": 0.0,
            "responses": 0.0
        }

        # Load persistent data
        self.load_data()
        
        # Start auto-save task
        self.save_task = self.bot.loop.create_task(self.auto_save())

    def load_data(self):
        """Load all persistent data from files"""
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r") as f:
                    self.active_channels = json.load(f).get("guilds", {})
            
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r") as f:
                    self.message_history = json.load(f)
            
            if os.path.exists(COST_FILE):
                with open(COST_FILE, "r") as f:
                    cost_data = json.load(f)
                    self.thread_costs = cost_data.get("thread_costs", {})
                    self.total_costs = cost_data.get("total_costs", self.total_costs)
                    
        except Exception as e:
            self.bot.logger.error(f"Error loading data: {e}")

    async def auto_save(self):
        """Periodically save all data"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                self.save_data()
                self.bot.logger.info("Auto-saved persistent data")
            except Exception as e:
                self.bot.logger.error(f"Auto-save failed: {e}")
            await asyncio.sleep(300)  # Save every 5 minutes

    def save_data(self):
        """Save all persistent data to files"""
        try:
            # Save active channels
            with open(DATA_FILE, "w") as f:
                json.dump({"guilds": self.active_channels}, f, indent=4)
            
            # Save message history
            with open(HISTORY_FILE, "w") as f:
                json.dump(self.message_history, f, indent=4)
            
            # Save cost tracking
            with open(COST_FILE, "w") as f:
                json.dump({
                    "thread_costs": self.thread_costs,
                    "total_costs": self.total_costs
                }, f, indent=4)
                
        except Exception as e:
            self.bot.logger.error(f"Save failed: {e}")

    def _calculate_cost(self, usage):
        """Calculate cost from API usage"""
        input_cost = (usage.prompt_tokens / 1000) * DEEPSEEK_INPUT_COST
        output_cost = (usage.completion_tokens / 1000) * DEEPSEEK_OUTPUT_COST
        return round(input_cost + output_cost, 4)

    async def cog_unload(self):
        """Save data when cog unloads"""
        self.save_task.cancel()
        self.save_data()
        self.bot.logger.info("Saved data before shutdown")

    # ... Keep your existing add_channel/remove_channel commands unchanged ...

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author == self.bot.user:
            return

        # System message and existing thread handling
        system_msg = "Your name is CryptoExpert..."  # Your full system message

        # Thread message handling
        if isinstance(message.channel, Thread):
            thread = message.channel
            thread_id = str(thread.id)

            # Initialize history if not exists
            if thread_id not in self.message_history:
                self.message_history[thread_id] = [{"role": "system", "content": system_msg}]

            # Store user message
            self.message_history[thread_id].append({"role": "user", "content": message.content})

            try:
                # Generate response
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=self.message_history[thread_id],
                    stream=False
                )
                
                # Calculate and track cost
                cost = self._calculate_cost(response.usage)
                self.total_costs["responses"] += cost
                self.thread_costs[thread_id] = self.thread_costs.get(thread_id, 0) + cost
                
                self.bot.logger.info(
                    f"Thread {thread_id} cost: ${cost:.4f} | "
                    f"Thread total: ${self.thread_costs[thread_id]:.4f} | "
                    f"Global total: ${self.total_costs['responses']:.4f}"
                )

                # Send response and update history
                bot_response = response.choices[0].message.content
                await thread.send(bot_response)
                self.message_history[thread_id].append({"role": "assistant", "content": bot_response})

                # Maintain history limit
                if len(self.message_history[thread_id]) > 10:
                    self.message_history[thread_id] = self.message_history[thread_id][-10:]

            except Exception as e:
                await thread.send(f"Error generating response: {e}")

        else:
            # Existing channel handling with decision API
            guild_id = str(message.guild.id)
            channel_id = str(message.channel.id)

            if guild_id in self.active_channels and channel_id in self.active_channels[guild_id]["channels"]:
                # Decision logic with retries
                decision_system = "Respond EXACTLY 'YES' or 'NO' if help is needed..."
                decision_messages = [
                    {"role": "system", "content": decision_system},
                    {"role": "user", "content": message.content}
                ]

                try:
                    max_attempts = 3
                    decision = None
                    total_cost = 0.0
                    
                    for attempt in range(max_attempts):
                        response = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=decision_messages,
                            stream=False
                        )
                        
                        cost = self._calculate_cost(response.usage)
                        total_cost += cost
                        self.total_costs["decisions"] += cost
                        
                        decision = response.choices[0].message.content.strip().upper()
                        if decision in ['YES', 'NO']:
                            break

                    self.bot.logger.info(
                        f"Decision cost: ${total_cost:.4f} | "
                        f"Total decision costs: ${self.total_costs['decisions']:.4f}"
                    )

                    if decision == 'YES':
                        try:
                            thread = await message.create_thread(name=f"Help-{message.author.name[:20]}")
                            self.thread_costs[str(thread.id)] = 0.0
                            # Initial response logic here...
                            
                        except discord.HTTPException:
                            await message.channel.send("Failed to create thread")

                except Exception as e:
                    self.bot.logger.error(f"Decision error: {e}")

async def setup(bot):
    await bot.add_cog(ChatCog(bot))