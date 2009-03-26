# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Archive interfaces."""

__metaclass__ = type

__all__ = [
    'ArchiveDependencyError',
    'ArchivePurpose',
    'CannotCopy',
    'ComponentNotFound',
    'DistroSeriesNotFound',
    'IArchive',
    'IArchiveAppend',
    'IArchiveView',
    'IArchiveEditDependenciesForm',
    'IArchivePackageCopyingForm',
    'IArchivePackageDeletionForm',
    'IArchivePublic',
    'IArchiveSet',
    'IArchiveSourceSelectionForm',
    'IDistributionArchive',
    'IPPA',
    'IPPAActivateForm',
    'MAIN_ARCHIVE_PURPOSES',
    'ALLOW_RELEASE_BUILDS',
    'PocketNotFound',
    'SourceNotFound',
    'default_name_by_purpose',
    ]

from zope.interface import Interface, Attribute
from zope.schema import (
    Bool, Choice, Datetime, Int, Object, List, Text, TextLine)
from lazr.enum import DBEnumeratedType, DBItem

from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice
from canonical.launchpad.interfaces import IHasOwner
from canonical.launchpad.interfaces.buildrecords import IHasBuildRecords
from canonical.launchpad.interfaces.gpg import IGPGKey
from canonical.launchpad.interfaces.person import IPerson
from canonical.launchpad.validators.name import name_validator

from canonical.lazr.fields import Reference
from canonical.lazr.rest.declarations import (
    export_as_webservice_entry, exported, export_read_operation,
    export_factory_operation, export_write_operation, operation_parameters,
    operation_returns_collection_of, rename_parameters_as, webservice_error)


class ArchiveDependencyError(Exception):
    """Raised when an `IArchiveDependency` does not fit the context archive.

    A given dependency is considered inappropriate when:

     * It is the archive itself,
     * It is not a PPA,
     * It is already recorded.
    """


# Exceptions used in the webservice that need to be in this file to get
# picked up therein.

class CannotCopy(Exception):
    """Exception raised when a copy cannot be performed."""
    webservice_error(400) #Bad request.


class PocketNotFound(Exception):
    """Invalid pocket."""
    webservice_error(400) #Bad request.


class DistroSeriesNotFound(Exception):
    """Invalid distroseries."""
    webservice_error(400) #Bad request.


class SourceNotFound(Exception):
    """Invalid source name."""
    webservice_error(400) #Bad request.


class ComponentNotFound(Exception):
    """Invalid source name."""
    webservice_error(400) #Bad request.


