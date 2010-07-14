#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Copy publications across suites."""

import _pythonpath

from canonical.config import config
from lp.soyuz.scripts.packagecopier import PackageCopier


if __name__ == '__main__':
    script = PackageCopier(
        'copy-package', dbuser=config.archivepublisher.dbuser)
    script.lock_and_run()

