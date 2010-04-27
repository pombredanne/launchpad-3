#!/usr/bin/python2.5 -S
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Copy rows from pg_stat_user_tables into DatabaseTableStats."""

__metaclass__ = type

import _pythonpath

from zope.component import getUtility

from canonical.launchpad.scripts import db_options
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR)
from lp.services.scripts.base import LaunchpadCronScript

class UpdateDatabaseTableStats(LaunchpadCronScript):
    """Copy rows from pg_stat_user_tables into DatabaseTableStats."""

    def main(self):
        "Run UpdateDatabaseTableStats."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        insert_result = store.execute("SELECT update_database_table_stats()")
        self.logger.debug("Invoked update_database_table_stats()");
        store.commit()
        self.logger.debug("Committed")

    def add_my_options(self):
        """Add standard database command line options."""
        db_options(self.parser)

if __name__ == '__main__':
    script = UpdateDatabaseTableStats(
        'update-database-table-stats', dbuser='update-database-table-stats')
    script.lock_and_run()

