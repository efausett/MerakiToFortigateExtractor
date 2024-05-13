"""Common file operations"""

import json
import logging
import os
import platform
import sys
from datetime import datetime
import re

import tomlkit


def load_file(filename, rtype="readlines"):
    """Opens a file to be read

    Args:
        filename (str): The name of the file to be opened
        rtype (str): The return type for the data being returned

    Returns:
        Depends on the rtype
            if read: returns a string of entire contents
            if readlines: returns a list with each line as an element
            if json: returns a json structure
            if toml: returns a toml structure
    """

    try:
        with open(filename, "r", encoding="UTF-8") as file:
            if rtype == "read":
                return file.read()
            elif rtype == "readlines":
                return file.readlines()
            elif rtype == "json":
                return json.load(file)
            elif rtype == "toml":
                return tomlkit.load(file)
            else:
                sys.exit(
                    f"Invalid return type requested. Change {rtype} to valid value"
                )
    except FileNotFoundError:
        sys.exit(f"Could not find file {filename}")


def writelines_to_file(filename, filedata):
    # Write text to given path
    try:
        with open(filename, "w", encoding="utf-8") as file_data:
            file_data.writelines(filedata)
    except FileNotFoundError:
        sys.exit("Error opening file")


def append_to_file(filename, filedata):
    # Write text to given path
    try:
        with open(filename, "a", encoding="utf-8") as file_data:
            file_data.writelines(filedata)
    except FileNotFoundError:
        sys.exit("Error opening file")


def progress_bar(progress, total, width=40):
    char = chr(9632)
    if progress >= total:
        fill_char = colorme(char, "green")
    else:
        fill_char = colorme(char, "red")
    completed = int(width * (progress / total))
    bar = "Progress: [" + fill_char * completed + "-" * (width - completed) + "] "
    percent_done = round(progress / total * 100, 1)
    bar += str(percent_done) + "% " + str(progress) + "/" + str(total)
    return bar


def clear_screen():
    if platform.system().lower() == "windows":
        cmd = "cls"
    else:
        cmd = "clear"
    os.system(cmd)


def colorme(msg, color):
    if color == "red":
        wrapper = "\033[91m"
    elif color == "blue":
        wrapper = "\033[94m"
    elif color == "green":
        wrapper = "\033[92m"
    else:
        # Defaults to white if invalid color is given
        wrapper = "\033[47m"
    return wrapper + msg + "\033[0m"


def load_settings(settings_path="input/settings.toml", required_keys=[]):
    settings = load_file(settings_path, "toml")
    # Make sure the needed keys are there
    for key in required_keys:
        if key not in settings:
            sys.exit(f"Missing key {key}, please make sure all settings are set")
    return settings


def setup_logging(script_name):
    settings = load_settings("input/general_settings.toml")
    log_level = settings["logging"]["file_log_level"]
    log_file = settings["logging"]["file_log_path"]
    time_stamp = datetime.now().strftime("__%Y-%m-%d__%H-%M-%S")
    logname = log_file + script_name + time_stamp + ".log"

    logging.basicConfig(
        filename=logname,
        level=log_level.upper(),
        format=(
            "%(asctime)2s %(filename)22s:%(lineno)6s " "%(levelname)11s > %(message)s"
        ),
        datefmt="%m/%d/%Y %I:%M:%S %p",
    )


def validate_domain(name):
    labels = name.split(".")
    for label in labels:
        if not re.match("^[a-zA-Z0-9][a-zA-Z0-9-]{0,60}[a-zA-Z0-9]$", label):
            raise ValueError("Invalid domain name provided")
    return True
