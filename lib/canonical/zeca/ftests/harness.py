# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os, os.path, shutil
from canonical.config import config
import canonical

from canonical.launchpad.daemons.tachandler import TacTestSetup

keysdir = os.path.join(os.path.dirname(__file__), 'keys')

class ZecaTestSetup(TacTestSetup):
    r"""Setup a zeca for use by functional tests

    >>> from urllib import urlopen
    >>> host = config.gpghandler.host
    >>> port = config.gpghandler.port

    >>> ZecaTestSetup().setUp()

    Make sure the server is running

    >>> urlopen('http://%s:%d/' % (host, port)).readline()
    'Copyright 2004-2005 Canonical Ltd.\n'

    >>> ZecaTestSetup().tearDown()

    And again for luck

    >>> ZecaTestSetup().setUp()
    >>> urlopen('http://%s:%d/' % (host, port)).readline()
    'Copyright 2004-2005 Canonical Ltd.\n'
    >>> ZecaTestSetup().tearDown()
    """
    def setUpRoot(self):
        """Recreate root directory and copy needed keys"""
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)
        shutil.copytree(keysdir, self.root)

    @property
    def root(self):
        return config.zeca.root

    @property
    def tacfile(self):
        return os.path.abspath(os.path.join(
            os.path.dirname(canonical.__file__), os.pardir, os.pardir,
            'daemons/zeca.tac'
            ))

    @property
    def pidfile(self):
        return os.path.join(self.root, 'zeca.pid')

    @property
    def logfile(self):
        return os.path.join(self.root, 'zeca.log')