class IArchivePublic(IHasOwner):
    """An Archive interface for publicly available operations."""
    id = Attribute("The archive ID.")

    owner = exported(
        PublicPersonChoice(
            title=_('Owner'), required=True, vocabulary='ValidOwner',
            description=_("""The archive owner.""")))

    name = exported(
        TextLine(
            title=_("Name"), required=True,
            constraint=name_validator,
            description=_("The name of this archive.")))

    displayname = exported(
        TextLine(
            title=_("Displayname"), required=False,
            description=_("Displayname for this archive.")))

    enabled = Bool(
        title=_("Enabled"), required=False,
        description=_("Whether the archive is enabled or not."))

    publish = Bool(
        title=_("Publish"), required=False,
        description=_("Whether the archive is to be published or not."))

    private = exported(
        Bool(
            title=_("Private"), required=False,
            description=_(
                "Whether the archive is private to the owner or not.")))

    require_virtualized = Bool(
        title=_("Require Virtualized Builder"), required=False,
        description=_("Whether this archive requires its packages to be "
                      "built on a virtual builder."))

    authorized_size = Int(
        title=_("Authorized PPA size "), required=False,
        max=(20 * 1024),
        description=_("Maximum size, in MiB, allowed for this PPA."))

    whiteboard = Text(
        title=_("Whiteboard"), required=False,
        description=_("Administrator comments."))

    purpose = Int(
        title=_("Purpose of archive."), required=True, readonly=True,
        )

    sources_cached = Int(
        title=_("Number of sources cached"), required=False,
        description=_("Number of source packages cached in this PPA."))

    binaries_cached = Int(
        title=_("Number of binaries cached"), required=False,
        description=_("Number of binary packages cached in this PPA."))

    package_description_cache = Attribute(
        "Concatenation of the source and binary packages published in this "
        "archive. Its content is used for indexed searches across archives.")

    distribution = exported(
        Reference(
            Interface, # Redefined to IDistribution later.
            title=_("The distribution that uses or is used by this "
                    "archive.")))

    signing_key = Object(
        title=_('Repository sigining key.'), required=False, schema=IGPGKey)

    dependencies = Attribute(
        "Archive dependencies recorded for this archive and ordered by owner "
        "displayname.")

    expanded_archive_dependencies = Attribute(
        "The expanded list of archive dependencies. It includes the implicit "
        "PRIMARY archive dependency for PPAs.")

    archive_url = Attribute("External archive URL.")

    is_ppa = Attribute("True if this archive is a PPA.")

    is_copy = Attribute("True if this archive is a copy archive.")

    is_main = Bool(
        title=_("True if archive is a main archive type"), required=False)

    series_with_sources = Attribute(
        "DistroSeries to which this archive has published sources")
    number_of_sources = Attribute(
        'The number of sources published in the context archive.')
    number_of_binaries = Attribute(
        'The number of binaries published in the context archive.')
    sources_size = Attribute(
        'The size of sources published in the context archive.')
    binaries_size = Attribute(
        'The size of binaries published in the context archive.')
    estimated_size = Attribute('Estimated archive size.')

    total_count = Int(
        title=_("Total number of builds in archive"), required=True,
        default=0,
        description=_("The total number of builds in this archive. "
                      "This counter does not include discontinued "
                      "(superseded, cancelled, obsoleted) builds"))

    pending_count = Int(
        title=_("Number of pending builds in archive"), required=True,
        default=0,
        description=_("The number of pending builds in this archive."))

    succeeded_count = Int(
        title=_("Number of successful builds in archive"), required=True,
        default=0,
        description=_("The number of successful builds in this archive."))

    building_count = Int(
        title=_("Number of active builds in archive"), required=True,
        default=0,
        description=_("The number of active builds in this archive."))

    failed_count = Int(
        title=_("Number of failed builds in archive"), required=True,
        default=0,
        description=_("The number of failed builds in this archive."))

    date_created = Datetime(
        title=_('Date created'), required=False, readonly=True,
        description=_("The time when the archive was created."))

    def getPubConfig():
        """Return an overridden Publisher Configuration instance.

        The original publisher configuration based on the distribution is
        modified according local context, it basically fixes the archive
        paths to cope with non-primary and PPA archives publication workflow.
        """

    def getSourcesForDeletion(name=None, status=None, distroseries=None):
        """All `ISourcePackagePublishingHistory` available for deletion.

        :param: name: optional source name filter (SQL LIKE)
        :param: status: `PackagePublishingStatus` filter, can be a sequence.
        :param: distroseries: `IDistroSeries` filter.

        :return: SelectResults containing `ISourcePackagePublishingHistory`.
        """

    def getPublishedOnDiskBinaries(name=None, version=None, status=None,
                                   distroarchseries=None, exact_match=False):
        """Unique `IBinaryPackagePublishingHistory` target to this archive.

        In spite of getAllPublishedBinaries method, this method only returns
        distinct binary publications inside this Archive, i.e, it excludes
        architecture-independent publication for other architetures than the
        nominatedarchindep. In few words it represents the binary files
        published in the archive disk pool.

        :param: name: binary name filter (exact match or SQL LIKE controlled
                      by 'exact_match' argument).
        :param: version: binary version filter (always exact match).
        :param: status: `PackagePublishingStatus` filter, can be a list.
        :param: distroarchseries: `IDistroArchSeries` filter, can be a list.
        :param: pocket: `PackagePublishingPocket` filter.
        :param: exact_match: either or not filter source names by exact
                             matching.

        :return: SelectResults containing `IBinaryPackagePublishingHistory`.
        """

    def getAllPublishedBinaries(name=None, version=None, status=None,
                                distroarchseries=None, exact_match=False):
        """All `IBinaryPackagePublishingHistory` target to this archive.

        See getUniquePublishedBinaries for further information.

        :param: name: binary name filter (exact match or SQL LIKE controlled
                      by 'exact_match' argument).
        :param: version: binary version filter (always exact match).
        :param: status: `PackagePublishingStatus` filter, can be a list.
        :param: distroarchseries: `IDistroArchSeries` filter, can be a list.
        :param: pocket: `PackagePublishingPocket` filter.
        :param: exact_match: either or not filter source names by exact
                             matching.

        :return: SelectResults containing `IBinaryPackagePublishingHistory`.
        """

    def allowUpdatesToReleasePocket():
        """Return whether the archive allows publishing to the release pocket.

        If a distroseries is stable, normally release pocket publishings are
        not allowed.  However some archive types allow this.

        :return: True or False
        """

    def updateArchiveCache():
        """Concentrate cached information about the archive contents.

        Group the relevant package information (source name, binary names,
        binary summaries and distroseries with binaries) strings in the
        IArchive.package_description_cache search indexes (fti).

        Updates 'sources_cached' and 'binaries_cached' counters.

        Also include owner 'name' and 'displayname' to avoid inpecting the
        Person table indexes while searching.
        """

    def findDepCandidateByName(distroarchseries, name):
        """Return the last published binarypackage by given name.

        Return the PublishedPackage record by binarypackagename or None if
        not found.
        """

    def getArchiveDependency(dependency):
        """Return the `IArchiveDependency` object for the given dependency.

        :param dependency: is an `IArchive` object.

        :return: `IArchiveDependency` or None if a corresponding object
            could not be found.
        """

    def removeArchiveDependency(dependency):
        """Remove the `IArchiveDependency` record for the given dependency.

        :param dependency: is an `IArchive` object.
        """

    def addArchiveDependency(dependency, pocket, component=None):
        """Record an archive dependency record for the context archive.

        :param dependency: is an `IArchive` object.
        :param pocket: is an `PackagePublishingPocket` enum.
        :param component: is an optional `IComponent` object, if not given
            the archive dependency will be tied to the component used
            for a corresponding source in primary archive.

        :raise: `ArchiveDependencyError` if given 'dependency' does not fit
            the context archive.
        :return: a `IArchiveDependency` object targeted to the context
            `IArchive` requiring 'dependency' `IArchive`.
        """

    def getPermissions(person, item, perm_type):
        """Get the `IArchivePermission` record with the supplied details.

        :param person: An `IPerson`
        :param item: An `IComponent`, `ISourcePackageName`
        :param perm_type: An ArchivePermissionType enum,
        :return: A list of `IArchivePermission` records.
        """

    @operation_parameters(person=Reference(schema=IPerson))
    # Really IArchivePermission, set below to avoid circular import.
    @operation_returns_collection_of(Interface)
    @export_read_operation()
    def getPermissionsForPerson(person):
        """Return the `IArchivePermission` records applicable to the person.

        :param person: An `IPerson`
        :return: A list of `IArchivePermission` records.
        """

    @operation_parameters(
        source_package_name=TextLine(
            title=_("Source Package Name"), required=True))
    # Really IArchivePermission, set below to avoid circular import.
    @operation_returns_collection_of(Interface)
    @export_read_operation()
    def getUploadersForPackage(source_package_name):
        """Return `IArchivePermission` records for the package's uploaders.

        :param source_package_name: An `ISourcePackageName` or textual name
            for the source package.
        :return: A list of `IArchivePermission` records.
        """

    @operation_parameters(
        component_name=TextLine(title=_("Component Name"), required=False))
    # Really IArchivePermission, set below to avoid circular import.
    @operation_returns_collection_of(Interface)
    @export_read_operation()
    def getUploadersForComponent(component_name=None):
        """Return `IArchivePermission` records for the component's uploaders.

        :param component_name: An `IComponent` or textual name for the
            component.
        :return: A list of `IArchivePermission` records.
        """

    @operation_parameters(
        component_name=TextLine(title=_("Component Name"), required=True))
    # Really IArchivePermission, set below to avoid circular import.
    @operation_returns_collection_of(Interface)
    @export_read_operation()
    def getQueueAdminsForComponent(component_name):
        """Return `IArchivePermission` records for authorised queue admins.

        :param component_name: An `IComponent` or textual name for the
            component.
        :return: A list of `IArchivePermission` records.
        """

    @operation_parameters(person=Reference(schema=IPerson))
    # Really IArchivePermission, set below to avoid circular import.
    @operation_returns_collection_of(Interface)
    @export_read_operation()
    def getComponentsForQueueAdmin(person):
        """Return `IArchivePermission` for the person's queue admin components

        :param person: An `IPerson`
        :return: A list of `IArchivePermission` records.
        """

    def canUpload(person, component_or_package=None):
        """Check to see if person is allowed to upload to component.

        :param person: An `IPerson` whom should be checked for authentication.
        :param component_or_package: The context `IComponent` or an
            `ISourcePackageName` for the check.  This parameter is
            not required if the archive is a PPA.

        :return: True if 'person' is allowed to upload to the specified
            component or package name.
        :raise TypeError: If component_or_package is not one of
            `IComponent` or `ISourcePackageName`.

        """

    def canAdministerQueue(person, component):
        """Check to see if person is allowed to administer queue items.

        :param person: An `IPerson` whom should be checked for authenticate.
        :param component: The context `IComponent` for the check.

        :return: True if 'person' is allowed to administer the package upload
        queue for items with 'component'.
        """

    # The following three factory methods are not in the
    # IArchiveEditRestricted interface because the rights to use them
    # does not depend on edit permissions to the archive.  The code they
    # contain does all the necessary security checking and is well
    # tested in xx-archive.txt and archivepermissions.txt.

    @operation_parameters(
        person=Reference(schema=IPerson),
        source_package_name=TextLine(
            title=_("Source Package Name"), required=True))
    # Really IArchivePermission, set below to avoid circular import.
    @export_factory_operation(Interface, [])
    def newPackageUploader(person, source_package_name):
        """Add permisson for a person to upload a package to this archive.

        :param person: An `IPerson` whom should be given permission.
        :param source_package_name: An `ISourcePackageName` or textual package
            name.
        :return: An `IArchivePermission` which is the newly-created
            permission.
        """

    @operation_parameters(
        person=Reference(schema=IPerson),
        component_name=TextLine(
            title=_("Component Name"), required=True))
    # Really IArchivePermission, set below to avoid circular import.
    @export_factory_operation(Interface, [])
    def newComponentUploader(person, component_name):
        """Add permission for a person to upload to a component.

        :param person: An `IPerson` whom should be given permission.
        :param component: An `IComponent` or textual component name.
        :return: An `IArchivePermission` which is the newly-created
            permission.
        """

    @operation_parameters(
        person=Reference(schema=IPerson),
        component_name=TextLine(
            title=_("Component Name"), required=True))
    # Really IArchivePermission, set below to avoid circular import.
    @export_factory_operation(Interface, [])
    def newQueueAdmin(person, component_name):
        """Add permission for a person to administer a distroseries queue.

        The supplied person will gain permission to administer the
        distroseries queue for packages in the supplied component.

        :param person: An `IPerson` whom should be given permission.
        :param component: An `IComponent` or textual component name.
        :return: An `IArchivePermission` which is the newly-created
            permission.
        """

    @operation_parameters(
        person=Reference(schema=IPerson),
        source_package_name=TextLine(
            title=_("Source Package Name"), required=True))
    @export_write_operation()
    def deletePackageUploader(person, source_package_name):
        """Revoke permission for the person to upload the package.

        :param person: An `IPerson` whose permission should be revoked.
        :param source_package_name: An `ISourcePackageName` or textual package
            name.
        """

    @operation_parameters(
        person=Reference(schema=IPerson),
        component_name=TextLine(
            title=_("Component Name"), required=True))
    @export_write_operation()
    def deleteComponentUploader(person, component_name):
        """Revoke permission for the person to upload to the component.

        :param person: An `IPerson` whose permission should be revoked.
        :param component: An `IComponent` or textual component name.
        """

    @operation_parameters(
        person=Reference(schema=IPerson),
        component_name=TextLine(
            title=_("Component Name"), required=True))
    @export_write_operation()
    def deleteQueueAdmin(person, component_name):
        """Revoke permission for the person to administer distroseries queues.

        The supplied person will lose permission to administer the
        distroseries queue for packages in the supplied component.

        :param person: An `IPerson` whose permission should be revoked.
        :param component: An `IComponent` or textual component name.
        """

    def getFileByName(filename):
        """Return the corresponding `ILibraryFileAlias` in this context.

        The following file types (and extension) can be looked up in the
        archive context:

         * Source files: '.orig.tar.gz', 'tar.gz', '.diff.gz' and '.dsc';
         * Binary files: '.deb' and '.udeb';
         * Source changesfile: '_source.changes';
         * Package diffs: '.diff.gz';

        :param filename: exactly filename to be looked up.

        :raises AssertionError if the given filename contains a unsupported
            filename and/or extension, see the list above.
        :raises NotFoundError if no file could not be found.

        :return the corresponding `ILibraryFileAlias` is the file was found.
        """

    def requestPackageCopy(target_location, requestor, suite=None,
                           copy_binaries=False, reason=None):
        """Return a new `PackageCopyRequest` for this archive.

        :param target_location: the archive location to which the packages
            are to be copied.
        :param requestor: The `IPerson` who is requesting the package copy
            operation.
        :param suite: The `IDistroSeries` name with optional pocket, for
            example, 'hoary-security'. If this is not provided it will
            default to the current series' release pocket.
        :param copy_binaries: Whether or not binary packages should be copied
            as well.
        :param reason: The reason for this package copy request.

        :raises NotFoundError: if the provided suite is not found for this
            archive's distribution.

        :return The new `IPackageCopyRequest`
        """

    # XXX: noodles 2009-03-02 bug=336779: This should be moved into
    # IArchiveView once the archive permissions are updated to grant
    # IArchiveView to archive subscribers.
    def newAuthToken(person, token=None, date_created=None):
        """Create a new authorisation token.

        XXX: noodles 2009-03-12 bug=341600 This method should not be exposed
        through the API as we do not yet check that the callsite has
        launchpad.Edit on the person.

        :param person: An IPerson whom this token is for
        :param token: Optional unicode text to use as the token. One will be
            generated if not given
        :param date_created: Optional, defaults to now

        :return: A new IArchiveAuthToken
        """


