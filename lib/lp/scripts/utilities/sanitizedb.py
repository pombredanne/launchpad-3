# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Scrub a Launchpad database of private data."""

import _pythonpath

__metaclass__ = type
__all__ = []

import re
import subprocess
import sys

import transaction
from zope.component import getUtility

from canonical.database.postgresql import ConnectionString
from canonical.launchpad.interfaces import IMasterStore
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR)
from canonical.lp import initZopeless
from lp.services.scripts.base import LaunchpadScript


class SanitizeDb(LaunchpadScript):
    usage = "%prog [options] pg_connection_string"
    description = "Destroy private information in a Launchpad database."

    def add_my_options(self):
        self.parser.add_option(
            "-f", "--force", action="store_true", default=False,
            help="Force running against a possible production database.")

    def _init_db(self, implicit_begin, isolation):
        if len(self.args) == 0:
            self.parser.error("PostgreSQL connection string required.")
        elif len(self.args) > 1:
            self.parser.error("Too many arguments.")

        self.pg_connection_string = ConnectionString(self.args[0])

        if ('prod' in str(self.pg_connection_string)
            and not self.options.force):
            self.parser.error(
            "Attempting to sanitize a potential production database '%s'. "
            "--force required." % pg_connection_string.dbname)

        self.logger.debug("Connect using '%s'." % self.pg_connection_string)

        self.txn = initZopeless(
            dbname=self.pg_connection_string.dbname,
            dbhost=self.pg_connection_string.host,
            dbuser=self.pg_connection_string.user,
            implicitBegin=implicit_begin,
            isolation=isolation)

        self.store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)

    def main(self):
        self._allForeignKeysCascade()
        transaction.commit()
        try:
            self.removePrivateBugs()
            self.removePrivateBranches()
            self.removeUnlinkedRevisions()
            self.removePrivateTeams()
            self.removePrivatePeople()
            self.removeNonLaunchpadAccounts()
            self.scrambleHiddenEmailAddresses()
            transaction.commit()
        finally:
            transaction.abort()
            self._resetForeignKeysCascade()
            transaction.commit()

    def removePrivateBugs(self):
        """Remove all private bugs."""
        from lp.bugs.model.bug import Bug
        count = self.store.find(Bug, Bug.private == True).remove()
        self.logger.info("Removed %d private bugs.", count)

    def removePrivateBranches(self):
        """Remove all private branches."""
        raise NotImplementedError

    def removePrivateTeams(self):
        """Remove all private teams."""
        raise NotImplementedError

    def removePrivatePeople(self):
        """Remove all private people."""
        raise NotImplementedError

    def removeNonLaunchpadAccounts(self):
        """Remove Account records not linked to a Person.
        """
        raise NotImplementedError

    def removeUnlinkedEmailAddresses(self):
        """Remove EmailAddress records not linked to a Person."""
        raise NotImplementedError

    def scrambleHiddenEmailAddresses(self):
        """Hide email addresses users have requested to not be public.

        This replaces the email addresses of all people with
        hide_email_addresses set with an @example.com email address.
        """
        raise NotImplementedError

    def _allForeignKeysCascade(self):
        """Set all foreign key constraints to ON DELETE CASCADE.

        The current state is recorded first so _resetForeignKeysCascade
        can repair the changes.

        Only tables in the public schema are modified.
        """
        # Get the SQL needed to create the foreign key constraints.
        # pg_dump seems the only sane way of getting this. We could
        # generate the SQL ourselves using the pg_constraints table,
        # but that can change between PostgreSQL releases.
        # Ideally we could use ALTER CONSTRAINT, but that doesn't exist.
        # Or modify pg_constraints, but that doesn't work.
        cmd = [
            'pg_dump', '--no-privileges', '--no-owner', '--schema-only',
            '--schema=public']
        cmd.extend(
            self.pg_connection_string.asPGCommandLineArgs().split(' '))
        self.logger.debug("Running %s", ' '.join(cmd))
        pg_dump = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE)
        (pg_dump_out, pg_dump_err) = pg_dump.communicate()
        if pg_dump.returncode != 0:
            self.fail("pg_dump returned %d" % pg_dump.returncode)

        cascade_sql = []
        restore_sql = []
        pattern = r"""
            (?x) ALTER \s+ TABLE \s+ ONLY \s+ (".*?"|\w+?) \s+
            ADD \s+ CONSTRAINT \s+ (".*?"|\w+?) \s+ FOREIGN \s+ KEY [^;]+;
            """
        for match in re.finditer(pattern, pg_dump_out):
            table = match.group(1)
            constraint = match.group(2)

            sql = match.group(0)

            # Drop the existing constraint so we can recreate it.
            drop_sql =  'ALTER TABLE %s DROP CONSTRAINT %s;' % (
                table, constraint)
            restore_sql.append(drop_sql)
            cascade_sql.append(drop_sql)

            # Store the SQL needed to restore the constraint.
            restore_sql.append(sql)

            # Recreate the constraint as ON DELETE CASCADE
            sql = re.sub(r"""(?xs)^
                (.*?)
                (?:ON \s+ DELETE \s+ (?:NO\s+|SET\s+)?\w+)? \s*
                ((?:NOT\s+)? DEFERRABLE|) \s*
                (INITIALLY\s+(?:DEFERRED|IMMEDIATE)|) \s*;
                """, r"\1 ON DELETE CASCADE \2 \3;", sql)
            cascade_sql.append(sql)

        # Set all the foreign key constraints to ON DELETE CASCADE, really.
        self.logger.info(
            "Setting %d constraints to ON DELETE CASCADE",
            len(cascade_sql) / 2)
        self.store.execute('\n'.join(cascade_sql))

        # Store the recovery SQL.
        self._reset_foreign_key_sql = restore_sql

    def _resetForeignKeysCascade(self):
        """Reset the foreign key constraints' ON DELETE mode."""
        self.logger.info(
            "Resetting %d foreign key constraints to initial state.",
            len(self._reset_foreign_key_sql)/2)
        self.store.execute('\n'.join(self._reset_foreign_key_sql))

    def _fail(self, error_message):
        self.logger.fatal(error_message)
        sys.exit(1)

