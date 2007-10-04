#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Import Debian bugs into Launchpad.

New bugs will be filed againts the Debian source package in Launchpad,
with the real Debian bug linked as a bug watch.
"""

import _pythonpath

from canonical.launchpad.scripts.importdebianbugs import DebianBugImportScript


if __name__ == '__main__':
    script = DebianBugImportScript(
        'canonical.launchpad.scripts.importdebianbugs')
    script.run()