class IArchiveView(IHasBuildRecords):
    """Archive interface for operations restricted by view privilege."""

    buildd_secret = TextLine(
        title=_("Buildd Secret"), required=False,
        description=_("The password used by the builder to access the "
                      "archive."))

    description = exported(
        Text(
            title=_("Archive contents description"), required=False,
            description=_("A short description of this archive's contents.")))

    signing_key_fingerprint = exported(
        Text(
            title=_("Archive signing key fingerprint"), required=False,
            description=_("A OpenPGP signing key fingerprint (40 chars) "
                          "for this PPA or None if there is no signing "
                          "key available.")))

    @rename_parameters_as(name="source_name", distroseries="distro_series")
    @operation_parameters(
        name=TextLine(title=_("Source package name"), required=False),
        version=TextLine(title=_("Version"), required=False),
        status=Choice(
            title=_('Package Publishing Status'),
            description=_('The status of this publishing record'),
            # Really PackagePublishingStatus, circular import fixed below.
            vocabulary=DBEnumeratedType,
            required=False),
        distroseries=Reference(
            # Really IDistroSeries, fixed below to avoid circular import.
            Interface,
            title=_("Distroseries name"), required=False),
        pocket=Choice(
            title=_("Pocket"),
            description=_("The pocket into which this entry is published"),
            # Really PackagePublishingPocket, circular import fixed below.
            vocabulary=DBEnumeratedType,
            required=False, readonly=True),
        exact_match=Bool(
            title=_("Exact Match"),
            description=_("Whether or not to filter source names by exact"
                          " matching."),
            required=False),
        published_since_date=Datetime(
            title=_("Published Since Date"),
            description=_("Return entries whose 'datepublished' is greater "
                          "than or equal to this date."),
            required=False))
    # Really returns ISourcePackagePublishingHistory, see below for
    # patch to avoid circular import.
    @operation_returns_collection_of(Interface)
    @export_read_operation()
    def getPublishedSources(name=None, version=None, status=None,
                            distroseries=None, pocket=None,
                            exact_match=False, published_since_date=None):
        """All `ISourcePackagePublishingHistory` target to this archive.

        :param name: source name filter (exact match or SQL LIKE controlled
                     by 'exact_match' argument).
        :param version: source version filter (always exact match).
        :param status: `PackagePublishingStatus` filter, can be a sequence.
        :param distroseries: `IDistroSeries` filter.
        :param pocket: `PackagePublishingPocket` filter.
        :param exact_match: either or not filter source names by exact
                             matching.
        :param published_since_date: Only return results whose 'datepublished'
            is greater than or equal to this date.

        :return: SelectResults containing `ISourcePackagePublishingHistory`.
        """

    @operation_parameters(
        include_needsbuild=Bool(
            title=_("Include builds with state NEEDSBUILD"), required=False))
    @export_read_operation()
    def getBuildCounters(include_needsbuild=True):
        """Return a dictionary containing the build counters for an archive.

        This is necessary currently because the IArchive.failed_builds etc.
        counters are not in use.

        The returned dictionary contains the follwoing keys and values:

         * 'total': total number of builds (includes SUPERSEDED);
         * 'pending': number of builds in BUILDING or NEEDSBUILD state;
         * 'failed': number of builds in FAILEDTOBUILD, MANUALDEPWAIT,
           CHROOTWAIT and FAILEDTOUPLOAD state;
         * 'succeeded': number of SUCCESSFULLYBUILT builds.
         * 'superseded': number of SUPERSEDED builds.

        :param include_needsbuild: Indicates whether to include builds with
            the status NEEDSBUILD in the pending and total counts. This is
            useful in situations where a build that hasn't started isn't
            considered a build by the user.
        :type include_needsbuild: ``bool``
        :return: a dictionary with the 4 keys specified above.
        :rtype: ``dict``.
        """

    @operation_parameters(
        source_ids=List(
            title=_("A list of source publishing history record ids."),
            value_type=TextLine()))
    @export_read_operation()
    def getBuildSummariesForSourceIds(source_ids):
        """Return a dictionary containing a summary of the build statuses.

        Only information for sources belonging to the current archive will
        be returned. See
        `IPublishingSet`.getBuildStatusSummariesForSourceIdsAndArchive() for
        details.

        :param source_ids: A list of source publishing history record ids.
        :type source_ids: ``list``
        :return: A dict consisting of the overall status summaries for the
            given ids that belong in the archive.
        """


