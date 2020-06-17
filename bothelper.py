"""
Helper functions for WaifuHoarder

(C) 2019-2020 by Jordan Aurora Kinsley

Licensed under MIT License, see LICENSE
"""

import datetime
import argparse


def log(output: str, mode: str, arguments: argparse.Namespace):
    """logs output to the locations indicated by mode: "s" for stdout, "v" for verbose output (includes date and time info), and "f" for logging to file"""
    if not mode:
        mode = "s"
        if arguments.verbose:
            mode += "v"
        if arguments.log_file:
            mode += "f"

    log_line = "@{0}: {1}".format(datetime.datetime.now().isoformat(" ", 'seconds'), output)
    if 's' in mode:
        print(output)
    if 'v' in mode and arguments.verbose:
        print(log_line)
    if 'f' in mode and arguments.log_file:
        try:
            # 'with' will close the file, even if an exception occurs
            with(open(arguments.log_file, "a", encoding="utf-8")) as lf:
                lf.writelines(log_line)
        except OSError:
            print("log file at {0} not found".format(arguments.log_file))


def discord_split(message: str):
    messages = []
    if len(message) > 2000:
        while len(message) > 2000:
            begin_check = 1972  # user ids can be up to 23 characters based on observation, which we subtract from the below
            end_check = 1995  # account for the ellipsis because 2000 chars is the max
            end_index = message.find('>', begin_check, end_check)
            if end_index == -1:
                end_index = end_check
            end_index += 1
            short = message[:end_index] + "..."
            message = message[end_index:]
            messages.append(short)
        else:
            messages.append(message)
    else:
        messages.append(message)
    return messages


def read_token(location: str):
    try:
        with open(location, "r") as f:
            lines = f.readlines()
            return lines[0].strip()
    except OSError:
        return None
