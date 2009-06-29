#!/usr/bin/python2.4
# pylint: disable-msg=W0403
# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Commit translations to translations_branch where requested."""

__metaclass__ = type
__all__ = []

import _pythonpath
from canonical.launchpad.scripts.translations_to_branch import (
    ExportTranslationsToBranch)


if __name__ == '__main__':
    script = ExportTranslationsToBranch(
        'translations-export-to-branch', dbuser='translationstobranch')
    script.lock_and_run()
