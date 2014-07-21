# Copyright 2011-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generic Override Policy classes."""

__metaclass__ = type

__all__ = [
    'BinaryOverride',
    'FromExistingOverridePolicy',
    'IBinaryOverride',
    'ISourceOverride',
    'SourceOverride',
    'UbuntuOverridePolicy',
    'UnknownOverridePolicy',
    ]


from storm.expr import (
    And,
    Desc,
    Or,
    )
from zope.component import getUtility
from zope.interface import (
    Attribute,
    implements,
    Interface,
    )
from zope.security.proxy import isinstance as zope_isinstance

from lp.registry.model.sourcepackagename import SourcePackageName
from lp.services.database import bulk
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.interfaces import IStore
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.interfaces.component import IComponentSet
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


class IOverride(Interface):
    """Override data class.

    This class represents all the basic overridable data on a publication.
    """

    component = Attribute("The IComponent override")
    section = Attribute("The ISection override")
    version = Attribute("The exclusive lower version limit")


class ISourceOverride(IOverride):
    """Source-specific overrides on a publication."""

    pass


class IBinaryOverride(IOverride):
    """Binary-specific overrides on a publication."""

    binary_package_name = Attribute(
        "The IBinaryPackageName that's being overridden")
    architecture_tag = Attribute(
        "The architecture tag for the publication")
    priority = Attribute(
        "The PackagePublishingPriority that's being overridden")
    phased_update_percentage = Attribute(
        "The phased update percentage that's being overridden")


class Override:
    """See `IOverride`."""

    def __init__(self, component=None, section=None, version=None):
        self.component = component
        self.section = section
        self.version = version

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        # Prevent people getting very confused with these new classes,
        # should their instances ever be put in a dict or set.
        raise NotImplementedError(
            "%s objects are not hashable." % self.__class__.__name__)


class SourceOverride(Override):
    """See `ISourceOverride`."""
    implements(ISourceOverride)

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__ and
            self.component == other.component and
            self.section == other.section and
            self.version == other.version)

    def __repr__(self):
        return (
            "<%s at %x component=%r section=%r version=%r>" %
            (self.__class__.__name__, id(self), self.component, self.section,
             self.version))


class BinaryOverride(Override):
    """See `IBinaryOverride`."""
    implements(IBinaryOverride)

    def __init__(self, component=None, section=None, priority=None,
                 phased_update_percentage=None, version=None):
        super(BinaryOverride, self).__init__(
            component=component, section=section, version=version)
        self.priority = priority
        self.phased_update_percentage = phased_update_percentage

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__ and
            self.component == other.component and
            self.section == other.section and
            self.priority == other.priority and
            self.phased_update_percentage == other.phased_update_percentage and
            self.version == other.version)

    def __repr__(self):
        return (
            "<%s at %x component=%r section=%r priority=%r "
            "phased_update_percentage=%r version=%r>" %
            (self.__class__.__name__, id(self), self.component, self.section,
             self.priority, self.phased_update_percentage, self.version))


class IOverridePolicy(Interface):
    """Override policy.

    An override policy returns overrides suitable for the given archive,
    distroseries, pocket for source or binary publications.

    For example, an implementation might allow existing publications to
    keep the same component and section as their ancestor publications.
    """

    phased_update_percentage = Attribute(
        "The phased update percentage to apply to binary publications.")

    def calculateSourceOverrides(archive, distroseries, pocket, sources):
        """Calculate source overrides.

        :param archive: The target `IArchive`.
        :param distroseries: The target `IDistroSeries`.
        :param pocket: The target `PackagePublishingPocket`.
        :param sources: A dict mapping `ISourcePackageName`s to
            `ISourceOverride`s.

        :return: A dict mapping `ISourcePackageName`s to `ISourceOverride`s.
        """
        pass

    def calculateBinaryOverrides(archive, distroseries, pocket, binaries):
        """Calculate binary overrides.

        :param archive: The target `IArchive`.
        :param distroseries: The target `IDistroSeries`.
        :param pocket: The target `PackagePublishingPocket`.
        :param binaries: A dict mapping (`IBinaryPackageName`, architecturetag)
            pairs to `IBinaryOverride`s. Architecturetag can be None for
            architecture-independent publications.

        :return: A dict mapping (`IBinaryPackageName`, architecturetag)
            pairs to `IBinaryOverride`s.
        """
        pass


