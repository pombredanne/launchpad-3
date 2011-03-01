#!/usr/bin/python -S
#
# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import _pythonpath

import sys
from canonical.lp import initZopeless
from canonical.database import postgresql
from canonical.database.sqlbase import cursor
from lp.registry.model.person import Person
from lp.registry.model.teammembership import TeamParticipation


person_handle = sys.argv[1]
txn = initZopeless()
try:
    int(person_handle)
except ValueError:
    if "@" in person_handle:
        person = Person.selectOne("EmailAddress.person = Person.id AND "
                               "emailaddress.email = %s" % person_handle)
    else:
        person = Person.selectOneBy(name=person_handle)
else:
    person = Person.selectOneBy(id=person_handle)

if person is None:
    print "Person %s not found" % person_handle
    sys.exit(1)


skip = []
cur = cursor()
references = list(postgresql.listReferences(cur, 'person', 'id'))

print ("Listing references for %s (ID %s, preferred email %s):\n" %
       (person.name, person.id,
        person.preferredemail and person.preferredemail.email))
for src_tab, src_col, ref_tab, ref_col, updact, delact in references:
    if (src_tab, src_col) in skip:
        continue
    query = "SELECT id FROM %s WHERE %s=%s" % (src_tab, src_col, person.id)
    cur.execute(query)
    rows = cur.fetchall()
    for row in rows:
        if src_tab.lower() == 'teamparticipation':
            tp = TeamParticipation.selectOneBy(
                personID=person.id, teamID=person.id)
            if tp.id == row[0]:
                # Every person has a teamparticipation entry for itself,
                # and we already know this. No need to output it, then.
                continue
        print ("\tColumn %s of table %s with id %s points to this "
               "person." % (src_col, src_tab, row[0]))

print
