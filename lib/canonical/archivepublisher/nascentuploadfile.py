
import os
import re
import sys
import md5
import sha
import time
import apt_inst
import apt_pkg
import subprocess

from zope.component import getUtility

from canonical.librarian.utils import filechunks

from canonical.lp.dbschema import (
    PackagePublishingPriority, DistroReleaseQueueCustomFormat, 
    DistroReleaseQueueStatus)

from canonical.launchpad.interfaces import (
    IComponentSet, ISectionSet)

from canonical.archivepublisher.utils import (
    prefix_multi_line_string)


# This is a marker as per the comment in dbschema.py: ##CUSTOMFORMAT##
# Essentially if you change anything to do with custom formats, grep for
# the marker in the codebase and make sure the same changes are made
# everywhere which needs them.
custom_sections = {
    'raw-installer': DistroReleaseQueueCustomFormat.DEBIAN_INSTALLER,
    'raw-translations': DistroReleaseQueueCustomFormat.ROSETTA_TRANSLATIONS,
    'raw-dist-upgrader': DistroReleaseQueueCustomFormat.DIST_UPGRADER,
    'raw-ddtp-tarball': DistroReleaseQueueCustomFormat.DDTP_TARBALL,
    }

# Capitalised because we extract direct from the deb/udeb where the
# other mandatory fields lists are lowercased by parse_tagfile
deb_mandatory_fields = set([
    "Package", "Architecture", "Version"
    ])

re_taint_free = re.compile(r"^[-+~/\.\w]+$")

re_isadeb = re.compile(r"(.+?)_(.+?)_(.+)\.(u?deb)$")
re_issource = re.compile(r"(.+)_(.+?)\.(orig\.tar\.gz|diff\.gz|tar\.gz|dsc)$")

re_no_epoch = re.compile(r"^\d+\:")
re_valid_version = re.compile(r"^([0-9]+:)?[0-9A-Za-z\.\-\+~:]+$")
re_valid_pkg_name = re.compile(r"^[\dA-Za-z][\dA-Za-z\+\-\.]+$")
re_extract_src_version = re.compile(r"(\S+)\s*\((.*)\)")

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

# Files need their content type for creating in the librarian.
# This maps endings of filenames onto content types we may encounter
# in the processing of an upload
filename_ending_content_type_map = {
    ".dsc": "text/x-debian-source-package",
    ".deb": "application/x-debian-package",
    ".udeb": "application/x-micro-debian-package",
    ".diff.gz": "application/gzipped-patch",
    ".tar.gz": "application/gzipped-tar"
    }

def split_section(section):
    """Split the component out of the section."""
    if "/" not in section:
        return "main", section
    return section.split("/", 1)


class UploadError(Exception):
    """All upload errors are returned in this form."""

class UploadWarning(Warning):
    """All upload warnings are returned in this form."""


class TarFileDateChecker:
    """Verify all files in a tar in a deb are within a given date range.

    This was taken from jennifer in the DAK suite.
    """
    def __init__(self, future_cutoff, past_cutoff):
        self.reset()
        self.future_cutoff = future_cutoff
        self.past_cutoff = past_cutoff

    def reset(self):
        self.future_files = {}
        self.ancient_files = {}

    def callback(self, Kind, Name, Link, Mode,
                 UID, GID, Size, MTime, Major, Minor):
        if MTime > self.future_cutoff:
            self.future_files[Name] = MTime
        if MTime < self.past_cutoff:
            self.ancient_files[Name] = MTime


