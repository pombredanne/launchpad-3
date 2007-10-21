#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Launchpad version of ftpmaster-tools/remove-package.py."""


import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.ftpmaster import PackageRemover


if __name__ == '__main__':
    script = PackageRemover(
        'lp-remove-package', dbuser=config.archivepublisher.dbuser)
    script.lock_and_run()

