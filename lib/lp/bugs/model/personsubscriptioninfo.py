# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'PersonSubscriptions',
    ]

from storm.expr import Or
from storm.store import Store
from zope.interface import implements
from zope.proxy import sameProxiedObjects

from lp.bugs.enum import BugNotificationLevel
from lp.bugs.model.bugsubscription import BugSubscription
from lp.bugs.model.bug import Bug
from lp.bugs.interfaces.personsubscriptioninfo import (
    IAbstractSubscriptionInfoCollection,
    IDirectSubscriptionInfoCollection,
    IDuplicateSubscriptionInfoCollection,
    IPersonSubscriptions,
    IRealSubscriptionInfo,
    IVirtualSubscriptionInfo,
    IVirtualSubscriptionInfoCollection,
    )
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.registry.model.person import Person
from lp.registry.model.teammembership import TeamParticipation


class RealSubscriptionInfo:
    """See `IRealSubscriptionInfo`"""

    implements(IRealSubscriptionInfo)

    def __init__(self, principal, bug, subscription):
        self.principal = principal
        self.bug = bug
        self.subscription = subscription
        self.principal_is_reporter = False
        self.security_contact_tasks = []
        self.bug_supervisor_tasks = []


class VirtualSubscriptionInfo:
    """See `IVirtualSubscriptionInfo`"""

    implements(IVirtualSubscriptionInfo)

    def __init__(self, principal, bug, pillar):
        self.principal = principal
        self.bug = bug
        self.pillar = pillar
        self.tasks = []


class AbstractSubscriptionInfoCollection:
    """See `IAbstractSubscriptionInfoCollection`"""

    implements(IAbstractSubscriptionInfoCollection)

    def __init__(self, person, is_team_admin):
        self.person = person
        self._is_team_admin = is_team_admin
        self._personal = []
        self.as_team_member = []
        self.as_team_admin = []
        self.count = 0

    @property
    def personal(self):
        return self._personal

    def add(self, principal, bug, *args):
        if sameProxiedObjects(principal, self.person):
            collection = self._personal
        else:
            assert principal.isTeam(), (principal, self.person)
            if self._is_team_admin(principal):
                collection = self.as_team_admin
            else:
                collection = self.as_team_member
        self._add_item_to_collection(
            collection, principal, bug, *args)

    def _add_item_to_collection(self, *args):
        raise NotImplementedError('Programmer error: use a subclass')


class VirtualSubscriptionInfoCollection(AbstractSubscriptionInfoCollection):
    """See `IVirtualSubscriptionInfoCollection`"""

    implements(IVirtualSubscriptionInfoCollection)

    def __init__(self, person, is_team_admin):
        super(VirtualSubscriptionInfoCollection, self).__init__(
            person, is_team_admin)
        self._principal_pillar_to_info = {}

    def _add_item_to_collection(self,
                                collection, principal, bug, pillar, task):
        key = (principal, pillar)
        info = self._principal_pillar_to_info.get(key)
        if info is None:
            info = VirtualSubscriptionInfo(principal, bug, pillar)
            collection.append(info)
            self.count += 1
        info.tasks.append(task)


class AbstractRealSubscriptionInfoCollection(
    AbstractSubscriptionInfoCollection):
    """Core functionality for Duplicate and Direct"""

    def __init__(self, person, is_team_admin):
        super(AbstractRealSubscriptionInfoCollection, self).__init__(
            person, is_team_admin)
        self._principal_bug_to_infos = {}

    def _add_item_to_collection(self, collection, principal, bug, subscription):
        info = RealSubscriptionInfo(principal, bug, subscription)
        key = (principal, bug)
        infos = self._principal_bug_to_infos.get(key)
        if infos is None:
            infos = self._principal_bug_to_infos[key] = []
        infos.append(info)
        collection.append(info)
        self.count += 1

    def annotateReporter(self, bug, principal):
        key = (principal, bug)
        infos = self._principal_bug_to_infos.get(key)
        if infos is not None:
            for info in infos:
                info.principal_is_reporter = True

    def annotateBugTaskResponsibilities(
        self, bugtask, pillar, security_contact, bug_supervisor):
        for principal, collection_name in (
            (security_contact, 'security_contact_tasks'),
            (bug_supervisor, 'bug_supervisor_tasks')):
            if principal is not None:
                key = (principal, bugtask.bug)
                infos = self._principal_bug_to_infos.get(key)
                if infos is not None:
                    value = {'task': bugtask, 'pillar': pillar}
                    for info in infos:
                        getattr(info, collection_name).append(value)


