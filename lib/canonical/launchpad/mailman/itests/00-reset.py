# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Launchpad-Mailman integration test #0

Reset the database without having to 'make schema'.
"""

from subprocess import call, Popen, PIPE, STDOUT
from canonical.database.sqlbase import cursor


def main():
    # Start by cleaning up the Launchpad database.
    cursor().execute("""
    CREATE TEMP VIEW DeathRowTeams AS SELECT id FROM Person WHERE name IN
    ('team-one', 'team-two');

    DELETE FROM TeamMembership
    WHERE team IN (SELECT id FROM DeathRowTeams);

    DELETE FROM TeamParticipation
    WHERE team IN (SELECT id FROM DeathRowTeams);

    DELETE FROM MailingList
    WHERE team IN (SELECT id FROM DeathRowTeams);

    DELETE FROM Person
    WHERE id IN (SELECT id FROM DeathRowTeams);
    """)
    # Now delete any mailing lists still hanging around.  We don't care if
    # this fails because the lists don't exist.
    for team_name in ('team-one', 'team-two'):
        call(('./rmlist', '-a', team_name),
             stdout=PIPE, stderr=STDOUT,
             cwd=MAILMAN_BIN)
    transactionmgr.commit()
