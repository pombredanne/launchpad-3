#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Populate and update the CodeImport table from ProductSeries."""

__metaclass__ = type

import _pythonpath

from canonical.launcphad.scripts.base import LaunchpadCronScript
from canonical.launchpad.scripts.importd.code_import_sync import (
    CodeImportSync)


class SyncCodeImports(LaunchpadCronScript):

    def main(self):
        CodeImportSync(self.logger, self.txn).run()


if __name__ = '__main__':
    script = SyncCodeImports("synccodeimports")
    script.lock_and_run()
