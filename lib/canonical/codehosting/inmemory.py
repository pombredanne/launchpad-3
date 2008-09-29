# Copyright 2008 Canonical Ltd.  All rights reserved.

"""In-memory doubles of core codehosting objects."""

__metaclass__ = type
__all__ = [
    'FakeLaunchpadFrontend',
    ]

from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces.branch import BranchType
from canonical.launchpad.testing import ObjectFactory
from canonical.launchpad.xmlrpc.codehosting import datetime_from_tuple
from canonical.launchpad.xmlrpc import faults


class FakeBranch:

    def __init__(self, branch_id, branch_type, url=None, unique_name=None,
                 stacked_on=None, private=False):
        self.id = branch_id
        self.branch_type = branch_type
        self.last_mirror_attempt = None
        self.last_mirrored = None
        self.last_mirrored_id = None
        self.next_mirror_time = None
        self.url = url
        self.unique_name = unique_name
        self.mirror_failures = 0
        self.stacked_on = None
        self.mirror_status_message = None
        self.stacked_on = stacked_on
        self.private = private

    @classmethod
    def _get_store(cls):
        # ZOMG!
        class FakeStore:
            def find(store, cls, **kwargs):
                branch_id = kwargs.pop('id')
                assert len(kwargs) == 1, (
                    'Expected only id and one other. Got %r' % kwargs)
                attribute = kwargs.keys()[0]
                expected_value = kwargs[attribute]
                branch = cls._branch_source.getBranchSet().get(branch_id)
                if branch is None:
                    return None
                if expected_value is getattr(branch, attribute):
                    return branch
                return None
        return FakeStore()

    def requestMirror(self):
        self.next_mirror_time = UTC_NOW


class ObjectSet:

    def __init__(self):
        self._objects = {}

    def _add(self, db_object):
        self._objects[db_object.id] = db_object

    def __iter__(self):
        return self._objects.itervalues()

    def get(self, id):
        try:
            return self._objects[id]
        except KeyError:
            return None

    def getByName(self, name):
        for obj in self:
            if obj.name == name:
                return obj


class FakeScriptActivity:

    def __init__(self, name, hostname, date_started, date_completed):
        self.id = self.name = name
        self.hostname = hostname
        self.date_started = datetime_from_tuple(date_started)
        self.date_completed = datetime_from_tuple(date_completed)


class FakeObjectFactory(ObjectFactory):

    def __init__(self, branch_source):
        super(FakeObjectFactory, self).__init__()
        self._branch_source = FakeBranch._branch_source = branch_source

    def makeBranch(self, branch_type=None, stacked_on=None, private=False):
        branch_id = self.getUniqueInteger()
        if branch_type == BranchType.MIRRORED:
            url = self.getUniqueURL()
        else:
            url = None
        branch = FakeBranch(
            branch_id, branch_type, url=url,
            unique_name=self.getUniqueString(), stacked_on=stacked_on)
        self._branch_source.getBranchSet()._add(branch)
        return branch


class FakeBranchPuller:

    def __init__(self, branch_set, script_activity_set):
        self._branch_set = branch_set
        self._script_activity_set = script_activity_set

    def _getBranchPullInfo(self, branch):
        return branch

    def getBranchPullQueue(self, branch_type):
        queue = []
        branch_type = BranchType.items[branch_type]
        for branch in self._branch_set:
            if (branch.branch_type == branch_type
                and branch.next_mirror_time < UTC_NOW):
                queue.append(branch)
        return queue

    def startMirroring(self, branch_id):
        branch = self._branch_set.get(branch_id)
        if branch is None:
            return faults.NoBranchWithID(branch_id)
        branch.last_mirror_attempt = UTC_NOW
        branch.next_mirror_time = None
        return True

    def mirrorComplete(self, branch_id, last_revision_id):
        branch = self._branch_set.get(branch_id)
        if branch is None:
            return faults.NoBranchWithID(branch_id)
        branch.last_mirrored_id = last_revision_id
        branch.last_mirrored = UTC_NOW
        branch.mirror_failures = 0
        for stacked_branch in self._branch_set:
            if stacked_branch.stacked_on is branch:
                stacked_branch.requestMirror()
        return True

    def mirrorFailed(self, branch_id, reason):
        branch = self._branch_set.get(branch_id)
        if branch is None:
            return faults.NoBranchWithID(branch_id)
        branch.mirror_failures += 1
        branch.mirror_status_message = reason
        return True

    def recordSuccess(self, name, hostname, date_started, date_completed):
        self._script_activity_set._add(
            FakeScriptActivity(name, hostname, date_started, date_completed))
        return True

    def setStackedOn(self, branch_id, stacked_on_location):
        branch = self._branch_set.get(branch_id)
        if branch is None:
            return faults.NoBranchWithID(branch_id)
        stacked_on_location = stacked_on_location.rstrip('/')
        for stacked_on_branch in self._branch_set:
            if stacked_on_location == stacked_on_branch.url:
                branch.stacked_on = stacked_on_branch
                break
            if stacked_on_location == '/' + stacked_on_branch.unique_name:
                branch.stacked_on = stacked_on_branch
                break
        else:
            return faults.NoSuchBranch(stacked_on_location)
        return True


class FakeLaunchpadFrontend:

    def __init__(self):
        self._branch_set = ObjectSet()
        self._script_activity_set = ObjectSet()
        self._puller = FakeBranchPuller(
            self._branch_set, self._script_activity_set)
        self._factory = FakeObjectFactory(self)

    def getPullerEndpoint(self):
        return self._puller

    def getLaunchpadObjectFactory(self):
        return self._factory

    def getBranchSet(self):
        return self._branch_set

    def getLastActivity(self, activity_name):
        return self._script_activity_set.getByName(activity_name)
