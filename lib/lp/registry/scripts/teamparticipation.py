# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX: Module docstring goes here."""

__metaclass__ = type
__all__ = [
    "check_teamparticipation",
    ]

from collections import (
    defaultdict,
    namedtuple,
    )
from itertools import (
    chain,
    imap,
    islice,
    )

import transaction

from canonical.database.sqlbase import cursor
from lp.registry.interfaces.teammembership import ACTIVE_STATES
from lp.services.scripts.base import LaunchpadScriptFailure


def chunked(things, chunk_size=50):
    """Yield `things` in chunks of not more than `chunk_size` slices."""
    for offset in xrange(0, len(things), chunk_size):
        yield islice(things, offset, offset + chunk_size)


def check_teamparticipation_self(log):
    # Check self-participation.
    query = """
        SELECT id, name
        FROM Person WHERE id NOT IN (
            SELECT person FROM Teamparticipation WHERE person = team
            ) AND merged IS NULL
        """
    cur = cursor()
    cur.execute(query)
    non_self_participants = cur.fetchall()
    if len(non_self_participants) > 0:
        log.warn("Some people/teams are not members of themselves: %s"
                 % non_self_participants)


def check_teamparticipation_circular(log):
    # Check if there are any circular references between teams.
    cur = cursor()
    cur.execute("""
        SELECT tp.team, tp2.team
        FROM teamparticipation AS tp, teamparticipation AS tp2
        WHERE tp.team = tp2.person
            AND tp.person = tp2.team
            AND tp.id != tp2.id;
        """)
    circular_references = cur.fetchall()
    if len(circular_references) > 0:
        raise LaunchpadScriptFailure(
            "Circular references found: %s" % circular_references)


def check_teamparticipation_consistency(log):
    # Check if there are any missing/spurious TeamParticipation entries.

    cur = cursor()

    # Slurp everything in.
    people = dict(
        cur.execute(
            "SELECT id, name FROM Person"
            " WHERE teamowner IS NULL"
            "   AND merged IS NULL"))
    teams = dict(
        cur.execute(
            "SELECT id, name FROM Person"
            " WHERE teamowner IS NOT NULL"
            "   AND merged IS NULL"))

    team_memberships = defaultdict(set)
    results = cur.execute(
        "SELECT team, person FROM TeamMembership"
        " WHERE status in %s", (ACTIVE_STATES,))
    for (team, person) in results:
        team_memberships[team].add(person)

    team_participations = defaultdict(set)
    results = cur.execute(
        "SELECT team, person FROM TeamParticipation")
    for (team, person) in results:
        team_participations[team].add(person)

    # Don't hold any locks.
    cur.close()
    transaction.abort()

    def get_participants(team):
        """Recurse through membership records to get participants."""
        member_people = team_memberships[team].intersection(people)
        member_people.add(team)  # Teams are always members of themselves.
        member_teams = team_memberships[team].intersection(teams)
        return member_people.union(
            chain.from_iterable(imap(get_participants, member_teams)))

    errors = []
    error_rec = namedtuple("error_rec", ("type", "team", "people"))

    for team in teams:
        participants_observed = team_participations[team]
        participants_expected = get_participants(team)
        participants_spurious = participants_expected - participants_observed
        participants_missing = participants_observed - participants_expected
        if len(participants_spurious) > 0:
            errors.append(error_rec("spurious", team, participants_spurious))
        if len(participants_missing) > 0:
            errors.append(error_rec("missing", team, participants_missing))

    def get_repr(id):
        return "%s (%d)" % (people[id] if id in people else teams[id], id)

    for error in errors:
        people_repr = ", ".join(imap(get_repr, error.people))
        log.warn(
            "%s: %s TeamParticipation entries for %s.",
            get_repr(error.team), error.type, people_repr)

    return errors


def check_teamparticipation(log):
    # Check self-participation.
    check_teamparticipation_self(log)
    # Check if there are any circular references between teams.
    check_teamparticipation_circular(log)
    # Check if there are any missing/spurious TeamParticipation entries.
    check_teamparticipation_consistency(log)
