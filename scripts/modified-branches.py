#!/usr/bin/python2.4
# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

"""Script to print disk locations of modified branches.

This script will be used by IS for the rsync backups.
"""

import _pythonpath

from lp.codehosting.scripts.modifiedbranches import (
    ModifiedBranchesScript)


if __name__ == '__main__':
    script = ModifiedBranchesScript('modified-branches')
    script.run()
