"""
A Discord bot that tags users who request to be notified when characters are posted to a server

email:      jordan@jordantkinsley.org
Discord:    JKinsley#6969

Invite: https://discordapp.com/oauth2/authorize?client_id=649702779320926248&scope=bot&permissions=224256

(C) 2019-2020 by Jordan Kinsley

Licensed under MIT License, see LICENSE
"""

import shelve
import argparse
import datetime
from discord.ext import commands, tasks
from discord.utils import escape_mentions as suppress_mentions

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
args = parser.parse_args()


def log(output: str):
    if args.verbose:
        print("@{0}: {1}".format(datetime.datetime.now().isoformat(" ", 'seconds'), output))


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
            log("default token used: {0}".format(default_token))
        else:
            print("no valid token supplied, exiting")
            quit(1)
    else:
        discord_api_token = file_token
        log("Loaded token from file: {0}".format(file_token))
elif args.token:
    discord_api_token = args.token
    log("using token from cli: {0}".format(args.token))

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
# TODO: tag multiple characters with ;notifyme


class Waifu(commands.Cog):
    # These two are used by the shelve module to store what is essentially a dict of IDs mapped to values
    notify_user_list = None
    character_aliases = None

    def __init__(self, bot):
        self.bot = bot
        # when we initialize, open a pair of 'shelves' (https://docs.python.org/3/library/shelve.html)
        # writeback is set to False to conserve memory at the expense of addition steps to add info the shelf
        self.notify_user_list = shelve.open(u_list_loc, flag='c', writeback=False)
        self.character_aliases = shelve.open(c_alias_loc, flag='c', writeback=False)
        # starts the sync_db function so we can have it run on a regular basis
        self.sync_db.start()

    def cog_unload(self):
        # if we're stopping the bot gracefully, close the shelves properly
        self.notify_user_list.close()
        self.character_aliases.close()

    # These @tasks, @commands, @bot symbols above functions are Python decorators and help the bot do specific tasks or
    # know where to look for functions
    @tasks.loop(minutes=15)  # ignore 'loop object not callable' message in IDE
    async def sync_db(self):
        # every 2.5 minutes, sync the shelves
        self.notify_user_list.close()
        self.notify_user_list = shelve.open(u_list_loc, flag='c', writeback=False)
        self.character_aliases.close()
        self.character_aliases = shelve.open(c_alias_loc, flag='c', writeback=False)

    # basic command that uses the function name as the command name
    @commands.command()
    async def its(self, ctx, *, character):
        """Pings users who've requested to be notified about <character>"""
        # takes a single argument without quotes, anything passed as the "character" gets sent as input
        await ctx.send(self.itis(ctx, character))

    # helper function for its() and itsm(), but not a command
    def itis(self, ctx, character):
        """Takes a Discord Context ctx and string character as arguments and sends notices to all users signed up for them"""
        log("character: " + character)
        notify_users = None
        resolved_character = str(self.resolve_server_alias(ctx, character.title()))
        log("resolved character: " + resolved_character)
        # we're only going to look for notices registered for the server where the command got called
        user_key = str(ctx.guild.id) + "\\" + resolved_character
        log("user_key: " + user_key)
        try:
            notify_users = self.notify_user_list[user_key]
            log("notify_users: " + str(notify_users))
            if not notify_users:  # if no values get returned for a <character>
                raise KeyError
        except KeyError:
            return str("Oops! I don't have an alert for {0},{1}\n".format(resolved_character, ctx.author.mention))
        to_notify = 'Hey,'
        for user in notify_users:
            to_notify = to_notify + ' ' + user
        to_notify = to_notify + ', it\'s ' + resolved_character
        # await ctx.send(to_notify)
        return to_notify

    @commands.command()
    async def itsm(self, ctx, *characters):
        """Pings users who have requested notices for however many characters are passed. Characters with spaces in names
        need to be enclosed in double quotes (i.e. Sunset Shimmer is not the same as "Sunset Shimmer")"""
        notice_list = None
        for character in characters:
            notice_list = notice_list + self.itis(ctx, character)
        await ctx.send(notice_list)

    # command that uses the assigned name as the command name instead of the function
    # also uses a cooldown to prevent overuse (in this case, 1 command every 60 seconds per server)
    @commands.command(name="knownwaifus")
    @commands.cooldown(1, 60, type=commands.BucketType.guild)
    async def known_waifus(self, ctx):
        """Lists the waifus known by the bot for this server. Has a cooldown of 60 seconds as this is a potentially time consuming request"""
        start = datetime.datetime.now()
        # running the .keys() function on shelf object is time consuming. We're going to measure the time it took
        async with ctx.typing():
            waifus = list(self.notify_user_list.keys())
            end = datetime.datetime.now()
            waifu_list = 'I know of the following waifus: '
            for waifu in waifus:
                # split the returned value into (<server>, \, <character>)
                waifu_t = waifu.partition("\\")
                if waifu_t[0] != str(ctx.guild.id):
                    # if the server doesn't match the current server for this command, skip it
                    pass
                else:
                    waifu_list += waifu_t[2] + ', '
            log("time elapsed: {0}".format(end - start))
            await ctx.send(waifu_list)

    @commands.command(name="knownaliases")
    @commands.cooldown(1, 60, type=commands.BucketType.guild)
    async def known_aliases(self, ctx):
        """Returns a list of all known aliases for this server. Has a cooldown of 60 seconds as this is a potentially time consuming request"""
        current_server = str(ctx.guild.id)
        start = datetime.datetime.now()
        async with ctx.typing():
            aliases = list(self.character_aliases.keys())
            end = datetime.datetime.now()
            alias_list = "I know of the following aliases: \n"
            for alias in aliases:
                alias_t = alias.partition('\\')  # returns a tuple of <server id>, \, and <alias>
                if alias_t[0] != current_server:
                    pass
                else:
                    alias_list += alias_t[2] + " (refers to "
                    alias_list += str(self.character_aliases[alias]) + ")\n"
            log("time elapsed: {0}".format(end - start))
            await ctx.send(alias_list)

    @commands.command(name="doyouknow")
    async def do_you_know(self, ctx, *, character):
        """Confirms if the bot knows of a particular <character>."""
        sender = ctx.author.mention
        resolved_character = str(self.resolve_server_alias(ctx, character.title()))
        # keys are entered into DB as <server>\<character> and Python strings use \ as an escape character, so a
        # literal "\" requires "\\". Other delimiters were tried, but failed
        notice_key = str(ctx.guild.id) + "\\" + resolved_character
        try:
            if notice_key in self.notify_user_list:
                log("notice key found: {0}".format(notice_key))
                if sender in self.notify_user_list[notice_key]:
                    log("sender on notice list")
                    await ctx.send(
                        "Yes, I know of {0} and you're all set to hear when they get posted next!".format(
                            resolved_character))
                else:
                    log("sender not on notice list")
                    await ctx.send(
                        "Yes, I know of {0}! I don't see you signed up for notices for them. Sign up with `{1}notifyme {0}`".format(
                            resolved_character, ctx.bot.command_prefix))
            else:
                await ctx.send(
                    "No, I don't have anything on {0}! Sign up with `{1}notifyme {0}`".format(resolved_character,
                                                                                              ctx.bot.command_prefix))
        except KeyError:
            log("notice key not found: {0}".format(notice_key))
            await ctx.send("No, I don't have anything on {0}! Sign up with `{1}notifyme {0}`".format(resolved_character,
                                                                                                     ctx.bot.command_prefix))

    # no decorator because this is an internal helper function
    def resolve_server_alias(self, ctx, character):
        """Internal command to help resolve an input <character> with any existing aliases.
        If <character> matches an existing alias, returns the character the alias refers to.
        If <character> does not match an alias, returns <character>"""
        current_server = str(ctx.guild.id)
        check_alias = current_server + '\\' + character
        resolved_character = ''
        try:
            # if we find that <character> refers to an alias in our character aliases, return the character referred to
            # by that alias. If this fails, it throws a KeyError, caught below
            resolved_character = self.character_aliases[check_alias].replace(current_server, '')
            log("resolved_character: " + resolved_character)
            log("check_alias: " + check_alias)
        except KeyError:
            # if we don't find any aliases, just return the character
            resolved_character = character
        log("character: " + character)
        log("resolved_character: " + resolved_character)
        log("check_alias: " + check_alias)
        return resolved_character

    @commands.command(name="notifyme")
    async def notify_me(self, ctx, *, character):
        """Adds the user to the list of people to notified when <character> is posted with the 'its' command. <character> can be an alias"""
        sender = ctx.author.mention
        log(sender)
        log("guild: " + str(ctx.guild))
        log("guild id: " + str(ctx.guild.id))
        resolved_character = str(self.resolve_server_alias(ctx, character.title()))
        notice_key = str(ctx.guild.id) + "\\" + resolved_character
        log(notice_key)
        current_notices = [None]
        try:
            current_notices = self.notify_user_list[notice_key]
            log("key found, current notices: " + str(current_notices))
            if sender in current_notices:
                await ctx.send("You've already signed up for notices for {0}, {1}".format(resolved_character, sender))
                return
            current_notices.append(sender)
        except KeyError:
            current_notices[0] = sender
            log("key not found, current notices: " + str(current_notices))
        self.notify_user_list[notice_key] = current_notices
        await ctx.send(
            'Thanks {0}, you\'ve successfully been added to the notice list for {1}'.format(sender, resolved_character))

    @commands.command(name="alias")
    async def add_alias(self, ctx, alias, character):
        """Assign an alias to a character, see notes.
        assign <alias> <character> - The "alias" is the new way to refer to "character".
        "Character" is the original notice assignment. Using quotes (") is key, otherwise the bot will not parse the characters correctly"""
        log("alias: " + alias)
        log("character: " + character)
        current_server = str(ctx.guild.id)
        sender = ctx.author.mention
        new_alias = current_server + '\\' + alias.title()
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
        notice_key = str(ctx.guild.id) + "\\" + str(self.resolve_server_alias(ctx, character.title()))
        current_notices = [None]
        try:
            current_notices = self.notify_user_list[notice_key]
            log(current_notices)
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

    @commands.command(name="removealias")
    async def remove_alias(self, ctx, *, character):
        """Removes the alias referenced by <character>"""
        notice_key = str(ctx.guild.id) + '\\' + character.title()
        try:
            del self.character_aliases[notice_key]
        except KeyError:
            await ctx.send("I don't have an alias for {0}".format(character))
        await ctx.send("The alias for {0} has been removed.".format(notice_key))

    @commands.command(name="stopall")
    # only allow the command to be run once every 60 seconds on each server this bot is in
    @commands.cooldown(1, 60, type=commands.BucketType.guild)
    async def stop_all_notices(self, ctx):
        """Stops all notices on this server for the user. Causes the command to enter a 60 second cooldown
        and the bot shows it is typing while running as it is a potentially slow operation"""
        async with ctx.typing():
            sender = ctx.author.mention
            notify_keys = list(self.notify_user_list.keys())
            halt_keys = []
            log("stop_all_notices invoked by {0}".format(sender))
            for key in notify_keys:
                log(str(key))
                if sender in self.notify_user_list[key]:
                    log(str(self.notify_user_list[key]))
                    current_notices = self.notify_user_list[key]
                    log(current_notices)
                    current_notices.remove(sender)
                    self.notify_user_list[key] = current_notices
                    halt_keys.append(key)
            end_msg = "Notices ended for the following characters: \n"
            for key in halt_keys:
                key_ns = str(key).partition('\\')[2]
                end_msg += key_ns + " "
            await ctx.send(end_msg)

    @commands.command(name="mynotices")
    @commands.cooldown(1, 60, type=commands.BucketType.guild)
    async def my_notices(self, ctx):
        """Lists all notices on this server for the user. Causes the command to enter a 60 second cooldown
        and the bot shows it is typing while running as it is a potentially slow operation"""
        async with ctx.typing():
            sender = ctx.author.mention
            notify_keys = list(self.notify_user_list.keys())
            all_keys = []
            log("my_notices invoked by {0}".format(sender))
            for key in notify_keys:
                log(str(key))
                if sender in self.notify_user_list[key]:
                    log(str(self.notify_user_list[key]))
                    all_keys.append(key)
            end_msg = "You are signed up for notices for the following characters: \n"
            for key in all_keys:
                key_ns = str(key).partition('\\')[2]
                end_msg += key_ns + " "
            await ctx.send(end_msg)

    # this command can only be run by the owner (user who owns the API token under which this bot is running)
    @commands.command(name="debugusers")
    @commands.is_owner()
    async def debug_user_list(self, ctx):
        """An owner-only debug command that lists all users and notices. Suppresses @ mentions"""
        async with ctx.typing():
            notify_keys = list(self.notify_user_list.keys())
            log(notify_keys)
            user_list = ''
            for key in notify_keys:
                log(key)
                user_list + 'key: ' + key + ' user: ' + suppress_mentions(str(self.notify_user_list[key])) + '\n'
                log(user_list)
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

    # only allows users who have the "Manage Server" permission to run (usually the server owner or admins/moderators)
    @commands.command(name="dropserver")
    @commands.has_permissions(manage_guild=True)
    async def drop_notices_server(self, ctx):
        """Drops all notices for this server only. Not yet implemented."""
        server = str(ctx.guild.id)
        notify_keys = list(self.notify_user_list.keys())
        for key in notify_keys:
            if server in key:
                del self.notify_user_list[key]
        await ctx.send("Notices for {0} dropped".format(ctx.guild.name))

    @commands.command(name="dropaliases")
    @commands.has_permissions(manage_guild=True)
    async def drop_aliases_server(self, ctx):
        """Drops all notices for this server only. Not yet implemented."""
        server = str(ctx.guild.id)
        alias_keys = list(self.character_aliases.keys())
        for key in alias_keys:
            if server in key:
                del self.character_aliases[key]
        await ctx.send("Aliases for {0} dropped".format(ctx.guild.name))

    @commands.command()
    async def wotd(self, ctx):
        """Prints the Waifu of the Day"""
        log("wotd invoked by " + str(ctx.author.mention))
        # TODO: implement admin/channel permissions for listing waifu on rotating schedule

        await ctx.send("Astolfo, always")

    """
    Below is the error handling code. Commands that generate errors won't run, and commands without error handlers
    have no way of informing the user that the command failed. These error handler methods are intended to provide enough
    info the user so that they can understand why a command failed and run it successfully in the future (if applicable,
    i.e. have appropriate permissions or contact the owner)
    """

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

    @stop_all_notices.error
    @known_aliases.error
    @known_waifus.error
    @my_notices.error
    async def cooldown_error(self, ctx, error):
        if await ctx.bot.is_owner(ctx.author):
            # if the owner ran the command, ignore the cooldown and run the command again
            await ctx.reinvoke()
            return
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("Uh oh, that command's on cooldown. Please wait a couple of minutes before trying again.")

    @debug_user_list.error
    @drop_all.error
    @drop_all_aliases.error
    @drop_all_notices.error
    @drop_notices_server.error
    @drop_aliases_server.error
    async def perm_error(self, ctx, error):
        # we can handle two different permission errors here: a missing server permission (Manage Server) or not being
        # the bot's owner
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Uh oh. You need to have the {0} permission to use that command".format(error.missing_perms))
        if isinstance(error, commands.NotOwner):
            await ctx.send("Uh on. This command is only usable by the bot's owner")  # indicate owner here?

    @add_alias.error
    async def quote_error(self, ctx, error):
        # the add_alias command requires that the character and alias be enclosed in quotes. If someone forgets, the
        # command fails.
        if isinstance(error, commands.ExpectedClosingQuoteError):
            await ctx.send("Hey! I didn't see a closing quote for that command")


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


@shutdown.error
async def not_bot_owner(ctx, error):
    if isinstance(error, commands.NotOwner):
        await ctx.send("Uh on. This command is only usable by the bot's owner")


bot.add_cog(Waifu(bot))
bot.run(discord_api_token)
