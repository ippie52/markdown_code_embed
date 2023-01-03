#!/usr/bin/python3
"""
@brief  Script used to embed code from files into markdown files

@author Kris Dunning (ippie52@gmail.com)
"""

from os import chdir, getcwd, walk, listdir, remove, chdir
from os.path import dirname, realpath, exists, isdir, isfile, join
from argparse import ArgumentParser
from re import search, IGNORECASE
from shutil import copyfile
from filecmp import cmp
from subprocess import Popen, PIPE, STDOUT, TimeoutExpired
from sys import exit
from logging import Log
import shlex

#
# Set up argument parsing for MDCE and command line arguments provided
#
parser = ArgumentParser(prog="Markdown Code Embed",
    description="Embed code within markdown documents")
parser.add_argument('-d', '--directories', metavar="directory",
    help='Directories to be scanned for README.md files',
    default=[], nargs='+')
parser.add_argument('-f', '--files', metavar="file_name",
    help='Files to be scanned',
    default=[], nargs='+')
parser.add_argument('-e', '--exclude', metavar='directory', nargs='+',
    help='Directories to exclude from searching',
    default=[])
parser.add_argument('-i', '--include-self', action='store_true', default=False,
    help="""
Includes the directory (and sub-directories with -s) of this script when parsing
""")
parser.add_argument('-s', '--sub', action="store_true", 
    help='Checks all sub-directories',
    default=False)
parser.add_argument('-b', '--backup', action="store_true", 
    help='Backs up the original file, appending ".old" to the file name',  
    default=False)
parser.add_argument('-g', '--ignore-git', action="store_true",
    help='Exit value ignores changes in git',
    default=False)
parser.add_argument('-u', '--ignore-untracked', action="store_true",
    help='Exit value ignores changes to untracked files',
    default=False)
parser.add_argument('-q', '--quiet', action='store_true',
    help='Reduces the number of messages printed',
    default=False)
parser.add_argument('-c', '--code', action='store_true',
    help='Displays the code parser usage instructions, then exit',
    default=False)
parser.add_argument('-t', '--timeout', type=int, default=None, metavar='timeout',
    help="""
The number of seconds to wait for the git requests to complete.
Default is no timeout.
""")


#
# Set up parser for block commands
#
code_parser = ArgumentParser(prog='Markdown Code Embed - Code Block Commands',
    description='Code block command parsing')
code_parser.add_argument('-s', '--start', metavar='line_number', default=None,
    help='The starting line to display from.')
code_parser.add_argument('-e', '--end', metavar='line_number', default=None,
    help="""
The end line (inclusive) to display to. If start is set, this will automatically
be set to the same, so that only one line is shown. Leave both blank to include
the entire file.
""")
code_parser.add_argument('-i', '--indent', metavar='indent_option (t | sN)',
    default=None,
    help="""
Indentation options for re-indenting to trim leading white space.
Use 't' for code using tab characters for indentation.
Use 'sN' for code using spaces, where 'N' is replaced by the number of spaces
  per indentation, e.g. s4.
If this value is not set, any leading white space will be left in the block.
""")
code_parser.add_argument('-r', '--run', action='store_true', default=False,
    help='Whether to run the file provided and capture the output from stdout.')
code_parser.add_argument('-a', '--args', default="",
    help="""
Arguments passed forward when the run option is provided.
Single arguments must be wrapped in two sets of quotation marks, for example:
"'-h'" to avoid them being interpreted as another option.
Multiple arguments must be surrounded with quotation marks, however not all need
to be wrapped individually unless they need to preserve spaces, e.g.
'a1, "arg 2", three'.
""")
code_parser.add_argument('-t', '--timeout', type=int, default=None,
    help="""
The number of seconds to wait for the process to complete.
Default is no timeout.
""")

#
# Helper functions
#
def getStrippedLines(lines, indent):
    """
    @brief  Strips the indentation from each lines to the minimum, where
            required
    @param  lines   The lines to be stripped
    @param  indent  The indent string
    @return Stripped lines
    """
    numbers = []
    for line in lines.copy():
        i = 0
        while line.startswith(indent):
            line = line[len(indent):]
            i += 1
        numbers.append(i)
    strip_count = min(numbers) * len(indent)
    return [line[strip_count:] for line in lines]


def getSourceLines(filename, start, end, indent=None):
    """
    @brief  Gets the list of lines to be extracted from the given file
    @param  filename    The name of the file to read from
    @param  start       The line number to start from
    @param  end         The line number to end on
    @param  indent      The indent string
    @return Gets the source lines from the given file, between start and end and
            with leading white space removed, where requested
    """
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

        if indent is not None:
            selected = getStrippedLines(selected, indent)

    return selected

