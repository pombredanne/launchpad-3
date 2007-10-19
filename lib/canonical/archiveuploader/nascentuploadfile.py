# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
"""Specific models for uploaded files"""

__metaclass__ = type

__all__ = [
    'UploadError',
    'UploadWarning',
    'splitComponentAndSection',
    'NascentUploadFile',
    'CustomUploadFile',
    'PackageUploadFile',
    'SourceUploadFile',
    'BaseBinaryUploadFile',
    'UdebBinaryUploadFile',
    'DebBinaryUploadFile',
    ]

import apt_inst
import apt_pkg
import os
import md5
import re
import sha
import subprocess
import sys
import time

from zope.component import getUtility

from canonical.archiveuploader.utils import (
    prefix_multi_line_string, re_taint_free, re_isadeb, re_issource,
    re_no_epoch, re_no_revision, re_valid_version, re_valid_pkg_name,
    re_extract_src_version)
from canonical.encoding import guess as guess_encoding
from canonical.launchpad.interfaces import (
    ArchivePurpose, IComponentSet, ISectionSet, IBuildSet,
    ILibraryFileAliasSet, IBinaryPackageNameSet)
from canonical.librarian.utils import filechunks
from canonical.lp.dbschema import (
    PackagePublishingPriority, PackageUploadCustomFormat,
    PackageUploadStatus, BinaryPackageFormat, BuildStatus)


apt_pkg.InitSystem()

class UploadError(Exception):
    """All upload errors are returned in this form."""

class UploadWarning(Warning):
    """All upload warnings are returned in this form."""


class TarFileDateChecker:
    """Verify all files in a tar in a deb are within a given date range.

    This was taken from jennifer in the DAK suite.
    """
    def __init__(self, future_cutoff, past_cutoff):
        """Setup timestamp limits """
        self.reset()
        self.future_cutoff = future_cutoff
        self.past_cutoff = past_cutoff

    def reset(self):
        """Reset local values."""
        self.future_files = {}
        self.ancient_files = {}

    def callback(self, kind, name, link, mode, uid, gid, size, mtime,
                 major, minor):
        """Callback designed to cope with apt_inst.debExtract.

        It check and store timestamp details of the extracted DEB.
        """
        if mtime > self.future_cutoff:
            self.future_files[name] = mtime
        if mtime < self.past_cutoff:
            self.ancient_files[name] = mtime


def splitComponentAndSection(component_and_section):
    """Split the component out of the section."""
    if "/" not in component_and_section:
        return "main", component_and_section
    return component_and_section.split("/", 1)