class BaseOverridePolicy:

    implements(IOverridePolicy)

    def __init__(self, phased_update_percentage=None):
        super(BaseOverridePolicy, self).__init__()
        self.phased_update_percentage = phased_update_percentage

    def calculateSourceOverrides(self, archive, distroseries, pocket, sources):
        raise NotImplementedError()

    def calculateBinaryOverrides(self, archive, distroseries, pocket,
                                 binaries):
        raise NotImplementedError()


class FromExistingOverridePolicy(BaseOverridePolicy):
    """Override policy that only searches for existing publications.

    Override policy that returns the SourcePackageName, component and
    section for the latest published source publication, or the
    BinaryPackageName, architecture_tag, component, section and priority
    for the latest published binary publication.
    """

    def getExistingPublishingStatuses(self, include_deleted):
        status = [
            PackagePublishingStatus.PENDING,
            PackagePublishingStatus.PUBLISHED,
            ]
        if include_deleted:
            status.append(PackagePublishingStatus.DELETED)
        return status

    def calculateSourceOverrides(self, archive, distroseries, pockets, sources,
                                 include_deleted=False):
        def eager_load(rows):
            bulk.load(Component, (row[1] for row in rows))
            bulk.load(Section, (row[2] for row in rows))

        spns = sources.keys()
        store = IStore(SourcePackagePublishingHistory)
        already_published = DecoratedResultSet(
            store.find(
                (SourcePackagePublishingHistory.sourcepackagenameID,
                 SourcePackagePublishingHistory.componentID,
                 SourcePackagePublishingHistory.sectionID,
                 SourcePackageRelease.version),
                SourcePackageRelease.id ==
                    SourcePackagePublishingHistory.sourcepackagereleaseID,
                SourcePackagePublishingHistory.archiveID == archive.id,
                SourcePackagePublishingHistory.distroseriesID ==
                    distroseries.id,
                SourcePackagePublishingHistory.status.is_in(
                    self.getExistingPublishingStatuses(include_deleted)),
                SourcePackagePublishingHistory.sourcepackagenameID.is_in(
                    spn.id for spn in spns)).order_by(
                        SourcePackagePublishingHistory.sourcepackagenameID,
                        Desc(SourcePackagePublishingHistory.datecreated),
                        Desc(SourcePackagePublishingHistory.id),
                ).config(
                    distinct=(
                        SourcePackagePublishingHistory.sourcepackagenameID,)),
            id_resolver((SourcePackageName, Component, Section, None)),
            pre_iter_hook=eager_load)
        return dict(
            (name, SourceOverride(
                component=component, section=section, version=version))
            for (name, component, section, version) in already_published)

    def calculateBinaryOverrides(self, archive, distroseries, pocket,
                                 binaries, include_deleted=False):
        def eager_load(rows):
            bulk.load(Component, (row[2] for row in rows))
            bulk.load(Section, (row[3] for row in rows))

        store = IStore(BinaryPackagePublishingHistory)
        expanded = calculate_target_das(distroseries, binaries.keys())

        candidates = [
            make_package_condition(archive, das, bpn)
            for bpn, das in expanded if das is not None]
        if len(candidates) == 0:
            return {}
        # Do not copy phased_update_percentage from existing publications;
        # it is too context-dependent to copy.
        already_published = DecoratedResultSet(
            store.find(
                (BinaryPackagePublishingHistory.binarypackagenameID,
                 BinaryPackagePublishingHistory.distroarchseriesID,
                 BinaryPackagePublishingHistory.componentID,
                 BinaryPackagePublishingHistory.sectionID,
                 BinaryPackagePublishingHistory.priority,
                 BinaryPackageRelease.version),
                BinaryPackageRelease.id ==
                    BinaryPackagePublishingHistory.binarypackagereleaseID,
                BinaryPackagePublishingHistory.status.is_in(
                    self.getExistingPublishingStatuses(include_deleted)),
                Or(*candidates)).order_by(
                    BinaryPackagePublishingHistory.distroarchseriesID,
                    BinaryPackagePublishingHistory.binarypackagenameID,
                    Desc(BinaryPackagePublishingHistory.datecreated),
                    Desc(BinaryPackagePublishingHistory.id),
                ).config(distinct=(
                    BinaryPackagePublishingHistory.distroarchseriesID,
                    BinaryPackagePublishingHistory.binarypackagenameID,
                    )
                ),
            id_resolver(
                (BinaryPackageName, DistroArchSeries, Component, Section,
                None, None)),
            pre_iter_hook=eager_load)
        overrides = {}
        for name, das, component, section, priority, ver in already_published:
            # These details can always fulfill their own archtag, and may
            # satisfy a None archtag if the DAS is nominatedarchindep.
            matching_keys = [(name, das.architecturetag)]
            if das == das.distroseries.nominatedarchindep:
                matching_keys.append((name, None))
            for key in matching_keys:
                if key not in binaries:
                    continue
                overrides[key] = BinaryOverride(
                    component=component, section=section, priority=priority,
                    phased_update_percentage=self.phased_update_percentage,
                    version=ver)
        return overrides


