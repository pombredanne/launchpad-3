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

for dir in sourcecode lib; do
    for f in $LAUNCHPAD_BASE/$dir/*; do 
        target=$dir/`basename $f`
        test ! -e $target && ln -sv $f $target; 
    done
done