class IArchiveAppend(Interface):
    """Archive interface for operations restricted by append privilege."""

    @operation_parameters(
        source_names=List(
            title=_("Source package names"),
            value_type=TextLine()),
        from_archive=Reference(schema=Interface), #Really IArchive, see below
        to_pocket=TextLine(title=_("Pocket name")),
        to_series=TextLine(title=_("Distroseries name"), required=False),
        include_binaries=Bool(
            title=_("Include Binaries"),
            description=_("Whether or not to copy binaries already built for"
                          " this source"),
            required=False))
    @export_write_operation()
    # Source_names is a string because exporting a SourcePackageName is
    # rather nonsensical as it only has id and name columns.
    def syncSources(source_names, from_archive, to_pocket,
                    to_series=None, include_binaries=False):
        """Synchronise (copy) named sources into this archive from another.

        This method takes string-based paramters and is intended for use
        in the API.

        :param source_names: a list of string names of packages to copy.
        :param from_archive: the source archive from which to copy.
        :param to_pocket: the target pocket (as a string).
        :param to_series: the target distroseries (as a string).
        :param include_binaries: optional boolean, controls whether or not
            the published binaries for each given source should also be
            copied along with the source.

        :raises SourceNotFound: if the source name is invalid
        :raises PocketNotFound: if the pocket name is invalid
        :raises DistroSeriesNotFound: if the distro series name is invalid
        :raises CannotCopy: if there is a problem copying.

        :return: a list of string names of packages that could be copied.
        """

    @operation_parameters(
        source_name=TextLine(title=_("Source package name")),
        version=TextLine(title=_("Version")),
        from_archive=Reference(schema=Interface), #Really IArchive, see below
        to_pocket=TextLine(title=_("Pocket name")),
        to_series=TextLine(title=_("Distroseries name"), required=False),
        include_binaries=Bool(
            title=_("Include Binaries"),
            description=_("Whether or not to copy binaries already built for"
                          " this source"),
            required=False))
    @export_write_operation()
    # XXX Julian 2008-11-05
    # This method takes source_name and version as strings because
    # SourcePackageRelease is not exported on the API yet.  When it is,
    # we should consider either changing this method or adding a new one
    # that takes that object instead.
    def syncSource(source_name, version, from_archive, to_pocket,
                   to_series=None, include_binaries=False):
        """Synchronise (copy) a single named source into this archive.

        This method takes string-based paramters and is intended for use
        in the API.

        :param source_name: a string name of the package to copy.
        :param version: the version of the package to copy.
        :param from_archive: the source archive from which to copy.
        :param to_pocket: the target pocket (as a string).
        :param to_series: the target distroseries (as a string).
        :param include_binaries: optional boolean, controls whether or not
            the published binaries for each given source should also be
            copied along with the source.

        :raises SourceNotFound: if the source name is invalid
        :raises PocketNotFound: if the pocket name is invalid
        :raises DistroSeriesNotFound: if the distro series name is invalid
        :raises CannotCopy: if there is a problem copying.
        """

    def newSubscription(subscriber, registrant, date_expires=None,
                        description=None):
        """Create a new subscribtion to this archive.

        Create an `ArchiveSubscriber` record which allows an `IPerson` to
        access a private repository.

        :param subscriber: An `IPerson` who is allowed to access the
        repository for this archive.
        :param registrant: An `IPerson` who created this subscription.
        :param date_expires: When the subscription should expire; None if
            it should not expire (default).
        :param description: An option textual description of the subscription
            being created.

        :return: The `IArchiveSubscriber` that was created.
        """


