# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This is a bin/withlist script for testing that Mailman's site list exists.
# It works by side effect; on success it exits with a return code of 99, which
# would be difficult to false positive, but very easy to check by the parent
# process.  See test-monkeypatch.txt for details.
#
# This script must be called like so:
#
# bin/withlist -r \
#   lp.services.mailman.tests.withlist_1.test_site_list mailman
#
# where the final argument is the name of the site list, which must exist.

import sys

from Mailman.mm_cfg import MAILMAN_SITE_LIST


def test_site_list(mlist):
    # The very fact that this function got called proves that Launchpad's
    # package namespace is accessible.  Do one more check for sanity.
    if mlist.internal_name() == MAILMAN_SITE_LIST:
        sys.exit(99)
    sys.exit(1)
