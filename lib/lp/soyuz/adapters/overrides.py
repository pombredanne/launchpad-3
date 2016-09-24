# Copyright 2011-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generic Override Policy classes."""

__metaclass__ = type

__all__ = [
    'BinaryOverride',
    'ConstantOverridePolicy',
    'FallbackOverridePolicy',
    'FromExistingOverridePolicy',
    'FromSourceOverridePolicy',
    'IBinaryOverride',
    'ISourceOverride',
    'SourceOverride',
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
    implementer,
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
    new = Attribute("Whether the package is considered new")


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

    source_override = Attribute(
        "A source override from which to determine defaults.")


class Override:
    """See `IOverride`."""

    def __init__(self, component=None, section=None, version=None, new=None):
        self.component = component
        self.section = section
        self.version = version
        self.new = new

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        # Prevent people getting very confused with these new classes,
        # should their instances ever be put in a dict or set.
        raise NotImplementedError(
            "%s objects are not hashable." % self.__class__.__name__)


@implementer(ISourceOverride)
class SourceOverride(Override):
    """See `ISourceOverride`."""

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__ and
            self.component == other.component and
            self.section == other.section and
            self.version == other.version and
            self.new == other.new)

    def __repr__(self):
        return (
            "<%s at %x component=%r section=%r version=%r new=%r>" %
            (self.__class__.__name__, id(self), self.component, self.section,
             self.version, self.new))


@implementer(IBinaryOverride)
class BinaryOverride(Override):
    """See `IBinaryOverride`."""

    def __init__(self, component=None, section=None, priority=None,
                 phased_update_percentage=None, version=None, new=None,
                 source_override=None):
        super(BinaryOverride, self).__init__(
            component=component, section=section, version=version, new=new)
        self.priority = priority
        self.phased_update_percentage = phased_update_percentage
        self.source_override = source_override

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__ and
            self.component == other.component and
            self.section == other.section and
            self.priority == other.priority and
            self.phased_update_percentage == other.phased_update_percentage and
            self.version == other.version and
            self.new == other.new and
            self.source_override == other.source_override)

    def __repr__(self):
        return (
            "<%s at %x component=%r section=%r priority=%r "
            "phased_update_percentage=%r version=%r new=%r "
            "source_override=%r>" %
            (self.__class__.__name__, id(self), self.component, self.section,
             self.priority, self.phased_update_percentage, self.version,
             self.new, self.source_override))


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


@implementer(IOverridePolicy)
class BaseOverridePolicy:

    def __init__(self, archive, distroseries, pocket,
                 phased_update_percentage=None):
        super(BaseOverridePolicy, self).__init__()
        self.archive = archive
        self.distroseries = distroseries
        self.pocket = pocket
        self.phased_update_percentage = phased_update_percentage

    def calculateSourceOverrides(self, sources):
        raise NotImplementedError()

    def calculateBinaryOverrides(self, binaries):
        raise NotImplementedError()