class UnknownOverridePolicy(BaseOverridePolicy):
    """Override policy that returns defaults.

    Override policy that assumes everything passed in doesn't exist, so
    returns the defaults.

    Newly-uploaded files have a default set of overrides to be applied.
    This reduces the amount of work that archive admins have to do
    since they override the majority of new uploads with the same
    values.  The rules for overriding are: (See bug #120052)
        'contrib' -> 'multiverse'
        'non-free' -> 'multiverse'
        everything else -> 'universe'
    This mainly relates to Debian syncs, where the default component
    is 'main' but should not be in main for Ubuntu.
    """

    DEBIAN_COMPONENT_OVERRIDE_MAP = {
        'contrib': 'multiverse',
        'non-free': 'multiverse',
        }

    DEFAULT_OVERRIDE_COMPONENT = 'universe'

    @classmethod
    def getComponentOverride(cls, component=None, return_component=False):
        # component can be a Component object or a component name.
        if zope_isinstance(component, Component):
            component = component.name
        override_component_name = cls.DEBIAN_COMPONENT_OVERRIDE_MAP.get(
            component, cls.DEFAULT_OVERRIDE_COMPONENT)
        if return_component:
            return getUtility(IComponentSet)[override_component_name]
        else:
            return override_component_name

    def calculateSourceOverrides(self, archive, distroseries, pocket, sources):
        return dict(
            (spn, SourceOverride(
                component=(
                    archive.default_component or
                    UnknownOverridePolicy.getComponentOverride(
                        override.component, return_component=True))))
            for spn, override in sources.items())

    def calculateBinaryOverrides(self, archive, distroseries, pocket,
                                 binaries):
        default_component = archive.default_component or getUtility(
            IComponentSet)['universe']
        return dict(
            ((binary_package_name, architecture_tag), BinaryOverride(
                component=default_component,
                phased_update_percentage=self.phased_update_percentage))
            for binary_package_name, architecture_tag in binaries.keys())


class UbuntuOverridePolicy(FromExistingOverridePolicy,
                           UnknownOverridePolicy):
    """Override policy for Ubuntu.

    An override policy that incorporates both the existing policy and the
    unknown policy.
    """

    def calculateSourceOverrides(self, archive, distroseries, pocket, sources):
        total = set(sources.keys())
        overrides = FromExistingOverridePolicy.calculateSourceOverrides(
            self, archive, distroseries, pocket, sources, include_deleted=True)
        existing = set(overrides.keys())
        missing = total.difference(existing)
        if missing:
            unknown = UnknownOverridePolicy.calculateSourceOverrides(
                self, archive, distroseries, pocket,
                dict((spn, sources[spn]) for spn in missing))
            overrides.update(unknown)
        return overrides

    def calculateBinaryOverrides(self, archive, distroseries, pocket,
                                 binaries):
        total = set(binaries.keys())
        overrides = FromExistingOverridePolicy.calculateBinaryOverrides(
            self, archive, distroseries, pocket, binaries,
            include_deleted=True)
        existing = set(overrides.keys())
        missing = total.difference(existing)
        if missing:
            unknown = UnknownOverridePolicy.calculateBinaryOverrides(
                self, archive, distroseries, pocket,
                dict((key, binaries[key]) for key in missing))
            overrides.update(unknown)
        return overrides


def calculate_target_das(distroseries, binaries):
    arch_map = dict(
        (arch.architecturetag, arch)
        for arch in distroseries.enabled_architectures)

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
        BinaryPackagePublishingHistory.binarypackagenameID == bpn.id)


def id_resolver(lookups):
    def _resolve(row):
        store = IStore(SourcePackagePublishingHistory)
        return tuple(
            (value if cls is None else store.get(cls, value))
            for value, cls in zip(row, lookups))

    return _resolve
