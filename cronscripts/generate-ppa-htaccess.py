#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403

# This script generates .htaccess files for private PPAs.

import _pythonpath

from canonical.config import config
from lp.archivepublisher.scripts.generate_ppa_htaccess import (
    HtaccessTokenGenerator)


if __name__ == '__main__':
    script = HtaccessTokenGenerator(
        'generate-ppa-htaccess', dbuser=config.generateppahtaccess.dbuser)
    script.lock_and_run()

