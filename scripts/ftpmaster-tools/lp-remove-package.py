#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403
"""Launchpad version of ftpmaster-tools/remove-package.py."""


import _pythonpath

from canonical.config import config
from lp.soyuz.scripts.ftpmaster import PackageRemover


if __name__ == '__main__':
    script = PackageRemover(
        'lp-remove-package', dbuser=config.archivepublisher.dbuser)
    script.lock_and_run()

