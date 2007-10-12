# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Launchpad-Mailman integration test #0

Reset the database without having to 'make schema'.
"""

import itest_helper
from canonical.database.sqlbase import cursor


def main():
    # Start by cleaning up the Launchpad database.
    cursor().execute("""
    CREATE TEMP VIEW DeathRowTeams AS SELECT id FROM Person WHERE name IN
    ('team-one', 'team-two', 'team-three');

    DELETE FROM EmailAddress
    WHERE person in (SELECT id FROM DeathRowTeams);

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
    # this fails because it means the list doesn't exist.
    for team_name in ('team-one', 'team-two', 'team-three'):
        try:
            itest_helper.run_mailman('./rmlist', '-a', team_name)
        except itest_helper.IntegrationTestFailure:
            pass
    itest_helper.transactionmgr.commit()