class IArchive(IArchivePublic, IArchiveAppend, IArchiveView):
    """Main Archive interface."""
    export_as_webservice_entry()


class IPPA(IArchive):
    """Marker interface so traversal works differently for PPAs."""


class IDistributionArchive(IArchive):
    """Marker interface so traversal works differently for distro archives."""


class IPPAActivateForm(Interface):
    """Schema used to activate PPAs."""

    name = TextLine(
        title=_("PPA name"), required=True,
        description=_("A unique name used to identify this PPA."))

    description = Text(
        title=_("PPA contents description"), required=False,
        description=_(
        "A short description of this PPA. URLs are allowed and will "
        "be rendered as links."))

    accepted = Bool(
        title=_("I have read and accepted the PPA Terms of Service."),
        required=True, default=False)


class IArchiveSourceSelectionForm(Interface):
    """Schema used to select sources within an archive."""


class IArchivePackageDeletionForm(IArchiveSourceSelectionForm):
    """Schema used to delete packages within an archive."""

    deletion_comment = TextLine(
        title=_("Deletion comment"), required=False,
        description=_("The reason why the package is being deleted."))


class IArchivePackageCopyingForm(IArchiveSourceSelectionForm):
    """Schema used to copy packages across archive."""



class IArchiveEditDependenciesForm(Interface):
    """Schema used to edit dependencies settings within a archive."""

    dependency_candidate = Choice(
        title=_('Add PPA dependency'), required=False, vocabulary='PPA')


