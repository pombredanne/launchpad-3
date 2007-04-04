# Copyright 2007 Canonical Ltd.  All rights reserved.

# This is a bin/withlist script for testing that Mailman can import and access
# Launchpad's modules.  It works by side effect; on success it exits with a
# return code of 99, which would be difficult to false positive, but very easy
# to check by the parent process.  See test-monkeypatch.txt for details.
#
# This script must be called like so:
#
# bin/withlist -r canonical.mailman.tests.launchpad.launchpad mailman
#
# where the final argument is the name of the site list, which must exist.

import sys
from Mailman.mm_cfg import MAILMAN_SITE_LIST


def launchpad(mlist):
    # The very fact that this function got called proves that Launchpad's
    # package namespace is accessible.  Do one more check for sanity.
    if mlist.internal_name() == MAILMAN_SITE_LIST:
        sys.exit(99)
    sys.exit(1)
