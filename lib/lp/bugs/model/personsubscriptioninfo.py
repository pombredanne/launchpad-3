# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'PersonSubscriptionInfo',
    'PersonSubscriptionInfoSet',
    ]

from storm.expr import Or
from storm.store import Store
from zope.interface import implements

from lp.bugs.model.bugsubscription import BugSubscription
from lp.bugs.model.bug import Bug
from lp.registry.model.person import Person
from lp.registry.model.teammembership import TeamParticipation
from lp.bugs.interfaces.personsubscriptioninfo import (
    IPersonSubscriptionInfo,
    IPersonSubscriptionInfoSet,
    PersonSubscriptionType,
    )

class PersonSubscriptionInfo(object):
    """See `IPersonSubscriptionInfo`."""

    implements(IPersonSubscriptionInfo)

    def __init__(self, person, bug,
                 subscription_type=PersonSubscriptionType.DIRECT,
                 duplicates=None, as_team_member=None, as_team_admin=None,
                 owner_for=None, supervisor_for=None):

        self.subscription_type = subscription_type

        self.bug = bug
        self.person = person
        self.personally = False

        # For duplicates.
        self.duplicates = duplicates

        # For supervisor.
        self.supervisor_for = supervisor_for
        self.owner_for = owner_for

        # For all types if subscription is through team membership.
        self.as_team_member = as_team_member
        self.as_team_admin = as_team_admin

    def addDuplicate(self, bug):
        assert self.subscription_type == PersonSubscriptionType.DUPLICATE, (
            "Subscription type is %s instead of DUPLICATE." % (
                self.subscription_type))
        assert bug.duplicateof == self.bug
        if self.duplicates is None:
            self.duplicates = set([bug])
        else:
            self.duplicates.add(bug)

    def _addAdmin(self, subscriber):
        if self.as_team_admin is None:
            self.as_team_admin = set([subscriber])
        else:
            self.as_team_admin.add(subscriber)

    def _addMember(self, subscriber):
        if self.as_team_member is None:
            self.as_team_member = set([subscriber])
        else:
            self.as_team_member.add(subscriber)

    def addSubscriber(self, subscriber, subscribed_bug=None):
        if subscriber.is_team:
            is_admin = False
            admins = subscriber.adminmembers
            for admin in admins:
                if self.person.inTeam(admin):
                    self._addAdmin(subscriber)
                    is_admin = True
                    break

            if not is_admin:
                self._addMember(subscriber)
        else:
            assert self.person == subscriber, (
                "Non-team subscription for a different person.")
            self.personally = True

    def addSupervisedTarget(self, target):
        assert self.subscription_type == PersonSubscriptionType.SUPERVISOR
        if self.supervisor_for is None:
            self.supervisor_for = set([target])
        else:
            self.supervisor_for.add(target)

    def addOwnedTarget(self, target):
        assert self.subscription_type == PersonSubscriptionType.SUPERVISOR
        if self.owner_for is None:
            self.owner_for = set([target])
        else:
            self.owner_for.add(target)


class PersonSubscriptionInfoSet(object):
    """See `IPersonSubscriptionInfoSet`."""

    implements(IPersonSubscriptionInfoSet)

    def __init__(self):
        self.direct_subscriptions = None
        self.duplicate_subscriptions = None
        self.supervisor_subscriptions = None

    def _getDirectAndDuplicateSubscriptions(self, person, bug):
        # Fetch all information for direct and duplicate
        # subscriptions (including indirect through team
        # membership) in a single query.
        store = Store.of(person)
        info = store.find(
            (BugSubscription, Bug, Person),
            BugSubscription.bug == Bug.id,
            BugSubscription.person == Person.id,
            Or(Bug.id == bug.id,
               Bug.duplicateofID == bug.id),
            TeamParticipation.personID == person.id,
            TeamParticipation.teamID == Person.id)

        has_direct = False
        direct = PersonSubscriptionInfo(
            person, bug, PersonSubscriptionType.DIRECT)
        has_duplicates = False
        duplicates = PersonSubscriptionInfo(
            person, bug, PersonSubscriptionType.DUPLICATE)
        for subscription, subscribed_bug, subscriber in info:
            if subscribed_bug != bug:
                # This is a subscription through a duplicate.
                duplicates.addDuplicate(subscribed_bug)
                duplicates.addSubscriber(subscriber, subscribed_bug)
                has_duplicates = True
            else:
                # This is a direct subscription.
                direct.addSubscriber(subscriber)
                has_direct = True
        if not has_duplicates:
            duplicates = None

        if not has_direct:
            direct = None

        return (direct, duplicates)

    def loadSubscriptionsFor(self, person, bug):
        # Categorise all subscriptions into three types:
        # direct, through duplicates, as supervisor.

        # First get direct and duplicate subscriptions.
        direct, duplicate = self._getDirectAndDuplicateSubscriptions(
            person, bug)
        self.direct_subscriptions = direct
        self.duplicate_subscriptions = duplicate

        # Then get supervisor subscriptions.
        has_supervisor = False
        supervisor = PersonSubscriptionInfo(
            person, bug, PersonSubscriptionType.SUPERVISOR)
        for bugtask in bug.bugtasks:
            target = bugtask.target
            is_owner = person.inTeam(target.owner)
            is_supervisor = person.inTeam(target.bug_supervisor)
            # If person is a bug supervisor, or there is no
            # supervisor, but person is the team owner.
            if (is_supervisor or
                (is_owner and target.bug_supervisor is None)):
                # Owner can change the supervisor.
                if is_owner:
                    supervisor.addOwnedTarget(target)
                    supervisor.addSubscriber(target.owner)
                else:
                    supervisor.addSupervisedTarget(target)
                    supervisor.addSubscriber(target.bug_supervisor)
                has_supervisor = True
        if not has_supervisor:
            supervisor = None
        self.supervisor_subscriptions = supervisor

