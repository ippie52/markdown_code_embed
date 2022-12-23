#!/usr/bin/python3
"""
@brief  Script used to embed code from files into markdown files

@author Kris Dunning (ippie52@gmail.com)
"""

from os import chdir, getcwd, walk, listdir, remove, chdir
from os.path import dirname, realpath, exists, isdir, isfile, join
from argparse import ArgumentParser
from re import search, split, IGNORECASE
from shutil import copyfile
from filecmp import cmp
from subprocess import Popen, PIPE, STDOUT
from sys import exit
from logging import Log

# Set up argument parsing
parser = ArgumentParser(prog="EmbedCode",
    description="Embed code within markdown documents")
parser.add_argument('-d', '--directories', metavar="directory",
    help='Directories to be scanned for README.md files',
    default=[], nargs='+')
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

# Check for no file or directories provided and set default
if len(args.files) == 0 and len(args.directories) == 0:
    args.directories = [getcwd()]

# Set up logging
TRACKED_TYPE = 'tracked'
UNTRACKED_TYPE = 'untracked'
Log.set_verb(Log.VERB_WARNING if args.quiet else Log.VERB_INFO)
Log.set_log(UNTRACKED_TYPE, colour=Log.COL_CYN, prefix='')
Log.set_log(TRACKED_TYPE, colour=Log.COL_YLW, prefix='')
Log.set_info(prefix='')


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
            Log.d(f"Grabbing lines {start} to {end}")
            selected = lines[start:end]
        else:
            raise IndexError(f"Line indices out of bounds: {start} {end} out of {len(lines)}" )
    return selected

def getRunnableLines(filename, args):
    """Gets the stdout from the given application or script with the given arguments"""
    args = [filename] + args if len(args) > 0 else filename

    p = Popen(args, stdout=PIPE)
    print("Running", args)
    o, e = p.communicate(timeout=2)
    o = o.decode("utf-8")
    return [o + '\n' for o in o.splitlines()]


class BlockInfo:
    """Simple class used to represent a code block start or end"""

    def __init__(self, is_start=False, is_end=False, runnable=False,
        length=0, filename=None, start_line=None, end_line=None, args=None):
        """Initialises the object"""
        self._is_start = is_start
        self._is_end = is_end
        self._runnable = runnable is not None
        self._filename = filename
        self._start_line = start_line
        self._end_line = end_line
        self._length = length
        self._args = args

    def __repr__(self):
        """Gets the string representation of this object"""
        if self._is_start:
            if self._runnable:
                return f'Start Block: Run {self._filename} <{self._args}>'
            else:
                return f'Start Block: File {self._filename} [{self._start_line}-{self._end_line}]'
        elif self._is_end:
            return 'End of code block'
        else:
            return 'No snippet info'

    def getRunnableArgs(self):
        """Gets the arguments to be passed to Popen"""
        args = []
        if self._args is not None:
            if type(self._args) is list:
                args = self._args
            elif type(self._args) is str:
                # Split the arguments by comma and remove
                args = self._args.split()
        return args


def getBlockInfo(line, last_block):
    """Uses the current line to create a BlockInfo object"""
    expr = r"^(?P<dash>```+)\s*(?P<syntax>\w+)?\:?(?P<runnable>run)?\s*\:?\s*(?P<filename>[\w_\-\.\/]+)?\s*\[?(?P<start_line>\d+)?\-?\:?(?P<end_line>\d+)?\]?\s*(\<(?P<args>.*?)\>)?"
    block = search(expr, line, IGNORECASE)
    info = BlockInfo()
    if block is not None:
        # for i in range(8):
        #     Log.w(f'{i} -> {block.group(i)}')
        if last_block is None:
            info = BlockInfo(is_start=True, length=len(block.group('dash')),
                    runnable=block.group('runnable'),
                    filename=block.group('filename'),
                    start_line=block.group('start_line'),
                    end_line=block.group('end_line'),
                    args=block.group('args'))
        elif last_block is not None and len(block.group('dash')) >= last_block._length:
            info = BlockInfo(is_end=True)

    return info


def parseMarkDown(filename, backup):
    """
    Parses the file for code snippets to embed from files
    @return True if the file has been modified on this run
    """

    old_file_name = filename + ".old"
    # Always create a copy
    copyfile(filename, old_file_name)

    out_lines = []
    last_block = None
    directory = dirname(filename)
    with open(filename) as file:
        code_blocks = []
        replacing = False
        try:
            for num, line in enumerate(file):
                # Check for being in code block within a code block
                block_info = getBlockInfo(line, last_block)
                if block_info._is_start:
                    last_block = block_info
                    out_lines.append(line)
                    if block_info._filename is not None:
                        fname = join(directory, block_info._filename)
                        if block_info._runnable:
                            stdout_lines = getRunnableLines(fname,
                                block_info.getRunnableArgs())
                            out_lines += stdout_lines
                        else:
                            source_lines = getSourceLines(fname,
                                block_info._start_line, block_info._end_line)
                            out_lines += source_lines
                elif block_info._is_end:
                    last_block = None
                    out_lines.append(line)
                elif last_block is None or last_block._filename is None:
                    out_lines.append(line)
                # No other action required, ignore these lines

        except IndexError as e:
            Log.w(f'Failed to parse file: {filename}\n{e}')
            return False

    with open(filename, 'w') as file:
        file.write(''.join(out_lines))
    # Result is true if the file has changed
    result = not cmp(old_file_name, filename)
    if not backup:
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
    Log.i(f'Checking {d}', end="")
    if args.sub:
        Log.i(' and sub-directories')
    else:
        Log.i('')

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
        if parseMarkDown(file, args.backup):
            files_changed.append(file)




original_directory = getcwd();
tracked_changes = []
Log.d(f'There are {len(files_changed)} files changed')
if len(files_changed) > 0:
    # We need to recover a new line after the parsing progress, so \n at start
    Log.i('\nFiles updated on this run:')
    for file in files_changed:
        Log.i('\t' + file)
        chdir(dirname(file))
        if isFileTracked(file) and isFileChangedInGit(file):
            tracked_changes.append(file)

if not args.ignore_git and len(tracked_changes) > 0:
    Log.message(TRACKED_TYPE, 'Files tracked by Git modified on this run:')
    for file in tracked_changes:
        Log.message(TRACKED_TYPE, '\t' + file)

chdir(original_directory)

if not args.ignore_untracked:
    exit(len(files_changed))
elif not args.ignore_git:
    exit(len(tracked_changes))

exit(0)