class NascentUploadedFile:
    """A nascent uploaded file is a file on disk that is part of an upload.

    The filename, along with information about it, is kept here.
    """

    type = None

    #
    # XXX
    #   - policy
    #   - logger
    #   - fsroot
    # XXX
    #

    def __init__(self, filename, digest, size, component_and_section,
                 priority, fsroot, policy, logger):
        self.filename = filename
        self.digest = digest
        self.size = int(size)
        self.component, self.section = split_section(component_and_section)
        self.priority = priority
        self.new = False
        self._values_checked = False
        self.policy = policy
        self.fsroot = fsroot
        self.logger = logger

        self.full_filename = os.path.join(fsroot, filename)

    #
    # Helpers used quen inserting into queue
    #

    @property
    def content_type(self):
        """The content type for this file ready for adding to the librarian."""
        for ending, content_type in filename_ending_content_type_map.items():
            if self.filename.endswith(ending):
                return content_type
        return "application/octet-stream"

    @property
    def custom_type(self):
        """The custom upload type for this file. (None if not custom)."""
        if self.custom:
            return custom_sections[self.section]
        return None

    #
    #
    #

    @property
    def custom(self):
        return self.priority == "-" and self.section in custom_sections

    @property
    def exists_on_disk(self):
        """Whether or not the file is present on disk."""
        return os.path.exists(self.full_filename)

    #
    # Verification
    #

    def validate(self):
        raise NotImplementedError

    def checkNameIsTaintFree(self):
        if not re_taint_free.match(self.filename):
            raise UploadError("Tainted filename: '%s'." % (file))

    def checkSizeAndCheckSum(self):
        """Check the md5sum and size of the nascent file.

        Raise UploadError if the digest or size does not match or if the
        file is not found on the disk.

        Populate self._sha_digest with the calculated sha1 digest of the
        file on disk.
        """
        if not self.exists_on_disk:
            raise UploadError(
                "File %s as mentioned in the changes file was not found." % (
                self.filename))

        # Read in the file and compute its md5 and sha1 checksums and remember
        # the size of the file as read-in.
        digest = md5.md5()
        sha_cksum = sha.sha()
        ckfile = open(self.full_filename, "r")
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

        # Record the sha1 digest and note that we have checked things.
        self.sha_digest = sha_cksum.hexdigest()



class PackageNascentUploadFile(NascentUploadedFile):
    """XXX"""

    def __init__(self, filename, digest, size, component_and_section,
                 priority, package, version, type, changes, fsroot, policy,
                 logger):
        """
        XXX

        Check presence of the component and section from an uploaded_file.

        They need to satisfy at least the NEW queue constraints that includes
        SourcePackageRelease creation, so component and section need to exist.
        Even if they might be overriden in the future.
        """
        NascentUploadedFile.__init__(
            self, filename, digest, size, component_and_section,
            priority, fsroot, policy, logger)
        self.package = package
        self.version = version
        self.type = type
        # XXX: I hate that we need to supply changes here, but the
        # verification methods need information from the changes. To
        # avoid this we could supply chopversion, chopversion2 and
        # architectures.
        self.changes = changes

        valid_components = [component.name for component in
                            getUtility(IComponentSet)]
        valid_sections = [section.name for section in getUtility(ISectionSet)]

        if self.component not in valid_components:
            self.reject("%s: Component %s is not valid" % (
                self.filename, self.component))

        if self.section not in valid_sections:
            # We used to reject invalid sections; when testing stuff we
            # were forced to accept a package with a broken section
            # (linux-meta_2.6.12.16_i386). Result: packages with invalid
            # sections now get put into misc -- cprov 20060119
            default_section = 'misc'
            self.warn("Unable to grok section %s, overriding it with %s"
                      % (self.section, default_section))
            self.section = default_section

    def verify(self):
        raise NotImplementedError


class SourceNascentUploadFile(PackageNascentUploadFile):
    """XXX"""


    def verify(self):
        """Verify the uploaded source file.

        Should not raise anything unless something unexpected happens. All
        errors should be accumulated in the rejection message.
        """
        self.logger.debug("Verifying source file %s" % self.filename)

        if self.type == "orig.tar.gz":
            changes_version = self.changes.chopversion2
        else:
            changes_version = self.changes.chopversion
        if changes_version != self.version:
            self.reject("%s: should be %s according to changes file." % (
                self.filename, changes_version))

        if 'source' not in self.changes.architectures:
            self.reject("%s: changes file doesn't list 'source' in "
                        "Architecture field." % (self.filename))
        return []