class FromExistingOverridePolicy(BaseOverridePolicy):
    """Override policy that only searches for existing publications.

    Override policy that returns the SourcePackageName, component and
    section for the latest published source publication, or the
    BinaryPackageName, architecture_tag, component, section and priority
    for the latest published binary publication.
    """

    def __init__(self, *args, **kwargs):
        self.any_arch = kwargs.pop('any_arch', False)
        self.include_deleted = kwargs.pop('include_deleted', False)
        super(FromExistingOverridePolicy, self).__init__(*args, **kwargs)

    def getExistingPublishingStatuses(self, include_deleted):
        status = [
            PackagePublishingStatus.PENDING,
            PackagePublishingStatus.PUBLISHED,
            ]
        if include_deleted:
            status.append(PackagePublishingStatus.DELETED)
        return status

    def calculateSourceOverrides(self, sources):
        def eager_load(rows):
            bulk.load(Component, (row[1] for row in rows))
            bulk.load(Section, (row[2] for row in rows))

        spns = sources.keys()
        store = IStore(SourcePackagePublishingHistory)
        other_conditions = []
        if self.pocket is not None:
            other_conditions.append(
                SourcePackagePublishingHistory.pocket == self.pocket)
        already_published = DecoratedResultSet(
            store.find(
                (SourcePackagePublishingHistory.sourcepackagenameID,
                 SourcePackagePublishingHistory.componentID,
                 SourcePackagePublishingHistory.sectionID,
                 SourcePackagePublishingHistory.status,
                 SourcePackageRelease.version),
                SourcePackageRelease.id ==
                    SourcePackagePublishingHistory.sourcepackagereleaseID,
                SourcePackagePublishingHistory.archiveID == self.archive.id,
                SourcePackagePublishingHistory.distroseriesID ==
                    self.distroseries.id,
                SourcePackagePublishingHistory.status.is_in(
                    self.getExistingPublishingStatuses(self.include_deleted)),
                SourcePackagePublishingHistory.sourcepackagenameID.is_in(
                    spn.id for spn in spns),
                *other_conditions).order_by(
                        SourcePackagePublishingHistory.sourcepackagenameID,
                        Desc(SourcePackagePublishingHistory.datecreated),
                        Desc(SourcePackagePublishingHistory.id),
                ).config(
                    distinct=(
                        SourcePackagePublishingHistory.sourcepackagenameID,)),
            id_resolver((SourcePackageName, Component, Section, None, None)),
            pre_iter_hook=eager_load)
        return dict(
            (name, SourceOverride(
                component=component, section=section, version=version,
                new=(status == PackagePublishingStatus.DELETED)))
            for (name, component, section, status, version)
            in already_published)

    def calculateBinaryOverrides(self, binaries):
        def eager_load(rows):
            bulk.load(Component, (row[2] for row in rows))
            bulk.load(Section, (row[3] for row in rows))

        store = IStore(BinaryPackagePublishingHistory)
        other_conditions = []
        if not self.any_arch:
            expanded = calculate_target_das(self.distroseries, binaries.keys())
            candidates = [
                make_package_condition(self.archive, das, bpn)
                for bpn, das in expanded if das is not None]
        else:
            candidates = []
            archtags = set()
            for bpn, archtag in binaries.keys():
                candidates.append(
                    BinaryPackagePublishingHistory.binarypackagenameID ==
                        bpn.id)
                archtags.add(archtag)
            other_conditions.extend([
                BinaryPackagePublishingHistory.archiveID == self.archive.id,
                DistroArchSeries.distroseriesID == self.distroseries.id,
                BinaryPackagePublishingHistory.distroarchseriesID ==
                    DistroArchSeries.id,
                ])
        if len(candidates) == 0:
            return {}
        if self.pocket is not None:
            other_conditions.append(
                BinaryPackagePublishingHistory.pocket == self.pocket)
        # Do not copy phased_update_percentage from existing publications;
        # it is too context-dependent to copy.
        already_published = DecoratedResultSet(
            store.find(
                (BinaryPackagePublishingHistory.binarypackagenameID,
                 BinaryPackagePublishingHistory.distroarchseriesID,
                 BinaryPackagePublishingHistory.componentID,
                 BinaryPackagePublishingHistory.sectionID,
                 BinaryPackagePublishingHistory.priority,
                 BinaryPackagePublishingHistory.status,
                 BinaryPackageRelease.version),
                BinaryPackageRelease.id ==
                    BinaryPackagePublishingHistory.binarypackagereleaseID,
                BinaryPackagePublishingHistory.status.is_in(
                    self.getExistingPublishingStatuses(self.include_deleted)),
                Or(*candidates),
                *other_conditions).order_by(
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
                None, None, None)),
            pre_iter_hook=eager_load)
        overrides = {}
        for (name, das, comp, sect, prio, status, ver) in already_published:
            # These details can always fulfill their own archtag, and may
            # satisfy a None archtag if the DAS is nominatedarchindep.
            if not self.any_arch:
                matching_keys = [(name, das.architecturetag)]
                if das == das.distroseries.nominatedarchindep:
                    matching_keys.append((name, None))
            else:
                matching_keys = [
                    (name, archtag) for archtag in archtags | set((None,))]
            for key in matching_keys:
                if key not in binaries:
                    continue
                overrides[key] = BinaryOverride(
                    component=comp, section=sect, priority=prio,
                    phased_update_percentage=self.phased_update_percentage,
                    version=ver,
                    new=(status == PackagePublishingStatus.DELETED))
        return overrides


class FromSourceOverridePolicy(BaseOverridePolicy):
    """Override policy that returns binary defaults based on their source."""

    def __init__(self, phased_update_percentage=None):
        self.phased_update_percentage = phased_update_percentage

    def calculateSourceOverrides(self, sources):
        return {}

    def calculateBinaryOverrides(self, binaries):
        overrides = {}
        for key, override_in in binaries.items():
            if (override_in.source_override is not None
                    and override_in.source_override.component is not None):
                overrides[key] = BinaryOverride(
                    component=override_in.source_override.component, new=True)
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

    def calculateSourceOverrides(self, sources):
        return dict(
            (spn, SourceOverride(
                component=UnknownOverridePolicy.getComponentOverride(
                    override.component, return_component=True),
                new=True))
            for spn, override in sources.items())

    def calculateBinaryOverrides(self, binaries):
        default_component = getUtility(IComponentSet)['universe']
        return dict(
            ((binary_package_name, architecture_tag), BinaryOverride(
                component=default_component, new=True,
                phased_update_percentage=self.phased_update_percentage))
            for binary_package_name, architecture_tag in binaries.keys())


class ConstantOverridePolicy(BaseOverridePolicy):
    """Override policy that returns constant values."""

    def __init__(self, component=None, section=None, priority=None,
                 phased_update_percentage=None, new=None):
        self.component = component
        self.section = section
        self.priority = priority
        self.phased_update_percentage = phased_update_percentage
        self.new = new

    def calculateSourceOverrides(self, sources):
        return dict(
            (key, SourceOverride(
                component=self.component, section=self.section,
                new=self.new)) for key in sources.keys())

    def calculateBinaryOverrides(self, binaries):
        return dict(
            (key, BinaryOverride(
                component=self.component, section=self.section,
                priority=self.priority,
                phased_update_percentage=self.phased_update_percentage,
                new=self.new)) for key in binaries.keys())


class FallbackOverridePolicy(BaseOverridePolicy):
    """Override policy that fills things through a sequence of policies."""

    def __init__(self, policies):
        self.policies = policies

    def calculateSourceOverrides(self, sources):
        overrides = {}
        missing = set(sources.keys())
        for policy in self.policies:
            if not missing:
                break
            these_overrides = policy.calculateSourceOverrides(
                dict((spn, sources[spn]) for spn in missing))
            overrides.update(these_overrides)
            missing -= set(these_overrides.keys())
        return overrides

    def calculateBinaryOverrides(self, binaries):
        overrides = {}
        missing = set(binaries.keys())
        for policy in self.policies:
            if not missing:
                break
            these_overrides = policy.calculateBinaryOverrides(
                dict((key, binaries[key]) for key in missing))
            overrides.update(these_overrides)
            missing -= set(these_overrides.keys())
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
