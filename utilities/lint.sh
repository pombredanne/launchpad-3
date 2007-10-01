#!/bin/bash
#
# Runs xmlint, pyflakes and pylint on files changed from parent branch.
# Use -v to run pylint under stricter conditions with additional messages.

VERBOSITY=0
if [ "$1" == "-v" ]; then
    shift
    VERBOSITY=1
fi

if [ -z "$1" ]; then
    rev=`bzr info | sed '/parent branch:/!d; s, .*file://,-r ancestor:,'`
    files=`bzr st $rev | sed '/^ /!d; /[a-z] /d; /@/d'`
else
    # Add newlines so grep filters out pyfiles correctly later
    files=`echo $* | tr " " "\n"`
fi

echo "= Launchpad lint ="
echo ""
echo "Checking for conflicts. Running xmllint, pyflakes, and pylint."
echo ""

if [ -z "$files" ]; then
    echo "No changed files detected."
    exit
fi
echo ""

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

if which xmllint >/dev/null; then
    xmlfiles=`echo "$files" | grep -E '(xml|zcml|pt)$'`
    output=""
    if [ ! -z "$xmlfiles" ]; then
        output=`xmllint --noout $xmlfiles 2>&1 | sed -e '/Entity/,+2d'`
    fi
    if [ ! -z "$output" ]; then
        echo "== XmlLint notices =="
        echo ""
        echo "$output"
        echo ""
        echo ""
    fi
fi

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

pylint=`which pylint`
if [ -z $pylint ]; then
    exit
fi

echo "== Pylint notices =="
echo ""
if [ $VERBOSITY -eq 1 ]; then
    echo "Using verbose rules."
else
    echo "Using normal rules."
fi

pylint="python2.4 -Wi::DeprecationWarning $pylint"
rcfile="--rcfile=utilities/lp.pylintrc"
sed_deletes="/^*/d; /Unused import \(action\|_python\)/d; "
sed_deletes="$sed_deletes /_action: Undefined variable/d; "
sed_deletes="$sed_deletes /_getByName: Instance/d; "
sed_deletes="$sed_deletes /Redefining built-in .id/d;"
sed_deletes="$sed_deletes /Redefining built-in 'filter'/d;"

if [ $VERBOSITY -eq 1 ]; then
    rcfile="--rcfile=utilities/lp-verbose.pylintrc"
fi

for file in $pyfiles; do
    # Messages are disabled by directory or file name.
    # Note that you can disable specific tests by placing pylint
    # instruction in a comment:
    # # pylint: disable-msg=W0401,W0612

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
        echo "=== $file ==="
        echo ""
        echo "$output"
    fi
done

