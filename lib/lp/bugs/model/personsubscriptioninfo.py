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

from lp.bugs.model.bugsubscription import BugSubscription
from lp.bugs.model.bug import Bug, BugMute
from lp.bugs.interfaces.personsubscriptioninfo import (
    IAbstractSubscriptionInfoCollection,
    IRealSubscriptionInfoCollection,
    IPersonSubscriptions,
    IRealSubscriptionInfo,
    IVirtualSubscriptionInfo,
    IVirtualSubscriptionInfoCollection,
    )
from lp.bugs.interfaces.structuralsubscription import (
    IStructuralSubscriptionTargetHelper)
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

    def __init__(self, person, administrated_team_ids):
        self.person = person
        self.administrated_team_ids = administrated_team_ids
        self.personal = []
        self.as_team_member = []
        self.as_team_admin = []
        self.count = 0

    def add(self, principal, bug, *args):
        if sameProxiedObjects(principal, self.person):
            collection = self.personal
        else:
            assert principal.isTeam(), (principal, self.person)
            if principal.id in self.administrated_team_ids:
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

    def __init__(self, person, administrated_team_ids):
        super(VirtualSubscriptionInfoCollection, self).__init__(
            person, administrated_team_ids)
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


class RealSubscriptionInfoCollection(
    AbstractSubscriptionInfoCollection):
    """Core functionality for Duplicate and Direct"""

    implements(IRealSubscriptionInfoCollection)

    def __init__(self, person, administrated_team_ids):
        super(RealSubscriptionInfoCollection, self).__init__(
            person, administrated_team_ids)
        self._principal_bug_to_infos = {}

    def _add_item_to_collection(self, collection, principal,
                                bug, subscription):
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


