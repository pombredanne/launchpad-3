#!/bin/bash
#
# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
#
# Update version-info.py -- but only if the revision number has
# changed
#

newfile=version-info-${RANDOM}.py

if [ -d .git ]; then
    if ! which git > /dev/null || ! test -x $(which git); then
        echo "No working 'git' executable found" >&2
        exit 1
    fi

    branch_nick="$(git rev-parse --abbrev-ref HEAD | sed "s/'/\\\\'/g")"
    revision_id="$(git rev-parse HEAD)"
    cat > $newfile <<EOF
#! /usr/bin/env python

from __future__ import print_function

version_info = {
    'branch_nick': u'$branch_nick',
    'revision_id': u'$revision_id',
    }

if __name__ == '__main__':
    print('revision id: %(revision_id)s' % version_info)
EOF
elif [ -d .bzr ]; then
    if ! which bzr > /dev/null || ! test -x $(which bzr); then
        echo "No working 'bzr' executable found" >&2
        exit 1
    fi

    bzr version-info --format=python > $newfile 2>/dev/null
else
    echo "Not in a Git or Bazaar working tree" >&2
    exit 1
fi

revision_id=$(python $newfile | sed -n 's/^revision id: //p')
if ! [ -f version-info.py ]; then
    echo "Creating version-info.py at revision $revision_id"
    mv ${newfile} version-info.py
else
    # Here we compare the actual output instead of the contents of the
    # file because bzr includes a build-date that is actually updated
    # every time you run bzr version-info.
    newcontents=$(python $newfile)
    oldcontents=$(python version-info.py)
    if [ "$newcontents" != "$oldcontents" ]; then
        echo "Updating version-info.py to revision $revision_id"
        mv ${newfile} version-info.py
    else
        echo "Skipping version-info.py update; already at revision $revision_id"
        rm ${newfile}
    fi
fi
