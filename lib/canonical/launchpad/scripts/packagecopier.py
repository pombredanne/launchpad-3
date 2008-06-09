# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
"""PackageCopier utilities."""

__metaclass__ = type

__all__ = [
    'PackageCopier',
    'UnembargoSecurityPackage',
    ]

import os
import tempfile

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    ArchivePurpose, IBinaryPackagePublishingHistory, ILibraryFileAliasSet,
    ISourcePackagePublishingHistory, NotFoundError, PackagePublishingStatus)
from canonical.launchpad.scripts.ftpmasterbase import (
    build_package_location, SoyuzScript, SoyuzScriptError)
from canonical.librarian.utils import copy_and_close


class PackageCopier(SoyuzScript):
    """SoyuzScript that copies published packages between locations.

    Possible exceptions raised are:
    * PackageLocationError: specified package or distro does not exist
    * PackageCopyError: the copy operation itself has failed
    * LaunchpadScriptFailure: only raised if entering via main(), ie this
        code is running as a genuine script.  In this case, this is
        also the _only_ exception to be raised.

    The test harness doesn't enter via main(), it calls doCopy(), so
    it only sees the first two exceptions.
    """

    usage = '%prog -s warty mozilla-firefox --to-suite hoary'
    description = 'MOVE or COPY a published package to another suite.'

    def add_my_options(self):

        SoyuzScript.add_my_options(self)

        self.parser.add_option(
            "-b", "--include-binaries", dest="include_binaries",
            default=False, action="store_true",
            help='Whether to copy related binaries or not.')

        self.parser.add_option(
            '--to-distribution', dest='to_distribution',
            default='ubuntu', action='store',
            help='Destination distribution name.')

        self.parser.add_option(
            '--to-suite', dest='to_suite', default=None,
            action='store', help='Destination suite name.')

        self.parser.add_option(
            '--to-ppa', dest='to_ppa', default=None,
            action='store', help='Destination PPA owner name.')

        self.parser.add_option(
            '--to-partner', dest='to_partner', default=False,
            action='store_true', help='Destination set to PARTNER archive.')

    def checkCopyOptions(self):
        """Check if the locations options are sane.

         * Catch Cross-PARTNER copies, they are not allowed.
         * Catch simulataneous PPA and PARTNER locations or destinations,
           results are unpredictable (in fact, the code will ignore PPA and
           operate only in PARTNER, but that's odd)
        """
        if ((self.options.partner_archive and not self.options.to_partner)
            or (self.options.to_partner and not
                self.options.partner_archive)):
            raise SoyuzScriptError(
                "Cross-PARTNER copies are not allowed.")

        if self.options.archive_owner_name and self.options.partner_archive:
            raise SoyuzScriptError(
                "Cannot operate with location PARTNER and PPA "
                "simultaneously.")

        if self.options.to_ppa and self.options.to_partner:
            raise SoyuzScriptError(
                "Cannot operate with destination PARTNER and PPA "
                "simultaneously.")

    def mainTask(self):
        """Execute package copy procedure.

        Copy source publication and optionally also copy its binaries by
        passing '-b' (include_binary) option.

        Modules using this class outside of its normal usage in the
        copy-package.py script can call this method to start the copy.

        In this case the caller can override test_args on __init__
        to set the command line arguments.

        Can raise SoyuzScriptError.
        """
        assert self.location, (
            "location is not available, call PackageCopier.setupLocation() "
            "before dealing with mainTask.")

        self.checkCopyOptions()

        sourcename = self.args[0]

        self.setupDestination()

        self.logger.info("FROM: %s" % (self.location))
        self.logger.info("TO: %s" % (self.destination))

        to_copy = []
        source_pub = self.findLatestPublishedSource(sourcename)
        to_copy.append(source_pub)
        if self.options.include_binaries:
            to_copy.extend(source_pub.getPublishedBinaries())

        self.logger.info("Copy candidates:")
        for candidate in to_copy:
            self.logger.info('\t%s' % candidate.displayname)

        copies = []
        for candidate in to_copy:
            try:
                copied = candidate.copyTo(
                    distroseries = self.destination.distroseries,
                    pocket = self.destination.pocket,
                    archive = self.destination.archive)
            except NotFoundError:
                self.logger.warn('Could not copy %s' % candidate.displayname)
            else:
                copies.append(copied)

        if len(copies) == 1:
            self.logger.info(
                "%s package successfully copied." % len(copies))
        elif len(copies) > 1:
            self.logger.info(
                "%s packages successfully copied." % len(copies))
        else:
            self.logger.info("No package copied (bug ?!?).")

        # Information returned mainly for the benefit of the test harness.
        return copies

    def setupDestination(self):
        """Build PackageLocation for the destination context."""
        if self.options.to_partner:
            self.destination = build_package_location(
                self.options.to_distribution,
                self.options.to_suite,
                ArchivePurpose.PARTNER)
        elif self.options.to_ppa:
            self.destination = build_package_location(
                self.options.to_distribution,
                self.options.to_suite,
                ArchivePurpose.PPA,
                self.options.to_ppa)
        else:
            self.destination = build_package_location(
                self.options.to_distribution,
                self.options.to_suite)

        if self.location == self.destination:
            raise SoyuzScriptError(
                "Can not sync between the same locations: '%s' to '%s'" % (
                self.location, self.destination))


