# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os, os.path, shutil
from canonical.config import config
import canonical

from canonical.launchpad.daemons.tachandler import TacTestSetup

class LibrarianTestSetup(TacTestSetup):
    r"""Setup a librarian for use by functional tests
    
    >>> from urllib import urlopen
    >>> from canonical.config import config
    >>> host = config.librarian.download_host
    >>> port = config.librarian.download_port

    >>> LibrarianTestSetup().setUp()

    Make sure the server is running

    >>> urlopen('http://%s:%d/' % (host, port)).readline()
    'Copyright 2004-2005 Canonical Ltd.\n'

    >>> LibrarianTestSetup().tearDown()
    
    And again for luck

    >>> LibrarianTestSetup().setUp()
    >>> urlopen('http://%s:%d/' % (host, port)).readline()
    'Copyright 2004-2005 Canonical Ltd.\n'
    >>> LibrarianTestSetup().tearDown()

    """
    def setUpRoot(self):
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)
        os.makedirs(self.root, 0700)

    @property
    def root(self):
        return config.librarian.server.root

    @property
    def tacfile(self):
        return os.path.abspath(os.path.join(
            os.path.dirname(canonical.__file__), os.pardir, os.pardir,
            'daemons/librarian.tac'
            ))

    @property
    def pidfile(self):
        return os.path.join(self.root, 'librarian.pid')

    @property
    def logfile(self):
        return os.path.join(self.root, 'librarian.log')

# Kill any librarian left lying around from a previous interrupted run.
# Be paranoid since we trash the librarian directory as part of this.
assert config.default_section == 'testrunner', \
        'Imported dangerous test harness outside of the test runner'
LibrarianTestSetup().killTac()
