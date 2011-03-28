#!/usr/bin/python -S
#
# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Master FTP distro publishing script."""

import _pythonpath

from canonical.config import config
from lp.soyuz.scripts.publish_ftpmaster import PublishFTPMaster


if __name__ == '__main__':
    script = PublishFTPMaster(
        "publish-ftpmaster", dbuser=config.archivepublisher.dbuser)
    script.lock_and_run()
