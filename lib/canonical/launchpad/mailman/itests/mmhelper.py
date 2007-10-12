# Copyright 2007 Canonical Ltd.  All rights reserved.

"""This is a bin/withlist script for Mailman.

It helps with the integration testing.
"""

import os
from Mailman import mm_cfg

def backup(mlist):
    print os.path.join(mm_cfg.VAR_PREFIX, 'backups',
                       mlist.internal_name() + '.tgz')


def welcome(mlist):
    print mlist.welcome_msg
