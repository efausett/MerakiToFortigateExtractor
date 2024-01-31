'''File operations'''

import sys
import platform
import os
import re
import json
import tomlkit


def writelines_to_file(filename, filedata):
    # Write text to given path
    try:
        with open(filename, 'w', encoding='utf-8') as file_data:
            file_data.writelines(filedata)
    except FileNotFoundError:
        sys.exit('Error opening file')


def append_to_file(filename, filedata):
    # Write text to given path
    try:
        with open(filename, 'a', encoding='utf-8') as file_data:
            file_data.writelines(filedata)
    except FileNotFoundError:
        sys.exit('Error opening file')


def progress_bar(progress, total, width=40):
    char = chr(9632)
    if progress >= total:
        fill_char = colorme(char, 'green')
    else:
        fill_char = colorme(char, 'red')
    completed = int(width * (progress / total))
    bar = 'Progress: [' + fill_char * completed + '-' * (width - completed) + '] '
    percent_done = round(progress / total * 100, 1)
    bar += str(percent_done) + '% ' + str(progress) + '/' + str(total)
    return bar


def clear_screen():
    if(platform.system().lower()=='windows'):
        cmd = 'cls'
    else:
        cmd = 'clear'
    os.system(cmd)


def colorme(msg, color):
    if color == 'red':
        wrapper = '\033[91m'
    elif color == 'blue':
        wrapper = '\033[94m'
    elif color == 'green':
        wrapper = '\033[92m'
    else:
        # Defaults to white if invalid color is given
        wrapper = '\033[47m'
    return wrapper + msg + '\033[0m'


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


def load_settings(settings_path="input/settings.toml"):
    settings = load_file(settings_path, "toml")
    # Make sure the needed keys are there
    required_keys = [
        "vlans"
    ]
    for key in required_keys:
        if key not in settings:
            sys.exit(f"Missing key {key}, please make sure all settings are set")
    return settings


def validate_domain(name):
    labels = name.split(".")
    for label in labels:
        if not re.match("^[a-zA-Z0-9][a-zA-Z0-9-]{0,60}[a-zA-Z0-9]$", label):
            raise ValueError("Invalid domain name provided")
    return True