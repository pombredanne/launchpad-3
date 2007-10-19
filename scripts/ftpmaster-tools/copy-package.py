#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Copy publications across suites."""

import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.ftpmaster import PackageCopier


if __name__ == '__main__':
    script = PackageCopier(
        'copy-package', dbuser=config.archivepublisher.dbuser)
    script.lock_and_run()