def getRunnableLines(filename, args, timeout):
    """
    @brief  Gets the stdout from the given application or script with the given
            arguments
    @param  filename    The name of the file to run
    @param  args        The arguments to pass to the command
    @param  timeout     The process timeout duration in seconds
    @return The output from the command
    """
    args = [filename] + args if len(args) > 0 else filename

    Log.i(f'Running {args}')
    p = Popen(args, stdout=PIPE, stderr=PIPE)
    o = ""
    try:
        o, e = p.communicate(timeout=timeout)
        if p.returncode != 0:
            e = e.decode('utf-8')
            raise RuntimeError(f'Process failed: {args}: \n{e}')
        o = o.decode('utf-8')
    except TimeoutExpired as e:
        Log.e('Process timed out.')
        raise e
    return [o + '\n' for o in o.splitlines()]

#
# Helper class
#
class BlockInfo:
    """Simple class used to represent a code block start or end"""

    def __init__(self, is_start=False, is_end=False, length=0, filename=None,
        # runnable=False, start_line=None, end_line=None, indent=None,
        args=None):
        """
        @brief  Initialises the object
        @param  is_start    Whether this is a start block
        @param  is_end      Whether this is an end block
        @param  length      The number of dashes for this block
        @param  filename    The name of the file to be processed
        @param  args        Code block arguments
        """
        self._is_start = is_start
        self._is_end = is_end
        self._filename = filename
        self._length = length

        if args is None:
            args = ""

        block_args = code_parser.parse_args(shlex.split(args)) if args is not None else None
        self._runnable = block_args.run
        self._start_line = block_args.start
        self._end_line = block_args.end
        self._timeout = block_args.timeout

        if block_args.indent is not None:
            self._indent = BlockInfo.getTab(block_args.indent)
        else:
            self._indent = None
        self._args = shlex.split(block_args.args)

    @staticmethod
    def getTab(in_val):
        """
        @brief  Gets the tab character from the value input from the user
        @param  in_val  The input value to be parsed
        @return The string representation of the tab used in the code block
        """
        tab = '\t'
        if in_val.lower().startswith('s'): # Using Spaces
            # Default to 4 if no value is provided
            space_count = int(in_val[1:]) if len(in_val) > 1 else 4
            tab = ' ' * space_count
        elif in_val.lower() != 't':
            raise ValueError('Indentation must be either "sN" (N being an integer) or "t"')

        return tab

    def __repr__(self):
        """
        @brief  Gets the string representation of this object
        """
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
        """
        @brief  Gets the arguments to be passed to Popen.
        """
        args = []
        Log.d(f'Parsing {self._args}')
        if self._args is not None:
            if type(self._args) is str:
                try:
                    self._args = shlex.split(self._args)
                except Exception as e:
                    raise ValueError(f'Invalid arguments found: {self._args} - ' + str(e))

            elif type(self._args) is dict:
                raise ValueError(f'Dictionary objects are not supported: {self._args}')

            if type(self._args) is list:
                args = self._args
                Log.d(f'Args are list: {self._args}')
            elif type(self._args) is str:
                Log.d(f'Args are string: {self._args}')
                args = [self._args]
        return args

#
# More helper functions
#
def getBlockInfo(line, start_block):
    """
    @brief  Uses the current line to create a BlockInfo object
    @param  line        The current line of text from the file
    @param  start_block The last start block found, otherwise None
    @return The BlockInfo object for the current line
    """
    # Expression to extract the dashes, syntax, file name and any options to be
    # processed for this block
    expr = r"^(?P<dash>```+)\s*((?P<syntax>\w+):)?\s*(?P<filename>[\w_\-\.\/]+)?(?P<args>.*)$"
    block = search(expr, line, IGNORECASE)
    info = BlockInfo()

    if block is not None:
        if start_block is None:
            if block.group('syntax') is not None:
                # This is a start block to be processed further
                dash = block.group('dash')
                info = BlockInfo(is_start=True, length=len(dash),
                        filename=block.group('filename'),
                        args=block.group('args'))
            else:
                # This is a simple start block
                info = BlockInfo(is_start=True, length=len(block.group('dash')))

        elif start_block is not None and len(block.group('dash')) >= start_block._length:
            info = BlockInfo(is_end=True)

    return info


