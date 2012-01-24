#!/usr/bin/python -S
#
# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# Stop lint warning about relative import:
# pylint: disable-msg=W0403

"""Tool for adding, removing and replacing buildd chroots."""

import _pythonpath

from lp.soyuz.scripts.chrootmanager import ManageChrootScript


if __name__ == '__main__':
    script = ManageChrootScript('manage-chroot', dbuser="fiera")
    script.lock_and_run()
