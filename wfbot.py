"""
(C) 2019 by Jordan Kinsley

A Discord bot that tags users who request to be notified when characters are posted to a server

email jordan@jordantkinsley.org
Discord JKinsley#6920

Invite: https://discordapp.com/oauth2/authorize?client_id=649702779320926248&scope=bot&permissions=224256
"""

import shelve
import argparse
from discord.ext import commands, tasks

description = '''A bot that notifies users on command. Options to use roles instead of DB coming soon!(TM)'''
default_token = None
discord_api_token = ''

parser = argparse.ArgumentParser()

parser.add_argument("-f", "--file", help="load token from file")
parser.add_argument("-t", "--token", help="specify token in arguments")
parser.add_argument("-p", "--prefix", help="command prefix")
args = parser.parse_args()


def read_token(location : str):
    try:
        with open(location, "r") as f:
            lines = f.readlines()
            return lines[0].strip()
    except:
        return None


if args.file:
    file_token = read_token()
    if file_token is None:
        discord_api_token = default_token
        print("default token used: {0}".format(default_token))
    else:
        discord_api_token = file_token
        print("Loaded token from file: {0}".format(file_token))
elif args.token:
    discord_api_token = args.token
    print("using token from cli: {0}".format(args.token))

prefix = ''
if args.prefix:
    prefix = args.prefix
else:
    prefix = ';'

bot = commands.Bot(command_prefix=prefix, description=description)


class Waifu(commands.Cog):
    notify_user_list = None

    def __init__(self, bot):
        self.bot = bot
        self.notify_user_list = shelve.open('userlist.db', flag='c', writeback=False)
        self.sync_db.start()

    def cog_unload(self):
        self.notify_user_list.close()

    @tasks.loop(minutes=2.5)
    async def sync_db(self):
        self.notify_user_list.sync()

    @commands.command()
    async def its(self, ctx, *, character):
        """Pings users who've requested to be notified about <character>"""
        notify_users = None
        try:
            notify_users = self.notify_user_list[character]
            if notify_users == []:
                raise KeyError
        except KeyError as ke:
            await ctx.send("Oops! I don't have an alert for {0}".format(character))
            return
        to_notify = 'Hey, '
        for user in notify_users:
            to_notify = to_notify + user
        to_notify = to_notify + ' it\'s ' + character
        await ctx.send(to_notify)

    @commands.command(name="knownwaifus")
    async def known_waifus(self, ctx):
        """Lists the waifus known by the bot"""
        waifus = list(self.notify_user_list.keys())
        waifu_list = 'I know of the following waifus: '
        for waifu in waifus:
            waifu_list += waifu + ', '
        await ctx.send(waifu_list)

    @commands.command(name="doyouknow")
    async def do_you_know(self, ctx, *, character):
        """Confirms if the bot knows of a particular waifu"""
        sender = ctx.author.mention
        try:
            if character in self.notify_user_list:
                if sender in self.notify_user_list[character]:
                    await ctx.send("Yes, I know of {0} and you're all set to hear when they get posted next!".format(character))
                else:
                    await ctx.send(
                        "Yes, I know of {0}! I don't see you signed up for notices for them. Sign up with `{1}notifyme {0}`".format(character, ctx.bot.command_prefix))
            else:
                await ctx.send("No, I don't have anything on {0}! Sign up with `{1}notifyme {0}`".format(character,
                                                                                                    ctx.bot.command_prefix))
        except KeyError:
            await ctx.send("No, I don't have anything on {0}! Sign up with `{1}notifyme {0}`".format(character, ctx.bot.command_prefix))

    @commands.command(name="notifyme")
    async def notify_me(self, ctx, *, character):
        """Adds the user to the list of people to notified when <character> is posted with the 'its' command"""
        # TODO: add server-only code (i.e. notices are only for the server requested
        sender = ctx.author.mention
        current_notices = [None]
        try:
            current_notices = self.notify_user_list[character]
            if sender in current_notices:
                await ctx.send("You've already signed up for notices for {0}, {1}".format(character, sender))
                return
            current_notices.append(sender)
        except KeyError:
            current_notices[0] = sender
        self.notify_user_list[character] = current_notices
        await ctx.send(
            'Thanks {0}, you\'ve successfully been added to the notice list for {1}'.format(sender, character))

    # TODO: alias command or option

    @commands.command(name="stopnotify")
    async def stop_notify(self, ctx, *, character):
        """Removes the user to the list of people to notified when <character> is posted with the 'its' command.
        Only removes the user from that character's notices."""
        sender = ctx.author.mention
        current_notices = [None]
        try:
            current_notices = self.notify_user_list[character]
            print(current_notices)
            current_notices.remove(sender)
            self.notify_user_list[character] = current_notices
        except KeyError:
            await ctx.send(
                "I don't show that anyone signed up for notices regarding {0}, {1}".format(character, sender))
            return
        except ValueError:
            await ctx.send(
                "I don't show that you're signed up for notices regarding {0}, {1}".format(character, sender))
            return
        await ctx.send(
            "Thanks, {0}, you've successfully been removed from the notice list for {1}".format(sender, character))

    # TODO: add a 'stopall' command to drop user from all notices (complicated with current implementation)

    # TODO: add a 'debug_user_list' command to show all notices and users (suppress @ replies)

    @commands.command()
    @commands.is_owner()
    async def drop_notices(self, ctx):
        """**WARNING** Drops the full list of notices. Only usable by owner"""
        self.notify_user_list.clear()
        await ctx.send("Removed all notices")

    @commands.command()
    async def wotd(self, ctx):
        """Prints the Waifu of the Day"""

        # TODO: implement admin/channel permissions for listing waifu on rotating schedule

        await ctx.send("Astolfo, always")

    @stop_notify.error
    @notify_me.error
    @its.error
    @do_you_know.error
    async def no_char_error(self, ctx, error):
        try:
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(
                    "You need to supply a character for this command! Try `{0}help`".format(ctx.bot.command_prefix))
        except commands.errors.CommandInvokeError:
            await ctx.send(
                "You need to supply a character for this command! Try `{0}help`".format(ctx.bot.command_prefix))


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('~~--~~--~~--~~')


@bot.command(name="off")
@commands.is_owner()
async def shutdown(ctx):
    """**WARNING** Shuts down the bot. Only usable by owner"""
    await ctx.send("OK, shutting down!")
    ctx.bot.get_cog("Waifu").cog_unload()
    await ctx.bot.close()
    quit(0)


bot.add_cog(Waifu(bot))
bot.run(discord_api_token)
