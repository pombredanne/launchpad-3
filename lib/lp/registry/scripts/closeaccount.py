# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Remove personal details of a user from the database, leaving a stub."""

__metaclass__ = type
__all__ = ['CloseAccountScript']

from storm.expr import (
    LeftJoin,
    Lower,
    Or,
    )

from lp.answers.enums import QuestionStatus
from lp.answers.model.question import Question
from lp.bugs.model.bugtask import BugTask
from lp.registry.interfaces.person import PersonCreationRationale
from lp.registry.model.person import Person
from lp.services.database.interfaces import IMasterStore
from lp.services.identity.model.account import Account
from lp.services.identity.model.emailaddress import EmailAddress
from lp.services.scripts.base import (
    LaunchpadScript,
    LaunchpadScriptFailure,
    )


def close_account(username, log):
    """Close a person's account.

    Return True on success, or log an error message and return False
    """
    store = IMasterStore(Person)

    row = store.using(
        Person,
        LeftJoin(EmailAddress, Person.id == EmailAddress.personID)
    ).find(
        (Person.id, Person.accountID, Person.name, Person.teamownerID),
        Or(Person.name == username,
           Lower(EmailAddress.email) == Lower(username))).one()
    if row is None:
        raise LaunchpadScriptFailure("User %s does not exist" % username)
    person_id, account_id, username, teamowner_id = row

    # We don't do teams
    if teamowner_id is not None:
        raise LaunchpadScriptFailure("%s is a team" % username)

    log.info("Closing %s's account" % username)

    def table_notification(table):
        log.debug("Handling the %s table" % table)

    # All names starting with 'removed' are blacklisted, so this will always
    # succeed.
    new_name = 'removed%d' % person_id

    # Remove the EmailAddress. This is the most important step, as
    # people requesting account removal seem to primarily be interested
    # in ensuring we no longer store this information.
    table_notification('EmailAddress')
    store.find(EmailAddress, EmailAddress.personID == person_id).remove()

    # Clean out personal details from the Person table
    table_notification('Person')
    store.find(Person, Person.id == person_id).set(
        display_name='Removed by request',
        name=new_name,
        accountID=None,
        homepage_content=None,
        iconID=None,
        mugshotID=None,
        hide_email_addresses=True,
        registrantID=None,
        logoID=None,
        creation_rationale=PersonCreationRationale.UNKNOWN,
        creation_comment=None)

    # Remove the Account. We don't set the status to deactivated,
    # as this script is used to satisfy people who insist on us removing
    # all their personal details from our systems. This includes any
    # identification tokens like email addresses or openid identifiers.
    # So the Account record would be unusable, and contain no useful
    # information.
    table_notification('Account')
    if account_id is not None:
        store.find(Account, Account.id == account_id).remove()

    # Reassign their bugs
    table_notification('BugTask')
    store.find(BugTask, BugTask.assigneeID == person_id).set(assigneeID=None)

    # Reassign questions assigned to the user, and close all their questions
    # since nobody else can
    table_notification('Question')
    store.find(Question, Question.assigneeID == person_id).set(assigneeID=None)
    store.find(Question, Question.ownerID == person_id).set(
        status=QuestionStatus.SOLVED,
        whiteboard=(
            'Closed by Launchpad due to owner requesting account removal'))

    # Remove rows from tables in simple cases in the given order
    removals = [
        # Trash their email addresses. People who request complete account
        # removal would be unhappy if they reregistered with their old email
        # address and this resurrected their deleted account, as the email
        # address is probably the piece of data we store that they were most
        # concerned with being removed from our systems.
        ('EmailAddress', 'person'),

        # Trash their codes of conduct and GPG keys
        ('SignedCodeOfConduct', 'owner'),
        ('GpgKey', 'owner'),

        # Subscriptions
        ('BranchSubscription', 'person'),
        ('GitSubscription', 'person'),
        ('BugSubscription', 'person'),
        ('QuestionSubscription', 'person'),
        ('SpecificationSubscription', 'person'),

        # Personal stuff, freeing up the namespace for others who want to play
        # or just to remove any fingerprints identifying the user.
        ('IrcId', 'person'),
        ('JabberId', 'person'),
        ('WikiName', 'person'),
        ('PersonLanguage', 'person'),
        ('PersonLocation', 'person'),
        ('SshKey', 'person'),

        # Karma
        ('Karma', 'person'),
        ('KarmaCache', 'person'),
        ('KarmaTotalCache', 'person'),

        # Team memberships
        ('TeamMembership', 'person'),
        ('TeamParticipation', 'person'),

        # Contacts
        ('AnswerContact', 'person'),

        # Pending items in queues
        ('POExportRequest', 'person'),

        # Access grants
        ('GitRuleGrant', 'grantee'),
        ]
    for table, person_id_column in removals:
        table_notification(table)
        store.execute("""
            DELETE FROM %(table)s WHERE %(person_id_column)s = ?
            """ % {
                'table': table,
                'person_id_column': person_id_column,
                },
            (person_id,))

    # Trash Sprint Attendance records in the future.
    table_notification('SprintAttendance')
    store.execute("""
        DELETE FROM SprintAttendance
        USING Sprint
        WHERE Sprint.id = SprintAttendance.sprint
            AND attendee = ?
            AND Sprint.time_starts > CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
        """, (person_id,))

    return True


class CloseAccountScript(LaunchpadScript):

    usage = '%prog [options] (username|email) [...]'
    description = (
        "Close a person's account, deleting as much personal information "
        "as possible.")

    def main(self):
        if not self.args:
            raise LaunchpadScriptFailure(
                "Must specify username (Person.name)")

        for username in self.args:
            try:
                close_account(unicode(username), self.logger)
            except Exception:
                self.txn.abort()
                raise
        self.logger.debug("Committing changes")
        self.txn.commit()
