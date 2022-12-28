# Markdown Code Embed

## Contents
- [Introduction](#introduction)
- [Usage](#usage)
	- [Markdown Syntax](#markdown-syntax)
	 	- [Embed A Full File](#embed-a-full-file)
	 	- [Embed Line Selections](#embed-line-selections)
	 	- [Embed Process Output](#embed-process-output)
 	- [Script Usage](#script-usage)
 		- [Defaults](#defaults)
 		- [Directories](#directories)
 		- [Files](#files)
    - [Exclude](#exclude)
    - [Include Self](#include-self)
 		- [Sub-directories](#sub-directories)
 		- [Backup](#backup)
 		- [Ignore Changes In Git](#ignore-changes-in-git)
 		- [Ignore Untracked Changes](#ignore-untracked-changes)
 		- [Quiet](#quiet)
- [Examples And Extras](#examples-and-extras)
	- [Building And Running](#building-and-running)
	- [Git Pre-Commit Hook](#git-pre-commit-hook)
  - [GitHub Actions/Workflows](#github-actionsworkflows)
  - [Running With A Local Copy](#running-with-a-local-copy)
  - [Running From The GitHub Marketplace](#running-from-the-github-marketplace)
- [Why Did I Make This?](#why-did-i-make-this)
- [TODO](#todo)

## Introduction
This module provides a means of embedding code into markdown files, based on syntax already accepted by markdown interpreters. When parsed, the contents is directly copied from the source files and entered into the code block. The syntax used to indicate the file and line selection is retained and ignored by markdown interpreters.

Note that the module will deliberately replace any existing code within the block. As your code changes, so too should any documentation referencing it. It is up to the developer to check these changes and ensure that the code selection matches up, and that the documentation still reflects what the code is doing.

The script can create backups, however these will need to be restored by the user. Ideally your `README` should be tracked by your version control system, so no real effort has been put into protecting the original document.

## Usage
### Markdown Syntax
This section covers some basics of writing your markdown document to include live code snippets.

General rules:
- The opening code block must all be on one line.
- Must start with at least three back-ticks.
- Must have a language/syntax type ([here](https://github.com/jincheng9/markdown_supported_languages) is a decent list).
- Relative file name placed after the syntax, following a colon.
- Line number range, if required, in square brackets with either a colon `:` or dash `-` separating the start and end lines. A single value is also accepted.
- Must be a closing block with greater than or equal to the number of back-ticks in the opening block.

General Syntax:
````markdown
```language:path/to/file [start_line-end_line]`
```
````

Additional rules for process captures:
- General rules above must be met
- Keyword `run` must appear after the syntax and a colon, and must be followed by a colon before the path of the file to be executed
- Arguments, if required, must be within chevrons and in JSON format (see [this section](#embed-process-output) for more details)
- Line numbers, if set, will be ignored
- Only data sent to `stdout` will be recorded. For `stderr`, a wrapper will be required.

General Syntax:
````markdown
```language:run:path/to/file <["arg1", "arg2", "arg3"]>`
```
````


#### Embed A Full File
By placing the code syntax and the relative path to the file, separated by a colon directly after the opening code block, the entire file will be embedded into the document. This is useful for small files.

Example, embedding the `greetings.h` file from the example folder:
```` markdown
``` cpp:examples/greeting.h
```
````

After running the embed script, the markdown will be filled with the contents of the file, like this:
```cpp:examples/greeting.h
/**
 * @file    greeting.h
 *
 * @brief   Prints a greeting to screen.
 *
 * @author  Kris Dunning (ippie52@gmail.com)
 * @date    2022
 */

#pragma once

/// @brief  Says hello to the name
/// @param  name    The name to greet
void sayHello(const char *name)
{
    printf("Hello, %s!\n", name);
}
```


We can see that this is useful, however, we may only wish to show a subset of a file.
#### Embed Line Selections

To view a smaller, concise sample from the file, we can select lines to and from. This is done by placing the line numbers to start and end on (both inclusive) within square brackets, separated by either a dash or a colon, i.e. `[14-17]` or `[14:17]`.

And so, the following:
````markdown
```cpp:examples/greeting.h [14-17]
```
````
Will render as:
```cpp:examples/greeting.h [14-17]
void sayHello(const char *name)
{
    printf("Hello, %s!\n", name);
}
```
This is much more useful when explaining code snippets.

To show a single line, we can also use a single value in square brackets, e.g. `[14]`.

#### Embed Process Output
This is a useful feature if your documentation contains the output from a process. For example, the help output from the many scripts, including `mdce.py`, is obtained by providing the help option `-h` and usually provides the script/application usage. If the usage is updated, the markdown document will remain up to date.

**Note: _The exit value of the process run must be zero (success). Any other value and `mdce.py` will consider the process to have failed. At which point, the document will fail to parse._**

For example, embedding the usage of the `mdce.py` script is done with the following:
````markdown
```text:run:mdce.py <"-h">
```
````
The result of which can be seen in the [script usage](#script-usage).

Another example, displaying the contents of the `example` directory within this repository:
````markdown
```text:run:/usr/bin/ls <["examples"]>
```
````
Gives:
```text:run:/usr/bin/ls <["examples"]>
build_example_app.sh
example.cpp
greeting.h
pre-commit
```

To capture this, the extra tag `run` is added _between the syntax type and the file/process name_ with its relative location. In addition to this, arguments are provided in JSON format, wrapped in chevrons, e.g. `<["arg1", "arg2"]>`.

**Note: _The limitations to providing arguments are as follows:_**
- Arguments must be in JSON format...
	- Single arguments must be started and terminated by a double quotation mark, e.g. `<"arg">`
	- Multiple arguments must be provided within a JSON array, i,e, surrounded by square brackets, and each argument is started and terminated by a double quotation mark, e.g. `<["arg1", "second arg"]>`
	- Single arguments can be within a JSON array for conformity, so long as the argument itself is still started and terminated in double quotation marks, e.g. `<["arg"]>`
- Any greater-than chevrons (`>`) will terminate your list.
- Only one JSON array is permitted.
- No JSON objects can be entered, they will cause an error.
- The argument list must be on the same line, as with the rest of the values.

In general, `mdce.py` isn't intended to be an all-singing, all-dancing script. If you want to pass arguments in that span multiple lines, include a closing chevron or something else that deviates from the above, I would recommend wrapping your call into a script of some form to make life easier.

For example, if you wish to pass arguments to pipe `stderr` to `/dev/null`, e.g. `my_command 2> /dev/null`, please wrap this in a script!

**Tip: _Avoid capturing process outputs that will differ on each run, they will trip up commit hooks and CI checks._**

**Caution: _Be careful not to pass anything too demanding or recursive. For instance, calling the `mdce.py` without the `-h` argument will result in a recursive call to itself, spawning many processes. No prizes will be awarded for realising that I made this happen during my testing._**

### Script Usage
To run the script, `Python3` is required.

From the script's usage output:

```text:run:mdce.py <"-h">
usage: EmbedCode [-h] [-d directory [directory ...]]
                 [-f file_name [file_name ...]] [-e directory [directory ...]]
                 [-i] [-s] [-b] [-g] [-u] [-q]

Embed code within markdown documents

options:
  -h, --help            show this help message and exit
  -d directory [directory ...], --directories directory [directory ...]
                        Directories to be scanned for README.md files
  -f file_name [file_name ...], --files file_name [file_name ...]
                        Files to be scanned
  -e directory [directory ...], --exclude directory [directory ...]
                        Directories to exclude from searching
  -i, --include-self    Includes the directory (and sub-directories with -s)
                        of this script when parsing
  -s, --sub             Checks all sub-directories
  -b, --backup          Backs up the original file, appending ".old" to the
                        file name
  -g, --ignore-git      Exit value ignores changes in git
  -u, --ignore-untracked
                        Exit value ignores changes to untracked files
  -q, --quiet           Reduces the number of messages printed
```

When run, provided at most only one of `ignore-git` or `ignore-untracked` are supplied, the exit status will indicate the number of files that the parser has updated. This allows commit hooks and CI to identify whether a developer has forgotten to update the documentation.

#### Defaults
By default, if no files or directories are provided, the current working directory will be selected for a search for a file called `README.md`. Any changes to the file will be reported in the exit value from the script. Information messages will be shown, and no backup will be made.

#### Directories
Multiple directories can be provided. Each will be searched for files called `README.md`

#### Files
If you wish to specify files to be parsed that are not called `README.md`, this option can be used. Multiple files can be provided.

#### Exclude
This provides excluded directories, although currently this only allows for literal directories (and sub-directories). There is no pattern matching, just a little string check, but it should be enough for most needs.

#### Include Self
By default, the directory (and sub-directories) of the `mdce.py` script are excluded from parsing. This option is to include it, only really useful for me developing this repository! Or if, for some reason, you have placed `README.md` files in this directory or sub-directories.

#### Sub-directories
With the `-s` option set, each directory provided with the `-d` option will be searched to their very depths. It is best to tread with caution using this option.

#### Backup
This option provides a crude backup for each file parsed, making a copy before parsing with `.old` appended to the file name.

#### Ignore Changes In Git
This option is only really useful when you want the exit value to always be zero, and should be combined with the `-u`/`--ignore-untracked` option, or you do not wish to be notified about changes to tracked files.

#### Ignore Untracked Changes
This option is useful when you only care about files tracked by Git. Setting this will cause the exit value to only reflect the number of updated files that Git is tracking, however the output will still mention all files changed, tracked or not providing the `-q/--quiet` option is not provided.

#### Quiet
This option turns off information and debug messages, and only shows warnings, errors and messages about changes to tracked files (providing the `ignore-git` option is not set). This option is useful when you only really care about the output and whether changes have been made. Errors and changes will still be shown, where appropriate.

## Examples And Extras
As well as the examples within this document, others can be found in the [example directory](/examples)
### Building And Running
In the examples directory are a C++ source file, header and build script. These combine to build a very simple application, but also provide a more ambitious example.

The following example should show the build output to build the application.

The script `build_example_app.sh` (shown below) takes in positional arguments. The first being the name of the executable to be built, and the rest being the files to compile. I have made it this way to further show multiple arguments being passed to a process, but also because I was lazy and there are issues with relative locations based on where `mdce.py` runs the applications from.
````markdown
```text:run:examples/build_example_app.sh <["hello", "examples/example.cpp"]>
```
````

The output of this call:
```text:run:examples/build_example_app.sh <["hello", "examples/example.cpp"]>
'hello' built successfully.
```
Provided the exit status of the script is correct, the above call will have now built the executable, and so the following example will provide the output, showing the result with and without an argument:
````markdown
```text:run:./hello
```
````
Output:
```text:run:./hello
Hello, World!
```

... And ...
````markdown
```text:run:./hello <"'My Name'">
```
````
Output:
```text:run:./hello <"My Name">
Hello, My Name!
```

**Note: _Of course this is all very meta and has a lot of potential to cause more harm than good. But I am not here to tell you what you should and shouldn't do. Avoid doing anything silly or overly complicated - this is not intended to be your build system with integrated CI features, although it could do something of the sort if desired._**

### Git Pre-Commit Hook
An example of a Git pre-commit hook is found [here](/examples/pre-commit). It shows a fairly straight-forward means of running `mdce.py` and preventing a commit if any changes have been made. This is a natural step for preventing commits that unintentionally update the `README` file. If the commit fails, the developer should inspect the changes to make sure that their documentation remains up to date, either adding the changes to their commit in whatever way is required.

**Caution: _This may cause problems if any processes run that modify files within the repository_**

To use this, copy the file to your `.git/hooks/` directory.

### GitHub Actions/Workflows

#### Running With A Local Copy
This repository is intended to be cloned to your development platform so that it can be used on any other repository. However, you may wish to include it in with your local changes, either with a sub-module or a direct copy. Feel free to do as you wish there. If doing so, there is an example of a workflow in this repository that runs this script on this very file, ensuring that any pull requests have up to date documentation.

Below is the contents of the [active workflow file](.github/workflows/check-readme.yml)
```yaml:.github/workflows/check-readme.yml
name: Check Readme

on:
  workflow_dispatch:
  pull_request:
    branches:
      - main
      - master

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3
      - name: Run MDCE
        run: ./mdce.py -q
```

#### Running From The GitHub Marketplace
Instead of having a copy within your repository, this check is available as an [Action on the GitHub Marketplace](https://github.com/ippie52/markdown_code_embed_action). Over there, you will find an [example](https://github.com/ippie52/markdown_code_embed_action/blob/main/example) file showing a simple way to include this action into your repository.


## Why Did I Make This?
I have found that maintaining documentation and README files can often fall behind, and so I wanted something that nudges me as a developer to check when my code changes and the documentation may have become out of date.

Initially, I wanted something to simply embed some code snippets automatically. I found a few good examples that could be added to GitHub's workflows, and some for `npm`, but none that were regularly maintained, worked efficiently or quite did what I wanted. At which point, I thought "How hard can it be?", so I whipped up the first instance pf `mdce.py`.

I took the examples that others have created out there, and made something fairly light-weight and simple. I didn't want anything overly complicated or hard to follow. I also wanted something that could be easily integrated into a GitHub workflow, Git hooks and so on.

As I wrote this very document, I also started to see other things that would be useful, so made them happen.

## TODO
Below are a list of things I am hoping to bring to this in future
1. Option to re-indent code to prevent too much leading white-space
1. Option to allow changes and create another commit - Despite going against the principals of this, but it may be useful in some situations.


If you happen to see this, like it, use it and want me to add anything else, or fix any bugs, feel free to post an issue and I'll reply when I can.

I am hoping to maintain this, however this is meant to be a fairly simple script so I do not wish to extend its purpose too far outside where it is now.