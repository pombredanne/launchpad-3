#!/bin/bash
#
# Links sourcecode and library from those present in a main tree into
# this tree.
#

if [ "x$1" = "x" ]; then 
    echo "Usage: $0 <directory with main tree>"
    echo "Example: '$0 ~/devel/launchpad-main/'"
    exit 2
fi

if [ ! -e "./sourcecode" ]; then
    echo -n "Error: Couldn't find ./sourcecode/; run me from the "
    echo "top-level of your launchpad tree"
    exit 1
fi

# Use this to obtain the actual absolute path to the tree, so relative
# links don't break
LAUNCHPAD_BASE=$(readlink -f "$1")
if [ ! -e "$LAUNCHPAD_BASE/sourcecode" ]; then
    echo -n "Error: Couldn't find $1/sourcecode; "
    echo "point me at the top level directory of your prebuilt launchpad tree"
    exit 1
fi

for f in $LAUNCHPAD_BASE/sourcecode/*; do
    target=sourcecode/`basename $f`
    if [ ! -e "$f" ]; then
        echo -n "Error: Couldn't find $f; point me at the top level "
        echo "directory of your prebuilt launchpad tree"
        exit 1
    fi
    test ! -e $target && ln -svf $f $target;
done

