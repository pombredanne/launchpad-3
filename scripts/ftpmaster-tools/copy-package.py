#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403
"""Copy publications across suites."""

import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.packagecopier import PackageCopier


if __name__ == '__main__':
    script = PackageCopier(
        'copy-package', dbuser=config.archivepublisher.dbuser)
    script.lock_and_run()

