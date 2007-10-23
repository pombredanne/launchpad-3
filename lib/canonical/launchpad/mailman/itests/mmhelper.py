# Copyright 2007 Canonical Ltd.  All rights reserved.

"""This is a bin/withlist script for Mailman.

It helps with the integration testing.
"""

import os
from Mailman import mm_cfg

def backup(mlist):
    """Print the path for a list's backup file."""
    print os.path.join(mm_cfg.VAR_PREFIX, 'backups',
                       mlist.internal_name() + '.tgz')


def welcome(mlist):
    """Print the list's welcome message."""
    print mlist.welcome_msg
