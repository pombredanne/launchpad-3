# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Package interfaces."""

__metaclass__ = type

__all__ = [
    'IPackages',
    'IPackageSet',
    'PackageUploadStatus',
    'PackageUploadCustomFormat',
    ]

from zope.schema import Int, TextLine
from zope.interface import Interface, Attribute

from canonical.lazr import DBEnumeratedType, DBItem


class IPackages(Interface):
    """Root object for web app."""
    binary = Attribute("Binary packages")
    source = Attribute("Source packages")

    def __getitem__(name):
        """Retrieve a package set by name."""


class IPackageSet(Interface):
    """A set of packages"""
    def __getitem__(name):
        """Retrieve a package by name."""
    def __iter__():
        """Iterate over names"""


class PackageUploadStatus(DBEnumeratedType):
    """Distro Release Queue Status

    An upload has various stages it must pass through before becoming part
    of a DistroSeries. These are managed via the Upload table
    and related tables and eventually (assuming a successful upload into the
    DistroSeries) the effects are published via the PackagePublishing and
    SourcePackagePublishing tables.  """

    NEW = DBItem(0, """
        New

        This upload is either a brand-new source package or contains a
        binary package with brand new debs or similar. The package must sit
        here until someone with the right role in the DistroSeries checks
        and either accepts or rejects the upload. If the upload is accepted
        then entries will be made in the overrides tables and further
        uploads will bypass this state """)

    UNAPPROVED = DBItem(1, """
        Unapproved

        If a DistroSeries is frozen or locked out of ordinary updates then
        this state is used to mean that while the package is correct from a
        technical point of view; it has yet to be approved for inclusion in
        this DistroSeries. One use of this state may be for security
        releases where you want the security team of a DistroSeries to
        approve uploads.  """)

    ACCEPTED = DBItem(2, """
        Accepted

        An upload in this state has passed all the checks required of it and
        is ready to have its publishing records created.  """)

    DONE = DBItem(3, """
        Done

        An upload in this state has had its publishing records created if it
        needs them and is fully processed into the DistroSeries. This state
        exists so that a logging and/or auditing tool can pick up accepted
        uploads and create entries in a journal or similar before removing
        the queue item.  """)

    REJECTED = DBItem(4, """
        Rejected

        An upload which reaches this state has, for some reason or another
        not passed the requirements (technical or human) for entry into the
        DistroSeries it was targetting. As for the 'done' state, this state
        is present to allow logging tools to record the rejection and then
        clean up any subsequently unnecessary records.  """)


# If you change this (add items, change the meaning, whatever) search for
# the token ##CUSTOMFORMAT## e.g. database/queue.py or nascentupload.py and
# update the stuff marked with it.
class PackageUploadCustomFormat(DBEnumeratedType):
    """Custom formats valid for the upload queue

    An upload has various files potentially associated with it, from source
    package releases, through binary builds, to specialist upload forms such
    as a debian-installer tarball or a set of translations.
    """

    DEBIAN_INSTALLER = DBItem(0, """
        raw-installer

        A raw-installer file is a tarball. This is processed as a version
        of the debian-installer to be unpacked into the archive root.
        """)

    ROSETTA_TRANSLATIONS = DBItem(1, """
        raw-translations

        A raw-translations file is a tarball. This is passed to the rosetta
        import queue to be incorporated into that package's translations.
        """)

    DIST_UPGRADER = DBItem(2, """
        raw-dist-upgrader

        A raw-dist-upgrader file is a tarball. It is simply published into
        the archive.
        """)

    DDTP_TARBALL = DBItem(3, """
        raw-ddtp-tarball

        A raw-ddtp-tarball contains all the translated package description
        indexes for a component.
        """)