class IArchiveSet(Interface):
    """Interface for ArchiveSet"""

    title = Attribute('Title')

    def getNumberOfPPASourcesForDistribution(distribution):
        """Return the number of sources for PPAs in a given distribution.

        Only public and published sources are considered.
        """

    def getNumberOfPPABinariesForDistribution(distribution):
        """Return the number of binaries for PPAs in a given distribution.

        Only public and published sources are considered.
        """


    def new(purpose, owner, name=None, distribution=None, description=None):
        """Create a new archive.

        :param purpose: `ArchivePurpose`;
        :param owner: `IPerson` owning the Archive;
        :param name: optional text to be used as the archive name, if not
            given it uses the names defined in
            `IArchiveSet._getDefaultArchiveNameForPurpose`;
        :param distribution: optional `IDistribution` to which the archive
            will be attached;
        :param description: optional text to be set as the archive
            description;

        :return: an `IArchive` object.
        :raises AssertionError if name is already taken within distribution.
        """

    def get(archive_id):
        """Return the IArchive with the given archive_id."""

    def getPPAByDistributionAndOwnerName(distribution, person_name, ppa_name):
        """Return a single PPA.

        :param distribution: The context IDistribution.
        :param person_name: The context IPerson.
        :param ppa_name: The name of the archive (PPA)
        """

    def getByDistroPurpose(distribution, purpose, name=None):
        """Return the IArchive with the given distribution and purpose.

        It uses the default names defined in
        `IArchiveSet._getDefaultArchiveNameForPurpose`.

        :raises AssertionError if used for with ArchivePurpose.PPA.
        """

    def getByDistroAndName(distribution, name):
        """Return the `IArchive` with the given distribution and name."""

    def __iter__():
        """Iterates over existent archives, including the main_archives."""

    def getPPAsForUser(user):
        """Return all PPAs the given user can participate.

        The result is ordered by PPA owner's displayname.
        """

    def getPPAsPendingSigningKey():
        """Return all PPAs pending signing key generation.

        The result is ordered by archive creation date.
        """

    def getLatestPPASourcePublicationsForDistribution(distribution):
        """The latest 5 PPA source publications for a given distribution.

        Private PPAs are excluded from the result.
        """

    def getMostActivePPAsForDistribution(distribution):
        """Return the 5 most active PPAs.

        The activity is currently measured by number of uploaded (published)
        sources for each PPA during the last 7 days.

        Private PPAs are excluded from the result.

        :return A list with up to 5 dictionaries containing the ppa 'title'
            and the number of 'uploads' keys and corresponding values.
        """

    def getBuildCountersForArchitecture(archive, distroarchseries):
        """Return a dictionary containing the build counters per status.

        The result is restricted to the given archive and distroarchseries.

        The returned dictionary contains the follwoing keys and values:

         * 'total': total number of builds (includes SUPERSEDED);
         * 'pending': number of builds in NEEDSBUILD or BUILDING state;
         * 'failed': number of builds in FAILEDTOBUILD, MANUALDEPWAIT,
           CHROOTWAIT and FAILEDTOUPLOAD state;
         * 'succeeded': number of SUCCESSFULLYBUILT builds.

        :param archive: target `IArchive`;
        :param distroarchseries: target `IDistroArchSeries`.

        :return a dictionary with the 4 keys specified above.
        """

    def getArchivesForDistribution(distribution, name=None, purposes=None,
        user=None):
        """Return a list of all the archives for a distribution.

        This will return all the archives for the given distribution, with
        the following parameters:

        :param distribution: target `IDistribution`
        :param name: An optional archive name which will further restrict
            the results to only those archives with this name.
        :param purposes: An optional achive purpose or list of purposes with
            which to filter the results.
        :param user: An optional `IPerson` who is requesting the archives,
            which is used to include private archives for which the user
            has permission. If it is not supplied, only public archives
            will be returned.

        :return: A queryset of all the archives for the given
            distribution matching the given params.
        """

    def getPrivatePPAs():
        """Return a result set containing all private PPAs."""


