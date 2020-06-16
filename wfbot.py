"""
A Discord bot that tags users who request to be notified when characters are posted to a server

email:      jordan@jordantkinsley.org
Discord:    AuroraKinsley#6969

Invite: https://discordapp.com/oauth2/authorize?client_id=649702779320926248&scope=bot&permissions=224256

(C) 2019-2020 by Jordan Aurora Kinsley

Licensed under MIT License, see LICENSE
"""

import argparse
from discord.ext import commands
import waifu
from bothelper import log
from bothelper import read_token

description = '''A bot that notifies users on command. Options to use roles instead of DB coming soon!(TM)'''
default_token = None  # enter a default Discord API token here unless you want to supply one via file or argument
discord_api_token = ''
c_alias_loc = ''
u_list_loc = ''

parser = argparse.ArgumentParser()

parser.add_argument("-f", "--file", help="load token from file")
parser.add_argument("-t", "--token", help="specify token in arguments")
parser.add_argument("-p", "--prefix", help="command prefix")
# if -v is passed on command line, no need to add argument following
parser.add_argument("-v", "--verbose", help="verbose mode (prints more info to terminal)", action="store_true")
parser.add_argument("-c", "--character", help="file location for character alias shelf")
parser.add_argument("-u", "--userlist", help="file location for user list shelf")
parser.add_argument("-lf", "--log_file", help="file location for logging")
args = parser.parse_args()

if args.file:
    file_token = read_token(args.file)  # try reading the supplied file token in, but if it fails, use default
    if file_token is None:
        if default_token:
            discord_api_token = default_token
            log("default token used: {0}".format(default_token), 'svf', args)
        else:
            print("no valid token supplied, exiting")
            quit(1)
    else:
        discord_api_token = file_token
        log("Loaded token from file: {0}".format(file_token), 'svf', args)
elif args.token:
    discord_api_token = args.token
    log("using token from cli: {0}".format(args.token), 'svf', args)

prefix = ''
if args.prefix:
    prefix = args.prefix
else:
    prefix = ';'

if args.character:
    c_alias_loc = args.character
else:
    c_alias_loc = 'aliases.test.db'

if args.userlist:
    u_list_loc = args.userlist
else:
    u_list_loc = 'userlist.test.db'

bot = commands.Bot(command_prefix=prefix, description=description)

# TODO: channel config, possibly as class?
# TODO: general documentation for contributors


@bot.event
async def on_ready():
    try:
        if args.log_file:
            with(open(args.log_file, 'a')) as lf:
                lf.truncate()
    except OSError:
        print("log file at {0} not found".format(args.log_file))
    log('Logged in as', 'sf', args)
    log(bot.user.name, 'sf', args)
    log(bot.user.id, 'sf', args)
    log('~~--~~--~~--~~', 'sf', args)


@bot.command(name="off")
@commands.is_owner()
async def shutdown(ctx):
    """**WARNING** Shuts down the bot. Only usable by owner"""
    await ctx.send("OK, shutting down!")
    ctx.bot.get_cog("Waifu").cog_unload()
    await ctx.bot.close()
    quit(0)


@shutdown.error
async def not_bot_owner(ctx, error):
    if isinstance(error, commands.NotOwner):
        await ctx.send("Uh on. This command is only usable by the bot's owner")


bot.add_cog(waifu.Waifu(bot))
bot.get_cog("Waifu").user_list_location = u_list_loc
bot.get_cog("Waifu").character_alias_location = c_alias_loc
bot.get_cog("Waifu").args = args
bot.run(discord_api_token)
