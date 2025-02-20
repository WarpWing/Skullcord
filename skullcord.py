import nextcord
from nextcord.ext import commands
import datetime
import json
import os

SKULL_EMOJI = "💀"
DEFAULT_REQUIRED_REACTIONS = 5

class SkullTrackerBot(commands.Bot):
    def __init__(self):
        intents = nextcord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        
        self.config = {}
        self.highlighted_messages = {}
        self.load_config()

    def load_config(self):
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    self.config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            self.config = {}

    def save_config(self):
        try:
            with open('config.json', 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    async def create_highlight_embed(self, message, skull_count):
        embed = nextcord.Embed(
            description=message.content,
            color=0x000000,
            timestamp=datetime.datetime.now()
        )
        
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.display_avatar.url
        )
        
        jump_url = message.jump_url
        embed.add_field(
            name="Source",
            value=f"[Jump to message]({jump_url})",
            inline=False
        )
        
        if message.attachments:
            embed.set_image(url=message.attachments[0].url)
            
        embed.set_footer(text=f"Message ID: {message.id}")
        
        return embed

bot = SkullTrackerBot()

@bot.slash_command(
    name="invite",
    description="Get the bot's invite link"
)
async def invite(interaction: nextcord.Interaction):
    invite_link = "https://discord.com/oauth2/authorize?client_id=1342223729761063105&scope=bot"
    await interaction.response.send_message(f"Add me to your server: {invite_link}", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.event
async def on_guild_join(guild):
    if str(guild.id) not in bot.config:
        bot.config[str(guild.id)] = {
            "highlights_channel": None,
            "required_reactions": DEFAULT_REQUIRED_REACTIONS
        }
        bot.save_config()

@bot.slash_command(
    name="configure",
    description="Configure the skull tracker for this server"
)
async def configure(
    interaction: nextcord.Interaction,
    highlights_channel: nextcord.TextChannel = nextcord.SlashOption(
        description="Channel where highlighted messages will be posted",
        required=True
    ),
    required_reactions: int = nextcord.SlashOption(
        description="Number of skull reactions required (default: 5)",
        required=False,
        min_value=1,
        max_value=50
    )
):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("You need 'Manage Server' permission to use this command.", ephemeral=True)
        return

    guild_id = str(interaction.guild_id)
    
    if guild_id not in bot.config:
        bot.config[guild_id] = {}
    
    bot.config[guild_id]["highlights_channel"] = highlights_channel.id
    if required_reactions:
        bot.config[guild_id]["required_reactions"] = required_reactions
    elif "required_reactions" not in bot.config[guild_id]:
        bot.config[guild_id]["required_reactions"] = DEFAULT_REQUIRED_REACTIONS
    
    bot.save_config()
    
    await interaction.response.send_message(
        f"Configuration updated!\n"
        f"Highlights Channel: {highlights_channel.mention}\n"
        f"Required Reactions: {bot.config[guild_id]['required_reactions']} {SKULL_EMOJI}",
        ephemeral=True
    )

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
        
    if str(payload.emoji) != SKULL_EMOJI:
        return
    
    guild_id = str(payload.guild_id)
    if guild_id not in bot.config or not bot.config[guild_id].get("highlights_channel"):
        return
        
    channel = await bot.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    
    skull_count = sum(1 for reaction in message.reactions if str(reaction.emoji) == SKULL_EMOJI)
    
    required_reactions = bot.config[guild_id].get("required_reactions", DEFAULT_REQUIRED_REACTIONS)
    
    highlights_channel = bot.get_channel(bot.config[guild_id]["highlights_channel"])
    
    if not highlights_channel:
        return
    
    if guild_id not in bot.highlighted_messages:
        bot.highlighted_messages[guild_id] = {}
    
    if skull_count >= required_reactions:
        if message.id not in bot.highlighted_messages[guild_id]:
            embed = await bot.create_highlight_embed(message, skull_count)
            header_message = f"{SKULL_EMOJI} **{skull_count}** <#{message.channel.id}>"
            highlight_message = await highlights_channel.send(content=header_message, embed=embed)
            bot.highlighted_messages[guild_id][message.id] = highlight_message.id
        else:
            highlight_message = await highlights_channel.fetch_message(
                bot.highlighted_messages[guild_id][message.id]
            )
            embed = await bot.create_highlight_embed(message, skull_count)
            header_message = f"{SKULL_EMOJI} **{skull_count}** #{message.channel.name}"
            await highlight_message.edit(content=header_message, embed=embed)

@bot.event
async def on_raw_reaction_remove(payload):
    if str(payload.emoji) != SKULL_EMOJI:
        return
    
    guild_id = str(payload.guild_id)
    if guild_id not in bot.config or not bot.config[guild_id].get("highlights_channel"):
        return
        
    channel = await bot.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    
    if (guild_id in bot.highlighted_messages and 
        message.id in bot.highlighted_messages[guild_id]):
        
        skull_count = sum(1 for reaction in message.reactions if str(reaction.emoji) == SKULL_EMOJI)
        required_reactions = bot.config[guild_id].get("required_reactions", DEFAULT_REQUIRED_REACTIONS)
        
        highlights_channel = bot.get_channel(bot.config[guild_id]["highlights_channel"])
        highlight_message = await highlights_channel.fetch_message(
            bot.highlighted_messages[guild_id][message.id]
        )
        
        if skull_count < required_reactions:
            await highlight_message.delete()
            del bot.highlighted_messages[guild_id][message.id]
        else:
            embed = await bot.create_highlight_embed(message, skull_count)
            await highlight_message.edit(embed=embed)

bot.run('banana bread :D')