class ArchivePurpose(DBEnumeratedType):
    """The purpose, or type, of an archive.

    A distribution can be associated with different archives and this
    schema item enumerates the different archive types and their purpose.

    For example, Partner/ISV software in ubuntu is stored in a separate
    archive. PPAs are separate archives and contain packages that 'overlay'
    the ubuntu PRIMARY archive.
    """

    PRIMARY = DBItem(1, """
        Primary Archive

        This is the primary Ubuntu archive.
        """)

    PPA = DBItem(2, """
        PPA Archive

        This is a Personal Package Archive.
        """)

    PARTNER = DBItem(4, """
        Partner Archive

        This is the archive for partner packages.
        """)

    COPY = DBItem(6, """
        Generalized copy archive

        This kind of archive will be used for rebuilds, snapshots etc.
        """)


default_name_by_purpose = {
    ArchivePurpose.PRIMARY: 'primary',
    ArchivePurpose.PPA: 'ppa',
    ArchivePurpose.PARTNER: 'partner',
    }


MAIN_ARCHIVE_PURPOSES = (
    ArchivePurpose.PRIMARY,
    ArchivePurpose.PARTNER,
    )

ALLOW_RELEASE_BUILDS = (
    ArchivePurpose.PARTNER,
    ArchivePurpose.PPA,
    ArchivePurpose.COPY,
    )

