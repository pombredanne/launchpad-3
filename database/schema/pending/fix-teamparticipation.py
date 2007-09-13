#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

import _pythonpath

from canonical.database.sqlbase import cursor
from canonical.launchpad.database import Person, TeamParticipation
from canonical.lp import initZopeless


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
removed_entries = 0
while batch:
    for [id] in batch:
        ztm.begin()
        person = Person.get(id)
        for team in person.teams_indirectly_participated_in:
            try:
                path = person.findPathToTeam(team)
            except AssertionError, e:
                print ("Removing TeamParticipation entry for %s on %s"
                       % (person.unique_displayname, team.unique_displayname))
                tp = TeamParticipation.selectOneBy(person=person, team=team)
                tp.destroySelf()
                removed_entries += 1
        ztm.commit()
    batch = people_ids[:50]
    people_ids = people_ids[50:]

print "Removed %d entries in total." % removed_entries
