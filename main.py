
import asyncio
import json
import logging
import math
import os
import traceback
from datetime import datetime, timedelta

import discord
from discord import Interaction, activity
from discord.ext import commands
from discord.ui import Button, View, button

from localization import lang
from log import logger

dirname = os.path.dirname(__file__)


logger = logger.getLogger('main')
logger.info('[init] Bot startup')

logger.debug("[language] requesting language")
lang.init()
lang = lang.langpref()['main']
intents = discord.Intents.all()


class CustomHelpCommand(commands.HelpCommand):

    def __init__(self):
        super().__init__()

    async def send_bot_help(self, mapping):
        await self.get_destination().send(embed=gen_help_menu(bot.commands), view=MenuView(bot.commands))

    async def send_cog_help(self, cog):
        await self.get_destination().send(embed=gen_help_menu(cog.get_commands()), view=MenuView(cog.get_commands()))

    async def send_command_help(self, command):
        await self.get_destination().send(embed=gen_help_menu(command))

    async def send_error_message(self, error):
        await self.get_destination().send(lang['help.not_found'].format(user=jdata['user']))

    async def send_group_help(self, group):
        return await super().send_group_help(group)
        # remain default help message for compatibility cuz we don't have a group command


# load settings and init
with open(os.path.join(dirname, 'setting.json'), 'r') as _jfile:
    jdata = json.load(_jfile)
bot = commands.Bot(command_prefix=commands.when_mentioned_or(jdata['command_prefix']), intents=intents)
start_time = datetime.now()
version = "v3.0.0"
logger.info(f"[init] Bot is now starting...")
HELP_MENU_FIELDS = lang["help.menu.fields"]


class MenuView(View):
    def __init__(self, commands):
        super().__init__(timeout=None)
        self.commands = commands
        self.page = 1
        self.commands_len = len(self.commands)
        self.ttl_page = math.ceil(self.commands_len / HELP_MENU_FIELDS)

    @button(label='◀️', custom_id='previous_page')
    async def previous_page(self, interaction: Interaction, button: Button):
        if self.page - 1 >= 1:
            self.page -= 1
        await interaction.response.edit_message(embed=gen_help_menu(self.commands, self.page), view=self)

    @button(label='▶️', custom_id='next_page')
    async def next_page(self, interaction: Interaction, button: Button):
        if self.page + 1 <= self.ttl_page:
            self.page += 1
        await interaction.response.edit_message(embed=gen_help_menu(self.commands, self.page), view=self)


@bot.event
async def on_ready():
    logger.info(f'[init] current version: {version}')
    logger.info('[init] Bot is now started')
    activity = discord.Activity(type=discord.ActivityType.watching, name=jdata['watching'])
    logger.info("[init] Bot activity set.")
    await bot.change_presence(activity=activity)
    logger.debug('[init] loading extensions')

    with open(os.path.join(dirname, 'cmds/noload.json'), 'r') as _jfile:
        noload = json.load(_jfile)

    for filename in os.listdir(os.path.join(dirname, 'cmds')):
        if filename.endswith('.py'):
            extname = filename[:-3]
            if filename not in noload:
                try:
                    await bot.load_extension(f'cmds.{extname}')
                    logger.debug(f'[init] loaded extension: {extname}')
                except Exception as exc:
                    logger.error(f'[init] {exc}', exc_info=True)
            else:
                logger.debug(f'extension: {extname} is not loaded,its in "cmds/noload.json"')
    bot.help_command = CustomHelpCommand()
    logger.debug('[init] Replaced default help command')


@bot.command(name='sync', aliases=[], brief='Bot synced!', description='The bot has been fully synchronized!')
async def sync_command(ctx):
    await bot.tree.sync()
    await ctx.send('Bot is fully synchronized!')
    logger.debug(f'extentions are synced to the command tree')


def gen_help_menu(commands, page=1):
    embed = discord.Embed(title=lang['help.embed.title'], color=0xccab2b)
    embed.set_author(name="Patreon", url="https://patreon.com/join/lonnstyle", icon_url="https://i.imgur.com/CCYuxwH.png")
    command_types = [discord.ext.commands.Command, discord.ext.commands.HybridCommand]
    if type(commands) not in command_types:
        fields = 0
        start = (page - 1) * HELP_MENU_FIELDS
        end = min(len(commands), page * HELP_MENU_FIELDS - 1)
        for command in list(commands)[start:end]:
            if command.brief is not None:
                embed.add_field(name=f"{jdata['command_prefix']}{command.name}", value=command.brief, inline=True)
            fields += 1
            embed.set_footer(text=lang['help.embed.footer'].format(command_prefix=jdata['command_prefix'], page=page, total=math.ceil(len(commands) / HELP_MENU_FIELDS)))
        return embed
    else:
        aliases = commands.name
        params = ""
        for param in commands.clean_params:
            params += f" <{param}>"
        for alias in commands.aliases:
            aliases += f"|{alias}"
        embed.add_field(name=f"{jdata['command_prefix']}[{aliases}]{params}", value=commands.description)
        embed.add_field(name="cog", value=commands.cog_name)
        return embed


