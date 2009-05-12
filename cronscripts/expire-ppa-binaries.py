#!/usr/bin/python2.4

# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

# This script expires PPA binaries that are superseded or deleted, and
# are older than 30 days.  It's done with pure SQL rather than Python
# for speed reasons.

import _pythonpath

from canonical.config import config
from lp.soyuz.scripts.expire_ppa_binaries import PPABinaryExpirer


if __name__ == '__main__':
    script = PPABinaryExpirer(
        'expire-ppa-binaries', dbuser=config.binaryfile_expire.dbuser)
    script.lock_and_run()

