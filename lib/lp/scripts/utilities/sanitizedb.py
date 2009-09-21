# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Scrub a Launchpad database of private data."""

__metaclass__ = type
__all__ = []


from canonical.database.postgresql import ConnectionString
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

        pg_connection_string = ConnectionString(self.args[0])

        if 'prod' in str(pg_connection_string) and not self.options.force:
            self.parser.error(
            "Attempting to sanitize a potential production database '%s'. "
            "--force required." % pg_connection_string.dbname)

        self.logger.debug("Connect using '%s'." % pg_connection_string)

        self.txn = initZopeless(
            dbname=pg_connection_string.dbname,
            dbhost=pg_connection_string.host,
            dbuser=pg_connection_string.user,
            implicitBegin=implicit_begin,
            isolation=isolation)

    def main(self):
        self.removePrivateBugs()
        self.removePrivateBranches()
        self.removeUnlinkedRevisions()
        self.removePrivateTeams()
        self.removePrivatePeople()
        self.removeNonLaunchpadAccounts()
        self.scrambleHiddenEmailAddresses()

    def removePrivateBugs(self):
        """Remove all private bugs."""
        raise NotImplemetnedError

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

    def scrambleHiddenEmailAddresses(self):
        """Hide email addresses users have requested to not be public.

        This replaces the email addresses of all people with
        hide_email_addresses set with an @example.com email address.
        """