class DirectSubscriptionInfoCollection(
    AbstractRealSubscriptionInfoCollection):
    """See `IDirectSubscriptionInfoCollection`."""

    implements(IDirectSubscriptionInfoCollection)

    @property
    def personal(self):
        if self._personal:
            assert len(self._personal) == 1
            return self._personal[0]
        return None


class DuplicateSubscriptionInfoCollection(
    AbstractRealSubscriptionInfoCollection):
    """See `IDuplicateSubscriptionInfoCollection`."""

    implements(IDuplicateSubscriptionInfoCollection)


class PersonSubscriptions(object):
    """See `IPersonSubscriptions`."""

    implements(IPersonSubscriptions)

    def __init__(self, person, bug):
        self.loadSubscriptionsFor(person, bug)

    def reload(self):
        """See `IPersonSubscriptions`."""
        self.loadSubscriptionsFor(self.person, self.bug)

    def _getDirectAndDuplicateSubscriptions(self, person, bug):
        # Fetch all information for direct and duplicate
        # subscriptions (including indirect through team
        # membership) in a single query.
        store = Store.of(person)
        bug_id_options = [Bug.id == bug.id, Bug.duplicateofID == bug.id]
        if bug.duplicateof is not None:
            bug_id_options.append(Bug.id == bug.duplicateof.id)
        info = store.find(
            (BugSubscription, Bug, Person),
            BugSubscription.bug == Bug.id,
            BugSubscription.person == Person.id,
            Or(*bug_id_options),
            TeamParticipation.personID == person.id,
            TeamParticipation.teamID == Person.id)

        direct = DirectSubscriptionInfoCollection(
            self.person, self.is_team_admin)
        duplicates = DuplicateSubscriptionInfoCollection(
            self.person, self.is_team_admin)
        bugs = set()
        for subscription, subscribed_bug, subscriber in info:
            bugs.add(subscribed_bug)
            if subscribed_bug != bug:
                # This is a subscription through a duplicate.
                collection = duplicates
            else:
                # This is a direct subscription.
                collection = direct
            collection.add(
                subscriber, subscribed_bug, subscription)
        for bug in bugs:
            # indicate the reporter, bug_supervisor, and security_contact
            duplicates.annotateReporter(bug, bug.owner)
            direct.annotateReporter(bug, bug.owner)
            for task in bug.bugtasks:
                # get security_contact and bug_supervisor
                pillar = self._get_pillar(task.target)
                duplicates.annotateBugTaskResponsibilities(
                    task, pillar,
                    pillar.security_contact, pillar.bug_supervisor)
                direct.annotateBugTaskResponsibilities(
                    task, pillar,
                    pillar.security_contact, pillar.bug_supervisor)
        return (direct, duplicates)

    def _get_pillar(self, target):
        if IProductSeries.providedBy(target):
            pillar = target.product
        elif IDistroSeries.providedBy(target):
            pillar = target.distribution
        elif ISourcePackage.providedBy(target):
            pillar = target.distribution
        else:
            pillar = target
        return pillar

    def is_team_admin(self, team):
        answer = self._is_team_admin.get(team)
        if answer is None:
            answer = False
            admins = team.adminmembers
            for admin in admins:
                if self.person.inTeam(admin):
                    answer = True
                    break
            self._is_team_admin[team] = answer
        return answer

    def loadSubscriptionsFor(self, person, bug):
        self.person = person
        self.bug = bug
        self._is_team_admin = {} # team to bool answer

        # First get direct and duplicate real subscriptions.
        direct, from_duplicate = (
            self._getDirectAndDuplicateSubscriptions(person, bug))

        # Then get owner and assignee virtual subscriptions.
        as_owner = VirtualSubscriptionInfoCollection(
            self.person, self.is_team_admin)
        as_assignee = VirtualSubscriptionInfoCollection(
            self.person, self.is_team_admin)
        for bugtask in bug.bugtasks:
            pillar = self._get_pillar(bugtask.target)
            owner = pillar.owner
            if person.inTeam(owner) and pillar.bug_supervisor is None:
                as_owner.add(owner, bug, pillar, bugtask)
            assignee = bugtask.assignee
            if person.inTeam(assignee):
                as_assignee.add(assignee, bug, pillar, bugtask)
        self.muted = (direct.personal is not None
                      and direct.personal.subscription.bug_notification_level
                          == BugNotificationLevel.NOTHING)
        self.count = 0
        for name, collection in (
            ('direct', direct), ('from_duplicate', from_duplicate),
            ('as_owner', as_owner), ('as_assignee', as_assignee)):
            self.count += collection.count
            setattr(self, name, collection if collection.count > 0 else None)

