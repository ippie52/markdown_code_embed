#!/usr/bin/python3

from os import chdir, getcwd, walk, listdir, remove, chdir
from os.path import dirname, realpath, exists, isdir, isfile, join
from argparse import ArgumentParser
from re import search
from shutil import copyfile
from filecmp import cmp
from subprocess import Popen, PIPE


# real_path = realpath(__file__)
# print('You file is at', realpath(__file__), "which is in path", dirname(real_path))
# print('Your terminal resides at', getcwd())

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
parser.add_argument('-g', '--ignore-git', action="store_true",
    help='Return value ignores changes in git',
    default=False)
parser.add_argument('-u', '--ignore-untracked', action="store_true",
    help='Return value ignores changes to untracked files',
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
            # print("GRABBING:", start, "to", end)
            selected = lines[start:end]
        else:
            raise IndexError("Line indiced out of bounds")
    return selected


def parseMarkDown(filename, backup, compare):
    """
    Parses the given file for code snippets with file names listed
    """
    old_file_name = filename + ".old"
    if backup or compare:
        copyfile(filename, old_file_name)
    out_lines = []
    directory = dirname(filename)
    with open(filename) as file:
        replacing = False
        
        for num, line in enumerate(file):
            if not replacing:
                start = search(r"^```\s*(\w+)\:([\w_\-\.\/]+)\s*\[?(\d+)?\-?\:?(\d+)?\]?.*$", line)
                # Append the line
                out_lines.append(line)
                # Check for the start of an embedded comment block
                replacing = start is not None and len(start.groups()) >= 4
                # If replacing, go add the line(s)
                if replacing:
                    print('@@@@', num, start.groups())
                    print(num, start.groups())
                    # print(getSourceLines(start.group(2), start.group(3), start.group(4)))
                    out_lines += getSourceLines(join(directory, start.group(2)), start.group(3), start.group(4))

            else:
                end = search(r"^```\s*$", line)
                replacing = end is None
                # print(end, "->", replacing, line)
                if not replacing:
                    out_lines.append(line)

    with open(filename, 'w') as file:
        file.write(''.join(out_lines))
    result = not compare or cmp(old_file_name, filename)
    if compare and not backup:
        remove(old_file_name)
    return result


def getFiles(root, check_subs, depth):
    """Gets the matching files recursively"""
    root = realpath(root)
    files = []
    file = join(root, "README.md")
    if exists(file):
        print('Found file:', file)
        files.append(file)
    if check_subs:
        for d in listdir(root):
            d = realpath(join(root, d))
            if isdir(d):
                files += getFiles(d, check_subs, depth + 1)

    return files

# TODO - Find out if file tracked in git
# git ls-files --error-unmatch <file name> | RETURN CODE
# TODO - Check if file is updated on working branch
# git update-index --refresh  | RETURN CODE ?
# git diff-index --quiet HEAD -- | RETURN CODE


def isFileTracked(filename):
    """Identifies whether a file is tracked in git"""
    args = ['git', 'ls-files', '--error-unmatch', filename]
    p = Popen(args, stderr=PIPE)
    o, e = p.communicate(timeout=2)
    tracked = False
    if p.returncode == 0:
        tracked = True
    elif p.returncode != 1:
        print('Error accessing Git repository in', dirname(fc))


    print(filename, "tracked?", p.returncode)
    # print(dir(p))
    # print()


# Gather files
for d in [realpath(join(getcwd(), d)) for d in args.directories]:
    print('Checking', d, "and sub-directories" if args.sub else "")

    if exists(d) and isdir(d):
        print('Directory Valid:', d)
        args.files += getFiles(d, args.sub, 1)

files_changed = []

for file in args.files:
    if isfile(file):
        print("Parsing:", file)
        if not parseMarkDown(file, args.backup, not args.ignore_untracked):
            files_changed.append(file)


original_directory = getcwd();
for fc in files_changed:
    chdir(dirname(fc))
    tracked = isFileTracked(fc)
    print("File", fc, "changed.")

chdir(original_directory)