class NascentUploadFile:
    """A nascent uploaded file is a file on disk that is part of an upload.

    The filename, along with information about it, is kept here.
    """
    new = False
    sha_digest = None

    # Files need their content type for creating in the librarian.
    # This maps endings of filenames onto content types we may encounter
    # in the processing of an upload.
    filename_ending_content_type_map = {
        ".dsc": "text/x-debian-source-package",
        ".deb": "application/x-debian-package",
        ".udeb": "application/x-micro-debian-package",
        ".diff.gz": "application/gzipped-patch",
        ".tar.gz": "application/gzipped-tar"
        }

    def __init__(self, filepath, digest, size, component_and_section,
                 priority_name, policy, logger):
        self.filepath = filepath
        self.digest = digest
        self.priority_name = priority_name
        self.policy = policy
        self.logger = logger

        self.size = int(size)
        self.component_name, self.section_name = (
            splitComponentAndSection(component_and_section))

        self.librarian = getUtility(ILibraryFileAliasSet)

    #
    # Helpers used quen inserting into queue
    #

    @property
    def content_type(self):
        """The content type for this file ready for adding to the librarian."""
        for content_type_map in self.filename_ending_content_type_map.items():
            ending, content_type = content_type_map
            if self.filename.endswith(ending):
                return content_type
        return "application/octet-stream"

    #
    # Useful properties.
    #
    @property
    def filename(self):
        """Return the NascentUpload filename."""
        return os.path.basename(self.filepath)

    @property
    def dirname(self):
        """Return the NascentUpload filename."""
        return os.path.dirname(self.filepath)


    @property
    def exists_on_disk(self):
        """Whether or not the file is present on disk."""
        return os.path.exists(self.filepath)

    #
    # DB storage helpers
    #

    def storeInDatabase(self):
        """Implement this to store this representation in the database."""
        raise NotImplementedError

    #
    # Verification
    #

    def verify(self):
        """Implemented locally.

        It does specific checks acording the subclass type and returns
        an iterator over all the encountered errors and warnings.
        """
        raise NotImplementedError

    def checkNameIsTaintFree(self):
        """Verify if the filename contains forbidden characters."""
        if not re_taint_free.match(self.filename):
            raise UploadError("Tainted filename: '%s'." % (file))

    def checkSizeAndCheckSum(self):
        """Check the md5sum and size of the nascent file.

        Raise UploadError if the digest or size does not match or if the
        file is not found on the disk.

        Populate self.sha_digest with the calculated sha1 digest of the
        file on disk.
        """
        if not self.exists_on_disk:
            raise UploadError(
                "File %s mentioned in the changes file was not found."
                % self.filename)

        # Read in the file and compute its md5 and sha1 checksums and remember
        # the size of the file as read-in.
        digest = md5.md5()
        sha_cksum = sha.sha()
        ckfile = open(self.filepath, "r")
        size = 0
        for chunk in filechunks(ckfile):
            digest.update(chunk)
            sha_cksum.update(chunk)
            size += len(chunk)
        ckfile.close()

        # Check the size and checksum match what we were told in __init__
        if digest.hexdigest() != self.digest:
            raise UploadError(
                "File %s mentioned in the changes has a checksum mismatch. "
                "%s != %s" % (self.filename, digest.hexdigest(), self.digest))
        if size != self.size:
            raise UploadError(
                "File %s mentioned in the changes has a size mismatch. "
                "%s != %s" % (self.filename, size, self.size))

        # The sha_digest is used later when verifying packages mentioned
        # in the DSC file; it's used to compare versus files in the
        # Librarian.
        self.sha_digest = sha_cksum.hexdigest()


class CustomUploadFile(NascentUploadFile):
    """NascentUpload file for Custom uploads.

    Custom uploads are anything else than source or binaries that are meant
    to be published in the archive.

    They are usually Tarballs which are processed according its type and
    results in new archive files.
    """

    # This is a marker as per the comment in dbschema.py: ##CUSTOMFORMAT##
    # Essentially if you change anything to do with custom formats, grep for
    # the marker in the codebase and make sure the same changes are made
    # everywhere which needs them.
    custom_sections = {
        'raw-installer': PackageUploadCustomFormat.DEBIAN_INSTALLER,
        'raw-translations': PackageUploadCustomFormat.ROSETTA_TRANSLATIONS,
        'raw-dist-upgrader': PackageUploadCustomFormat.DIST_UPGRADER,
        'raw-ddtp-tarball': PackageUploadCustomFormat.DDTP_TARBALL,
        }

    @property
    def custom_type(self):
        """The custom upload type for this file. (None if not custom)."""
        return self.custom_sections[self.section_name]

    def verify(self):
        """Verify CustomUploadFile.

        Simply check is the given section is allowed for custom uploads.
        It returns an iterator over all the encountered errors and warnings.
        """
        if self.section_name not in self.custom_sections:
            yield UploadError(
                "Unsupported custom section name %r" % self.section_name)

    def storeInDatabase(self):
        """Create and return the corresponding LibraryFileAlias reference."""
        libraryfile = self.librarian.create(
            self.filename, self.size,
            open(self.filepath, "rb"),
            self.content_type)
        return libraryfile


