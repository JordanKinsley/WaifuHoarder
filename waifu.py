import shelve
import datetime
from discord.ext import commands, tasks
from discord.utils import escape_mentions as suppress_mentions
from bothelper import log, discord_split


class Waifu(commands.Cog):
    # These two are used by the shelve module to store what is essentially a dict of IDs mapped to values
    notify_user_list = None
    character_aliases = None
    user_list_location = ''
    character_alias_location = ''
    args = None

    def __init__(self, bot):
        self.bot = bot
        # when we initialize, open a pair of 'shelves' (https://docs.python.org/3/library/shelve.html)
        # writeback is set to False to conserve memory at the expense of addition steps to add info the shelf
        self.notify_user_list = shelve.open(self.user_list_location, flag='c', writeback=False)
        self.character_aliases = shelve.open(self.character_alias_location, flag='c', writeback=False)
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
        self.notify_user_list = shelve.open(self.user_list_location, flag='c', writeback=False)
        self.character_aliases.close()
        self.character_aliases = shelve.open(self.user_list_location, flag='c', writeback=False)

    # basic command that uses the function name as the command name
    @commands.command()
    async def its(self, ctx, *, character):
        """Pings users who've requested to be notified about <character>"""
        # takes a single argument without quotes, anything passed as the "character" gets sent as input
        await ctx.send(self.itis(ctx, character))

    @commands.command()
    @commands.is_owner()
    async def itsnn(self, ctx, *, character):
        """Owner-only test command for sending notices for a character without pinging the user(s) signed up for the notice"""
        no_mention = suppress_mentions(self.itis(ctx, character))
        await ctx.send(no_mention, delete_after=300)

    # helper function for its() and itsm(), but not a command
    def itis(self, ctx, character):
        """Takes a Discord Context ctx and string character as arguments and sends notices to all users signed up for them"""
        log("def itis: character: " + character, 'vf', self.args)
        notify_users = None
        resolved_character = str(self.resolve_server_alias(ctx, character.title()))
        log("def itis: resolved character: " + resolved_character, 'vf', self.args)
        # we're only going to look for notices registered for the server where the command got called
        user_key = str(ctx.guild.id) + "\\" + resolved_character
        log("def itis: user_key: " + user_key, 'vf', self.args)
        try:
            notify_users = self.notify_user_list[user_key]
            log("def itis: notify_users: " + str(notify_users), 'vf', self.args)
            if not notify_users:  # if no values get returned for a <character>
                raise KeyError
        except KeyError:
            return str("Oops! I don't have an alert for {0}, {1}\n".format(resolved_character, ctx.author.mention))
        to_notify = 'Hey,'
        for user in notify_users:
            to_notify = to_notify + ' ' + user
        to_notify = to_notify + ', it\'s ' + resolved_character
        to_notify += "\n"
        return to_notify

    @commands.command()
    async def itsm(self, ctx, *characters):
        """Pings users who have requested notices for however many characters are passed. Characters with spaces in names
        need to be enclosed in double quotes (i.e. Sunset Shimmer is not the same as "Sunset Shimmer")"""
        notice_list = ''
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
            waifus = sorted(waifus)
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
            log("time elapsed: {0}".format(end - start), 'vf', self.args)
            results = discord_split(waifu_list)
            for result in results:
                await ctx.send(result, delete_after=300)

    @commands.command(name="knownaliases")
    @commands.cooldown(1, 60, type=commands.BucketType.guild)
    async def known_aliases(self, ctx):
        """Returns a list of all known aliases for this server. Has a cooldown of 60 seconds as this is a potentially time consuming request"""
        current_server = str(ctx.guild.id)
        start = datetime.datetime.now()
        async with ctx.typing():
            aliases = list(self.character_aliases.keys())
            aliases = sorted(aliases)
            end = datetime.datetime.now()
            alias_list = "I know of the following aliases: \n"
            for alias in aliases:
                alias_t = alias.partition('\\')  # returns a tuple of <server id>, \, and <alias>
                if alias_t[0] != current_server:
                    pass
                else:
                    alias_list += alias_t[2] + " (refers to "
                    alias_list += str(self.character_aliases[alias]) + ")\n"
            log("time elapsed: {0}".format(end - start), 'vf', self.args)
            results = discord_split(alias_list)
            for result in results:
                await ctx.send(result, delete_after=300)

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
                log("notice key found: {0}".format(notice_key), 'vf', self.args)
                if sender in self.notify_user_list[notice_key]:
                    log("sender on notice list", 'vf', self.args)
                    await ctx.send(
                        "Yes, I know of {0} and you're all set to hear when they get posted next!".format(
                            resolved_character))
                else:
                    log("sender not on notice list", 'vf', self.args)
                    await ctx.send(
                        "Yes, I know of {0}! I don't see you signed up for notices for them. Sign up with `{1}notifyme {0}`".format(
                            resolved_character, ctx.bot.command_prefix))
            else:
                await ctx.send(
                    "No, I don't have anything on {0}! Sign up with `{1}notifyme {0}`".format(resolved_character,
                                                                                              ctx.bot.command_prefix))
        except KeyError:
            log("notice key not found: {0}".format(notice_key), 'vf', self.args)
            await ctx.send("No, I don't have anything on {0}! Sign up with `{1}notifyme {0}`".format(resolved_character,
                                                                                                     ctx.bot.command_prefix))

    # no decorator because this is an internal helper function
    def resolve_server_alias(self, ctx, character):
        """Internal command to help resolve an input <character> with any existing aliases.
        If <character> matches an existing alias, returns the character the alias refers to.
        If <character> does not match an alias, returns <character>"""
        current_server = str(ctx.guild.id)
        check_alias = current_server + '\\' + character
        log("def resolve_server_alias: check_alias: " + check_alias, 'vf', self.args)
        resolved_character = ''
        try:
            # if we find that <character> refers to an alias in our character aliases, return the character referred to
            # by that alias. If this fails, it throws a KeyError, caught below
            full_character = self.character_aliases[check_alias]
            log("def resolve_server_alias: full_character: {0}".format(full_character), 'vf', self.args)
            resolved_character = full_character.replace(current_server, '')
            log("def resolve_server_alias: resolved_character: " + resolved_character, 'vf', self.args)
        except KeyError:
            # if we don't find any aliases, just return the character
            resolved_character = character
        log("def resolve_server_alias: post character: " + character, 'vf', self.args)
        log("def resolve_server_alias: post resolved_character: " + resolved_character, 'vf', self.args)
        log("def resolve_server_alias: post check_alias: " + check_alias, 'vf', self.args)
        return resolved_character

    @commands.command(name="notifyme")
    async def notify_me(self, ctx, *, character):
        """Adds the user to the list of people to notified when <character> is posted with the 'its' command. <character> can be an alias"""
        await ctx.send(self.notify(ctx, character))

    @commands.command(name="multinotify")
    async def notify_multiple(self, ctx, *characters):
        """Adds the user to the list of characters, specified as <"character 1", "character 2", ... "character n"> """
        confirmed_notices = ''
        for character in characters:
            confirmed_notices = confirmed_notices + self.notify(ctx, character)
        results = discord_split(confirmed_notices)
        for result in results:
            await ctx.send(result)

    def notify(self, ctx, character):
        sender = ctx.author.mention
        log(sender, 'vf', self.args)
        log("guild: " + str(ctx.guild), 'vf', self.args)
        log("guild id: " + str(ctx.guild.id), 'vf', self.args)
        resolved_character = str(self.resolve_server_alias(ctx, character.title()))
        notice_key = str(ctx.guild.id) + "\\" + resolved_character
        log(notice_key, 'vf', self.args)
        current_notices = [None]
        try:
            current_notices = self.notify_user_list[notice_key]
            log("key found, current notices: " + str(current_notices), 'vf', self.args)
            if sender in current_notices:
                return str("You've already signed up for notices for {0}, {1}\n".format(resolved_character, sender))
            current_notices.append(sender)
        except KeyError:
            current_notices[0] = sender
            log("key not found, current notices: " + str(current_notices), 'vf', self.args)
        self.notify_user_list[notice_key] = current_notices
        return str('Thanks {0}, you\'ve successfully been added to the notice list for {1}\n'.format(sender,
                                                                                                     resolved_character))

    @commands.command(name="alias")
    async def add_alias(self, ctx, alias, character):
        """Assign an alias to a character, see notes.
        alias <alias> <character> - The "alias" is the new way to refer to "character".
        "Character" is the original notice assignment. Using quotes (") is key, otherwise the bot will not parse the characters correctly"""
        log("alias: " + alias, 'vf', self.args)
        log("character: " + character, 'vf', self.args)
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
            log(current_notices, 'vf', self.args)
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
        """Removes the alias referenced by <character>. Usable by any member of a server"""
        notice_key = str(ctx.guild.id) + '\\' + character
        try:
            del self.character_aliases[notice_key]
        except KeyError:
            await ctx.send("I don't have an alias for {0}".format(character))
        await ctx.send("The alias for {0} has been removed.".format(notice_key))

    @commands.command(name="removewaifu")
    @commands.has_permissions(manage_guild=True)
    async def remove_waifu(self, ctx, *, character):
        """Removes the alias referenced by <character>.
        Only usable by people with the Manage Server permission or the bot owner"""
        notice_key = str(ctx.guild.id) + '\\' + character
        try:
            del self.notify_user_list[notice_key]
        except KeyError:
            await ctx.send("I don't have a character by the name of {0}".format(character))
        await ctx.send("The character {0} has been removed.".format(notice_key))

    @commands.command(name="renamewaifu")
    @commands.has_permissions(manage_guild=True)
    async def rename_waifu(self, ctx, character, new_name):
        """Renames the character referred to by <character> to <new name>.
        Only usable by people with the Manage Server permission or the bot owner"""
        notice_key = str(ctx.guild.id) + '\\' + character
        new_key = str(ctx.guild.id) + '\\' + new_name
        try:
            self.notify_user_list[new_key] = self.notify_user_list.pop(notice_key)
        except KeyError:
            await ctx.send("I don't have a character by the name of {0}".format(character))
        await ctx.send("The character {0} has been renamed to {1}.".format(notice_key, new_key))

    @commands.command(name="stopall")
    # only allow the command to be run once every 60 seconds on each server this bot is in
    @commands.cooldown(1, 30, type=commands.BucketType.guild)
    async def stop_all_notices(self, ctx):
        """Stops all notices on this server for the user. Causes the command to enter a 30 second cooldown
        and the bot shows it is typing while running as it is a potentially slow operation"""
        async with ctx.typing():
            sender = ctx.author.mention
            notify_keys = list(self.notify_user_list.keys())
            halt_keys = []
            log("stop_all_notices invoked by {0}".format(sender), 'vf', self.args)
            for key in notify_keys:
                log(str(key), 'vf', self.args)
                if sender in self.notify_user_list[key]:
                    log(str(self.notify_user_list[key]), 'vf', self.args)
                    current_notices = self.notify_user_list[key]
                    log(current_notices, 'vf', self.args)
                    current_notices.remove(sender)
                    self.notify_user_list[key] = current_notices
                    halt_keys.append(key)
            end_msg = "Notices ended for the following characters: \n"
            for key in halt_keys:
                key_ns = str(key).partition('\\')[2]
                end_msg += key_ns + " "
            await ctx.send(end_msg)

    @commands.command(name="mynotices")
    @commands.cooldown(1, 30, type=commands.BucketType.guild)
    async def my_notices(self, ctx):
        """Lists all notices on this server for the user. Causes the command to enter a 30 second cooldown
        and the bot shows it is typing while running as it is a potentially slow operation"""
        async with ctx.typing():
            sender = ctx.author.mention
            notify_keys = list(self.notify_user_list.keys())
            all_keys = []
            log("my_notices invoked by {0}".format(sender), 'vf', self.args)
            for key in notify_keys:
                log(str(key), 'vf', self.args)
                if sender in self.notify_user_list[key]:
                    log(str(self.notify_user_list[key]), 'vf', self.args)
                    all_keys.append(key)
            end_msg = "You are signed up for notices for the following characters: \n"
            all_keys = sorted(all_keys)
            for key in all_keys:
                key_ns = str(key).partition('\\')[2]
                end_msg += key_ns + ", "
            await ctx.send(end_msg)

    # this command can only be run by the owner (user who owns the API token under which this bot is running)
    @commands.command(name="debugusers")
    @commands.is_owner()
    async def debug_user_list(self, ctx):
        """An owner-only debug command that lists all users and notices. Suppresses @ mentions"""
        async with ctx.typing():
            notify_keys = list(self.notify_user_list.keys())
            log(str(notify_keys), 'vf', self.args)
            user_list = ''
            for key in notify_keys:
                log(key, 'vf', self.args)
                user_list += 'key: ' + key + ' user: ' + str(self.notify_user_list[key]) + '\n'
            log(user_list, 'vf', self.args)
            user_list = suppress_mentions(user_list)
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
        log("wotd invoked by " + str(ctx.author.mention), 'vf', self.args)
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
    @itsm.error
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
    @itsnn.error
    @remove_waifu.error
    @rename_waifu.error
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
