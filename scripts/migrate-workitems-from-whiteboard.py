#!/usr/bin/python -uS
# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import _pythonpath

from lp.services.scripts.base import LaunchpadScript

from lp.blueprints.model.specification import SpecificationSet
from lp.blueprints.workitemmigration import extractWorkItemsFromWhiteboard


class WorkitemMigrator(LaunchpadScript):
    """Migrate work-items from Specification.whiteboard to
    SpecificationWorkItem.

    Migrating work items from the whiteboard is an all-or-nothing thing; if we
    encounter any errors when parsing the whiteboard of a spec, we abort the
    transaction and leave its whiteboard unchanged.

    On a test with production data, only 100 whiteboards (out of almost 2500)
    could not be migrated. On 24 of those the assignee in at least one work
    item is not valid, on 33 the status of a work item is not valid and on 42
    one or more milestones are not valid.
    """

    def main(self):
        for specification in SpecificationSet():
            if not specification.whiteboard:
                continue

            #self.txn.begin()
            try:
                work_items = extractWorkItemsFromWhiteboard(specification)
            except Exception, e:
                self.logger.error(
                    "Failed to parse whiteboard of %s: %s" % (
                        specification, unicode(e)))
                #self.txn.abort()
                continue

            # XXX: Short-circuit while testing
            continue

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

        self.txn.abort()


if __name__ == '__main__':
    # FIXME: fix the dbuser
    script = WorkitemMigrator(
        'workitem-migration-script', dbuser='launchpad_main')
    script.lock_and_run()
