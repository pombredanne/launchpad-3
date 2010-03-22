# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX: Module docstring goes here."""

__metaclass__ = type
__all__ = ['SetProcTitleHook']

import setproctitle

class SetProcTitleHook:

    def __init__(self):
        self.basename = setproctitle.getproctitle()

    def seen(self, branch_url):
        branch_url = branch_url.strip('/')
        setproctitle.setproctitle(self.basename + ' BRANCH:' + branch_url)
