#!/usr/bin/python -uS
# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import _pythonpath

from lp.services.scripts.base import LaunchpadScript

from lp.blueprints.model.specification import SpecificationSet
from lp.blueprints.workitemmigration import extractWorkItemsFromWhiteboard


class WorkitemMigrator(LaunchpadScript):

    def add_my_options(self):
        # TODO: add option to limit to only BPs of the given project/distro.
        pass

    def main(self):
        for specification in SpecificationSet():
            if not specification.whiteboard:
                continue

            self.txn.begin()
            try:
                work_items = extractWorkItemsFromWhiteboard(specification)
            except Exception, e:
                self.logger.error(
                    "Failed to parse whiteboard of %s: %s" % (
                        specification, str(e)))
                self.txn.abort()

            if len(work_items) > 0:
                self.logger.info(
                    "Migrated %d work items from the whiteboard of %s: %s" % (
                        len(work_items), specification, work_items))
                self.txn.abort()
                #self.txn.commit()
            else:
                self.logger.info(
                    "No work items found on the whiteboard of %s" %
                        specification)
                self.txn.abort()


if __name__ == '__main__':
    # FIXME: fix the dbuser
    script = WorkitemMigrator(
        'workitem-migration-script', dbuser='launchpad_main')
    script.lock_and_run()
