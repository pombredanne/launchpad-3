#!/bin/sh
#
# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
#
# Lists pages that are unregistered or missing titles

LPDIR=lib/canonical/launchpad
REGISTRY="lib/canonical/launchpad/zcml/*.zcml lib/canonical/*.zcml
          lib/canonical/launchpad/*.zcml *.zcml
          lib/zope/app/exception/browser/configure.zcml
          lib/zope/app/debugskin/configure.zcml
          lib/canonical/launchpad/webapp/*.zcml
          lib/canonical/launchpad/browser/*.py"

MASTER_MACRO='metal:use-macro="context/@@main_template/master"'

for f in $LPDIR/templates/*.pt; do
    base=`basename $f`
    clean=`echo $base | cut -d. -f1 | tr - _`
    if echo $base | grep -qa ^template-; then
        # Ignore template-* prefixed files.
        continue
    fi
    if grep -qs $base $REGISTRY; then
        if grep -q $MASTER_MACRO $f; then
            # If this is a page that should require a title
            grep -qs $clean $LPDIR/pagetitles.py || \
                echo "** Missing Title: $base"
        fi
    else
        if grep $clean $LPDIR/pagetitles.py | grep -vqs ^\# ; then
            # Why is the page not registered but has a title listed?
            echo Not registered, but has title: $base
        else
            echo Not registered: $base
        fi
    fi
done

