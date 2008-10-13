#!/bin/bash
#
# Update bzr-version-info.py -- but only if the revision number has
# changed
#

if ! which bzr > /dev/null || !  test -x $(which bzr); then
    echo "No working 'bzr' executable found"
    exit 1
fi

newfile=bzr_version_info_${RANDOM}.py
PYTHONPATH= bzr version-info --format=python > $newfile 2>/dev/null;
# There's a leading space here that I don't care to trim.. 
revno=$(python $newfile | grep revision: | cut -d: -f2)
if ! [ -f bzr_version_info.py ]; then
    echo "Creating bzr_version_info.py at revno$revno"
    mv ${newfile} bzr_version_info.py
else
    # Here we compare the actual output instead of the contents of the
    # file because bzr includes a build-date that is actually updated
    # every time you run bzr version-info.
    newcontents=$(python $newfile)
    oldcontents=$(python bzr_version_info.py)
    if [ "$newcontents" != "$oldcontents" ]; then
        echo "Updating bzr_version_info.py to revno$revno"
        mv ${newfile} bzr_version_info.py
    else
        echo "Skipping bzr_version_info.py update; already at revno$revno"
        rm ${newfile}
    fi
fi
