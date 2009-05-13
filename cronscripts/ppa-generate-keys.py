#!/usr/bin/python2.4

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

"""A cron script that generate missing PPA signing keys."""

__metaclass__ = type

import _pythonpath

from canonical.config import config
from lp.soyuz.scripts.ppakeygenerator import PPAKeyGenerator


if __name__ == '__main__':
    script = PPAKeyGenerator(
        "ppa-generate-keys", config.archivepublisher.dbuser)
    script.lock_and_run()