# MONKEY PATCH TIME!
# Fix circular dependency issues.
from canonical.launchpad.components.apihelpers import (
    patch_entry_return_type, patch_collection_return_type,
    patch_plain_parameter_type, patch_choice_parameter_type,
    patch_reference_property)

from canonical.launchpad.interfaces.distribution import IDistribution
patch_reference_property(IArchive, 'distribution', IDistribution)

from canonical.launchpad.interfaces.archivepermission import (
    IArchivePermission)
patch_collection_return_type(
    IArchive, 'getPermissionsForPerson', IArchivePermission)
patch_collection_return_type(
    IArchive, 'getUploadersForPackage', IArchivePermission)
patch_collection_return_type(
    IArchive, 'getUploadersForComponent', IArchivePermission)
patch_collection_return_type(
    IArchive, 'getQueueAdminsForComponent', IArchivePermission)
patch_collection_return_type(
    IArchive, 'getComponentsForQueueAdmin', IArchivePermission)
patch_entry_return_type(IArchive, 'newPackageUploader', IArchivePermission)
patch_entry_return_type(IArchive, 'newComponentUploader', IArchivePermission)
patch_entry_return_type(IArchive, 'newQueueAdmin', IArchivePermission)
patch_plain_parameter_type(IArchive, 'syncSources', 'from_archive', IArchive)
patch_plain_parameter_type(IArchive, 'syncSource', 'from_archive', IArchive)

from canonical.launchpad.interfaces.distroseries import IDistroSeries
from canonical.launchpad.interfaces.publishing import (
    ISourcePackagePublishingHistory, PackagePublishingPocket,
    PackagePublishingStatus)
patch_plain_parameter_type(
    IArchive, 'getPublishedSources', 'distroseries', IDistroSeries)
patch_collection_return_type(
    IArchive, 'getPublishedSources', ISourcePackagePublishingHistory)
patch_choice_parameter_type(
    IArchive, 'getPublishedSources', 'status', PackagePublishingStatus)
patch_choice_parameter_type(
    IArchive, 'getPublishedSources', 'pocket', PackagePublishingPocket)

# This is patched here to avoid even more circular imports in
# interfaces/person.py.
from canonical.launchpad.interfaces.person import IPersonPublic
patch_reference_property(IPersonPublic, 'archive', IArchive)

