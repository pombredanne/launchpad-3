#!/bin/bash
#
# Runs xmlint, pyflakes and pylint on files changed from parent branch.
# Use '-v' to run pylint under stricter conditions with additional messages.


# Fail if any of the required tools are not installed.
if ! which pylint >/dev/null; then
    echo "Error: pylint is not installed."
    echo "    Install the pylint package."
    exit 1
elif ! which xmllint >/dev/null; then
    echo "Error: xmlllint is not installed."
    echo "    Install the libxml2-utils package."
    exit 1
elif ! which pyflakes >/dev/null; then
    echo "Error: pyflakes is not installed."
    echo "    Install the pyflakes package."
    exit 1
fi


rules="Using normal rules."
rcfile="--rcfile=utilities/lp.pylintrc"
if [ "$1" == "-v" ]; then
    shift
    rules="Using verbose rules."
    rcfile="--rcfile=utilities/lp-verbose.pylintrc"
elif [ "$1" == "-vv" ]; then
    shift
    rules="Using very verbose rules."
    rcfile="--rcfile=utilities/lp-very-verbose.pylintrc"
fi


if [ -z "$1" ]; then
    rev=`bzr info | sed '/parent branch:/!d; s/ *parent branch: /ancestor:/'`
    files=`bzr st --short -r $rev | sed '/^.[MN]/!d; s/.* //'`
else
    # Add newlines so grep filters out pyfiles correctly later.
    files=`echo $* | tr " " "\n"`
fi


echo "= Launchpad lint ="
echo ""
echo "Checking for conflicts. Running xmllint, pyflakes, and pylint."
echo "$rules"

if [ -z "$files" ]; then
    echo "No changed files detected."
    exit 0
fi


group_lines_by_file() {
    # Format file:line:message output as lines grouped by file.
    file_name=""
    echo "$1" | sed 's,\(^[^ :<>=+]*:\),~~\1\n,' | while read line; do
        current=`echo $line | sed '/^~~/!d; s/^~~\(.*\):$/\1/;'`
        if [ -z "$current" ]; then
            echo "    $line"
        elif [ "$file_name" != "$current" ]; then
            file_name="$current"
            echo ""
            echo "$file_name"
        fi
    done
}


conflicts=""
for file in $files; do
    # NB. Odd syntax on following line to stop lint.sh detecting conflict
    # markers in itself.
    if [ ! -f "$file" ]; then
        continue
    fi
    if grep -q -e '<<<''<<<<' -e '>>>''>>>>' $file; then
        conflicts="$conflicts $file"
    fi
done

if [ "$conflicts" ]; then
    echo ""
    echo ""
    echo "== Conflicts =="
    echo ""
    for conflict in $conflicts; do
        echo "$conflict"
    done
fi


xmlfiles=`echo "$files" | grep -E '(xml|zcml|pt)$'`
xmllint_notices=""
if [ ! -z "$xmlfiles" ]; then
    xmllint_notices=`xmllint --noout $xmlfiles 2>&1 | sed -e '/Entity/,+2d'`
fi
if [ ! -z "$xmllint_notices" ]; then
    echo ""
    echo ""
    echo "== XmlLint notices =="
    group_lines_by_file "$xmllint_notices"
fi


pyfiles=`echo "$files" | grep '.py$'`
if [ -z "$pyfiles" ]; then
    exit 0
fi


sed_deletes="/detect undefined names/d; /'_pythonpath' .* unused/d;"
pyflakes_notices=`pyflakes $pyfiles 2>&1 | sed "$sed_deletes"`
if [ ! -z "$pyflakes_notices" ]; then
    echo ""
    echo ""
    echo "== Pyflakes notices =="
    group_lines_by_file "$pyflakes_notices"
fi


export PYTHONPATH="/usr/share/pycentral/pylint/site-packages:$PYTHONPATH"
pylint="python2.4 -Wi::DeprecationWarning `which pylint`"

# XXX sinzui 2007-10-18 bug=154140:
# Pylint should really do a better job of not reporting false positives.
sed_deletes="/^*/d; /Unused import \(action\|_python\)/d; "
sed_deletes="$sed_deletes /Unable to import .*sql\(object\|base\)/d; "
sed_deletes="$sed_deletes /_action.* Undefined variable/d; "
sed_deletes="$sed_deletes /_getByName.* Instance/d; "
sed_deletes="$sed_deletes /Redefining built-in .id/d; "
sed_deletes="$sed_deletes /Redefining built-in 'filter'/d; "
sed_deletes="$sed_deletes /<lambda>] Using variable .* before assignment/d; "
sed_deletes="$sed_deletes /Comma not followed by a space/{N;N};/,[])}]/d; "
sed_deletes="$sed_deletes s,^/.*lib/canonical/,lib/canonical,; "

# Note that you can disable specific tests by placing pylint
# instruction in a comment:
# # pylint: disable-msg=W0401,W0612,W0403
pylint_notices=`$pylint $rcfile $pyfiles | sed "$sed_deletes"`

if [ ! -z "$pylint_notices" ]; then
    echo ""
    echo ""
    echo "== Pylint notices =="
    group_lines_by_file "$pylint_notices"
fi

