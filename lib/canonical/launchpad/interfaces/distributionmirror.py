# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['IDistributionMirror', 'IMirrorDistroArchRelease',
           'IMirrorDistroReleaseSource', 'IMirrorProbeRecord',
           'IDistributionMirrorSet', 'IMirrorCDImageDistroRelease',
           'PROBE_INTERVAL', 'UnableToFetchCDImageFileList',
           'main_ubuntu_mirrors_http_urls']

from zope.schema import Bool, Choice, Datetime, Int, TextLine
from zope.interface import Interface, Attribute
from zope.component import getUtility

from canonical.lp.dbschema import MirrorContent
from canonical.launchpad.fields import ContentNameField, URIField
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad import _


# The number of hours before we bother probing a mirror again
PROBE_INTERVAL = 23

# XXX: Although one day this will probably have to become a per-distribution
# setting, we don't need to worry about it now.
# -- Guilherme Salgado, 2007-02-12
main_ubuntu_mirrors_http_urls = {
    MirrorContent.ARCHIVE: 'http://archive.ubuntu.com',
    MirrorContent.RELEASE: 'http://releases.ubuntu.com'}


class DistributionMirrorNameField(ContentNameField):
    errormessage = _("%s is already in use by another distribution mirror.")

    @property
    def _content_iface(self):
        return IDistributionMirror

    def _getByName(self, name):
        return getUtility(IDistributionMirrorSet).getByName(name)


class DistroMirrorURIField(URIField):
    """Base class for the DistributionMirror unique URI fields."""

    def getMirrorByURI(self, uri):
        """Return the mirror with the given URI."""
        raise NotImplementedError()

    def _validate(self, value):
        # import here to avoid circular import
        from canonical.launchpad.webapp import canonical_url
        from canonical.launchpad.webapp.uri import URI

        super(DistroMirrorURIField, self)._validate(value)
        # URIField has already established that we have a valid URI
        uri = URI(value)

        if (IDistributionMirror.providedBy(self.context)
            and URI(self.get(self.context)) == uri):
            return # url was not changed

        mirror = self.getMirrorByURI(str(uri))
        if mirror is not None:
            message = _(
                'The distribution mirror <a href="%s">%s</a> is already '
                'registered with this URL.')
            raise LaunchpadValidationError(
                message, canonical_url(mirror), mirror.title)


class DistroMirrorHTTPURIField(DistroMirrorURIField):

    def getMirrorByURI(self, url):
        return getUtility(IDistributionMirrorSet).getByHttpUrl(url)


class DistroMirrorFTPURIField(DistroMirrorURIField):

    def getMirrorByURI(self, url):
        return getUtility(IDistributionMirrorSet).getByFtpUrl(url)


class DistroMirrorRsyncURIField(DistroMirrorURIField):

    def getMirrorByURI(self, url):
        return getUtility(IDistributionMirrorSet).getByRsyncUrl(url)


