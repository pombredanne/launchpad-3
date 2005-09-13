#!/bin/sh
#
# Lists pages that are unregistered or missing titles
#

LPDIR=lib/canonical/launchpad
REGISTRY="lib/canonical/launchpad/zcml/*.zcml lib/canonical/*.zcml
          lib/canonical/lp/*.zcml *.zcml lib/canonical/launchpad/browser/*.py"

MASTER_MACRO='metal:use-macro="context/@@main_template/master"'

for f in $LPDIR/templates/*.pt; do 
    base=`basename $f`
    clean=`echo $base | cut -d. -f1 | tr - _`
    if grep -qs $base $REGISTRY; then
        if grep -q $MASTER_MACRO $f; then
            grep -qs $clean $LPDIR/pagetitles.py || \
                echo "** Missing Title: $base"
        fi
    else
        if grep -qs $clean $LPDIR/pagetitles.py; then
            echo Not registered, but has title: $base
        else
            echo Not registered: $base
        fi
    fi
done

