#!/usr/bin/python2.4
# Stop lint warning about relative import:
# pylint: disable-msg=W0403
"""Change the component of a package.

This tool allows you to change the component of a package.  Changes won't
take affect till the next publishing run.
"""

import _pythonpath

from canonical.config import config
from lp.soyuz.scripts.changeoverride import ChangeOverride

if __name__ == '__main__':
    script = ChangeOverride(
        'change-override', dbuser=config.archivepublisher.dbuser)
    script.lock_and_run()
