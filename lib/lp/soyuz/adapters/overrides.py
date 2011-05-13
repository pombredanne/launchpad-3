# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generic Override Policy classes.
"""

__metaclass__ = type

__all__ = [
    'FromExistingOverridePolicy',
    'UbuntuOverridePolicy',
    'UnknownOverridePolicy',
    ]


from storm.expr import (
    And,
    Desc,
    Or,
    SQL,
    )

from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.interfaces.lpstorm import IStore
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.services.database import bulk
from lp.soyuz.interfaces.publishing import active_publishing_status
from lp.soyuz.model.binarypackagename import BinaryPackageName
from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease
from lp.soyuz.model.component import Component
from lp.soyuz.model.distroarchseries import DistroArchSeries
from lp.soyuz.model.publishing import (
    BinaryPackagePublishingHistory,
    SourcePackagePublishingHistory,
    )
from lp.soyuz.model.section import Section
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease


class BaseOverridePolicy:

    def calculateSourceOverrides(self, archive, distroseries, pocket,
                                 sources):
        raise NotImplementedError()

    def calculateBinaryOverrides(self, archive, distroseries, pocket,
                                 binaries):
        raise NotImplementedError()


class FromExistingOverridePolicy(BaseOverridePolicy):
    """Override policy that only searches for existing publications.
    
    Override policy that returns the SourcePackageName, component and
    section for the latest published source publication, or the
    BinaryPackageName, DistroArchSeries, component, section and priority
    for the latest published binary publication.
    """

    def calculateSourceOverrides(self, archive, distroseries, pocket, spns):
        store = IStore(SourcePackagePublishingHistory)
        already_published = DecoratedResultSet(
            store.find(
                (SQL("""DISTINCT ON (
                    SourcePackageRelease.sourcepackagename) 0 AS ignore"""),
                    SourcePackageRelease.sourcepackagenameID,
                    SourcePackagePublishingHistory.componentID,
                    SourcePackagePublishingHistory.sectionID),
                SourcePackagePublishingHistory.pocket == pocket,
                SourcePackagePublishingHistory.archiveID == archive.id,
                SourcePackagePublishingHistory.distroseriesID ==
                    distroseries.id,
                SourcePackagePublishingHistory.status.is_in(
                    active_publishing_status),
                SourcePackageRelease.id ==
                    SourcePackagePublishingHistory.sourcepackagereleaseID,
                SourcePackageRelease.sourcepackagenameID.is_in(
                    spn.id for spn in spns)).order_by(
                        SourcePackageRelease.sourcepackagenameID,
                        Desc(SourcePackagePublishingHistory.datecreated),
                        Desc(SourcePackagePublishingHistory.id)),
            source_resolve_ids, pre_iter_hook=source_eager_load)
        return list(already_published)

    def calculateBinaryOverrides(self, archive, distroseries, pocket,
                                 binaries):
        store = IStore(BinaryPackagePublishingHistory)
        expanded = calculate_target_das(distroseries, binaries)
        candidates = (
            make_package_condition(archive, das, bpn)
            for bpn, das in expanded)
        already_published = DecoratedResultSet(
            store.find(
                (SQL("""DISTINCT ON (
                    BinaryPackagePublishingHistory.distroarchseries,
                    BinaryPackageRelease.binarypackagename) 0
                    AS ignore"""),
                    BinaryPackageRelease.binarypackagenameID,
                    BinaryPackagePublishingHistory.distroarchseriesID,
                    BinaryPackagePublishingHistory.componentID,
                    BinaryPackagePublishingHistory.sectionID,
                    BinaryPackagePublishingHistory.priority),
                BinaryPackagePublishingHistory.pocket == pocket,
                BinaryPackagePublishingHistory.status.is_in(
                    active_publishing_status),
                BinaryPackageRelease.id ==
                    BinaryPackagePublishingHistory.binarypackagereleaseID,
                Or(*candidates)),
            binary_resolve_ids, pre_iter_hook=binary_eager_load)
        return list(already_published)


class UnknownOverridePolicy(BaseOverridePolicy):
    """Override policy that returns defaults.
    
    Override policy that assumes everything passed in doesn't exist, so
    returns the defaults.
    """
    
    def __init__(self):
        self.default_component = 'universe'

    def calculateSourceOverrides(self, archive, distroseries, pocket,
                                 sources):
        store = IStore(SourcePackageName)
        store.find(SourcePackageName.id.is_in(spn.id for spn in sources))
        if archive.default_component:
            self.default_component = archive.default_component
        overrides = []
        for source in sources:
            overrides.append((
                store.get(SourcePackageName, source.id),
                self.default_component, None))
        return overrides

    def calculateBinaryOverrides(self, archive, distroseries, pocket,
                                 binaries):
        store = IStore(BinaryPackageName)
        store.find(
            BinaryPackageName.id.is_in(bpn.id for bpn, ign in binaries))
        if archive.default_component:
            self.default_component = archive.default_component
        overrides = []
        for binary, das in calculate_target_das(distroseries, binaries):
            overrides.append((
                store.get(BinaryPackageName, binary.id), das,
                self.default_component, None, None))
        return overrides


class UbuntuOverridePolicy(FromExistingOverridePolicy,
                           UnknownOverridePolicy):
    """Override policy for Ubuntu.
    
    An override policy that incorporates both the from existing policy 
    and the unknown policy.
    """

    def calculateSourceOverrides(self, archive, distroseries, pocket,
                                 sources):
        total = set(sources)
        overrides = FromExistingOverridePolicy.calculateSourceOverrides(
            self, archive, distroseries, pocket, sources)
        existing = set(override[0] for override in overrides)
        missing = total.difference(existing)
        if missing:
            unknown = UnknownOverridePolicy.calculateSourceOverrides(
                self, archive, distroseries, pocket, missing)
            overrides.extend(unknown)
        return overrides

    def calculateBinaryOverrides(self, archive, distroseries, pocket,
                                 binaries):
        total = set(binaries)
        overrides = FromExistingOverridePolicy.calculateBinaryOverrides(
            self, archive, distroseries, pocket, binaries)
        existing = set((
            overide[0], overide[1].architecturetag)
                for overide in overrides)
        missing = total.difference(existing)
        if missing:
            unknown = UnknownOverridePolicy.calculateBinaryOverrides(
                self, archive, distroseries, pocket, missing)
            overrides.extend(unknown)
        return overrides


def calculate_target_das(distroseries, binaries):
    archs = list(distroseries.enabled_architectures)
    arch_map = dict((arch.architecturetag, arch) for arch in archs)

    with_das = []
    for bpn, archtag in binaries:
        if archtag is not None:
            with_das.append((bpn, arch_map.get(archtag)))
        else:
            with_das.append((bpn, distroseries.nominatedarchindep))
    return with_das


def make_package_condition(archive, das, bpn):
    return And(
        BinaryPackagePublishingHistory.archiveID == archive.id,
        BinaryPackagePublishingHistory.distroarchseriesID == das.id,
        BinaryPackageRelease.binarypackagenameID ==
            bpn.id)


def source_eager_load(rows):
    bulk.load(Component, (row[2] for row in rows))
    bulk.load(Section, (row[3] for row in rows))


def binary_eager_load(rows):
    bulk.load(Component, (row[3] for row in rows))
    bulk.load(Section, (row[4] for row in rows))


def source_resolve_ids(row):
    store = IStore(SourcePackagePublishingHistory)
    return (
        store.get(SourcePackageName, row[1]), store.get(Component, row[2]),
        store.get(Section, row[3]))


def binary_resolve_ids(row):
    store = IStore(BinaryPackagePublishingHistory)
    return (
        store.get(BinaryPackageName, row[1]),
        store.get(DistroArchSeries, row[2]),
        store.get(Component, row[3]), store.get(Section, row[4]), row[5])
