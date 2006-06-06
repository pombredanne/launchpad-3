#!/usr/bin/env python
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Creates the Bug Watch Updater person."""

import _pythonpath

from zope.component import getUtility

from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.lp import initZopeless

def create_bug_watch_updater():
    ztm = initZopeless()
    execute_zcml_for_scripts()
    bug_watch_updater = getUtility(IPersonSet).createPersonAndEmail(
        'bugwatch@bugs.launchpad.net', name='bug-watch-updater',
        displayname='Bug Watch Updater', hide_email_addresses=True)
    ztm.commit()
    print "Successfully created the Bug Watch Updater person."

if __name__ == '__main__':
    create_bug_watch_updater()
