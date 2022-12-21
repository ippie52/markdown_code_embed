#!/usr/bin/python3
"""
@brief  Script used to embed code from files into markdown files

@author Kris Dunning (ippie52@gmail.com)
"""

from os import chdir, getcwd, walk, listdir, remove, chdir
from os.path import dirname, realpath, exists, isdir, isfile, join
from argparse import ArgumentParser
from re import search
from shutil import copyfile
from filecmp import cmp
from subprocess import Popen, PIPE
from sys import exit
from logging import Log


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
parser.add_argument('-q', '--quiet', action='store_true',
    help='Reduces the number of messages printed',
    default=False)

args = parser.parse_args()

Log.set_verb(Log.VERB_WARNING if args.quiet else Log.VERB_INFO)


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
            Log.d(f"GRABBING: {start} to {end}")
            selected = lines[start:end]
        else:
            raise IndexError(f"Line indices out of bounds: {start} {end} out of {len(lines)}" )
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
        try:
        
            for num, line in enumerate(file):
                if not replacing:
                    start = search(r"^```\s*(\w+)\:([\w_\-\.\/]+)\s*\[?(\d+)?\-?\:?(\d+)?\]?.*$", line)
                    # Append the line
                    out_lines.append(line)
                    # Check for the start of an embedded comment block
                    replacing = start is not None and len(start.groups()) >= 4
                    # If replacing, go add the line(s)
                    if replacing:
                        Log.d(f'{num} -> {start.groups()}')
                        out_lines += getSourceLines(join(directory, start.group(2)), start.group(3), start.group(4))

                else:
                    end = search(r"^```\s*$", line)
                    replacing = end is None
                    Log.d(f'{end} -> replacing {line}')
                    if not replacing:
                        out_lines.append(line)
        except IndexError as e:
            Log.w(f'Failed to parse file: {filename}\n{e}')
            return False

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
        Log.i(f'Found file: {file}')
        files.append(file)
    if check_subs:
        for d in listdir(root):
            d = realpath(join(root, d))
            if isdir(d):
                files += getFiles(d, check_subs, depth + 1)

    return files

# TODO - Find out if file tracked in git
# git ls-files --error-unmatch <file name> | RETURN CODE


def isFileTracked(filename):
    """Identifies whether a file is tracked in git"""
    args = ['git', 'ls-files', '--error-unmatch', filename]
    p = Popen(args, stdout=PIPE, stderr=PIPE)
    p.communicate(timeout=2)
    tracked = False
    if p.returncode == 0:
        tracked = True
    elif p.returncode != 1:
        Log.w(f'Error accessing Git repository in {dirname(filename)}')

    return tracked


# TODO - Check if file is updated on working branch
# git update-index --refresh  | RETURN CODE ?
# git diff-index --quiet HEAD -- | RETURN CODE

def isFileChangedInGit(filename):
    """
    Identifies whether a file has been updated on the current working directory
    """
    args = ['git', 'diff-index', '--quiet', 'HEAD', '--', filename]
    p = Popen(args, stderr=PIPE)
    o, e = p.communicate(timeout=2)
    return p.returncode == 1


# Gather files
for d in [realpath(join(getcwd(), d)) for d in args.directories]:
    Log.i(f'Checking {d} and sub-directories' if args.sub else "")

    if exists(d) and isdir(d):
        Log.d(f'Directory Valid: {d}')
        args.files += getFiles(d, args.sub, 1)

files_changed = []
for i, file in enumerate(args.files):
    last_msg_length = 0
    if isfile(file):
        progress = 100. * float(i + 1) / float(len(args.files))
        msg = f"\rParsing: [{round(progress)}%] " + file
        Log.i(' '.rjust(last_msg_length), end="")
        Log.i(msg, end="")
        last_msg_length = len(msg)
        if not parseMarkDown(file, args.backup, not args.ignore_untracked):
            files_changed.append(file)
Log.i("")

Log.set_log('untracked', colour=Log.COL_CYN, prefix='')
Log.set_log('tracked', colour=Log.COL_YLW, prefix='Git')

original_directory = getcwd();
tracked_changes = []
if len(files_changed) > 0:
    Log.message('untracked', 'Files updated on this run:')
    for file in files_changed:
        Log.message('untracked', '\t' + file)
        chdir(dirname(file))
        if isFileTracked(file) and isFileChangedInGit(file):
            tracked_changes.append(file)

if not args.ignore_git and len(tracked_changes) > 0:
    Log.message('tracked', 'Files tracked by Git modified on this run:')
    for file in tracked_changes:
        Log.message('tracked', '\t' + file)

chdir(original_directory)

if not args.ignore_untracked:
    exit(len(files_changed))
elif not args.ignore_git:
    exit(len(tracked_changes))

exit(0)
