#!/bin/bash
#
# Runs pyflakes and pylint on files changed in tree
#
# 2005-07-14 creation (kiko)
# 2005-07-15 added verbose mode, and fixed up warnings
# 2005-07-20 added detection of conflict markers
# 2005-07-21 nicer handling of verbose mode, tweaking of warnings
# 2005-09-23 tweak more warnings on a dir-specific basis

PYLINT=pylint.python2.4

# Note that you can disable certain tests by placing in a comment, at
# the top of the file, a disable-msg command:
#   # pylint: disable-msg=W0401, E0202

# XXX kiko 2005-07-21: Stuff I'd like to add:
# E0201 (Access to undefined member) fails for classmethods and
#       SQLObject's id and _table attributes
# W0613 (Unused argument) triggers often for hook methods, and for tuple
#       unpacking where you really want it to make the code clearer
PYLINTOFF="W0232,C0103,W0103,C0101,W0142,R0903,W0201,W0212"

if [ "$1" == "-v" ]; then
    shift
else
    # Silent mode; disabled:
    # W0131 (Missing docstring) we don't have enough of them :-(
    # R0912 (Too many branches)
    # R0913 (Too many arguments)
    # R0914 (Too many local variables)
    # R0915 (Too many statements)
    # W0221 (Arguments number differs from overriden method)
    PYLINTOFF="$PYLINTOFF,W0131,R0912,R0913,R0914,R0915,W0221"
    # W0511 (XXX and TODO listings)
    # W0302 (Too many lines in module)
    # R0902 (Too many instance attributes)
    # R0904 (Too many public methods)
    # W0622 (Redefining built-in)
    PYLINTOFF="$PYLINTOFF,W0511,W0302,R0902,R0904,W0622"
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

# Disables:
# W0702 (No exception's type specified)
# W0703 (Catch "Exception")
PYLINTOPTS_SCRIPT="$PYLINTOPTS,W0702,W0703"

# Disables:
# W0613 (Unused argument)
# R0911 (Too many return statements)
PYLINTOPTS_TRAVERSERS="$PYLINTOPTS,W0613,R0911"

if grep -r verifyObject lib/canonical/launchpad/doc/* | \
   grep zope.interface; then
   echo "Fix these to use canonical.launchpad.webapp.testing please."
fi

if [ -z "$1" ]; then
    files=`bzr added ; bzr modified`
else
    # Add newlines so grep filters out pyfiles correctly later
    files=`echo $* | tr " " "\n"`
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
    output=`pyflakes $pyfiles \
            | grep -v "unable to detect undefined names"`
    if [ ! -z "$output" ]; then
        echo "============================================================="
        echo "Pyflakes notices"
        echo "-------------------------------------------------------------"
        echo "$output"
    fi
fi

for file in $pyfiles; do
    OPTS=$PYLINTOPTS
    if echo $file | grep -qs "scripts/"; then
        OPTS=$PYLINTOPTS_SCRIPT
    fi
    if echo $file | grep -qs "launchpad/interfaces/"; then
        OPTS=$PYLINTOPTS_INT
    fi
    if echo $file | grep -qs "launchpad/browser/traversers.py"; then
        OPTS=$PYLINTOPTS_TRAVERSERS
    fi
    if echo $file | grep -qs "/__init__.py"; then
        # Disable "Wildcard Import" warnings for __init__ files; doing
        # this for pyflakes is unfortunately not as simple
        OPTS=$PYLINTOPTS,W0401
    fi
    if echo $file | grep -qs "launchpad/browser/"; then
        output=`$PYLINT $file $OPTS 2>/dev/null \
                | grep -v "Access to undefined member 'request'" \
                | grep -v "Access to undefined member 'context'" \
                | grep -v "Access to undefined member '.*_widget'" \
                | grep -v '^*'`
    elif echo $file | grep -qs "launchpad/pagetitles.py"; then
        output=`$PYLINT $file $OPTS 2>/dev/null \
                | grep -v "Unused argument 'view'" \
                | grep -v "Unused argument 'context'" \
                | grep -v '^*'`
# XXX Stuart Bishop 2005-10-27: wtf is this?
#     elif echo $file | grep -qs "launchpad/pagetitles.py"; then
#         output=`$PYLINT $file $OPTS 2>/dev/null \
#                 | grep -v "Unused argument 'furtherPath'" \
#                 | grep -v '^*'`
    elif echo $file | grep -qs "launchpad/database/"; then
        output=`$PYLINT $file $OPTS 2>/dev/null \
                | grep -v "Access to undefined member 'getByName'" \
                | grep -v '^*'`
    else
        output=`$PYLINT $file $OPTS 2>/dev/null | grep -v '^*'`
    fi
    if [ ! -z "$output" ]; then
        echo "============================================================="
        echo "Pylint notices on $file"
        echo "-------------------------------------------------------------"
        echo "$output"
    fi
done

