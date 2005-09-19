#!/bin/sh
#
# Runs pyflakes and pylint on files changed in tree
#
# 2005-07-14 creation (kiko)
# 2005-07-15 added verbose mode, and fixed up warnings
# 2005-07-20 added detection of conflict markers
# 2005-07-21 nicer handling of verbose mode, tweaking of warnings

# Stuff I'd like to add:
# XXX: E0201 (Access to undefined member) fails for classmethods and
#            SQLObject's id and _table attributes
# XXX: W0613 (Unused argument) triggers often for hook methods, and for tuple
#            unpacking where you really want it to make the code clearer
PYLINTOFF="W0232,C0103,W0103,C0101,W0142,R0903,W0201"

if [ "$1" == "-v" ]; then
    shift
else
    # Silent mode; disabled:
    # W0131 (Missing docstring) we don't have enough of them :-(
    # R0912 (Too many branches)
    # R0913 (Too many arguments)
    # R0914 (Too many local variables)
    # R0915 (Too many statements)
    # W0511 (XXX and TODO listings)
    # W0302 (Too many lines in module)
    # R0902 (Too many instance attributes)
    PYLINTOFF="$PYLINTOFF,W0131,R0912,R0913,R0914,R0915,W0511,W0302"
fi

# hint: use --include-ids=y to find out the ids of messages you want to
# disable.
PYLINTOPTS="--reports=n --enable-metrics=n --include-ids=y
            --disable-msg=$PYLINTOFF"

# Disables:
# E0213 (Method doesn't have "self" as first argument)
# E0211 (Method has no argument)
# W0613 (Unused argument)
PYLINTOPTS_INT="$PYLINTOPTS,E0213,E0211,W0613"

export PYTHONPATH=lib:$PYTHONPATH

if [ -z "$1" ]; then
    files=`baz status | grep '^ ' | cut -c5-`
else
    files=$*
fi

if [ -z "$files" ]; then
    echo "No changed files detected"
    exit
fi

for file in $files; do
    # NB. Odd syntax on following line to stop lint.sh detecting conflict
    # markers in itself.
    if grep -q -e '<<<''<<<<' -e '>>>''>>>>' $file; then
        echo "============================================================="
        echo "Conflict marker found in $file"
    fi
done

pyfiles=`echo "$files" | grep '.py$'`
if [ -z "$pyfiles" ]; then
    exit
fi

if which pyflakes >/dev/null; then
    output=`pyflakes $pyfiles`
    if [ ! -z "$output" ]; then
        echo "============================================================="
        echo "Pyflakes notices"
        echo "-------------------------------------------------------------"
        echo "$output"
    fi
fi

for file in $pyfiles; do
    OPTS=$PYLINTOPTS
    if echo $file | grep -qs "launchpad/interfaces/"; then
        OPTS=$PYLINTOPTS_INT
    fi
    output=`pylint.python2.4 $file $OPTS 2>/dev/null | grep -v '^*'`
    if [ ! -z "$output" ]; then
        echo "============================================================="
        echo "Pylint notices on $file"
        echo "-------------------------------------------------------------"
        echo "$output"
    fi
done

