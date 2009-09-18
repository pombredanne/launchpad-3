#! /usr/bin/python2.4
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403

"""Perform auto-approvals and auto-blocks on translation import queue"""

import _pythonpath

from canonical.config import config
from lp.translations.scripts.import_approval import AutoApproveProcess


if __name__ == '__main__':
    script = AutoApproveProcess(
        'rosetta-approve-imports', dbuser=config.poimport.dbuser)
    script.lock_and_run()
