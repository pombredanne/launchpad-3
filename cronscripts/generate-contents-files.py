#!/usr/bin/python -S
#
# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Master distro publishing script."""

import _pythonpath

from canonical.config import config
from lp.archivepublisher.scripts.generate_contents_files import (
    GenerateContents,
    )


if __name__ == '__main__':
    script = GenerateContents(
        "generate-contents", dbuser=config.archivepublisher.dbuser)
    script.lock_and_run()
