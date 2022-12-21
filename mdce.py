#!/usr/bin/python3

from os import chdir, getcwd, walk, listdir
from os.path import dirname, realpath, exists, isdir, isfile, join
from argparse import ArgumentParser
from re import search


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
parser.add_argument('-s', '--sub', action="store_true", default=False)

args = parser.parse_args()
print('ARGS:', args)

def parseFile(filename):
    """
    Parses the given file for code snippets with file names listed
    """
    with open(filename) as file:
        for num, line in enumerate([line.rstrip() for line in file]):
            re_out = search(r"^```\s*(\w+)\:([\w_\-\.\/]+)\s*\[(\d+)\-?(\d+)?\]?.*$", line)
            # print(re_out)
            if re_out is not None and len(re_out.groups()) >= 4:
                print(num, re_out.groups())
                

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
        parseFile(file)

