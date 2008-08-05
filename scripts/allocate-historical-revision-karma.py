#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Allocates karma for the revisions that we know the author of.

This script is a one shot update script for the 2.1.8 rollout.
"""

import _pythonpath

from storm.zope.interfaces import IZStorm
from zope.component import getUtility

from canonical.launchpad.database.revision import RevisionAuthor
from canonical.launchpad.scripts import execute_zcml_for_scripts


def main():
    execute_zcml_for_scripts()
    store = getUtility(IZStorm).get('main')
    authors = store.find(RevisionAuthor)
    for author in authors:
        author._claimRevisionKarma()
    print "Done."


if __name__ == "__main__":
    main()