class IDistributionMirror(Interface):
    """A mirror of a given distribution."""

    id = Int(title=_('The unique id'), required=True, readonly=True)
    owner = Choice(title=_('Owner'), required=False, readonly=True,
                   vocabulary='ValidOwner')
    distribution = Attribute(_("The distribution that is mirrored"))
    name = DistributionMirrorNameField(
        title=_('Name'), required=True, readonly=False,
        description=_('A short and unique name for this mirror.'),
        constraint=name_validator)
    displayname = TextLine(
        title=_('Organisation Name'), required=False, readonly=False,
        description=_('The name of the organization hosting this mirror.'))
    description = TextLine(
        title=_('Description'), required=False, readonly=False)
    http_base_url = DistroMirrorHTTPURIField(
        title=_('HTTP URL'), required=False, readonly=False,
        allowed_schemes=['http'], allow_userinfo=False,
        allow_query=False, allow_fragment=False, trailing_slash=True,
        description=_('e.g.: http://archive.ubuntu.com/ubuntu/'))
    ftp_base_url = DistroMirrorFTPURIField(
        title=_('FTP URL'), required=False, readonly=False,
        allowed_schemes=['ftp'], allow_userinfo=False,
        allow_query=False, allow_fragment=False, trailing_slash=True,
        description=_('e.g.: ftp://archive.ubuntu.com/ubuntu/'))
    rsync_base_url = DistroMirrorRsyncURIField(
        title=_('Rsync URL'), required=False, readonly=False,
        allowed_schemes=['rsync'], allow_userinfo=False,
        allow_query=False, allow_fragment=False, trailing_slash=True,
        description=_('e.g.: rsync://archive.ubuntu.com/ubuntu/'))
    enabled = Bool(
        title=_('This mirror was probed successfully.'),
        required=False, readonly=False, default=False)
    speed = Choice(
        title=_('Link Speed'), required=True, readonly=False,
        vocabulary='MirrorSpeed')
    country = Choice(
        title=_('Location (Country)'), required=True, readonly=False,
        vocabulary='CountryName')
    content = Choice(
        title=_('Content'), required=True, readonly=False, 
        description=_(
            'Choose Release if this mirror contains CD images of any of the '
            'various releases of this distribution, or choose Archive if this '
            'mirror contains packages for this distribution and is meant to '
            'be used in conjunction with apt.'),
        vocabulary='MirrorContent')
    official_candidate = Bool(
        title=_('Apply to be an official mirror of this distribution'),
        required=False, readonly=False, default=True)
    official_approved = Bool(
        title=_('This is one of the official mirrors of this distribution'),
        required=False, readonly=False, default=False)

    title = Attribute('The title of this mirror')
    cdimage_releases = Attribute(
        'All MirrorCDImageDistroReleases of this mirror')
    source_releases = Attribute('All MirrorDistroReleaseSources of this mirror')
    arch_releases = Attribute('All MirrorDistroArchReleases of this mirror')
    last_probe_record = Attribute('The last MirrorProbeRecord for this mirror.')
    all_probe_records = Attribute('All MirrorProbeRecords for this mirror.')
    has_ftp_or_rsync_base_url = Bool(
        title=_('Does this mirror have a ftp or rsync base URL?'))
    base_url = Attribute('The HTTP or FTP base URL of this mirror')

    def getSummarizedMirroredSourceReleases():
        """Return a summarized list of this distribution_mirror's 
        MirrorDistroReleaseSource objects.

        Summarized, in this case, means that it ignores pocket and components
        and returns the MirrorDistroReleaseSource with the worst status for
        each distrorelease of this distribution mirror.
        """

    def getSummarizedMirroredArchReleases():
        """Return a summarized list of this distribution_mirror's 
        MirrorDistroArchRelease objects.

        Summarized, in this case, means that it ignores pocket and components
        and returns the MirrorDistroArchRelease with the worst status for
        each distro_arch_release of this distribution mirror.
        """

    def getOverallStatus():
        """Return this mirror's overall status.

        For ARCHIVE mirrors, the overall status is the worst status of all
        of this mirror's content objects (MirrorDistroArchRelease,
        MirrorDistroReleaseSource or MirrorCDImageDistroReleases).

        For RELEASE mirrors, the overall status is either UPTODATE, if the
        mirror contains all ISO images that it should or UNKNOWN if it doesn't
        contain one or more ISO images.
        """

    def isOfficial():
        """Return True if this is an official mirror."""

    def shouldDisable(self, expected_file_count=None):
        """Should this mirror be marked disabled?

        If this is a RELEASE mirror then expected_file_count must not be None,
        and it should be disabled if the number of cdimage_releases it
        contains is smaller than the given expected_file_count.

        If this is an ARCHIVE mirror, then it should be disabled only if it
        has no content at all.

        We could use len(get_expected_cdimage_paths()) to obtain the
        expected_file_count, but that's not a good idea because that method
        gets the expected paths from releases.ubuntu.com, which is something
        we don't have control over.
        """

    def disable(notify_owner):
        """Mark this mirror as disabled and notify the distributions's mirror
        admins by email.

        if notify_owner is True, an identical notification is sent to the
        mirror owner.

        This method can't be called before a probe record has been created
        because we'll link to the latest probe record in the email we send to
        notify the owner.

        The notification(s) are actually sent only if this mirror was
        previously enabled or if it was probed only once.
        """

    def newProbeRecord(log_file):
        """Create and return a new MirrorProbeRecord for this mirror."""

    def deleteMirrorDistroArchRelease(distro_arch_release, pocket, component):
        """Delete the MirrorDistroArchRelease with the given arch release and
        pocket, in case it exists.
        """

    def ensureMirrorDistroArchRelease(distro_arch_release, pocket, component):
        """Check if we have a MirrorDistroArchRelease with the given arch
        release and pocket, creating one if not.

        Return that MirrorDistroArchRelease.
        """

    def ensureMirrorDistroReleaseSource(distrorelease, pocket, component):
        """Check if we have a MirrorDistroReleaseSource with the given distro
        release, creating one if not.

        Return that MirrorDistroReleaseSource.
        """

    def deleteMirrorDistroReleaseSource(distrorelease, pocket, component):
        """Delete the MirrorDistroReleaseSource with the given distro release,
        in case it exists.
        """

    def ensureMirrorCDImageRelease(arch_release, flavour):
        """Check if we have a MirrorCDImageDistroRelease with the given
        arch release and flavour, creating one if not.

        Return that MirrorCDImageDistroRelease.
        """

    def deleteMirrorCDImageRelease(arch_release, flavour):
        """Delete the MirrorCDImageDistroRelease with the given arch 
        release and flavour, in case it exists.
        """

    def deleteAllMirrorCDImageReleases():
        """Delete all MirrorCDImageDistroReleases of this mirror."""

    def getExpectedPackagesPaths():
        """Get all paths where we can find Packages.gz files on this mirror.

        Return a list containing, for each path, the DistroArchRelease,
        the PackagePublishingPocket and the Component to which that given
        Packages.gz file refer to and the path to the file itself.
        """

    def getExpectedSourcesPaths():
        """Get all paths where we can find Sources.gz files on this mirror.

        Return a list containing, for each path, the DistroRelease, the
        PackagePublishingPocket and the Component to which that given
        Sources.gz file refer to and the path to the file itself.
        """


