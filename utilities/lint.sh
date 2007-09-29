#!/bin/bash
#
# Runs pyflakes and pylint on files changed in tree
#
# 2005-07-14 creation (kiko)
# 2005-07-15 added verbose mode, and fixed up warnings
# 2005-07-20 added detection of conflict markers
# 2005-07-21 nicer handling of verbose mode, tweaking of warnings
# 2005-09-23 tweak more warnings on a dir-specific basis

if [ -z "$1" ]; then
    rev=`bzr info | sed '/parent branch:/!d; s, .*file://,-r ancestor:,'`
    files=`bzr st $rev | sed '/^ /!d; /[a-z] /d; /@/d'`
else
    # Add newlines so grep filters out pyfiles correctly later
    files=`echo $* | tr " " "\n"`
fi

echo "= Launchpad lint ="
echo ""

if [ -z "$files" ]; then
    echo "No changed files detected."
    exit
fi

for file in $files; do
    # NB. Odd syntax on following line to stop lint.sh detecting conflict
    # markers in itself.
    conflicts=""
    if grep -q -e '<<<''<<<<' -e '>>>''>>>>' $file; then
        conflicts="$conflicts $file"
    fi
    if [ $conflicts ]; then
        echo "== Conflicts =="
        echo ""
        for conflict in $conflicts; do
            echo "$file"
        done
        echo ""
        echo ""
    fi
done

pyfiles=`echo "$files" | grep '.py$'`
if [ -z "$pyfiles" ]; then
    exit
fi

if which pyflakes >/dev/null; then
    sed_deletes="/detect undefined names/d; /'_pythonpath' .* unused/d;"
    output=`pyflakes $pyfiles | sed "$sed_deletes"`
    if [ ! -z "$output" ]; then
        echo "== Pyflakes notices =="
        echo ""
        echo "$output"
        echo ""
        echo ""
    fi
fi

PYLINT=`which pylint`
if [ -z $PYLINT ]; then
    exit
fi

echo "== Pylint notices =="

# Note that you can disable specific tests by placing pylint instruction
# in a comment:
#   # pylint: disable-msg=W0401,W0612

pylint="python2.4 -Wi::DeprecationWarning $PYLINT"
rcfile="--rcfile=utilities/lp.pylintrc"
sed_deletes="/^*/d; /Unused import \(action\|_python\)/d; "
sed_deletes="$sed_deletes /_action: Undefined variable/d; "
sed_deletes="$sed_deletes /_getByName: Instance/d; "
sed_deletes="$sed_deletes /Redefining built-in .id/d;"

for file in $pyfiles; do
    opts=""
    if echo $file | grep -qs "/__init__.py"; then
        # :W0401: *Wildcard import %s*
        opts='--disable-msg=W0401'
    elif echo $file | grep -qs "launchpad/interfaces/"; then
        # :E0211: *Method has no argument*
        # :E0213: *Method should have "self" as first argument*
        opts='--disable-msg=E0211,E0213'
    elif echo $file | grep -qs "launchpad/database/"; then
        # sqlobject imports cause:
        # :E0611: *No name %r in module %r*
        # :W0212: *Access to a protected member %s of a client class*
        # :W0622: *Redefining built-in %r*
        opts='--disable-msg=E0611,W0212,W0622'
    elif echo $file | grep -qs "cronscripts/"; then
        # :W0403: *Relative import %r*
        opts='--disable-msg=W0403'
    elif echo $file | grep -qs "scripts/"; then
        # :W0702: *No exception's type specified*
        # :W0703: *Catch "Exception"*
        opts='--disable-msg=W0702,W0703'
    fi

    output=`$pylint $rcfile $opts $file | sed "$sed_deletes"`

    if [ ! -z "$output" ]; then
        echo ""
        echo ""
        echo "=== Pylint notices on $file ==="
        echo "$output"
    fi
done

