#!/usr/bin/python3

from os import chdir, getcwd, walk, listdir
from os.path import dirname, realpath, exists, isdir, isfile, join
from argparse import ArgumentParser
from re import search
from shutil import copyfile


real_path = realpath(__file__)
print('You file is at', realpath(__file__), "which is in path", dirname(real_path))
print('Your terminal resides at', getcwd())

parser = ArgumentParser(prog="EmbedCode",
    description="Embed code within markdown documents")
parser.add_argument('-d', '--directories', metavar="directory",
    help='Directories to be scanned for README.md files',
    default=getcwd(), nargs='+')
parser.add_argument('-f', '--files', metavar="file name",
    help='Files to be scanned',
    default=[], nargs='+')
parser.add_argument('-s', '--sub', action="store_true", 
    help='Checks all sub-directories',
    default=False)
parser.add_argument('-b', '--backup', action="store_true", 
    help='Backs up the original file, appending ".old" to the file name',  
    default=False)

args = parser.parse_args()
print('ARGS:', args)

def getSourceLines(filename, start, end):
    """Gets the list of lines to be extracted from the given file"""
    selected = None
    with open(filename) as file:
        lines = file.readlines()
        # Bounds check
        if start is None:
            start = 1
            end = len(lines)
        elif end is None:
            end = start
        # Add one, zero indexed list vs lines starting at 1
        start = int(start) - 1
        # No need to remove from end
        end = int(end)
        if start <= len(lines) and end <= len(lines):
            print("GRABBING:", start, "to", end)
            selected = lines[start:end]
        else:
            raise IndexError("Line indiced out of bounds")
    return selected


def parseReadme(filename, backup):
    """
    Parses the given file for code snippets with file names listed
    """
    if backup:
        copyfile(filename, filename + ".old")
    out_lines = []
    with open(filename) as file:
        replacing = False
        
        for num, line in enumerate(file):
            if not replacing:
                start = search(r"^```\s*(\w+)\:([\w_\-\.\/]+)\s*\[?(\d+)?\-?(\d+)?\]?.*$", line)
                # Append the line
                out_lines.append(line)
                # Check for the start of an embedded comment block
                replacing = start is not None and len(start.groups()) >= 4
                # If replacing, go add the line(s)
                if replacing:
                    print('@@@@', num, start.groups())
                    # print(num, start.groups())
                    # print(getSourceLines(start.group(2), start.group(3), start.group(4)))
                    out_lines += getSourceLines(start.group(2), start.group(3), start.group(4))

            else:
                end = search(r"^```\s*$", line)
                replacing = end is None
                print(end, "->", replacing, line)
                if not replacing:
                    out_lines.append(line)
    for l in out_lines:
        print(l)
    with open(filename, 'w') as file:
        file.write(''.join(out_lines))
                

                
                

def getFiles(root, check_subs, depth):
    """Gets the matching files recursively"""
    root = realpath(root)
    files = []
    file = join(root, "README.md")
    if exists(file):
        print('Found file:', file)
        files.append(file)
    if check_subs:
        for d in [join(root, d) for d in listdir(root) if isdir(d)]:
            files += getFiles(d, check_subs, depth + 1)

    return files

# Gather files
for directory in args.directories:
    if exists(directory) and isdir(directory):
        args.files += getFiles(directory, args.sub, 1)

for file in args.files:
    if isfile(file):
        print("Scanning:", file)
        parseReadme(file, args.backup)