class UnableToFetchCDImageFileList(Exception):
    """Couldn't feth the file list needed for probing release mirrors."""


class IDistributionMirrorSet(Interface):
    """The set of DistributionMirrors"""

    def __getitem__(mirror_id):
        """Return the DistributionMirror with the given id."""

    def getMirrorsToProbe(content_type, ignore_last_probe=False):
        """Return all official mirrors with the given content type that need
        to be probed.

        A mirror needs to be probed either if it was never probed before or if
        it wasn't probed in the last PROBE_INTERVAL hours.

        If ignore_last_probe is True, then all official mirrors of the given
        content type will be probed even if they were probed in the last 
        PROBE_INTERVAL hours.
        """

    def getBestMirrorsForCountry(country, content_type):
        """Return the best mirrors to be used by someone in the given country.

        The list of mirrors is composed by the official mirrors located in
        the given country (or in the country's continent if the country
        doesn't have any) plus the main mirror of that content type.
        """

    def getByName(name):
        """Return the mirror with the given name or None."""

    def getByHttpUrl(url):
        """Return the mirror with the given HTTP URL or None."""

    def getByFtpUrl(url):
        """Return the mirror with the given FTP URL or None."""

    def getByRsyncUrl(url):
        """Return the mirror with the given Rsync URL or None."""


class IMirrorDistroArchRelease(Interface):
    """The mirror of the packages of a given Distro Arch Release"""

    distribution_mirror = Attribute(_("The Distribution Mirror"))
    distro_arch_release = Choice(
        title=_('Distribution Arch Release'), required=True, readonly=True,
        vocabulary='FilteredDistroArchRelease')
    status = Choice(
        title=_('Status'), required=True, readonly=False,
        vocabulary='MirrorStatus')
    # Is it possible to use a Choice here without specifying a vocabulary?
    component = Int(title=_('Component'), required=True, readonly=True)
    pocket = Choice(
        title=_('Pocket'), required=True, readonly=True,
        vocabulary='PackagePublishingPocket')

    def getURLsToCheckUpdateness():
        """Return a dictionary mapping each different MirrorStatus to a URL on
        this mirror.

        If there's not publishing records for this DistroArchRelease,
        Component and Pocket, an empty dictionary is returned.

        These URLs should be checked and, if they are accessible, we know
        that's the current status of this mirror.
        """


class IMirrorDistroReleaseSource(Interface):
    """The mirror of a given Distro Release"""

    distribution_mirror = Attribute(_("The Distribution Mirror"))
    distrorelease = Choice(
        title=_('Distribution Release'), required=True, readonly=True,
        vocabulary='FilteredDistroRelease')
    status = Choice(
        title=_('Status'), required=True, readonly=False,
        vocabulary='MirrorStatus')
    # Is it possible to use a Choice here without specifying a vocabulary?
    component = Int(title=_('Component'), required=True, readonly=True)
    pocket = Choice(
        title=_('Pocket'), required=True, readonly=True,
        vocabulary='PackagePublishingPocket')

    def getURLsToCheckUpdateness():
        """Return a dictionary mapping each different MirrorStatus to a URL on
        this mirror.

        If there's not publishing records for this DistroRelease, Component
        and Pocket, an empty dictionary is returned.

        These URLs should be checked and, if they are accessible, we know
        that's the current status of this mirror.
        """


class IMirrorCDImageDistroRelease(Interface):
    """The mirror of a given CD/DVD image"""

    distribution_mirror = Attribute(_("The Distribution Mirror"))
    distrorelease = Attribute(_("The DistroRelease"))
    flavour = TextLine(
        title=_("The Flavour's name"), required=True, readonly=True)


class IMirrorProbeRecord(Interface):
    """A record stored when a mirror is probed.

    We store this in order to have a history of that mirror's probes.
    """

    distribution_mirror = Attribute(_("The Distribution Mirror"))
    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)
    log_file = Attribute(_("The log of this probing."))

