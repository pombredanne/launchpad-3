# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'Snap',
    ]

import pytz
from storm.exceptions import IntegrityError
from storm.locals import (
    Bool,
    DateTime,
    Int,
    Reference,
    Storm,
    Unicode,
    )
from storm.store import Store
from zope.component import getUtility
from zope.interface import implementer

from lp.buildmaster.interfaces.processor import IProcessorSet
from lp.buildmaster.model.processor import Processor
from lp.registry.interfaces.role import IHasOwner
from lp.services.database.constants import (
    DEFAULT,
    UTC_NOW,
    )
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.services.features import getFeatureFlag
from lp.snappy.interfaces.snap import (
    DuplicateSnapName,
    ISnap,
    ISnapSet,
    SNAP_FEATURE_FLAG,
    SnapFeatureDisabled,
    SnapNotOwner,
    NoSourceForSnap,
    NoSuchSnap,
    )


def snap_modified(snap, event):
    """Update the date_last_modified property when a Snap is modified.

    This method is registered as a subscriber to `IObjectModifiedEvent`
    events on snap packages.
    """
    snap.date_last_modified = UTC_NOW


@implementer(ISnap, IHasOwner)
class Snap(Storm):
    """See `ISnap`."""

    __storm_table__ = 'Snap'

    id = Int(primary=True)

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=False)
    date_last_modified = DateTime(
        name='date_last_modified', tzinfo=pytz.UTC, allow_none=False)

    registrant_id = Int(name='registrant', allow_none=False)
    registrant = Reference(registrant_id, 'Person.id')

    owner_id = Int(name='owner', allow_none=False)
    owner = Reference(owner_id, 'Person.id')

    distro_series_id = Int(name='distro_series', allow_none=False)
    distro_series = Reference(distro_series_id, 'DistroSeries.id')

    name = Unicode(name='name', allow_none=False)

    description = Unicode(name='description', allow_none=True)

    branch_id = Int(name='branch', allow_none=True)
    branch = Reference(branch_id, 'Branch.id')

    git_repository_id = Int(name='git_repository', allow_none=True)
    git_repository = Reference(git_repository_id, 'GitRepository.id')

    git_path = Unicode(name='git_path', allow_none=True)

    require_virtualized = Bool(name='require_virtualized')

    def __init__(self, registrant, owner, distro_series, name,
                 description=None, branch=None, git_repository=None,
                 git_path=None, require_virtualized=True,
                 date_created=DEFAULT):
        """Construct a `Snap`."""
        if not getFeatureFlag(SNAP_FEATURE_FLAG):
            raise SnapFeatureDisabled
        super(Snap, self).__init__()
        self.registrant = registrant
        self.owner = owner
        self.distro_series = distro_series
        self.name = name
        self.description = description
        self.branch = branch
        self.git_repository = git_repository
        self.git_path = git_path
        self.require_virtualized = require_virtualized
        self.date_created = date_created
        self.date_last_modified = date_created

    def _getProcessors(self):
        return list(Store.of(self).find(
            Processor,
            Processor.id == SnapArch.processor_id,
            SnapArch.snap == self))

    def setProcessors(self, processors):
        """See `ISnap`."""
        enablements = dict(Store.of(self).find(
            (Processor, SnapArch),
            Processor.id == SnapArch.processor_id,
            SnapArch.snap == self))
        for proc in enablements:
            if proc not in processors:
                Store.of(self).remove(enablements[proc])
        for proc in processors:
            if proc not in self.processors:
                snaparch = SnapArch()
                snaparch.snap = self
                snaparch.processor = proc
                Store.of(self).add(snaparch)

    processors = property(_getProcessors, setProcessors)

    def requestBuild(self, requester, archive, distro_arch_series, pocket):
        """See `ISnap`."""
        raise NotImplementedError

    @property
    def builds(self):
        """See `ISnap`."""
        return []

    @property
    def _pending_states(self):
        """All the build states we consider pending (non-final)."""
        raise NotImplementedError

    @property
    def completed_builds(self):
        """See `ISnap`."""
        return []

    @property
    def pending_builds(self):
        """See `ISnap`."""
        return []

    def destroySelf(self):
        """See `ISnap`."""
        raise NotImplementedError


class SnapArch(Storm):
    """Link table to back `Snap.processors`."""

    __storm_table__ = 'SnapArch'
    __storm_primary__ = ('snap_id', 'processor_id')

    snap_id = Int(name='snap', allow_none=False)
    snap = Reference(snap_id, 'Snap.id')

    processor_id = Int(name='processor', allow_none=False)
    processor = Reference(processor_id, 'Processor.id')


@implementer(ISnapSet)
class SnapSet:
    """See `ISnapSet`."""

    def new(self, registrant, owner, distro_series, name, description=None,
            branch=None, git_repository=None, git_path=None,
            require_virtualized=True, processors=None, date_created=DEFAULT):
        """See `ISnapSet`."""
        if not registrant.inTeam(owner):
            if owner.is_team:
                raise SnapNotOwner(
                    "%s is not a member of %s." %
                    (registrant.displayname, owner.displayname))
            else:
                raise SnapNotOwner(
                    "%s cannot create snap packages owned by %s." %
                    (registrant.displayname, owner.displayname))

        if branch is None and git_repository is None:
            raise NoSourceForSnap

        store = IMasterStore(Snap)
        snap = Snap(
            registrant, owner, distro_series, name, description=description,
            branch=branch, git_repository=git_repository, git_path=git_path,
            require_virtualized=require_virtualized, date_created=date_created)
        store.add(snap)

        if processors is None:
            processors = [
                p for p in getUtility(IProcessorSet).getAll()
                if p.build_by_default]
        snap.setProcessors(processors)

        try:
            store.flush()
        except IntegrityError:
            raise DuplicateSnapName

        return snap

    def _getByName(self, owner, name):
        return IStore(Snap).find(
            Snap, Snap.owner == owner, Snap.name == name).one()

    def exists(self, owner, name):
        """See `ISnapSet`."""
        return self._getByName(owner, name) is not None

    def getByName(self, owner, name):
        """See `ISnapSet`."""
        snap = self._getByName(owner, name)
        if snap is None:
            raise NoSuchSnap(name)
        return snap

    def findByPerson(self, owner):
        """See `ISnapSet`."""
        return IStore(Snap).find(Snap, Snap.owner == owner)

    def empty_list(self):
        """See `ISnapSet`."""
        return []