class PackageUploadFile(NascentUploadFile):
    """Base class to model sources and binary files contained in a upload. """

    def __init__(self, filepath, digest, size, component_and_section,
                 priority_name, package, version, changes, policy, logger):
        """Check presence of the component and section from an uploaded_file.

        They need to satisfy at least the NEW queue constraints that includes
        SourcePackageRelease creation, so component and section need to exist.
        Even if they might be overriden in the future.
        """
        NascentUploadFile.__init__(
            self, filepath, digest, size, component_and_section,
            priority_name, policy, logger)
        self.package = package
        self.version = version
        self.changes = changes

        valid_components = [component.name for component in
                            getUtility(IComponentSet)]
        valid_sections = [section.name for section in getUtility(ISectionSet)]

        if self.section_name not in valid_sections:
            # We used to reject invalid sections; when testing stuff we
            # were forced to accept a package with a broken section
            # (linux-meta_2.6.12.16_i386). Result: packages with invalid
            # sections now get put into misc -- cprov 20060119
            if self.policy.archive.purpose == ArchivePurpose.PPA:
                # PPA uploads should not override because it will probably
                # make the section inconsistent with the one in the .dsc.
                raise UploadError(
                    "%s: Section %r is not valid" % (
                    self.filename, self.section_name))
            else:
                default_section = 'misc'
                self.logger.warn("Unable to grok section %r, "
                                 "overriding it with %s"
                          % (self.section_name, default_section))
                self.section_name = default_section

        if self.component_name not in valid_components:
            raise UploadError(
                "%s: Component %r is not valid" % (
                self.filename, self.component_name))


    @property
    def component(self):
        """Return an IComponent for self.component.name."""
        return getUtility(IComponentSet)[self.component_name]

    @property
    def section(self):
        """Return an ISection for self.section_name."""
        return getUtility(ISectionSet)[self.section_name]


class SourceUploadFile(PackageUploadFile):
    """Files mentioned in changesfile as source (orig, diff, tar).

    This class only check consistency on information contained in
    changesfile (CheckSum, Size, component, section, filename).
    Further checks on file contents and package consistency are done
    in DSCFile.
    """
    def verify(self):
        """Verify the uploaded source file.

        It returns an iterator over all the encountered errors and warnings.
        """
        self.logger.debug("Verifying source file %s" % self.filename)

        if 'source' not in self.changes.architectures:
            yield UploadError("%s: changes file doesn't list 'source' in "
                "Architecture field." % (self.filename))

        version_chopped = re_no_epoch.sub('', self.version)
        if self.filename.endswith("orig.tar.gz"):
            version_chopped = re_no_revision.sub('', version_chopped)

        source_match = re_issource.match(self.filename)
        filename_version = source_match.group(2)
        if filename_version != version_chopped:
            yield UploadError("%s: should be %s according to changes file."
                % (filename_version, version_chopped))