class PersonSubscriptions(object):
    """See `IPersonSubscriptions`."""

    implements(IPersonSubscriptions)

    def __init__(self, person, bug):
        self.loadSubscriptionsFor(person, bug)

    def reload(self):
        """See `IPersonSubscriptions`."""
        self.loadSubscriptionsFor(self.person, self.bug)

    def _getTaskPillar(self, bugtask):
        """Return a pillar for a given BugTask."""
        # There is no adaptor for ISourcePackage. Perhaps there
        # should be since the data model doesn't seem to prohibit it.
        # For now, we simply work around the problem.  It Would Be Nice If
        # there were a reliable generic way of getting the pillar for any
        # bugtarget, but we are not going to tackle that right now.
        if ISourcePackage.providedBy(bugtask.target):
            pillar = IStructuralSubscriptionTargetHelper(
                bugtask.target.distribution_sourcepackage).pillar
        else:
            pillar = IStructuralSubscriptionTargetHelper(
                bugtask.target).pillar
        return pillar

    def _getDirectAndDuplicateSubscriptions(self, person, bug):
        # Fetch all information for direct and duplicate
        # subscriptions (including indirect through team
        # membership) in a single query.
        store = Store.of(person)
        bug_id_options = [Bug.id == bug.id, Bug.duplicateofID == bug.id]
        info = store.find(
            (BugSubscription, Bug, Person),
            BugSubscription.bug == Bug.id,
            BugSubscription.person == Person.id,
            Or(*bug_id_options),
            TeamParticipation.personID == person.id,
            TeamParticipation.teamID == Person.id)

        direct = RealSubscriptionInfoCollection(
            self.person, self.administrated_team_ids)
        duplicates = RealSubscriptionInfoCollection(
            self.person, self.administrated_team_ids)
        bugs = set()
        for subscription, subscribed_bug, subscriber in info:
            bugs.add(subscribed_bug)
            if subscribed_bug.id != bug.id:
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
                pillar = self._getTaskPillar(task)
                duplicates.annotateBugTaskResponsibilities(
                    task, pillar,
                    pillar.security_contact, pillar.bug_supervisor)
                direct.annotateBugTaskResponsibilities(
                    task, pillar,
                    pillar.security_contact, pillar.bug_supervisor)
        return (direct, duplicates)

    def _isMuted(self, person, bug):
        store = Store.of(person)
        mutes = store.find(
            BugMute,
            BugMute.bug == bug,
            BugMute.person == person)
        is_muted = mutes.one()
        if is_muted is None:
            return False
        else:
            return True

    def loadSubscriptionsFor(self, person, bug):
        self.person = person
        self.administrated_team_ids = [
            team.id for team in person.getAdministratedTeams()]
        self.bug = bug

        # First get direct and duplicate real subscriptions.
        direct, from_duplicate = (
            self._getDirectAndDuplicateSubscriptions(person, bug))

        # Then get the 'muted' flag.
        self.muted = self._isMuted(person, bug)

        # Then get owner and assignee virtual subscriptions.
        as_owner = VirtualSubscriptionInfoCollection(
            self.person, self.administrated_team_ids)
        as_assignee = VirtualSubscriptionInfoCollection(
            self.person, self.administrated_team_ids)
        for bugtask in bug.bugtasks:
            pillar = self._getTaskPillar(bugtask)
            owner = pillar.owner
            if person.inTeam(owner) and pillar.bug_supervisor is None:
                as_owner.add(owner, bug, pillar, bugtask)
            assignee = bugtask.assignee
            if person.inTeam(assignee):
                as_assignee.add(assignee, bug, pillar, bugtask)
        self.count = 0
        for name, collection in (
            ('direct', direct), ('from_duplicate', from_duplicate),
            ('as_owner', as_owner), ('as_assignee', as_assignee)):
            self.count += collection.count
            setattr(self, name, collection)

    def getDataForClient(self):
        reference_map = {}
        dest = {}

        def get_id(obj):
            "Get an id for the object so it can be shared."
            # We could leverage .id for most objects, but not pillars.
            identifier = reference_map.get(obj)
            if identifier is None:
                identifier = 'subscription-cache-reference-%d' % (
                    len(reference_map),)
                reference_map[obj] = identifier
                dest[identifier] = obj
            return identifier

        def virtual_sub_data(info):
            return {
                'principal': get_id(info.principal),
                'bug': get_id(info.bug),
                'pillar': get_id(info.pillar),
                # We won't add bugtasks yet unless we need them.
                }

        def real_sub_data(info):
            return {
                'principal': get_id(info.principal),
                'bug': get_id(info.bug),
                'subscription': get_id(info.subscription),
                'principal_is_reporter': info.principal_is_reporter,
                # We won't add bugtasks yet unless we need them.
                'security_contact_pillars': sorted(set(
                    get_id(d['pillar']) for d
                    in info.security_contact_tasks)),
                'bug_supervisor_pillars': sorted(set(
                    get_id(d['pillar']) for d
                    in info.bug_supervisor_tasks)),
                }
        direct = {}
        from_duplicate = {}
        as_owner = {} # This is an owner of a pillar with no bug supervisor.
        as_assignee = {}
        subscription_data = {
            'direct': direct,
            'from_duplicate': from_duplicate,
            'as_owner': as_owner,
            'as_assignee': as_assignee,
            'count': self.count,
            'muted': self.muted,
            'bug_id': self.bug.id,
            }
        for category, collection in ((as_owner, self.as_owner),
                                 (as_assignee, self.as_assignee)):
            for name, inner in (
                ('personal', collection.personal),
                ('as_team_admin', collection.as_team_admin),
                ('as_team_member', collection.as_team_member)):
                category[name] = [virtual_sub_data(info) for info in inner]
            category['count'] = collection.count
        for category, collection in ((direct, self.direct),
                                     (from_duplicate, self.from_duplicate)):
            for name, inner in (
                ('personal', collection.personal),
                ('as_team_admin', collection.as_team_admin),
                ('as_team_member', collection.as_team_member)):
                category[name] = [real_sub_data(info) for info in inner]
            category['count'] = collection.count
        return subscription_data, dest
