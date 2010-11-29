#!/usr/bin/python -S
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Migrate current flag to imported flag on project translations."""

import _pythonpath

from lp.services.scripts.base import LaunchpadScript
from lp.translations.scripts.migrate_current_flag import (
    MigrateCurrentFlagProcess)


class MigrateTranslationFlags(LaunchpadScript):
    """Go through all POFiles and TranslationMessages and get rid of variants.

    Replaces use of `variant` field with a new language with the code
    corresponding to the 'previous language'@'variant'.
    """

    def main(self):
        fixer = MigrateCurrentFlagProcess(self.txn, self.logger)
        fixer.run()


if __name__ == '__main__':
    script = MigrateTranslationFlags(
        name="migratecurrentflag", dbuser='rosettaadmin')
    script.lock_and_run()
