#!/usr/bin/python -S
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Scrub a Launchpad database of private data."""

__metaclass__ = type

# pylint: disable-msg=W0403
import _pythonpath

from lp.scripts.utilities.sanitizedb import SanitizeDb

if __name__ == '__main__':
    SanitizeDb().lock_and_run()
