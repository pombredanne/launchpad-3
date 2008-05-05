#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unembargo a package from the security private PPA."""

import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.ftpmaster import UnembargoSecurityPackage


if __name__ == '__main__':
    script = UnembargoSecurityPackage(
        'unembargo-package', dbuser=config.archivepublisher.dbuser)
    script.lock_and_run()