class BinaryNascentUploadedFile(PackageNascentUploadFile):
    """XXX"""
    def __init__(self, XXX, changes):
        self.changes = changes
        self.convert_priority()

    def is_archindep(self):
        return "XXX"

    def verify(self):
        if self.type == "deb":
            # XXX: don't we verify timestamps for udebs?
            self.verify_timestamp()
        self.real_verify()
        return []

    def convert_priority(self):
        """Checks whether the priority indicated is valid"""

        if self.priority in priority_map:
            # map priority tag to dbschema
            priority = priority_map[self.priority]
        else:
            default_priority = priority_map['extra']
            self.warn("Unable to grok priority %r, overriding it with %s"
                      % (self.priority, default_priority))
            priority = default_priority

        self.priority = priority

    def verify_timestamp(self):
        self.logger.debug("Verifying timestamps in %s" % (
            self.filename))

        future_cutoff = time.time() + self.policy.future_time_grace
        past_cutoff = time.mktime(
            time.strptime(str(self.policy.earliest_year), "%Y"))
        tar_checker = TarFileDateChecker(future_cutoff, past_cutoff)

        tar_checker.reset()
        try:
            deb_file = open(self.full_filename, "rb")
            apt_inst.debExtract(deb_file, tar_checker.callback,
                                "control.tar.gz")
            deb_file.seek(0)
            try:
                apt_inst.debExtract(deb_file,tar_checker.callback,
                                    "data.tar.gz")
            except SystemError, e:
                # If we can't find a data.tar.gz,
                # look for data.tar.bz2 instead.
                if not re.search(r"Cannot f[ui]nd chunk data.tar.gz$",
                                 str(e)):
                    raise
                deb_file.seek(0)
                apt_inst.debExtract(deb_file,tar_checker.callback,
                                    "data.tar.bz2")
            deb_file.close();

            future_files = tar_checker.future_files.keys()
            if future_files:
                self.reject("%s: has %s file(s) with a time stamp too "
                            "far into the future (e.g. %s [%s])." % (
                    self.filename, len(future_files),
                    future_files[0],
                    time.ctime(
                    tar_checker.future_files[future_files[0]])))

            ancient_files = tar_checker.ancient_files.keys()
            if ancient_files:
                self.reject("%s: has %s file(s) with a time stamp too "
                            "far into the future (e.g. %s [%s])." % (
                    self.filename, len(ancient_files),
                    ancient_files[0],
                    time.ctime(
                    tar_checker.ancient_files[ancient_files[0]])))

        except:
            # There is a very large number of places where we
            # might get an exception while checking the timestamps.
            # Many of them come from apt_inst/apt_pkg and they are
            # terrible in giving sane exceptions. We thusly capture
            # them all and make them into rejection messages instead
            self.reject("%s: deb contents timestamp check failed "
                        "[%s: %s]" % (
                self.filename, sys.exc_type, sys.exc_value));


    def real_verify(self):
        """Verify the contents of the .deb or .udeb as best we can.

        Should not raise anything itself but makes little effort to catch
        exceptions raised in anything it calls apart from where apt_pkg or
        apt_inst may go bonkers. Those are generally caught and swallowed.
        """
        self.logger.debug("Verifying binary %s" % self.filename)
        if not self.binaryful:
            self.reject("Found %s in an allegedly non-binaryful upload." % (
                self.filename))
        deb_file = open(self.full_filename, "r")
        # Extract the control information
        try:
            control_file = apt_inst.debExtractControl(deb_file)
            control = apt_pkg.ParseSection(control_file)
        except:
            # Swallow everything apt_pkg and apt_inst throw at us because they
            # are not desperately pythonic and can raise odd or confusing
            # exceptions at times and are out of our control.
            deb_file.close();
            self.reject("%s: debExtractControl() raised %s." % (
                self.filename, sys.exc_type));
            return

        # Check for mandatory control fields
        for mandatory_field in deb_mandatory_fields:
            if control.Find(mandatory_field) is None:
                self.reject("%s: control file lacks %s field." % (
                    self.filename, mandatory_field))

        # Ensure the package name matches one in the changes file
        if control.Find("Package", "") not in self.changes.binaries:
            self.reject(
                "%s: control file lists name as `%s', which isn't in changes "
                "file." % (self.filename,
                           control.Find("Package", "")))

        # Cache the control information for later.
        self.control = {}
        for key in control.keys():
            self.control[key] = control.Find(key)

        # Validate the package field
        package = control.Find("Package");
        if not re_valid_pkg_name.match(package):
            self.reject("%s: invalid package name '%s'." % (
                self.filename, package));

        # Validate the version field
        version = control.Find("Version");
        if not re_valid_version.match(version):
            self.reject("%s: invalid version number '%s'." % (
                self.filename, version));

        # Ensure the architecture of the .deb is valid in the target
        # distrorelease
        arch = control.Find('Architecture', "")
        valid_archs = self.policy.distrorelease.architectures
        found_arch = False
        for valid_arch in valid_archs:
            if valid_arch.architecturetag == arch:
                found_arch = True
        if not found_arch and arch != "all":
            self.reject("%s: Unknown architecture: '%s'." % (
                self.filename, arch))

        # Ensure the arch of the .deb is listed in the changes file
        if arch not in self.changes.architectures:
            self.reject("%s: control file lists arch as '%s' which isn't "
                        "in the changes file." % (self.filename,
                                                  arch))

        # Sanity check the depends field.
        depends = control.Find('Depends')
        if depends == '':
            self.reject("%s: Depends field present and empty." % (
                self.filename))

        # Check the section & priority match those in the .changes Files entry
        control_component, control_section = split_section(
            control.Find("Section"))
        if ((control_component, control_section) !=
            (self.component, self.section)):
            self.reject(
                "%s control file lists section as %s/%s but changes file "
                "has %s/%s." % (self.filename, control_component,
                                control_section, self.component,
                                self.section))

        if (control.Find("Priority") and
            self.priority != "" and
            self.priority != control.Find("Priority")):
            self.reject("%s control file lists priority as %s but changes file"
                        " has %s." % (self.filename,
                                      control.Find("Priority"),
                                      self.priority))

        # Check the filename ends with .deb or .udeb
        if not (self.filename.endswith(".deb") or
                self.filename.endswith(".udeb")):
            self.reject(
                "%s is neither a .deb or a .udeb" % self.filename)

        self.package = package
        self.architecture = arch
        self.version = version
        self.maintainer = control.Find("Maintainer", "")
        self.source = control.Find("Source", package)

        # Find the source version for the package.
        source = self.source
        source_version = ""
        if "(" in source:
            src_match = re_extract_src_version.match(source)
            source = src_match.group(1)
            source_version = src_match.group(2)
        if not source_version:
            source_version = version

        self.source_package = source
        self.source_version = source_version

        # Ensure the filename matches the contents of the .deb
        deb_match = re_isadeb.match(self.filename)
        # First check the file package name matches the deb contents.
        file_package = deb_match.group(1)
        if package != file_package:
            self.reject(
                "%s: package part of filename (%s) does not match "
                "package name in the control fields (%s)." % (
                self.filename,
                file_package,
                package))

        # Next check the version matches.
        epochless_version = re_no_epoch.sub('', version)
        file_version = deb_match.group(2)
        if epochless_version != file_version:
            self.reject(
                "%s: version part of the filename (%s) does not match "
                "the version in the control fields (%s)." % (
                self.filename,
                file_version,
                epochless_version))

        # Verify that the source versions match if present.
        if 'source' in self.changes.architectures:
            if source_version != self.changes['version']:
                self.reject(
                    "source version (%s) for %s does not match changes "
                    "version %s" % (
                    source_version,
                    self.filename,
                    self.changes['version']))
        else:
            found = False

            # Try and find the source in the distrorelease.
            dr = self.policy.distrorelease
            # Check published source in any pocket
            releases = dr.getPublishedReleases(source, include_pending=True)
            for spr in releases:
                if spr.sourcepackagerelease.version == source_version:
                    # XXX: DO NOT FUCKING CHANGE THE POLICY HERE OR YOU
                    # WILL GO TO HELL TEN TIMES
                    self.policy.sourcepackagerelease = spr.sourcepackagerelease
                    found = True

            # If we didn't find it, try to find it in the queues...
            if not found:
                # Obtain the ACCEPTED queue

                # XXX cprov 20060809: Building from ACCEPTED is special
                # condition, not really used in production. We should
                # remove the support for this use case, see further
                # info in bug #55774.
                self.logger.debug("Checking in the ACCEPTED queue")
                q = dr.getQueueItems(status=DistroReleaseQueueStatus.ACCEPTED)
                for qitem in q:
                    self.logger.debug("Looking at qitem %s/%s" % (
                        qitem.sourcepackagerelease.name,
                        qitem.sourcepackagerelease.version))
                    if (qitem.sourcepackagerelease.name == source and
                        qitem.sourcepackagerelease.version == source_version):
                        # XXX: DO NOT FUCKING CHANGE THE POLICY HERE OR YOU
                        # WILL GO TO HELL TEN TIMES
                        self.policy.sourcepackagerelease = (
                            qitem.sourcepackagerelease )
                        found = True

            if not found:
                # XXX: dsilvers: 20051012: Perhaps check the NEW queue too?
                # bug 3138
                self.reject("Unable to find source package %s/%s in %s" % (
                    source, source_version, dr.name))

        # Debian packages are in fact 'ar' files. Thus we run '/usr/bin/ar'
        # to look at the contents of the deb files to confirm they make sense.
        ar_process = subprocess.Popen(
            ["/usr/bin/ar", "t", self.full_filename],
            stdout=subprocess.PIPE)
        output = ar_process.stdout.read()
        result = ar_process.wait()
        if result != 0:
            self.reject("%s: 'ar t' invocation failed." % (
                self.filename))
            self.reject(prefix_multi_line_string(output, " [ar output:] "))
        chunks = output.strip().split("\n")
        if len(chunks) != 3:
            self.reject("%s: found %d chunks, expecting 3. %r" % (
                self.filename, len(chunks), chunks))

        debian_binary, control_tar, data_tar = chunks
        if debian_binary != "debian-binary":
            self.reject("%s: first chunk is %s, expected debian-binary" % (
                self.filename, debian_binary))
        if control_tar != "control.tar.gz":
            self.reject("%s: second chunk is %s, expected control.tar.gz" % (
                self.filename, control_tar))
        if data_tar == "data.tar.bz2":
            # Packages using bzip2 must Pre-Depend on dpkg >= 1.10.24
            apt_pkg.InitSystem()
            found = False
            for parsed_dep in apt_pkg.ParseDepends(
                control.Find("Pre-Depends", "")):
                if len(parsed_dep) > 1:
                    continue
                for dep, version, constraint in parsed_dep:
                    if dep != "dpkg" or (constraint not in ('>=', '>>')):
                        continue
                    if ((constraint == ">=" and
                         apt_pkg.VersionCompare(version, "1.10.24") < 0) or
                        (constraint == ">>" and
                         apt_pkg.VersionCompare(version, "1.10.23") < 0)):
                        continue
                    found = True
            if not found:
                self.reject("%s uses bzip2 compression but doesn't Pre-Depend "
                            "on dpkg (>= 1.10.24)" % self.filename)
        elif data_tar != "data.tar.gz":
            self.reject("%s: third chunk is %s, expected data.tar.gz or "
                        "data.tar.bz2" % (self.filename, data_tar))

        # That's all folks.


class ByHandUploadedFile(NascentUploadedFile):
    pass

class DSCUploadedFile(NascentUploadedFile):
    # XXX XXX
    pass