class BaseBinaryUploadFile(PackageUploadFile):
    """Base methods for binary upload modeling."""

    format = None

    # Capitalised because we extract these directly from the control file.
    mandatory_fields = set(["Package", "Architecture", "Version"])

    # Map priorities to their dbschema valuesa
    # We treat a priority of '-' as EXTRA since some packages in some distros
    # are broken and we can't fix the world.
    priority_map = {
        "required": PackagePublishingPriority.REQUIRED,
        "important": PackagePublishingPriority.IMPORTANT,
        "standard": PackagePublishingPriority.STANDARD,
        "optional": PackagePublishingPriority.OPTIONAL,
        "extra": PackagePublishingPriority.EXTRA,
        "-": PackagePublishingPriority.EXTRA
        }

    # These are divined when parsing the package file in verify(), and
    # then used to locate or create the relevant sources and build.
    control = None
    control_version = None
    sourcepackagerelease = None
    source_name = None
    source_version = None

    def __init__(self, filepath, digest, size, component_and_section,
                 priority_name, package, version, changes, policy, logger):

        PackageUploadFile.__init__(
            self, filepath, digest, size, component_and_section,
            priority_name, package, version, changes, policy, logger)

        if self.priority_name not in self.priority_map:
            default_priority = 'extra'
            self.logger.warn(
                 "Unable to grok priority %r, overriding it with %s"
                 % (self.priority_name, default_priority))
            self.priority_name = default_priority

        # Yeah, this is weird. Where else can I discover this without
        # unpacking the deb file, though?
        binary_match = re_isadeb.match(self.filename)
        self.architecture = binary_match.group(3)

    #
    # Useful properties.
    #

    @property
    def is_archindep(self):
        """Check if the binary is targeted to architecture 'all'.

        We call binaries in this condition 'architecture-independent', i.e.
        They can be build in any architecture and the result will fit all
        architectures available.
        """
        return self.architecture.lower() == 'all'

    @property
    def archtag(self):
        """Return the binary target architecture.

        If the binary is architecture independent, return the architecture
        of the machine that has built it (it is encoded in the changesfile
        name).
        """
        archtag = self.architecture
        if archtag == 'all':
            return self.changes.filename_archtag
        return archtag

    @property
    def priority(self):
        """Checks whether the priority indicated is valid"""
        return self.priority_map[self.priority_name]

    #
    # Binary file checks
    #
    @property
    def local_checks(self):
        """Should be implemented locally."""
        raise NotImplementedError

    def verify(self):
        """Verify the contents of the .deb or .udeb as best we can.

        It returns an iterator over all the encountered errors and warnings.
        """
        self.logger.debug("Verifying binary %s" % self.filename)

        # Run mandatory and local checks and collect errors.
        mandatory_checks = [
            self.extractAndParseControl,
            ]
        checks = mandatory_checks + self.local_checks
        for check in checks:
            for error in check():
                yield error

    def extractAndParseControl(self):
        """Extract and parse tcontrol information."""
        deb_file = open(self.filepath, "r")
        try:
            control_file = apt_inst.debExtractControl(deb_file)
            control_lines = apt_pkg.ParseSection(control_file)
        except (SystemExit, KeyboardInterrupt):
            raise
        except:
            deb_file.close()
            yield UploadError(
                "%s: debExtractControl() raised %s, giving up."
                 % (self.filename, sys.exc_type))
            return

        for mandatory_field in self.mandatory_fields:
            if control_lines.Find(mandatory_field) is None:
                yield UploadError(
                    "%s: control file lacks mandatory field %r"
                     % (self.filename, mandatory_field))

        # XXX kiko 2007-02-15: We never use the Maintainer information in
        # the control file for anything. Should we? --
        self.control = {}
        for key in control_lines.keys():
            self.control[key] = control_lines.Find(key)

        control_source = self.control.get("Source", None)
        if control_source is not None:
            if "(" in control_source:
                src_match = re_extract_src_version.match(control_source)
                self.source_name = src_match.group(1)
                self.source_version = src_match.group(2)
            else:
                self.source_name = control_source
                self.source_version = self.control.get("Version")
        else:
            self.source_name = self.control.get("Package")
            self.source_version = self.control.get("Version")

        # Store control_version for external use (archive version consistency
        # checks in nascentupload.py)
        self.control_version = self.control.get("Version")

    def verifyPackage(self):
        """Check if the binary is in changesfile and its name is valid."""
        control_package = self.control.get("Package", '')
        if control_package not in self.changes.binaries:
            yield UploadError(
                "%s: control file lists name as %r, which isn't in changes "
                "file." % (self.filename, control_package))

        if not re_valid_pkg_name.match(control_package):
            yield UploadError("%s: invalid package name %r." % (
                self.filename, control_package))

        # Ensure the filename matches the contents of the .deb
        # First check the file package name matches the deb contents.
        binary_match = re_isadeb.match(self.filename)
        file_package = binary_match.group(1)
        if control_package != file_package:
            yield UploadError(
                "%s: package part of filename %r does not match "
                "package name in the control fields %r"
                % (self.filename, file_package, control_package))

    def verifyVersion(self):
        """Check if control version is valid matches the filename version.

        Binary version  doesn't need to match the changesfile version,
        because the changesfile version refers to the SOURCE version.
        """
        if not re_valid_version.match(self.control_version):
            yield UploadError("%s: invalid version number %r."
                              % (self.filename, control_version))

        binary_match = re_isadeb.match(self.filename)
        filename_version = binary_match.group(2)
        control_version_chopped = re_no_epoch.sub('', self.control_version)
        if filename_version != control_version_chopped:
            yield UploadError("%s: should be %s according to control file."
                              % (filename_version, control_version_chopped))

    def verifyArchitecture(self):
        """Check if the control architecture matches the changesfile.

        Also check if it is a valid architecture in LP context.
        """
        control_arch = self.control.get("Architecture", '')
        valid_archs = [a.architecturetag
                       for a in self.policy.distroseries.architectures]

        if control_arch not in valid_archs and control_arch != "all":
            yield UploadError(
                "%s: Unknown architecture: %r" % (self.filename, control_arch))

        if control_arch not in self.changes.architectures:
            yield UploadError(
                "%s: control file lists arch as %r which isn't "
                "in the changes file." % (self.filename, control_arch))

        if control_arch != self.architecture:
            yield UploadError(
                "%s: control file lists arch as %r which doesn't "
                "agree with version %r in the filename."
                % (self.filename, control_arch, self.architecture))

    def verifyDepends(self):
        """Check if control depends field is present and not empty."""
        control_depends = self.control.get('Depends', "--unset-marker--")
        if not control_depends:
            yield UploadError(
                "%s: Depends field present and empty." % self.filename)

    def verifySection(self):
        """Check the section & priority match those in changesfile."""
        control_section_and_component = self.control.get('Section', '')
        control_component, control_section = splitComponentAndSection(
            control_section_and_component)
        if ((control_component, control_section) !=
            (self.component_name, self.section_name)):
            yield UploadError(
                "%s control file lists section as %s/%s but changes file "
                "has %s/%s." % (self.filename, control_component,
                                control_section, self.component_name,
                                self.section_name))

    def verifyPriority(self):
        """Check if priority matches changesfile."""
        control_priority = self.control.get('Priority', '')
        if control_priority and self.priority_name != control_priority:
            yield UploadError(
                "%s control file lists priority as %s but changes file has %s."
                % (self.filename, control_priority, self.priority_name))

    def verifyFormat(self):
        """Check if the DEB format is sane.

        Debian packages are in fact 'ar' files. Thus we run '/usr/bin/ar'
        to look at the contents of the deb files to confirm they make sense.
        """
        ar_process = subprocess.Popen(
            ["/usr/bin/ar", "t", self.filepath],
            stdout=subprocess.PIPE)
        output = ar_process.stdout.read()
        result = ar_process.wait()
        if result != 0:
            yield UploadError(
                "%s: 'ar t' invocation failed." % self.filename)
            yield UploadError(
                prefix_multi_line_string(output, " [ar output:] "))

        chunks = output.strip().split("\n")
        if len(chunks) != 3:
            yield UploadError(
                "%s: found %d chunks, expecting 3. %r" % (
                self.filename, len(chunks), chunks))

        debian_binary, control_tar, data_tar = chunks
        if debian_binary != "debian-binary":
            yield UploadError(
                "%s: first chunk is %s, expected debian-binary" % (
                self.filename, debian_binary))
        if control_tar != "control.tar.gz":
            yield UploadError(
                "%s: second chunk is %s, expected control.tar.gz" % (
                self.filename, control_tar))
        if data_tar not in ("data.tar.gz", "data.tar.bz2"):
            yield UploadError(
                "%s: third chunk is %s, expected data.tar.gz or "
                "data.tar.bz2" % (self.filename, data_tar))

    def verifyDebTimestamp(self):
        """Check specific DEB format timestamp checks."""
        self.logger.debug("Verifying timestamps in %s" % (self.filename))

        future_cutoff = time.time() + self.policy.future_time_grace
        earliest_year = time.strptime(str(self.policy.earliest_year), "%Y")
        past_cutoff = time.mktime(earliest_year)

        tar_checker = TarFileDateChecker(future_cutoff, past_cutoff)
        tar_checker.reset()
        try:
            deb_file = open(self.filepath, "rb")
            apt_inst.debExtract(deb_file, tar_checker.callback,
                                "control.tar.gz")
            deb_file.seek(0)
            try:
                apt_inst.debExtract(deb_file, tar_checker.callback,
                                    "data.tar.gz")
            except SystemError, error:
                # If we can't find a data.tar.gz,
                # look for data.tar.bz2 instead.
                if re.search(r"Cannot f[ui]nd chunk data.tar.gz$",
                                 str(error)):
                    deb_file.seek(0)
                    apt_inst.debExtract(deb_file, tar_checker.callback,
                                        "data.tar.bz2")
                else:
                    yield UploadError("Could not find data tarball in %s"
                                       % self.filename)
                    deb_file.close();
                    return

            deb_file.close();

            future_files = tar_checker.future_files.keys()
            if future_files:
                first_file = future_files[0]
                timestamp = time.ctime(tar_checker.future_files[first_file])
                yield UploadError(
                    "%s: has %s file(s) with a time stamp too "
                    "far into the future (e.g. %s [%s])."
                     % (self.filename, len(future_files), first_file,
                        timestamp))

            ancient_files = tar_checker.ancient_files.keys()
            if ancient_files:
                first_file = ancient_files[0]
                timestamp = time.ctime(tar_checker.ancient_files[first_file])
                yield UploadError(
                    "%s: has %s file(s) with a time stamp too "
                    "far into the future (e.g. %s [%s])."
                     % (self.filename, len(ancient_files), first_file,
                        timestamp))

        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception, error:
            # There is a very large number of places where we
            # might get an exception while checking the timestamps.
            # Many of them come from apt_inst/apt_pkg and they are
            # terrible in giving sane exceptions. We thusly capture
            # them all and make them into rejection messages instead
            yield UploadError("%s: deb contents timestamp check failed: %s"
                 % (self.filename, error))

