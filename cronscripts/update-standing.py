#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A cron script for updating personal standings."""

__metaclass__ = type
__all__ = []


# pylint: disable-msg=W0403
import _pythonpath

from canonical.config import config
from lp.registry.scripts.standing import UpdatePersonalStanding


if __name__ == '__main__':
    script = UpdatePersonalStanding(
        'update-personal-standing',
        dbuser=config.standingupdater.dbuser)
    script.lock_and_run()