class UnembargoSecurityPackage(PackageCopier):
    """`SoyuzScript` that unembargoes security packages and their builds.

    Security builds are done in the ubuntu-security private PPA.
    When they are ready to be unembargoed, this script will copy
    them from the PPA to the Ubuntu archive and re-upload any files
    from the restricted librarian into the non-restricted one.

    This script simply wraps up PackageCopier with some nicer options,
    and implements the file re-uploading.

    An assumption is made, to reduce the number of command line options,
    that packages are always copied between the same distroseries.
    """

    usage = ("%prog [-d <distribution>] [-s <series>] [--ppa <private ppa>] "
             "<package(s)>")
    description = ("Unembargo packages in a private PPA by copying to the "
                   "specified location and re-uploading any files to the "
                   "unrestricted librarian.")

    def add_my_options(self):
        """Add -d, -s, dry-run and confirmation options."""
        SoyuzScript.add_distro_options(self)
        SoyuzScript.add_transaction_options(self)

        self.parser.add_option(
            "-p", "--ppa", dest="archive_owner_name",
            default="ubuntu-security", action="store",
            help="Private PPA owner's name.")

    def mainTask(self):
        """Invoke PackageCopier to copy the package(s) and re-upload files."""

        assert self.location, (
            "location is not available, call SoyuzScript.setupLocation() "
            "before calling mainTask().")

        # Set up the options for PackageCopier that are needed in addition
        # to the ones that this class sets up.
        self.options.to_partner = False
        self.options.to_ppa = False
        self.options.partner_archive = None
        self.options.include_binaries = True
        self.options.to_distribution = self.options.distribution_name
        self.options.to_suite = "-".join((self.options.suite, "security"))
        self.options.version = None
        self.options.component = None

        # Invoke the package copy operation.
        copies = PackageCopier.mainTask(self)

        # Do an ancestry check to override the component.
        self.overrideFromAncestry(copies)

        # Now re-upload the files associated with the package.
        for pub_record in copies:
            self.copyPublishedFiles(pub_record, False)

        # Return this for the benefit of the test suite.
        return copies

    def copyPublishedFiles(self, pub_record, to_restricted):
        """Move files for a publishing record between librarians.

        :param pub_record: One of a SourcePackagePublishingHistory or
            BinaryPackagePublishingHistory record.
        :param to_restricted: True or False depending on whether the target
            librarian to be used is the restricted one or not.
        """
        if ISourcePackagePublishingHistory.providedBy(pub_record):
            files = pub_record.sourcepackagerelease.files
            # Re-upload the changes file if necessary.
            sourcepackagerelease = pub_record.sourcepackagerelease
            queue_record = sourcepackagerelease.getQueueRecord(
                distroseries=pub_record.distroseries)
            if queue_record is not None:
                changesfile = queue_record.changesfile
            else:
                changesfile = None
            if changesfile is not None and changesfile.restricted:
                new_lfa = self.reUploadFile(changesfile, False)
                queue_record.changesfile = new_lfa
        elif IBinaryPackagePublishingHistory.providedBy(pub_record):
            files = pub_record.binarypackagerelease.files
        else:
            raise AssertionError(
                "pub_record is not one of SourcePackagePublishingHistory "
                "or BinaryPackagePublishingHistory")

        for package_file in files:
            # Open the old library file.
            libfile = package_file.libraryfile
            new_lfa = self.reUploadFile(libfile, to_restricted)
            package_file.libraryfile = new_lfa

    def reUploadFile(self, libfile, to_restricted):
        """Re-upload a librarian file between librarians.

        :param libfile: A LibraryFileAlias for the file.
        :param to_restricted: True if copying to the restricted librarian.
        :return: A new LibraryFileAlias that is not restricted.
        """
        libfile.open()

        # Make a temporary file to hold the download.  It's annoying
        # having to download to a temp file but there are no guarantees
        # how large the files are, so using StringIO would be dangerous.
        fd, filepath = tempfile.mkstemp()
        temp_file = open(filepath, "w")

        # Read the old library file into the temp file.
        copy_and_close(libfile, temp_file)

        # Upload the file to the unrestricted librarian and make
        # sure the publishing record points to it.
        librarian = getUtility(ILibraryFileAliasSet)
        new_lfa = librarian.create(
            libfile.filename, libfile.content.filesize,
            open(filepath, "rb"), libfile.mimetype,
            restricted=to_restricted)

        self.logger.info(
            "Re-uploaded %s to the unrestricted librarian with ID %d" % (
                libfile.filename, new_lfa.id))

        # Junk the temporary file.
        os.remove(filepath)

        return new_lfa

    def overrideFromAncestry(self, pub_records):
        """Set the right published component from publishing ancestry.

        Start with the publishing records and fall back to the original
        uploaded package if necessary.
        """
        for pub_record in pub_records:
            archive = pub_record.archive
            if ISourcePackagePublishingHistory.providedBy(pub_record):
                is_source = True
                source_package = pub_record.sourcepackagerelease
                prev_published = archive.getPublishedSources(
                    name=source_package.sourcepackagename.name,
                    status=PackagePublishingStatus.PUBLISHED,
                    distroseries=pub_record.distroseries,
                    exact_match=True)
            elif IBinaryPackagePublishingHistory.providedBy(pub_record):
                is_source = False
                binary_package = pub_record.binarypackagerelease
                prev_published = archive.getAllPublishedBinaries(
                    name=binary_package.binarypackagename.name,
                    status=PackagePublishingStatus.PUBLISHED,
                    distroarchseries=pub_record.distroarchseries,
                    exact_match=True)
            else:
                raise AssertionError(
                    "pub_records contains something that's not one of "
                    "SourcePackagePublishingHistory or "
                    "BinaryPackagePublishingHistory")

            if prev_published.count() > 0:
                # Use the first record (the most recently published).
                component = prev_published[0].component
            else:
                # It's not been published yet, check the original package.
                if is_source:
                    component = pub_record.sourcepackagerelease.component
                else:
                    component = pub_record.binarypackagerelease.component

            # We don't want to use changeOverride here because it
            # creates a new publishing record.
            pub_record.secure_record.component = component
