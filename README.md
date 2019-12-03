**WaifuHoarder** 

A Discord bot for tagging users on command when certain characters are posted


**Requirements**

Python 3.6 or later (3.6.9 used)

Discord.py (version 1.2.5 used)


**Usage**

python wfbot.py -f/--file FILE TOKEN -t/--token TOKEN -p/--prefix PREFIX -v/--verbose VERBOSE FLAG

All arguments are technically optional. However, no default token is currently set. If no default token is set,
and no token is supplied either in a file or with the -t/--token option, the bot will exit with a non-zero status.
This bot requires a current and valid Discord bot token (see https://discordapp.com/developers/applications)
