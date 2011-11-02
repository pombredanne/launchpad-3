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
        FROM Person WHERE id NOT IN (
            SELECT person FROM Teamparticipation WHERE person = team
            ) AND merged IS NULL
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
        FROM teamparticipation AS tp, teamparticipation AS tp2
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
    transaction.abort()

    # Check team memberships.
    def get_participants(team):
        """Recurse through membership records to get participants."""
        member_people = team_memberships[team].intersection(people)
        member_people.add(team)  # Teams always participate in themselves.
        member_teams = team_memberships[team].intersection(teams)
        return member_people.union(
            chain.from_iterable(imap(get_participants, member_teams)))

    errors = []
    for team in teams:
        participants_observed = team_participations[team]
        participants_expected = get_participants(team)
        participants_spurious = participants_expected - participants_observed
        participants_missing = participants_observed - participants_expected
        if len(participants_spurious) > 0:
            error = ConsistencyError("spurious", team, participants_spurious)
            errors.append(error)
        if len(participants_missing) > 0:
            error = ConsistencyError("missing", team, participants_missing)
            errors.append(error)

    # TODO:
    # - Check that the only participant of a *person* is the person.
    # - Check that merged people and teams do not appear in TeamParticipation.

    def get_repr(id):
        return "%s (%d)" % (people[id] if id in people else teams[id], id)

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
