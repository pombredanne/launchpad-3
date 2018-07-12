#!/usr/bin/python -S
#
# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import _pythonpath

from lp.registry.scripts.createbotaccount import SuspendBotAccountScript


if __name__ == '__main__':
    script = SuspendBotAccountScript('suspend-bot-account', dbuser='launchpad')
    script.run()