#
#   Database relationship methods
#

    def findSourcePackageRelease(self):
        """Return the respective ISourcePackagRelease for this binary upload.

        It inspect publication in the targeted DistroSeries and also the
        ACCEPTED queue for sources matching stored (source_name, source_version).

        It raises UploadError if the source was not found.

        Verifications on the designed source are delayed because for
        mixed_uploads (source + binary) we do not have the source stored
        in DB yet (see verifySourcepackagerelease).
        """
        distroseries = self.policy.distroseries
        spphs = distroseries.getPublishedReleases(
            self.source_name, version=self.source_version,
            include_pending=True, archive=self.policy.archive)

        sourcepackagerelease = None
        if spphs:
            # We know there's only going to be one release because
            # version is unique.
            assert len(spphs) == 1, "Duplicated ancestry"
            sourcepackagerelease = spphs[0].sourcepackagerelease
        else:
            # XXX cprov 2006-08-09 bug=55774: Building from ACCEPTED is
            # special condition, not really used in production. We should
            # remove the support for this use case.
            self.logger.debug("No source published, checking the ACCEPTED queue")

            queue_candidates = distroseries.getQueueItems(
                status=PackageUploadStatus.ACCEPTED,
                name=self.source_name, version=self.source_version,
                archive=self.policy.archive, exact_match=True)

            for queue_item in queue_candidates:
                if queue_item.sources.count():
                    sourcepackagerelease = queue_item.sourcepackagerelease

        if sourcepackagerelease is None:
            # At this point, we can't really do much more to try
            # building this package. If we look in the NEW queue it is
            # possible that multiple versions of the package exist there
            # and we know how bad that can be. Time to give up!
            raise UploadError(
                "Unable to find source package %s/%s in %s" % (
                self.source_name, self.source_version, distroseries.name))

        return sourcepackagerelease

    def verifySourcePackageRelease(self, sourcepackagerelease):
        """Check if the given ISourcePackageRelease matches the context."""
        assert 'source' in self.changes.architectures, (
            "It should be a mixed upload, but no source part was found.")

        if self.source_version != sourcepackagerelease.version:
            raise UploadError(
                "source version %r for %s does not match version %r "
                "from control file" % (sourcepackagerelease.version,
                self.source_version, self.filename))

        if self.source_name != sourcepackagerelease.name:
            raise UploadError(
                "source name %r for %s does not match name %r in "
                "control file"
                % (sourcepackagerelease.name, self.filename, self.source_name))

    def findBuild(self, sourcepackagerelease):
        """Find and return a build for the given archtag, cached on policy.

        To find the right build, we try these steps, in order, until we have
        one:
        - Check first if a build id was provided. If it was, load that build.
        - Try to locate an existing suitable build, and use that. We also,
        in this case, change this build to be FULLYBUILT.
        - Create a new build in FULLYBUILT status.

        If by any chance an inconsistent build was found this method will
        raise UploadError resulting in a upload rejection.
        """
        build_id = getattr(self.policy.options, 'buildid', None)
        dar = self.policy.distroseries[self.archtag]

        if build_id is None:
            # Check if there's a suitable existing build.
            build = sourcepackagerelease.getBuildByArch(
                dar, self.policy.archive)
            if build is not None:
                build.buildstate = BuildStatus.FULLYBUILT
                self.logger.debug("Updating build for %s: %s" % (
                    dar.architecturetag, build.id))
            else:
                # No luck. Make one.
                # Usually happen for security binary uploads.
                build = sourcepackagerelease.createBuild(
                    dar, self.policy.pocket, self.policy.archive,
                    status=BuildStatus.FULLYBUILT)
                self.logger.debug("Build %s created" % build.id)
        else:
            build = getUtility(IBuildSet).getByBuildID(build_id)
            self.logger.debug("Build %s found" % build.id)
            # Ensure gathered binary is related to a FULLYBUILT build
            # record. It will be check in slave-scanner procedure to
            # certify that the build was processed correctly.
            build.buildstate = BuildStatus.FULLYBUILT

        # Sanity check; raise an error if the build we've been
        # told to link to makes no sense (ie. is not for the right
        # source package).
        if (build.sourcepackagerelease != sourcepackagerelease or
            build.pocket != self.policy.pocket or
            build.distroarchseries != dar or
            build.archive != self.policy.archive):
            raise UploadError(
                "Attempt to upload binaries specifying "
                "build %s, where they don't fit." % build.id)

        return build

    def storeInDatabase(self, build):
        """Insert this binary release and build into the database."""
        # Reencode everything we are supplying, because old packages
        # contain latin-1 text and that sucks.
        encoded = {}
        for key, value in self.control.items():
            encoded[key] = guess_encoding(value)

        desclines = encoded['Description'].split("\n")
        summary = desclines[0]
        description = "\n".join(desclines[1:])

        # XXX: dsilvers 2005-10-14 bug 3160: erm, need to work shlibdeps out.
        shlibdeps = ""

        is_essential = encoded.get('Essential', '').lower() == 'yes'
        architecturespecific = not self.is_archindep
        installedsize = int(self.control.get('Installed-Size','0'))
        binary_name = getUtility(
            IBinaryPackageNameSet).getOrCreateByName(self.package)

        binary = build.createBinaryPackageRelease(
            binarypackagename=binary_name,
            version=self.control_version,
            summary=summary,
            description=description,
            binpackageformat=self.format,
            component=self.component,
            section=self.section,
            priority=self.priority,
            shlibdeps=shlibdeps,
            depends=encoded.get('Depends', ''),
            recommends=encoded.get('Recommends', ''),
            suggests=encoded.get('Suggests', ''),
            conflicts=encoded.get('Conflicts', ''),
            replaces=encoded.get('Replaces', ''),
            provides=encoded.get('Provides', ''),
            essential=is_essential,
            installedsize=installedsize,
            architecturespecific=architecturespecific)

        library_file = self.librarian.create(self.filename,
             self.size, open(self.filepath, "rb"), self.content_type)
        binary.addFile(library_file)
        return binary


class UdebBinaryUploadFile(BaseBinaryUploadFile):
    """Represents an uploaded binary package file in udeb format."""
    format = BinaryPackageFormat.UDEB

    @property
    def local_checks(self):
        """Checks to be executed on UDEBs."""
        return [
            self.verifyPackage,
            self.verifyVersion,
            self.verifyArchitecture,
            self.verifyDepends,
            self.verifySection,
            self.verifyPriority,
            self.verifyFormat,
            ]


class DebBinaryUploadFile(BaseBinaryUploadFile):
    """Represents an uploaded binary package file in deb format."""
    format = BinaryPackageFormat.DEB

    @property
    def local_checks(self):
        """Checks to be executed on DEBs."""
        return [
            self.verifyPackage,
            self.verifyVersion,
            self.verifyArchitecture,
            self.verifyDepends,
            self.verifySection,
            self.verifyPriority,
            self.verifyFormat,
            self.verifyDebTimestamp,
            ]
