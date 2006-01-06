# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['IDistributionMirror', 'IMirrorDistroArchRelease',
           'IMirrorDistroReleaseSource', 'IMirrorProbeRecord']

from zope.schema import Bool, Choice, Datetime, TextLine
from zope.interface import Interface, Attribute

from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.interfaces.validation import (
    valid_http_url, valid_ftp_url, valid_rsync_url)
from canonical.launchpad import _


class IDistributionMirror(Interface):
    """A mirror of a given distribution."""

    owner = Choice(title=_('Owner'), required=False, readonly=True,
                   vocabulary='ValidOwner')
    distribution = Attribute(_("The distribution that is mirrored"))
    name = TextLine(
        title=_('Name'), required=True, readonly=False,
        constraint=name_validator)
    displayname = TextLine(
        title=_('Display Name'), required=False, readonly=False)
    description = TextLine(
        title=_('Description'), required=False, readonly=False)
    http_base_url = TextLine(
        title=_('HTTP URL'), required=False, readonly=False,
        constraint=valid_http_url)
    ftp_base_url = TextLine(
        title=_('FTP URL'), required=False, readonly=False,
        constraint=valid_ftp_url)
    rsync_base_url = TextLine(
        title=_('Rsync URL'), required=False, readonly=False,
        constraint=valid_rsync_url)
    pulse_source = TextLine(
        title=_('Pulse Source'), required=False, readonly=False,
        description=_("The URL where we can pulse this mirror, in case this "
                      "mirror's pulse type is Pull."))
    enabled = Bool(
        title=_('Enabled?'), required=False, readonly=False, default=False)
    speed = Choice(
        title=_('Link Speed'), required=True, readonly=False,
        vocabulary='MirrorSpeed')
    country = Choice(
        title=_('Location (Country)'), required=True, readonly=False,
        vocabulary='CountryName')
    content = Choice(
        title=_('Content'), required=True, readonly=False, 
        vocabulary='MirrorContent')
    pulse_type = Choice(
        title=_('Pulse Type'), required=True, readonly=False,
        vocabulary='MirrorPulseType')
    official_candidate = Bool(
        title=_('Official Candidate?'), required=False, readonly=False,
        default=False)
    official_approved = Bool(
        title=_('Official Approved?'), required=False, readonly=False,
        default=False)

    title = Attribute('The title of this mirror')
    source_releases = Attribute('All MirrorDistroReleaseSources of this mirror')
    arch_releases = Attribute('All MirrorDistroArchReleases of this mirror')

    def isOfficial(self):
        """Return True if this is an official mirror."""

    def newMirrorArchRelease(distro_arch_release, pocket):
        """Create and return a new MirrorDistroArchRelease for this
        distribution.
        """

    def newMirrorSourceRelease(distro_release):
        """Create and return a new MirrorDistroReleaseSource for this
        distribution.
        """


class IMirrorDistroArchRelease(Interface):
    """The mirror of the packages of a given Distro Arch Release"""

    distribution_mirror = Attribute(_("The Distribution Mirror"))
    distro_arch_release = Choice(
        title=_('Distribution Arch Release'), required=True, readonly=True,
        vocabulary='FilteredDistroArchRelease')
    status = Choice(
        title=_('Status'), required=True, readonly=False,
        vocabulary='MirrorStatus')
    pocket = Choice(
        title=_('Pocket'), required=True, readonly=False,
        vocabulary='PackagePublishingPocket')


class IMirrorDistroReleaseSource(Interface):
    """The mirror of a given Distro Release"""

    distribution_mirror = Attribute(_("The Distribution Mirror"))
    distro_release = Choice(
        title=_('Distribution Release'), required=True, readonly=True,
        vocabulary='FilteredDistroRelease')
    status = Choice(
        title=_('Status'), required=True, readonly=False,
        vocabulary='MirrorStatus')


class IMirrorProbeRecord(Interface):
    """A record stored when a mirror is probed.
    
    We store this in order to have a history of that mirror's probes.
    """

    distribution_mirror = Attribute(_("The Distribution Mirror"))
    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)

