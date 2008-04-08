#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

# Stop lint warning about relative import:
# pylint: disable-msg=W0403

"""Tool for adding, removing and replacing buildd chroots."""

import _pythonpath

from canonical.launchpad.scripts.ftpmaster import ManageChrootScript


if __name__ == '__main__':
    script = ManageChrootScript('mangage-chroot', dbuser="fiera")
    script.lock_and_run()

