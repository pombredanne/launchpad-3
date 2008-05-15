#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403
"""Process pending PackageDiffs.

Process a optionally limited set of pending PackageDiffs.

By default it process up to 50 diffs each run, which is enough to catch
up on 1 hour of uploads (in average).

However users might benefit of more frequently runs since the diff ETA
relative to the upload will be shorter.

The cycle time needs to be balance with the run time to produce the shortest
diff ETA and do not overlap much, for instance, if it has to diff monster
sources like openoffice or firefox.

Experiments with the cycle time will be safe enough and won't sink the host
performance, since the lock file is exclusive.
"""

__metaclass__ = type

import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.packagediff import ProcessPendingPackageDiffs

if __name__ == '__main__':
    script = ProcessPendingPackageDiffs(
        'process-pending-packagediffs', dbuser=config.uploader.dbuser)
    script.lock_or_quit()
    try:
        script.run()
    finally:
        script.unlock()
