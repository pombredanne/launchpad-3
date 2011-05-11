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

    def policySpecificChecks(self, **args):
        raise AssertionError("Must be implemented by sub-class.")


class FromExistingOverridePolicy(BaseOverridePolicy):
    """Override policy that returns the SPN, component and section for
    the latest published source publication, or the BPN, DAS, component,
    section and priority for the latest published binary publication.
    """

    def findSourceOverrides(self, archive, distroseries, pocket, spns):
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

    def findBinaryOverrides(self, archive, distroseries, pocket, binaries):
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

    def policySpecificChecks(self, archive, distroseries, pocket,
                             sources=None, binaries=None):
        if sources is not None and binaries is not None:
            raise AssertionError(
                "Can not check for both source and binary overrides "
                "together.")
        if sources:
            return self.findSourceOverrides(
                archive, distroseries, pocket, sources)
        if binaries:
            return self.findBinaryOverrides(
                archive, distroseries, pocket, binaries)


class UnknownOverridePolicy(BaseOverridePolicy):
    """Override policy that assumes everything passed in doesn't exist, so
    returns the defaults.
    """
    
    def __init__(self):
        self.default_component = 'universe'

    def policySpecificChecks(self, archive, distroseries, pocket,
                             sources=None, binaries=None):
        if sources is not None and binaries is not None:
            raise AssertionError(
                "Can not check for both source and binary overrides "
                "together.")
        if sources:
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
        if binaries:
            store = IStore(BinaryPackageName)
            store.find(
                BinaryPackageName.id.is_in(bpn.id for bpn, ign in binaries))
            if archive.default_component:
                self.default_component = archive.default_component
            overrides = []
            for binary, archtag in binaries:
                overrides.append((
                    store.get(BinaryPackageName, binary.id), None,
                    self.default_component, None, None))
            return overrides


class UbuntuOverridePolicy(FromExistingOverridePolicy,
                           UnknownOverridePolicy):

    def policySpecificChecks(self, archive, distroseries, pocket,
                             sources=None, binaries=None):
        overrides = FromExistingOverridePolicy.policySpecificChecks(
            archive, distroseries, pocket, sources=sources,
            binaries=binaries)
        if overrides is []:
            overrides = UnknownOverridePolicy.policySpecificChecks(
                archive, distroseries, pocket, sources=sources,
                binaries=binaries)
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
    IStore(Component).find(
        Component, Component.id.is_in(row[2] for row in rows))
    IStore(Section).find(
        Section, Section.id.is_in(row[3] for row in rows))


def binary_eager_load(rows):
    IStore(Component).find(
        Component, Component.id.is_in(row[3] for row in rows))
    IStore(Section).find(
        Section, Section.id.is_in(row[4] for row in rows))


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
