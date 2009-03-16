#!/usr/bin/python2.4

# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

# This script generates .htaccess files for private PPAs.

import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.generate_ppa_htaccess import (
    HtaccessTokenGenerator)


if __name__ == '__main__':
    script = HtaccessTokenGenerator(
        'generate-ppa-htaccess', dbuser=config.generateppahtaccess.dbuser)
    script.lock_and_run()

