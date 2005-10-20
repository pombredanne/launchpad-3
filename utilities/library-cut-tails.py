#!/usr/bin/env python
# From https://chinstrap.ubuntu.com/~dsilvers/paste/fileTPA2Qu.html
import _pythonpath
# Usage: library-cut-tails

# Remove all revisions but the head of each branch in the revision library.

import pybaz

for archive in pybaz.iter_library_archives():
    for version in archive.iter_library_versions():
        revisions = list(version.iter_library_revisions())
        if len(revisions) < 2:
            continue
        tail = revisions[:-1]
        for revision in tail:
            print revision.fullname
            revision.library_remove()
