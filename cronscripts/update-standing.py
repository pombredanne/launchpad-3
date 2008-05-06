#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""A cron script for updating personal standings."""

__metaclass__ = type
__all__ = []


import _pythonpath

from canonical.launchpad.scripts.standing import UpdatePersonalStanding


if __name__ == '__main__':
    script = UpdatePersonalStanding('update-personal-standing')
    script.lock_and_run()
