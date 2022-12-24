#!/usr/bin/bash
# Builds the example C++ application

# Note that g++ is required (apt install build-essentials) and
# the files to compile are passed in as arguments.
#
# The latter is because the location of the files is relative, and where
# the script runs would either mean hard-coding the locations of the files
# here or in the README.md file.
g++ -o $1 ${@:2}

result=$?
if [ $result != 0 ]
then
	echo Build failed
	exit $result
fi

echo "'$1' built successfully."

exit 0