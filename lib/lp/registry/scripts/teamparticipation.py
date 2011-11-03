# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Script code relating to team participations."""

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
    )

import transaction
from zope.component import getUtility

from canonical.database.sqlbase import quote
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector,
    MAIN_STORE,
    SLAVE_FLAVOR,
    )
from lp.registry.interfaces.teammembership import ACTIVE_STATES
from lp.services.scripts.base import LaunchpadScriptFailure


def get_store():
    """Return a slave store.

    Errors in `TeamPartipation` can be detected using a replicated copy.
    """
    return getUtility(IStoreSelector).get(MAIN_STORE, SLAVE_FLAVOR)


def check_teamparticipation_self(log):
    """Check self-participation.

    All people and teams should participate in themselves.
    """
    query = """
        SELECT id, name
          FROM Person
         WHERE id NOT IN (
            SELECT person FROM TeamParticipation
             WHERE person = team)
           AND merged IS NULL
        """
    non_self_participants = list(get_store().execute(query))
    if len(non_self_participants) > 0:
        log.warn(
            "Some people/teams are not members of themselves: %s",
            non_self_participants)


def check_teamparticipation_circular(log):
    """Check circular references.

    There can be no mutual participation between teams.
    """
    query = """
        SELECT tp.team, tp2.team
          FROM TeamParticipation AS tp,
               TeamParticipation AS tp2
         WHERE tp.team = tp2.person
           AND tp.person = tp2.team
           AND tp.id != tp2.id;
        """
    circular_references = list(get_store().execute(query))
    if len(circular_references) > 0:
        raise LaunchpadScriptFailure(
            "Circular references found: %s" % circular_references)


ConsistencyError = namedtuple(
    "ConsistencyError", ("type", "team", "people"))


def check_teamparticipation_consistency(log):
    """Check for missing or spurious participations.

    For example, participations for people who are not members, or missing
    participations for people who are members.
    """
    store = get_store()

    # Slurp everything in.
    people = dict(
        store.execute(
            "SELECT id, name FROM Person"
            " WHERE teamowner IS NULL"
            "   AND merged IS NULL"))
    teams = dict(
        store.execute(
            "SELECT id, name FROM Person"
            " WHERE teamowner IS NOT NULL"
            "   AND merged IS NULL"))
    team_memberships = defaultdict(set)
    results = store.execute(
        "SELECT team, person FROM TeamMembership"
        " WHERE status in %s" % quote(ACTIVE_STATES))
    for (team, person) in results:
        team_memberships[team].add(person)
    team_participations = defaultdict(set)
    results = store.execute(
        "SELECT team, person FROM TeamParticipation")
    for (team, person) in results:
        team_participations[team].add(person)

    # Don't hold any locks.
    transaction.commit()

    def get_participants(team):
        """Recurse through membership records to get participants."""
        member_people = team_memberships[team].intersection(people)
        member_people.add(team)  # Teams always participate in themselves.
        member_teams = team_memberships[team].intersection(teams)
        return member_people.union(
            chain.from_iterable(imap(get_participants, member_teams)))

    def check_participants(expected, observed):
        spurious = observed - expected
        missing = expected - observed
        if len(spurious) > 0:
            yield ConsistencyError("spurious", team, sorted(spurious))
        if len(missing) > 0:
            yield ConsistencyError("missing", team, sorted(missing))

    errors = []

    for person in people:
        participants_expected = set((person,))
        participants_observed = team_participations[person]
        errors.extend(
            check_participants(participants_expected, participants_observed))

    for team in teams:
        participants_expected = get_participants(team)
        participants_observed = team_participations[team]
        errors.extend(
            check_participants(participants_expected, participants_observed))

    def get_repr(id):
        if id in people:
            name = people[id]
        elif id in teams:
            name = teams[id]
        else:
            name = "<unknown>"
        return "%s (%d)" % (name, id)

    for error in errors:
        people_repr = ", ".join(imap(get_repr, error.people))
        log.warn(
            "%s: %s TeamParticipation entries for %s.",
            get_repr(error.team), error.type, people_repr)

    return errors


def check_teamparticipation(log):
    """Perform various checks on the `TeamParticipation` table."""
    check_teamparticipation_self(log)
    check_teamparticipation_circular(log)
    check_teamparticipation_consistency(log)
