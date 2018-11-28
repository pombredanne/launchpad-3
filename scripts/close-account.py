#!/usr/bin/python -S
#
# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Remove personal details of a user from the database, leaving a stub."""

import _pythonpath

from lp.registry.scripts.closeaccount import CloseAccountScript


if __name__ == '__main__':
    script = CloseAccountScript('close-account', dbuser='launchpad')
    script.run()
