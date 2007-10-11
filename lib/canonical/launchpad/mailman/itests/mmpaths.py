# Copyright 2007 Canonical Ltd.  All rights reserved.

"""This is a bin/withlist script for Mailman.

It prints various paths to stdout.
"""

import os
from Mailman import mm_cfg

def backup(mlist):
    print os.path.join(mm_cfg.VAR_PREFIX, 'backups',
                       mlist.internal_name() + '.tgz')
