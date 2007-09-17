#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Check for invalid TeamParticipation entries.

These are the ones for which there are no active TeamMemberships leading to.

This script is usually run on staging to find discrepancies between the
TeamMembership and TeamParticipation tables wich are a good indication of
bugs in the code which maintains the TeamParticipation table.

Ideally there should be database constraints to prevent this sort of
situation, but that's not a simple thing and this should do for now.
"""

import _pythonpath

from canonical.database.sqlbase import cursor
from canonical.launchpad.database import Person
from canonical.lp import initZopeless


if __name__ == '__main__':
    ztm = initZopeless(implicitBegin=False)

    ztm.begin()
    query = """
        SELECT DISTINCT Person.id
        FROM Person, TeamParticipation
        WHERE Person.id = Teamparticipation.person
            AND TeamParticipation.team != Person.id
        """
    cur = cursor()
    cur.execute(query)
    people_ids = cur.fetchall()
    ztm.abort()

    batch = people_ids[:50]
    people_ids = people_ids[50:]
    while batch:
        for [id] in batch:
            ztm.begin()
            person = Person.get(id)
            for team in person.teams_indirectly_participated_in:
                try:
                    path = person.findPathToTeam(team)
                except AssertionError, e:
                    print ("Invalid teamParticipation entry for %s (%d) on %s "
                           "(%d) -- there's no team membership leading to that"
                           % (person.unique_displayname, person.id,
                              team.unique_displayname, team.id))
            ztm.abort()
        batch = people_ids[:50]
        people_ids = people_ids[50:]

