#!/usr/bin/python
# Copyright 2005 Canonical Ltd. All rights reserved.

import sys

from canonical.lp import initZopeless
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.scripts.po_export_queue import process_queue

def main(args):
    lockfile = LockFile('/var/lock/rosetta-export-queue.lock')

    try:
        lockfile.acquire()
    except OSError:
        return 0

    try:
        ztm = initZopeless()
        execute_zcml_for_scripts()
        process_queue()
        ztm.commit()
    finally:
        lockfile.release()

if __name__ == '__main__':
    sys.exit(main(sys.argv))

