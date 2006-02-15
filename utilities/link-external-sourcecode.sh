#!/bin/sh
#
# Links sourcecode and library from those present in a main tree into
# this tree.
#

if [ "x$1" == "x" ]; then 
    echo "Usage: $0 <directory with main tree>"
    echo "Example: '$0 ~/devel/launchpad-main/'"
    exit 2
fi

LAUNCHPAD_BASE=$1

for f in $LAUNCHPAD_BASE/sourcecode/*; do
    target=sourcecode/`basename $f`
    if [ ! -e "$f" ]; then
        echo -n "Couldn't find $f; point me at the top level "
        echo "directory of your launchpad tree"
        exit 1
    fi
    test ! -e $target && ln -svf $f $target;
done

