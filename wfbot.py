"""
A Discord bot that tags users who request to be notified when characters are posted to a server

email:      jordan@jordantkinsley.org
Discord:    JKinsley#6920

Invite: https://discordapp.com/oauth2/authorize?client_id=649702779320926248&scope=bot&permissions=224256

(C) 2019 by Jordan Kinsley

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import shelve
import argparse
import datetime
from discord.ext import commands, tasks
from discord.utils import escape_mentions as suppress_mentions

description = '''A bot that notifies users on command. Options to use roles instead of DB coming soon!(TM)'''
default_token = None  # enter a default Discord API token here unless you want to supply one via file or argument
discord_api_token = ''

parser = argparse.ArgumentParser()

parser.add_argument("-f", "--file", help="load token from file")
parser.add_argument("-t", "--token", help="specify token in arguments")
parser.add_argument("-p", "--prefix", help="command prefix")
parser.add_argument("-v", "--verbose", help="verbose mode (prints more info to terminal)", action="store_true")
args = parser.parse_args()


def read_token(location: str):
    try:
        with open(location, "r") as f:
            lines = f.readlines()
            return lines[0].strip()
    except:
        return None


if args.file:
    file_token = read_token(args.file)  # try reading the supplied file token in, but if it fails, use default
    if file_token is None:
        if default_token:
            discord_api_token = default_token
            if args.verbose:
                print("default token used: {0}".format(default_token))
        else:
            print("no valid token supplied, exiting")
            quit(1)
    else:
        discord_api_token = file_token
        if args.verbose:
            print("Loaded token from file: {0}".format(file_token))
elif args.token:
    discord_api_token = args.token
    if args.verbose:
        print("using token from cli: {0}".format(args.token))

prefix = ''
if args.prefix:
    prefix = args.prefix
else:
    prefix = ';'

bot = commands.Bot(command_prefix=prefix, description=description)


class Waifu(commands.Cog):
    # These two are used by the shelve module to store what is essentially a dict of IDs mapped to values
    notify_user_list = None
    character_aliases = None

    def __init__(self, bot):
        self.bot = bot
        self.notify_user_list = shelve.open('userlist.db', flag='c', writeback=False)
        self.character_aliases = shelve.open("aliases.db", flag="c", writeback=False)
        self.sync_db.start()

    def cog_unload(self):
        self.notify_user_list.close()
        self.character_aliases.close()

    @tasks.loop(minutes=2.5)
    async def sync_db(self):
        self.notify_user_list.sync()
        self.character_aliases.sync()

    @commands.command()
    async def its(self, ctx, *, character):
        """Pings users who've requested to be notified about <character>"""
        if args.verbose:
            print("character: " + character)
        notify_users = None
        resolved_character = str(self.resolve_server_alias(ctx, character))
        if args.verbose:
            print("resolved character: " + resolved_character)
        user_key = str(ctx.guild.id) + "\\" + resolved_character
        if args.verbose:
            print("user_key: " + user_key)
        # TODO: resolve server code and aliases
        try:
            notify_users = self.notify_user_list[user_key]
            if args.verbose:
                print("notify_users: " + str(notify_users))
            if not notify_users:  # if no values get returned for a <character>
                raise KeyError
        except KeyError:
            await ctx.send("Oops! I don't have an alert for {0}".format(resolved_character))
            return
        to_notify = 'Hey,'
        for user in notify_users:
            to_notify = to_notify + ' ' + user
        to_notify = to_notify + ', it\'s ' + resolved_character
        await ctx.send(to_notify)

    @commands.command(name="knownwaifus")
    # TODO rate-limit this command or restrict to admins
    async def known_waifus(self, ctx):
        """Lists the waifus known by the bot"""
        start = datetime.datetime.now()
        # running the .keys() function on shelf object is time consuming. We're going to measure the time it took
        waifus = list(self.notify_user_list.keys())
        end = datetime.datetime.now()
        waifu_list = 'I know of the following waifus: '
        for waifu in waifus:
            waifu_list += waifu + ', '
        await ctx.send(waifu_list)

    @commands.command(name="knownaliases")
    async def known_aliases(self, ctx):
        start = datetime.datetime.now()
        aliases = list(self.character_aliases.keys())
        end = datetime.datetime.now()
        alias_list = "I know of the following aliases: \n"
        for alias in aliases:
            alias_list += alias + " (refers to "
            alias_list += str(self.character_aliases[alias]) + ")\n"
        await ctx.send(alias_list)

    @commands.command(name="doyouknow")
    async def do_you_know(self, ctx, *, character):
        """Confirms if the bot knows of a particular <character>."""
        sender = ctx.author.mention
        resolved_character = str(self.resolve_server_alias(ctx, character))
        notice_key = str(ctx.guild.id) + "\\" + resolved_character
        try:
            if resolved_character in self.notify_user_list:
                if sender in self.notify_user_list[notice_key]:
                    await ctx.send(
                        "Yes, I know of {0} and you're all set to hear when they get posted next!".format(resolved_character))
                else:
                    await ctx.send(
                        "Yes, I know of {0}! I don't see you signed up for notices for them. Sign up with `{1}notifyme {0}`".format(
                            resolved_character, ctx.bot.command_prefix))
            else:
                await ctx.send("No, I don't have anything on {0}! Sign up with `{1}notifyme {0}`".format(resolved_character,
                                                                                                         ctx.bot.command_prefix))
        except KeyError:
            await ctx.send("No, I don't have anything on {0}! Sign up with `{1}notifyme {0}`".format(resolved_character,
                                                                                                     ctx.bot.command_prefix))

    def resolve_server_alias(self, ctx, character):
        current_server = str(ctx.guild.id)
        check_alias = current_server + '\\' + character
        resolved_character = ''
        try:
            resolved_character = self.character_aliases[check_alias].replace(current_server, '')
            if args.verbose:
                print("resolved_character: " + resolved_character)
                print("check_alias: " + check_alias)
        except KeyError:
            resolved_character = character
        if args.verbose:
            print("character: " + character)
            print("resolved_character: " + resolved_character)
            print("check_alias: " + check_alias)
        return resolved_character

    @commands.command(name="notifyme")
    async def notify_me(self, ctx, *, character):
        """Adds the user to the list of people to notified when <character> is posted with the 'its' command."""
        sender = ctx.author.mention
        if args.verbose:
            print(sender)
            print("guild: " + str(ctx.guild))
            print("guild id: " + str(ctx.guild.id))
        resolved_character = str(self.resolve_server_alias(ctx, character))
        notice_key = str(ctx.guild.id) + "\\" + resolved_character
        if args.verbose:
            print(notice_key)
        current_notices = [None]
        try:
            current_notices = self.notify_user_list[notice_key]
            if args.verbose:
                print("key found, current notices: " + str(current_notices))
            if sender in current_notices:
                await ctx.send("You've already signed up for notices for {0}, {1}".format(resolved_character, sender))
                return
            current_notices.append(sender)
        except KeyError:
            current_notices[0] = sender
            if args.verbose:
                print("key not found, current notices: " + str(current_notices))
        self.notify_user_list[notice_key] = current_notices
        await ctx.send(
            'Thanks {0}, you\'ve successfully been added to the notice list for {1}'.format(sender, resolved_character))

    @commands.command(name="alias")
    async def add_alias(self, ctx, alias, character):
        if args.verbose:
            print("alias: " + alias)
            print("character: " + character)
        current_server = str(ctx.guild.id)
        sender = ctx.author.mention
        new_alias = current_server + '\\' + alias
        try:
            existing_alias = self.character_aliases[new_alias]
            if existing_alias:
                await ctx.send("{0} is already referenced by alias {1}, {2}".format(existing_alias, new_alias, sender))
            else:
                raise KeyError
        except KeyError:
            self.character_aliases[new_alias] = character
            await ctx.send(
                "OK, notices for {0} will triggered if someone uses `its {1}` from now on.".format(character, alias))

    @commands.command(name="stopnotify")
    async def stop_notify(self, ctx, *, character):
        """Removes the user to the list of people to notified when <character> is posted with the 'its' command.
        Only removes the user from that character's notices."""
        sender = ctx.author.mention
        notice_key = str(ctx.guild.id) + "\\" + str(self.resolve_server_alias(ctx, character))
        current_notices = [None]
        try:
            current_notices = self.notify_user_list[notice_key]
            if args.verbose:
                print(current_notices)
            current_notices.remove(sender)
            self.notify_user_list[notice_key] = current_notices
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

    @commands.command(name="debugusers")
    @commands.is_owner()
    async def debug_user_list(self, ctx):
        notify_keys = list(self.notify_user_list.keys())
        if args.verbose:
            print(notify_keys)
        user_list = ''
        for key in notify_keys:
            if args.verbose:
                print(key)
            user_list + 'key: ' + key + ' user: ' + suppress_mentions(str(self.notify_user_list[key])) + '\n'
            if args.verbose:
                print(user_list)
        await ctx.send(user_list)

    @commands.command(name="dropall")
    @commands.is_owner()
    async def drop_all(self, ctx):
        """**WARNING** Drops the full list of notices and aliases. Only usable by owner."""
        self.notify_user_list.clear()
        self.character_aliases.clear()
        await ctx.send("Removed all notices and aliases")

    @commands.command(name="droptablenotices")
    @commands.is_owner()
    async def drop_all_notices(self, ctx):
        """**WARNING** Drops the full list of notices. Only usable by owner."""
        self.notify_user_list.clear()
        await ctx.send("Removed all notices")

    @commands.command(name="droptablealiases")
    @commands.is_owner()
    async def drop_all_aliases(self, ctx):
        """**WARNING** Drops the full list of aliases. Only usable by owner."""
        self.character_aliases.clear()
        await ctx.send("Removed all aliases")

    @commands.command(name="dropserver")
    # TODO @commands.is_admin()
    async def drop_notices_server(self, ctx):
        """Drops all notices for this server only. Not yet implemented."""
        server = str(ctx.guild.id)
        # TODO server code, check admin
        await ctx.send("Uh oh, not ready yet! Message JKinsley")

    @commands.command()
    async def wotd(self, ctx):
        """Prints the Waifu of the Day"""
        if args.verbose:
            print("wotd invoked by " + str(ctx.author.mention))
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
