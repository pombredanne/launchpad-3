# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This is a bin/withlist script for testing that Mailman can import and access
# the common libmailman package.  It works by side effect; on success it exits
# with a return code of 99, which would be difficult to false positive, but
# very easy to check by the parent process.  See test-lpmm.txt for details.
#
# This script must be called like so:
#
# bin/withlist -r lp.services.mailman.tests.withlist_2.can_import

import sys


def can_import(mlist):
    try:
        import lp.services.mailman
    except ImportError:
        sys.exit(1)
    else:
        sys.exit(99)
