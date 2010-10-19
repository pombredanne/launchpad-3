#!/usr/bin/python -S
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Migrate all objects specifying variants to appropriate languages."""

import _pythonpath

from lp.services.scripts.base import LaunchpadScript
from lp.translations.scripts.migrate_variants import (
    MigrateVariantsProcess)


class MigrateVariants(LaunchpadScript):
    """Go through all POFiles and TranslationMessages and get rid of variants.

    Replaces use of `variant` field with a new language with the code
    corresponding to the 'previous language'@'variant'.
    """

    def main(self):
        fixer = MigrateVariantsProcess(self.txn, self.logger)
        fixer.run()


if __name__ == '__main__':
    script = MigrateVariants(name="migratevariants",
                             dbuser='rosettaadmin')
    script.lock_and_run()
