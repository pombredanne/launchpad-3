#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

import _pythonpath

from canonical.config import config

from lp.code.scripts.revisionkarma import RevisionKarmaAllocator


if __name__ == '__main__':
    script = RevisionKarmaAllocator('allocate-revision-karma',
        dbuser=config.revisionkarma.dbuser)
    script.lock_and_run(implicit_begin=True)
