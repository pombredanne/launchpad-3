#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403

"""Check for invalid/missing TeamParticipation entries.

Invalid TP entries are the ones for which there are no active TeamMemberships
leading to.

This script is usually run on staging to find discrepancies between the
TeamMembership and TeamParticipation tables which are a good indication of
bugs in the code which maintains the TeamParticipation table.

Ideally there should be database constraints to prevent this sort of
situation, but that's not a simple thing and this should do for now.
"""

import _pythonpath

import optparse
import sys

from canonical.database.sqlbase import cursor
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger)
from canonical.lp import initZopeless


if __name__ == '__main__':
    parser = optparse.OptionParser(
        description="Check for invalid/missing TeamParticipation entries.")
    logger_options(parser)
    options, args = parser.parse_args(sys.argv[1:])
    log = logger(options, 'check-teamparticipation')

    execute_zcml_for_scripts()
    ztm = initZopeless(implicitBegin=False)

    # Check self-participation.
    query = """
        SELECT id, name
        FROM Person WHERE id NOT IN (
            SELECT person FROM Teamparticipation WHERE person = team
            ) AND merged IS NULL
        """
    ztm.begin()
    cur = cursor()
    cur.execute(query)
    non_self_participants = cur.fetchall()
    if len(non_self_participants) > 0:
        log.warn("Some people/teams are not members of themselves: %s"
                 % non_self_participants)

    # Check if there are any circular references between teams.
    cur.execute("""
        SELECT tp.team, tp2.team
        FROM teamparticipation AS tp, teamparticipation AS tp2
        WHERE tp.team = tp2.person
            AND tp.person = tp2.team
            AND tp.id != tp2.id;
        """)
    circular_references = cur.fetchall()
    if len(circular_references) > 0:
        log.warn("Circular references found: %s" % circular_references)
        sys.exit(1)

    # Check if there are any missing/spurious TeamParticipation entries.
    cur.execute("SELECT id FROM Person WHERE teamowner IS NOT NULL")
    team_ids = cur.fetchall()
    ztm.abort()

    def get_participants(team):
        """Recurse through the team's members to get all its participants."""
        participants = set()
        for member in team.activemembers:
            participants.add(member)
            if member.is_team:
                participants.update(get_participants(member))
        return participants

    from lp.registry.model.person import Person
    batch = team_ids[:50]
    team_ids = team_ids[50:]
    while batch:
        for [id] in batch:
            ztm.begin()
            team = Person.get(id)
            expected = get_participants(team)
            found = set(team.allmembers)
            difference = expected.difference(found)
            if len(difference) > 0:
                people = ", ".join("%s (%s)" % (person.name, person.id)
                                   for person in difference)
                log.warn("%s (%s): missing TeamParticipation entries for %s."
                         % (team.name, team.id, people))
            reverse_difference = found.difference(expected)
            if len(reverse_difference) > 0:
                people = ", ".join("%s (%s)" % (person.name, person.id)
                                   for person in reverse_difference)
                log.warn("%s (%s): spurious TeamParticipation entries for %s."
                         % (team.name, team.id, people))
            ztm.abort()
        batch = team_ids[:50]
        team_ids = team_ids[50:]
