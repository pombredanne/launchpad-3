#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403
"""Copy publications across suites."""

import _pythonpath

from canonical.config import config
from lp.soyuz.scripts.packagecopier import PackageCopier


if __name__ == '__main__':
    script = PackageCopier(
        'copy-package', dbuser=config.archivepublisher.dbuser)
    script.lock_and_run()

