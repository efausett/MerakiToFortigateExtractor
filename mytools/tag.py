"""A module to add a tag to all .md files in Obsidian directory"""

import sys
from pathlib import Path


def writelines_to_file(filename, filedata):
    # Write text to given path
    try:
        with open(filename, "a", encoding="utf-8") as file_data:
            file_data.writelines(filedata)
    except FileNotFoundError:
        sys.exit("Error opening file")


def main():
    md_files = []
    count = 0
    mypath = Path("~/Documents/Obsidian")
    dir_contents = mypath.expanduser().iterdir()
    for file in dir_contents:
        if ".md" in file.name:
            writelines_to_file(file, "\n#process")
            md_files.append(file)
            count += 1
    print(f"The length of markdown files is {len(md_files)}")
    print(f"The count of modified markdown files is {count}")


if __name__ == "__main__":
    main()
