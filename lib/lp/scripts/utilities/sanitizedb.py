# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Scrub a Launchpad database of private data."""

import _pythonpath


__metaclass__ = type
__all__ = []

import re
import subprocess
import sys

from storm.locals import Or
import transaction
from zope.component import getUtility

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import cursor, sqlvalues
from canonical.database.postgresql import ConnectionString, listReferences
from canonical.launchpad.scripts.logger import DEBUG2, DEBUG3
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
        self.parser.add_option(
            "-n", "--dry-run", action="store_true", default=False,
            help="Don't commit changes.")

    def _init_db(self, isolation):
        if len(self.args) == 0:
            self.parser.error("PostgreSQL connection string required.")
        elif len(self.args) > 1:
            self.parser.error("Too many arguments.")

        self.pg_connection_string = ConnectionString(self.args[0])

        if ('prod' in str(self.pg_connection_string)
            and not self.options.force):
            self.parser.error(
            "Attempting to sanitize a potential production database '%s'. "
            "--force required." % self.pg_connection_string.dbname)

        self.logger.debug("Connect using '%s'." % self.pg_connection_string)

        self.txn = initZopeless(
            dbname=self.pg_connection_string.dbname,
            dbhost=self.pg_connection_string.host,
            dbuser=self.pg_connection_string.user,
            isolation=isolation)

        self.store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)

    def main(self):
        self.allForeignKeysCascade()
        triggers_to_disable = [
            ('bugmessage', 'set_bug_message_count_t'),
            ('bugmessage', 'set_date_last_message_t'),
            ]
        self.disableTriggers(triggers_to_disable)

        tables_to_empty = [
            'accountpassword',
            'archiveauthtoken',
            'archivesubscriber',
            'authtoken',
            'buildqueue',
            'commercialsubscription',
            'entitlement',
            'job',
            'logintoken',
            'mailinglistban',
            'mailinglistsubscription',
            'oauthaccesstoken',
            'oauthconsumer',
            'oauthnonce',
            'oauthrequesttoken',
            'openidassociation',
            'openidconsumerassociation',
            'openidconsumernonce',
            'openidrpsummary',
            'openididentifier',
            'requestedcds',
            'scriptactivity',
            'shipitreport',
            'shipitsurvey',
            'shipitsurveyanswer',
            'shipitsurveyquestion',
            'shipitsurveyresult',
            'shipment',
            'shippingrequest',
            'shippingrun',
            'sprintattendance', # Is this private?
            'standardshipitrequest',
            'temporaryblobstorage',
            'usertouseremail',
            'vote',
            'votecast',
            'webserviceban',
            ]
        for table in tables_to_empty:
            self.removeTableRows(table)

        self.removePrivatePeople()
        self.removePrivateTeams()
        self.removePrivateBugs()
        self.removePrivateBugMessages()
        self.removePrivateBranches()
        self.removePrivateHwSubmissions()
        self.removePrivateSpecifications()
        self.removePrivateLocations()
        self.removePrivateArchives()
        self.removePrivateAnnouncements()
        self.removePrivateLibrarianFiles()
        self.removeInactiveProjects()
        self.removeInactiveProducts()
        self.removeInvalidEmailAddresses()
        self.removePPAArchivePermissions()
        self.scrambleHiddenEmailAddresses()

        self.removeDeactivatedPeopleAndAccounts()

        # Remove unlinked records. These might contain private data.
        self.removeUnlinkedEmailAddresses()
        self.removeUnlinkedAccounts()
        self.removeUnlinked('revision', [
            ('revisioncache', 'revision'),
            ('revisionparent', 'revision'),
            ('revisionproperty', 'revision'),
            ])
        self.removeUnlinked('libraryfilealias', [
            ('libraryfiledownloadcount', 'libraryfilealias')])
        self.removeUnlinked('libraryfilecontent')
        self.removeUnlinked('message', [('messagechunk', 'message')])
        self.removeUnlinked('staticdiff')
        self.removeUnlinked('previewdiff')
        self.removeUnlinked('diff')

        # Scrub data after removing all the records we are going to.
        # No point scrubbing data that is going to get removed later.
        columns_to_scrub = [
            ('account', ['status_comment']),
            ('distribution', ['reviewer_whiteboard']),
            ('distributionmirror', ['whiteboard']),
            ('hwsubmission', ['raw_emailaddress']),
            ('nameblacklist', ['comment']),
            ('person', [
                'personal_standing_reason',
                'mail_resumption_date']),
            ('product', ['reviewer_whiteboard']),
            ('project', ['reviewer_whiteboard']),
            ('revisionauthor', ['email']),
            ('signedcodeofconduct', ['admincomment']),
            ]
        for table, column in columns_to_scrub:
            self.scrubColumn(table, column)

        self.enableTriggers(triggers_to_disable)
        self.repairData()

        self.resetForeignKeysCascade()
        if self.options.dry_run:
            self.logger.info("Dry run - rolling back.")
            transaction.abort()
        else:
            self.logger.info("Committing.")
            transaction.commit()

    def removeDeactivatedPeopleAndAccounts(self):
        """Remove all suspended and deactivated people & their accounts.

        Launchpad celebrities are ignored.
        """
        from canonical.launchpad.database.account import Account
        from canonical.launchpad.database.emailaddress import EmailAddress
        from canonical.launchpad.interfaces.account import AccountStatus
        from canonical.launchpad.interfaces.launchpad import (
            ILaunchpadCelebrities)
        from lp.registry.model.person import Person
        celebrities = getUtility(ILaunchpadCelebrities)
        # This is a slow operation due to the huge amount of cascading.
        # We remove one row at a time for better reporting and PostgreSQL
        # memory use.
        deactivated_people = self.store.find(
            Person,
            Person.account == Account.id,
            Account.status != AccountStatus.ACTIVE)
        total_deactivated_count = deactivated_people.count()
        deactivated_count = 0
        for person in deactivated_people:
            # Ignore celebrities
            if celebrities.isCelebrityPerson(person.name):
                continue
            deactivated_count += 1
            self.logger.debug(
                "Removing %d of %d deactivated people (%s)",
                deactivated_count, total_deactivated_count, person.name)
            # Clean out the EmailAddress and Account for this person
            # while we are here, making subsequent unbatched steps
            # faster. These don't cascade due to the lack of a foreign
            # key constraint between Person and EmailAddress, and the
            # ON DELETE SET NULL foreign key constraint between
            # EmailAddress and Account.
            self.store.find(
                EmailAddress, EmailAddress.person == person).remove()
            self.store.find(Account, Account.id == person.accountID).remove()
            self.store.remove(person)
            self.store.flush()
        self.logger.info(
            "Removed %d suspended or deactivated people + email + accounts",
            deactivated_count)

    def removePrivatePeople(self):
        """Remove all private people."""
        from lp.registry.interfaces.person import PersonVisibility
        from lp.registry.model.person import Person
        count = self.store.find(
            Person,
            Person.teamowner == None,
            Person.visibility != PersonVisibility.PUBLIC).remove()
        self.store.flush()
        self.logger.info("Removed %d private people.", count)

    def removePrivateTeams(self):
        """Remove all private people."""
        from lp.registry.interfaces.person import PersonVisibility
        from lp.registry.model.person import Person
        count = self.store.find(
            Person,
            Person.teamowner != None,
            Person.visibility != PersonVisibility.PUBLIC).remove()
        self.store.flush()
        self.logger.info("Removed %d private teams.", count)

    def removePrivateBugs(self):
        """Remove all private bugs."""
        from lp.bugs.model.bug import Bug
        count = self.store.find(Bug, Bug.private == True).remove()
        self.store.flush()
        self.logger.info("Removed %d private bugs.", count)

    def removePrivateBugMessages(self):
        """Remove all hidden bug messages."""
        from lp.bugs.model.bugmessage import BugMessage
        count = self.store.find(
            BugMessage, BugMessage.visible == False).remove()
        self.store.flush()
        self.logger.info("Removed %d private bug messages.", count)

    def removePrivateBranches(self):
        """Remove all private branches."""
        from lp.code.model.branch import Branch
        count = self.store.find(Branch, Branch.private == True).remove()
        self.store.flush()
        self.logger.info("Removed %d private branches.", count)

    def removePrivateHwSubmissions(self):
        """Remove all private hardware submissions."""
        from lp.hardwaredb.model.hwdb import HWSubmission
        count = self.store.find(
            HWSubmission, HWSubmission.private == True).remove()
        self.store.flush()
        self.logger.info("Removed %d private hardware submissions.", count)

    def removePrivateSpecifications(self):
        """Remove all private specifications."""
        from lp.blueprints.model.specification import Specification
        count = self.store.find(
            Specification, Specification.private == True).remove()
        self.store.flush()
        self.logger.info("Removed %d private specifications.", count)

    def removePrivateLocations(self):
        """Remove private person locations."""
        from lp.registry.model.personlocation import PersonLocation
        count = self.store.find(
            PersonLocation, PersonLocation.visible == False).remove()
        self.store.flush()
        self.logger.info("Removed %d person locations.", count)

    def removePrivateArchives(self):
        """Remove private archives.

        This might over delete, but lets be conservative for now.
        """
        from lp.soyuz.model.archive import Archive
        count = self.store.find(Archive, Archive.private == True).remove()
        self.store.flush()
        self.logger.info(
            "Removed %d private archives.", count)

    def removePrivateAnnouncements(self):
        """Remove announcements that have not yet been published."""
        from lp.registry.model.announcement import Announcement
        count = self.store.find(
            Announcement, Or(
                Announcement.date_announced == None,
                Announcement.date_announced > UTC_NOW,
                Announcement.active == False)).remove()
        self.store.flush()
        self.logger.info(
            "Removed %d unpublished announcements.", count)

    def removePrivateLibrarianFiles(self):
        """Remove librarian files only available via the restricted librarian.
        """
        from canonical.launchpad.database.librarian import LibraryFileAlias
        count = self.store.find(
            LibraryFileAlias, LibraryFileAlias.restricted == True).remove()
        self.store.flush()
        self.logger.info("Removed %d restricted librarian files.", count)

    def removeInactiveProjects(self):
        """Remove inactive projects."""
        from lp.registry.model.projectgroup import ProjectGroup
        count = self.store.find(
            ProjectGroup, ProjectGroup.active == False).remove()
        self.store.flush()
        self.logger.info("Removed %d inactive product groups.", count)

    def removeInactiveProducts(self):
        """Remove inactive products."""
        from lp.registry.model.product import Product
        count = self.store.find(
            Product, Product.active == False).remove()
        self.store.flush()
        self.logger.info("Removed %d inactive products.", count)

    def removeTableRows(self, table):
        """Remove all data from a table."""
        count = self.store.execute("DELETE FROM %s" % table).rowcount
        self.store.execute("ANALYZE %s" % table)
        self.logger.info("Removed %d %s rows (all).", count, table)

    def removeUnlinked(self, table, ignores=()):
        """Remove all unlinked entries in the table.

        References from the ignores list are ignored.

        :param table: table name.

        :param ignores: list of (table, column) references to ignore.
        """
        references = []
        for result in listReferences(cursor(), table, 'id'):
            (from_table, from_column, to_table,
                to_column, update, delete) = result
            if (to_table == table and to_column == 'id'
                and (from_table, from_column) not in ignores):
                references.append(
                    "EXCEPT SELECT %s FROM %s" % (from_column, from_table))
        query = (
            "DELETE FROM %s USING (SELECT id FROM %s %s) AS Unreferenced "
            "WHERE %s.id = Unreferenced.id"
            % (table, table, ' '.join(references), table))
        self.logger.log(DEBUG2, query)
        count = self.store.execute(query).rowcount
        self.logger.info("Removed %d unlinked %s rows.", count, table)

    def removeInvalidEmailAddresses(self):
        """Remove all invalid and old email addresses."""
        from canonical.launchpad.database.emailaddress import EmailAddress
        from canonical.launchpad.interfaces.emailaddress import (
            EmailAddressStatus)
        count = self.store.find(
            EmailAddress, Or(
                EmailAddress.status == EmailAddressStatus.NEW,
                EmailAddress.status == EmailAddressStatus.OLD,
                EmailAddress.email.lower().like(
                    u'%@example.com', case_sensitive=True))).remove()
        self.store.flush()
        self.logger.info(
            "Removed %d invalid, unvalidated and old email addresses.", count)

    def removePPAArchivePermissions(self):
        """Remove ArchivePermission records for PPAs."""
        from lp.soyuz.enums import ArchivePurpose
        count = self.store.execute("""
            DELETE FROM ArchivePermission
            USING Archive
            WHERE ArchivePermission.archive = Archive.id
                AND Archive.purpose = %s
            """ % sqlvalues(ArchivePurpose.PPA)).rowcount
        self.logger.info(
            "Removed %d ArchivePermission records linked to PPAs.", count)

    def scrambleHiddenEmailAddresses(self):
        """Hide email addresses users have requested to not be public.

        Call after removeInvalidEmailAddresses to avoid any possible
        name clashes.

        This replaces the email addresses of all people with
        hide_email_addresses set with an @example.com email address.
        """
        # One day there might be Storm documentation telling me how to
        # do this via the ORM.
        count = self.store.execute("""
            UPDATE EmailAddress
            SET email='e' || text(EmailAddress.id) || '@example.com'
            FROM Person
            WHERE EmailAddress.person = Person.id
                AND Person.hide_email_addresses IS TRUE
            """).rowcount
        self.logger.info(
            "Replaced %d hidden email addresses with @example.com", count)

    def removeUnlinkedEmailAddresses(self):
        """Remove EmailAddresses not linked to a Person.

        We call this before removeUnlinkedAccounts to avoid the
        ON DELETE SET NULL overhead from the EmailAddress -> Account
        foreign key constraint.
        """
        from canonical.launchpad.database.emailaddress import EmailAddress
        count = self.store.find(
            EmailAddress, EmailAddress.person == None).remove()
        self.store.flush()
        self.logger.info(
            "Removed %d email addresses not linked to people.", count)

    def removeUnlinkedAccounts(self):
        """Remove Accounts not linked to a Person."""
        from canonical.launchpad.database.account import Account
        from lp.registry.model.person import Person
        all_accounts = self.store.find(Account)
        linked_accounts = self.store.find(
            Account, Account.id == Person.accountID)
        unlinked_accounts = all_accounts.difference(linked_accounts)
        total_unlinked_accounts = unlinked_accounts.count()
        count = 0
        for account in unlinked_accounts:
            self.store.remove(account)
            self.store.flush()
            count += 1
            self.logger.debug(
                "Removed %d of %d unlinked accounts."
                % (count, total_unlinked_accounts))
        self.logger.info("Removed %d accounts not linked to a person", count)

    def scrubColumn(self, table, columns):
        """Remove production admin related notes."""
        query = ["UPDATE %s SET" % table]
        for column in columns:
            query.append("%s = NULL" % column)
            query.append(",")
        query.pop()
        query.append("WHERE")
        for column in columns:
            query.append("%s IS NOT NULL" % column)
            query.append("OR")
        query.pop()
        self.logger.log(DEBUG3, ' '.join(query))
        count = self.store.execute(' '.join(query)).rowcount
        self.logger.info(
            "Scrubbed %d %s.{%s} entries."
            % (count, table, ','.join(columns)))

    def allForeignKeysCascade(self):
        """Set all foreign key constraints to ON DELETE CASCADE.

        The current state is recorded first so resetForeignKeysCascade
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
            drop_sql = 'ALTER TABLE %s DROP CONSTRAINT %s;' % (
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
        for statement in cascade_sql:
            self.logger.log(DEBUG3, statement)
            self.store.execute(statement)

        # Store the recovery SQL.
        self._reset_foreign_key_sql = restore_sql

    def resetForeignKeysCascade(self):
        """Reset the foreign key constraints' ON DELETE mode."""
        self.logger.info(
            "Resetting %d foreign key constraints to initial state.",
            len(self._reset_foreign_key_sql)/2)
        for statement in self._reset_foreign_key_sql:
            self.store.execute(statement)

    def disableTriggers(self, triggers_to_disable):
        """Disable a set of triggers.

        :param triggers_to_disable: List of (table_name, trigger_name).
        """
        self.logger.debug("Disabling %d triggers." % len(triggers_to_disable))
        for table_name, trigger_name in triggers_to_disable:
            self.logger.debug(
                "Disabling trigger %s.%s." % (table_name, trigger_name))
            self.store.execute(
                "ALTER TABLE %s DISABLE TRIGGER %s"
                % (table_name, trigger_name))

    def enableTriggers(self, triggers_to_enable):
        """Renable a set of triggers.

        :param triggers_to_enable: List of (table_name, trigger_name).
        """
        self.logger.debug("Enabling %d triggers." % len(triggers_to_enable))
        for table_name, trigger_name in triggers_to_enable:
            self.logger.debug(
                "Enabling trigger %s.%s." % (table_name, trigger_name))
            self.store.execute(
                "ALTER TABLE %s ENABLE TRIGGER %s"
                % (table_name, trigger_name))

    def repairData(self):
        """After scrubbing, repair any data possibly damaged in the process.
        """
        # Repair Bug.message_count and Bug.date_last_message.
        # The triggers where disabled while we where doing the cascading
        # deletes because they fail (attempting to change a mutating table).
        # We can repair these caches by forcing the triggers to run for
        # every row.
        self.store.execute("UPDATE BugMessage SET visible=visible")

    def _fail(self, error_message):
        self.logger.fatal(error_message)
        sys.exit(1)