def parseMarkDown(filename, backup):
    """
    @brief  Parses the file for code snippets to embed from files
    @param  filename    The name of the file to be parsed
    @param  backup      Whether to store a backup of the file
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
                                block_info.getRunnableArgs(),
                                block_info._timeout)
                            out_lines += stdout_lines
                        else:
                            source_lines = getSourceLines(fname,
                                block_info._start_line,
                                block_info._end_line,
                                block_info._indent)
                            out_lines += source_lines
                elif block_info._is_end:
                    last_block = None
                    out_lines.append(line)
                elif last_block is None or last_block._filename is None:
                    out_lines.append(line)
                # No other action required, ignore these lines

        except (IndexError, ValueError, RuntimeError, FileNotFoundError) as e:
            # Report the error with line number to make it easier to find
            Log.w(f'Failed to parse file [{num + 1}]: {filename}\n{e}')
            return False
    # Re-write the file with the updated output
    with open(filename, 'w') as file:
        file.write(''.join(out_lines))
    # Result is true if the file has changed
    result = not cmp(old_file_name, filename)
    # Remove original file if no back-ups were requested
    if not backup:
        remove(old_file_name)
    return result


def getFiles(root, check_subs, ignored_dirs):
    """
    @brief  Gets the matching files recursively (where required)
    @param  root            The root directory
    @param  check_subs      Whether to check sub-directories
    @param  ignored_dirs    Collection of directories to be ignored
    @return Collection of files to be processed
    """
    root = realpath(root)
    files = []
    # Must not start with any ignored directory
    if not root.startswith(tuple(ignored_dirs)):
        file = join(root, "README.md")
        if exists(file):
            Log.i(f'Found file: {file}')
            files.append(file)
        if check_subs:
            for d in listdir(root):
                d = realpath(join(root, d))
                if isdir(d):
                    files += getFiles(d, check_subs, ignored_dirs)
    else:
        Log.d(f'Ignoring {root}, found in {ignored_dirs}')

    return files

def isFileTracked(filename, timeout):
    """
    @brief  Identifies whether a file is tracked in git
    @param  filename    The file to be checked
    @param  timeout     The length of time to wait for the git command
    @return Whether the file is tracked
    """
    args = ['git', 'ls-files', '--error-unmatch', filename]
    p = Popen(args, stdout=PIPE, stderr=PIPE)
    p.communicate(timeout=timeout)
    tracked = False
    if p.returncode == 0:
        tracked = True
    elif p.returncode != 1:
        Log.w(f'Error accessing Git repository in {dirname(filename)}')
    return tracked


def isFileChangedInGit(filename, timeout):
    """
    @brief  Identifies whether a file has been updated on the current working
            directory
    @param  filename    The file to be checked
    @param  timeout     The length of time to wait for the git command
    @return Whether the file has changed in git
    """
    args = ['git', 'diff-index', '--quiet', 'HEAD', '--', filename]
    p = Popen(args, stderr=PIPE)
    o, e = p.communicate(timeout=timeout)
    return p.returncode == 1


#
# The main functionality of the script
#
if __name__ == '__main__':
    #
    # Process arguments
    #
    args = parser.parse_args()
    if args.code:
        code_parser.print_help()
        exit(0)

    # Check for no file or directories provided and set default
    if len(args.files) == 0 and len(args.directories) == 0:
        args.directories = [getcwd()]

    # Add to excluded files
    if not args.include_self:
        args.exclude.append(dirname(realpath(__file__)))

    # Get correct directories for individual files provided
    for i in range(len(args.files)):
        args.files[i] = join(getcwd(), args.files[i])

    #
    # Set up logging
    #
    TRACKED_TYPE = 'tracked'
    Log.set_verb(Log.VERB_WARNING if args.quiet else Log.VERB_INFO)
    Log.set_log(TRACKED_TYPE, colour=Log.COL_YLW, prefix='')
    Log.set_info(prefix='')

    #
    # Gather files in requested directories and sub-directories
    #
    for d in [realpath(join(getcwd(), d)) for d in args.directories]:
        Log.i(f'Checking {d}', end="")
        if args.sub:
            Log.i(' and sub-directories')
        else:
            Log.i('')

        if exists(d) and isdir(d):
            Log.d(f'Directory Valid: {d}')
            args.files += getFiles(d, args.sub, args.exclude)

    #
    # Parse files
    #
    files_changed = []
    for i, file in enumerate(args.files):
        if isfile(file):
            progress = 100. * float(i + 1) / float(len(args.files))
            Log.i(f"Parsing: [{round(progress)}%] {file}")
            if parseMarkDown(file, args.backup):
                files_changed.append(file)

    #
    # Report changed files
    #
    original_directory = getcwd();
    tracked_changes = []
    Log.d(f'There are {len(files_changed)} files changed')
    if len(files_changed) > 0:
        # We need to recover a new line after the parsing progress, so \n at start
        Log.i('\nFiles updated on this run:')
        for file in files_changed:
            Log.i('\t' + file)
            chdir(dirname(file))
            if isFileTracked(file, args.timeout) and isFileChangedInGit(file, args.timeout):
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
