from discord.ext import commands
from discord import Message, Thread
import discord
import json
import os
from openai import OpenAI
from discord.ext.commands import Context
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the OpenAI client with environment variable
client = OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)
# Define cost rates (replace with actual rates from your provider)
DEEPSEEK_INPUT_COST_PER_1K_TOKENS = 0.01  # $0.01 per 1k input tokens
DEEPSEEK_OUTPUT_COST_PER_1K_TOKENS = 0.02  # $0.02 per 1k output tokens

# Define the path to the JSON file
DATA_FILE = "active_channels.json"

class ChatCog(commands.Cog, name="chat"):
    def __init__(self, bot):
        self.bot = bot
        self.active_channels = {}
        self.message_history = {}
        self.thread_costs = {}  # Track costs per thread
        self.total_costs = {    # Track all costs
            "decision_calls": 0.0,
            "thread_responses": 0.0
        }

        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                self.active_channels = data.get("guilds", {})

    def save_active_channels(self):
        with open(DATA_FILE, "w") as f:
            json.dump({"guilds": self.active_channels}, f, indent=4)

    def _calculate_cost(self, usage):
        input_cost = (usage.prompt_tokens / 1000) * DEEPSEEK_INPUT_COST_PER_1K_TOKENS
        output_cost = (usage.completion_tokens / 1000) * DEEPSEEK_OUTPUT_COST_PER_1K_TOKENS
        return round(input_cost + output_cost, 6)

    # ... keep add_channel and remove_channel commands unchanged ...

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author == self.bot.user:
            return

        system_message = """Your name is CryptoExpert..."""  # Your full system message

        thread = message.channel if isinstance(message.channel, Thread) else None

        if thread:
            if thread.id not in self.message_history:
                self.message_history[thread.id] = [{"role": "system", "content": system_message}]

            self.message_history[thread.id].append({"role": "user", "content": message.content})

            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=self.message_history[thread.id],
                    stream=False
                )
                bot_response = response.choices[0].message.content
                
                # Calculate and log thread message cost
                cost = self._calculate_cost(response.usage)
                self.total_costs["thread_responses"] += cost
                self.thread_costs[thread.id] = self.thread_costs.get(thread.id, 0) + cost
                
                self.bot.logger.info(
                    f"Thread response cost: ${cost:.4f} | "
                    f"Thread total: ${self.thread_costs[thread.id]:.4f} | "
                    f"Global total: ${self.total_costs['thread_responses']:.4f}"
                )

                await thread.send(bot_response)
                self.message_history[thread.id].append({"role": "assistant", "content": bot_response})

                if len(self.message_history[thread.id]) > 10:
                    self.message_history[thread.id] = self.message_history[thread.id][-10:]

            except Exception as e:
                await thread.send(f"Error generating response: {e}")

        else:
            guild_id = str(message.guild.id)
            channel_id = str(message.channel.id)

            if guild_id in self.active_channels and channel_id in self.active_channels[guild_id]["channels"]:
                decision_system_msg = """Determine if the user's message is a request for help related to cryptocurrency or blockchain. Respond exactly 'YES' or 'NO' without any other text."""
                decision_messages = [
                    {"role": "system", "content": decision_system_msg},
                    {"role": "user", "content": message.content}
                ]

                try:
                    max_attempts = 3
                    attempts = 0
                    decision = None
                    decision_cost = 0.0
                    
                    while attempts < max_attempts:
                        decision_response = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=decision_messages,
                            stream=False
                        )
                        
                        # Calculate decision cost
                        cost = self._calculate_cost(decision_response.usage)
                        decision_cost += cost
                        self.total_costs["decision_calls"] += cost
                        
                        self.bot.logger.info(
                            f"Decision API call cost: ${cost:.4f} | "
                            f"Attempt {attempts+1}/{max_attempts}"
                        )
                        
                        decision = decision_response.choices[0].message.content.strip().upper()
                        
                        if decision in ['YES', 'NO']:
                            break
                            
                        attempts += 1

                    # Log final decision cost
                    self.bot.logger.info(
                        f"Final decision cost: ${decision_cost:.4f} | "
                        f"Total decision costs: ${self.total_costs['decision_calls']:.4f}"
                    )

                    if decision not in ['YES', 'NO']:
                        self.bot.logger.error("Failed to get valid decision after 3 attempts")
                        return
                        
                    if decision == 'YES':
                        try:
                            thread = await message.create_thread(name=f"Help with {message.author.name}")
                            self.thread_costs[thread.id] = 0.0  # Initialize thread cost
                        except discord.HTTPException:
                            await message.channel.send("Could not create thread.")
                            return

                        self.message_history[thread.id] = [
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": message.content}
                        ]

                        try:
                            response = client.chat.completions.create(
                                model="deepseek-chat",
                                messages=self.message_history[thread.id],
                                stream=False
                            )
                            # Calculate initial thread response cost
                            cost = self._calculate_cost(response.usage)
                            self.total_costs["thread_responses"] += cost
                            self.thread_costs[thread.id] += cost
                            
                            self.bot.logger.info(
                                f"Initial thread response cost: ${cost:.4f} | "
                                f"Thread total: ${self.thread_costs[thread.id]:.4f}"
                            )

                            bot_response = response.choices[0].message.content
                            await thread.send(bot_response)
                            self.message_history[thread.id].append({"role": "assistant", "content": bot_response})
                        except Exception as e:
                            await thread.send(f"Error generating response: {e}")
                            
                except Exception as e:
                    self.bot.logger.error(f"Error in decision API call: {e}")

async def setup(bot):
    await bot.add_cog(ChatCog(bot))