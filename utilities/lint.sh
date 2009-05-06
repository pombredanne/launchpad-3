#!/bin/bash
#
# Runs xmlint, pyflakes and pylint on files changed from parent branch.
# Use '-v' to run pylint under stricter conditions with additional messages.

utilitiesdir=`dirname $0`
[ -z "$utilitiesdir" ] && utilitiesdir=.

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

bzr() {
    # For pylint to operate properly, PYTHONPATH must point to the ./lib
    # directory in the launchpad tree. This directory includes a bzrlib. When
    # this script calls bzr, we want it to use the system bzrlib, not the one
    # in the launchpad tree.
    PYTHONPATH='' `which bzr` "$@"
}

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
    # No command line argument provided, use the default logic.
    bzr diff > /dev/null
    diff_status=$?
    if [ $diff_status -eq 0 ] ; then
        # No uncommitted changes in the tree.
        bzr status | grep "^Current thread:" > /dev/null
        if [ $? -eq 0 ] ; then
            # This is a loom, lint changes relative to the lower thread.
            rev_option="-r thread:"
        else
            # Lint changes relative to the parent.
            rev=`bzr info | sed '/parent branch:/!d; s/ *parent branch: /ancestor:/'`
            rev_option="-r $rev"
        fi
    elif [ $diff_status -eq 1 ] ; then
        # Uncommitted changes in the tree, lint those changes.
        rev_option=""
    else
        # bzr diff failed
        exit 1
    fi
    files=`bzr st --short $rev_option | sed '/^.[MN]/!d; s/.* //'`
else
    # Add newlines so grep filters out pyfiles correctly later.
    files=`echo $* | tr " " "\n"`
fi

# Are there patches to the schema or changes to current.sql?
database_changes=$(echo $files | sed '/database.*\(patch-\|current\)/!d')

echo "= Launchpad lint ="
echo ""
echo "Checking for conflicts. and issues in doctests and templates."
echo "Running jslint, xmllint, pyflakes, and pylint."

echo "$rules"

if [ -z "$files" ]; then
    echo "No changed files detected."
    exit 0
else
    echo
    echo "Linting changed files:"
    for file in $files; do
        echo "  $file"
    done
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


sample_dir="database/sampledata"
current_sql="${sample_dir}/current.sql"
current_dev_sql="${sample_dir}/current-dev.sql"
lintdata_sql="${sample_dir}/lintdata.sql"
lintdata_dev_sql="${sample_dir}/lintdata-dev.sql"

if [ -n "${database_changes}" ]; then
    make -C database/schema lintdata > /dev/null
    sql_diff=$(diff -q "${current_sql}" "${lintdata_sql}")
    if [ -z "$sql_diff" ]; then
        rm $lintdata_sql
    fi
    sql_dev_diff=$(diff -q "${current_dev_sql}" "${lintdata_dev_sql}")
    if [ -z "$sql_dev_diff" ]; then
        rm $lintdata_dev_sql
    fi
else
    sql_diff=""
    sql_dev_diff=""
fi

karma_bombs=`sed '/INTO karma /!d; /2000-/d; /2001-/d' $current_sql`

echo_sampledata_changes () {
    echo "    $2 differs from $1."
    echo "    Patches to the schema, or manual edits to $1"
    echo "    do not match the dump of the $3 database."
    echo "    If $2 is correct, copy it to"
    echo "    $1."
    echo "    Otherwise update $1 and run:"
    echo "        make schema"
    echo "        make newsampledata"
    echo "        cd ${sample_dir}"
    echo "        cp $4 $1"
    echo "    Run make schema again to update the test/dev database."
}
    
if [ -n "$sql_diff" -o -n "$sql_dev_diff" -o -n "$karma_bombs" ]; then
    echo ""
    echo ""
    echo "== Schema =="
    echo ""
fi

# 
if [ -n "$sql_diff" -o -n "$karma_bombs" ]; then
    echo "$current_sql"
fi
if [ -n "$sql_diff" ]; then
    echo_sampledata_changes \
        "$current_sql" "$lintdata_sql" "launchpad_ftest_template"\
       	"newsampledata.sql"
fi
if [ -n "$karma_bombs" ]; then
    echo "    Karma time bombs were added to sampledata."
    echo "        The Karma table has dates after 2002-01-01; either revise"
    echo "        them or remove rows if they are unneeded."
fi

if [ -n "$sql_dev_diff" ]; then
    echo ""
    echo "$current_sql"
    echo_sampledata_changes \
        "$current_dev_sql" "$lintdata_dev_sql" "launchpad_dev_template"\
       	"newsampledata-dev.sql"
fi

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
    xmllint_notices=`xmllint --noout $xmlfiles 2>&1 |
        sed -e '/Entity/,+2d; {/StartTag/N; /define-slot="doctype"/,+1d}'`
fi
if [ ! -z "$xmllint_notices" ]; then
    echo ""
    echo ""
    echo "== XmlLint notices =="
    group_lines_by_file "$xmllint_notices"
fi


templatefiles=`echo "$files" | grep -E '(pt)$'`
template_notices=""
if [ ! -z "$templatefiles" ]; then
    obsolete='"(portlets_one|portlets_two|pageheading|help)"'
    template_notices=`grep -HE "fill-slot=$obsolete" $templatefiles`
fi
if [ ! -z "$template_notices" ]; then
    echo ""
    echo ""
    echo "== Template notices =="
    echo ""
    echo "There are obsolete slots in these templates."
    group_lines_by_file "$template_notices"
fi


doctestfiles=`echo "$files" | grep -E '/(doc|pagetests|f?tests)/.*txt$'`
if [ ! -z "$doctestfiles" ]; then
    pyflakes_doctest_notices=`$utilitiesdir/pyflakes-doctest.py $doctestfiles`
    if [ ! -z "$pyflakes_doctest_notices" ]; then
        echo ""
        echo ""
        echo "== Pyflakes Doctest notices =="
        group_lines_by_file "$pyflakes_doctest_notices"
    fi
fi


jsfiles=`echo "$files" | grep -E 'js$'`
if [ ! -z "$jsfiles" ]; then
    jslint_notices=`$utilitiesdir/../sourcecode/lazr-js/tools/jslint.py 2>&1`
    if [ ! -z "$jslint_notices" ]; then
        echo ""
        echo ""
        echo "== JSLint notices =="
        echo "$jslint_notices"
    fi
fi


pyfiles=`echo "$files" | grep '.py$'`
if [ -z "$pyfiles" ]; then
    exit 0
fi


sed_deletes="/detect undefined names/d; /'_pythonpath' .* unused/d; "
sed_deletes="$sed_deletes /BYUSER/d; "
sed_deletes="$sed_deletes /ENABLED/d; "
pyflakes_notices=`pyflakes $pyfiles 2>&1 | sed "$sed_deletes"`
if [ ! -z "$pyflakes_notices" ]; then
    echo ""
    echo ""
    echo "== Pyflakes notices =="
    group_lines_by_file "$pyflakes_notices"
fi

extra_path="/usr/share/pyshared:/usr/share/pycentral/pylint/site-packages"
export PYTHONPATH="$extra_path:lib:$PYTHONPATH"
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
sed_deletes="$sed_deletes /Undefined variable.*valida/d; "
sed_deletes="$sed_deletes s,^/.*lib/canonical/,lib/canonical,; "
sed_deletes="$sed_deletes /ENABLED/d; "
sed_deletes="$sed_deletes /BYUSER/d; "

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

