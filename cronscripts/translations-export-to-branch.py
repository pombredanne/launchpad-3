#!/usr/bin/python2.4
# pylint: disable-msg=W0403
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Commit translations to translations_branch where requested."""

__metaclass__ = type
__all__ = []

import _pythonpath
from lp.translations.scripts.translations_to_branch import (
    ExportTranslationsToBranch)


if __name__ == '__main__':
    script = ExportTranslationsToBranch(
        'translations-export-to-branch', dbuser='translationstobranch')
    script.lock_and_run()