@bot.command(name='load', aliases=lang['load.aliases'], brief=lang['load.brief'], description=lang['load.description'])
async def load(ctx, extension):
    if await bot.is_owner(ctx.author):
        await bot.load_extension(F'cmds.{extension}')
        await ctx.send(lang['load.loaded'].format(extension=extension))
        logger.debug(f'[load] loaded extension: {extension}')

        await bot.tree.sync()
        logger.debug('[load] Command tree synced')
    else:
        await ctx.send(embed=discord.Embed(title=lang['load.error.title'], description=lang['load.error.description'].format(owner=bot.owner_id), color=0xff0000))


@bot.command(name='unload', aliases=lang['unload.aliases'], brief=lang['unload.brief'], description=lang['unload.description'])
async def unload(ctx, extension):
    if await bot.is_owner(ctx.author):
        await bot.unload_extension(F'cmds.{extension}')
        await ctx.send(lang['unload.unloaded'].format(extension=extension))
        logger.debug(f'[unload] unloaded extension: {extension}')
        logger.debug('[init] Replaced default help command')
        await bot.tree.sync()
        logger.debug('[unload] Command tree synced')
    else:
        await ctx.send(embed=discord.Embed(title=lang['unload.error.title'], description=lang['unload.error.description'].format(owner=bot.owner_id), color=0xff0000))


@bot.command(name='reload', aliases=lang['reload.aliases'], brief=lang['reload.brief'], description=lang['reload.description'])
async def reload(ctx, extension):
    if await bot.is_owner(ctx.author):
        await bot.reload_extension(F'cmds.{extension}')
        await ctx.send(lang['reload.reloaded'].format(extension=extension))
        logger.debug(f'[reload] reloaded extension: {extension}')
        logger.debug('[init] Replaced default help command')
        await bot.tree.sync()
        logger.debug('[reload] Command tree synced')
    else:
        await ctx.send(embed=discord.Embed(title=lang['reload.error.title'], description=lang['reload.error.description'].format(owner=bot.owner_id), color=0xff0000))


@bot.command(name='disconnect', aliases=lang['disconnect.aliases'], brief=lang['disconnect.brief'], description=lang['disconnect.description'].format(owner=bot.owner_id))
async def turn_off_bot(ctx):
    if await bot.is_owner(ctx.author):
        await ctx.send(lang['disconnect.disconnected'])
        logger.info('[disconnect] bot is now closing')
        await bot.close()
    else:
        await ctx.send(embed=discord.Embed(title=lang['disconnect.error.title'], description=lang['disconnect.error.description'].format(owner=bot.owner_id), color=0xff0000))


@bot.command(name='status', aliases=lang['status.aliases'], brief=lang['status.brief'], description=lang['status.description'].format(owner=bot.owner_id))
async def status(ctx):
    if await bot.is_owner(ctx.message.author):
        embed = discord.Embed(title=lang['status.embed.title'])
        embed.add_field(name=lang['status.embed.field.ping'], value=f"{round(bot.latency*1000)}ms", inline=False)
        perms = ">>> "
        for name, value in ctx.channel.permissions_for(ctx.me):
            if value == True:
                perms += name + '\n'
        embed.add_field(name=lang['status.embed.field.perms'], value=perms, inline=True)
        exts = ">>> "
        for ext in bot.extensions:
            exts += ext.replace("cmds.", "") + '\n'
        embed.add_field(name=lang['status.embed.field.exts'], value=exts, inline=True)
        embed.add_field(name=lang['status.embed.uptime'], value=f">>> <t:{int(start_time.timestamp())}:R>\n{version}", inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(embed=discord.Embed(title=lang['status.error.title'], description=lang['status.error.description'].format(owner=bot.owner_id)))


@bot.command(name='sponsor', aliases=lang['sponsor.aliases'], description=lang['sponsor.description'])
async def sponsor(ctx):
    embed = discord.Embed(title=lang['sponsor.embed.title'], description=lang['sponsor.embed.description'], color=0xff424d, url="https://patreon.com/join/lonnstyle")
    embed.set_thumbnail(url="https://i.imgur.com/CCYuxwH.png")
    await ctx.send(embed=embed)


@bot.command(name='documentation', aliases=lang['documentation.aliases'], description=lang['documentation.description'])
async def documentation(ctx):
    embed = discord.Embed(title=lang['documentation.embed.title'], description=lang['documentation.embed.description'], color=0x2980b9, url=lang['documentation.embed.url'])
    await ctx.send(embed=embed)


@bot.listen()
async def on_command_error(ctx, error):
    owner = await bot.application_info()
    owner = owner.owner
    embed = discord.Embed(title="Error", description=str(error))
    embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
    embed.add_field(name="Context", value=ctx.message.clean_content)
    if isinstance(ctx.channel, discord.channel.TextChannel):
        embed.add_field(name="Channel", value=ctx.guild.name + '/' + ctx.channel.name)
    if ctx.command in bot.commands:
        logger.error(f"[command_error]message: {ctx.message.clean_content}")
        logger.error(f"[command_error]error: {error}")
        traceback_lines = error.__traceback__
        traceback_text = '\n'.join(traceback_lines)
        embed.add_field(name="Traceback", value=f"```{traceback_text}```")
        await owner.send(embed=embed)
        traceback_text = ''.join(traceback_lines)
        logger.error(f"[command_error]{traceback_text}")


if __name__ == "__main__":
    try:
        file_handler = logging.FileHandler(filename='runtime.log', encoding='utf-8', mode='a')
        bot.run(jdata['TOKEN'], log_handler=file_handler, log_formatter=logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(lineno)d: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    except Exception as exc:
        logger.critical(exc, exc_info=True)
