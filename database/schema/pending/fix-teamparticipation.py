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
while batch:
    for [id] in batch:
        ztm.begin()
        person = Person.get(id)
        for team in person.teams_indirectly_participated_in:
            try:
                path = person.findPathToTeam(team)
            except AssertionError, e:
                print str(e)
                print "*****removing this indirect membership*****"
                tp = TeamParticipation.selectOneBy(person=person, team=team)
                tp.destroySelf()
        ztm.commit()
    batch = people_ids[:50]
    people_ids = people_ids[50:]
