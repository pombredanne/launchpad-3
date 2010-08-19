#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Launchpad version of ftpmaster-tools/remove-package.py."""


import _pythonpath

from canonical.config import config
from lp.soyuz.scripts.ftpmaster import PackageRemover


if __name__ == '__main__':
    script = PackageRemover(
        'lp-remove-package', dbuser=config.archivepublisher.dbuser)
    script.lock_and_run()

