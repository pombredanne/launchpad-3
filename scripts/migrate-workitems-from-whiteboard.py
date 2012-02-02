#!/usr/bin/python -uS
# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import _pythonpath

from lp.services.scripts.base import LaunchpadScript

from lp.blueprints.workitemmigration import (
    SpecificationWorkitemMigratorProcess)


class WorkitemMigrator(LaunchpadScript):

    def main(self):
        proc = SpecificationWorkitemMigratorProcess(self.txn, self.logger)
        proc.run()


if __name__ == '__main__':
    # FIXME: fix the dbuser
    script = WorkitemMigrator(
        'workitem-migration-script', dbuser='launchpad_main')
    script.lock_and_run()
