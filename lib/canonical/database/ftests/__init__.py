# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os
from canonical.launchpad.daemons.tachandler import TacTestSetup

class PortForwardTestSetup(TacTestSetup):

    def setUpRoot(self):
        if os.path.exists(self.pidfile):
            os.remove(self.pidfile)
        if os.path.exists(self.logfile):
            os.remove(self.logfile)

    @property
    def tacfile(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            'portforward-to-postgres.tac'))

    @property
    def logfile(self):
        return os.path.join(os.getcwd(), 'portforward-to-postgres.log')

    @property
    def pidfile(self):
        return os.path.join(os.getcwd(), 'portforward-to-postgres.pid')
