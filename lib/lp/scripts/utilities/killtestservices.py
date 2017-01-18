# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Kill all the test services that may persist between test runs."""

from __future__ import print_function

import sys

from lp.services.config import config
from lp.services.librarianserver.testing.server import LibrarianServerFixture
from lp.services.osutils import kill_by_pidfile
from lp.testing.layers import MemcachedLayer


def main():
    args = sys.argv[1:]
    if '-h' in args or '--help' in args:
        print(__doc__)
        return 0
    # Tell lp.services.config to use the testrunner config instance, so that
    # we don't kill the real services.
    config.setInstance('testrunner')
    config.generate_overrides()
    print("Killing Memcached....", end="")
    kill_by_pidfile(MemcachedLayer.getPidFile())
    print("done.")
    print("Killing Librarian....", end="")
    librarian_fixture = LibrarianServerFixture(None)
    kill_by_pidfile(librarian_fixture.pidfile)
    librarian_fixture.tearDownRoot()
    print("done.")
    return 0
