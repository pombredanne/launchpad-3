
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

from canonical.encoding import guess as guess_encoding

from canonical.archivepublisher.utils import prefix_multi_line_string
from canonical.librarian.utils import filechunks
from canonical.launchpad.interfaces import (
    IComponentSet, ISectionSet, IBuildSet, ILibraryFileAliasSet,
    IBinaryPackageNameSet)
from canonical.lp.dbschema import (
    PackagePublishingPriority, DistroReleaseQueueCustomFormat, 
    DistroReleaseQueueStatus, BinaryPackageFormat, BuildStatus)


re_taint_free = re.compile(r"^[-+~/\.\w]+$")

re_isadeb = re.compile(r"(.+?)_(.+?)_(.+)\.(u?deb)$")
re_issource = re.compile(r"(.+)_(.+?)\.(orig\.tar\.gz|diff\.gz|tar\.gz|dsc)$")

re_no_epoch = re.compile(r"^\d+\:")
re_no_revision = re.compile(r"-[^-]+$")

re_valid_version = re.compile(r"^([0-9]+:)?[0-9A-Za-z\.\-\+~:]+$")
re_valid_pkg_name = re.compile(r"^[\dA-Za-z][\dA-Za-z\+\-\.]+$")
re_extract_src_version = re.compile(r"(\S+)\s*\((.*)\)")

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


class NascentUploadFile:
    """A nascent uploaded file is a file on disk that is part of an upload.

    The filename, along with information about it, is kept here.
    """
    new = False
    sha_digest = None

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

    def __init__(self, filename, digest, size, component_and_section,
                 priority, fsroot, policy, logger):
        self.filename = filename
        self.digest = digest
        self.priority = priority
        self.fsroot = fsroot
        self.policy = policy
        self.logger = logger

        self.size = int(size)
        self.component, self.section = self.split_component_and_section(
            component_and_section)
        self.full_filename = os.path.join(fsroot, filename)

        self.librarian = getUtility(ILibraryFileAliasSet)

    #
    # Helpers used quen inserting into queue
    #

    @property
    def content_type(self):
        """The content type for this file ready for adding to the librarian."""
        for ending, content_type in self.filename_ending_content_type_map.items():
            if self.filename.endswith(ending):
                return content_type
        return "application/octet-stream"

    #
    #
    #

    @property
    def exists_on_disk(self):
        """Whether or not the file is present on disk."""
        return os.path.exists(self.full_filename)

    def split_component_and_section(self, component_and_section):
        """Split the component out of the section."""
        if "/" not in component_and_section:
            return "main", component_and_section
        return component_and_section.split("/", 1)

    #
    #
    #

    def store_in_database(self):
        """Implement this to store this representation in the database."""
        raise NotImplementedError

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
                "File %s mentioned in the changes file was not found."
                % self.filename)

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

        # The sha_digest is used later when verifying packages mentioned
        # in the DSC file; it's used to compare versus files in the
        # Librarian.
        self.sha_digest = sha_cksum.hexdigest()


class CustomUploadFile(NascentUploadFile):
    """XXX"""

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

    # These uploads are by definition, new.
    new = True

    @property
    def custom_type(self):
        """The custom upload type for this file. (None if not custom)."""
        return self.custom_sections[self.section]

    def verify(self):
        if self.section not in self.custom_sections:
            yield UploadError("Unsupported custom section name %r" % self.section)

    def store_in_database(self):
        libraryfile = self.librarian.create(
            self.filename, self.size,
            open(self.full_filename, "rb"),
            self.content_type)
        return libraryfile


class PackageUploadFile(NascentUploadFile):
    """XXX"""

    def __init__(self, filename, digest, size, component_and_section,
                 priority, package, version, changes, fsroot, policy,
                 logger):
        """
        XXX

        Check presence of the component and section from an uploaded_file.

        They need to satisfy at least the NEW queue constraints that includes
        SourcePackageRelease creation, so component and section need to exist.
        Even if they might be overriden in the future.
        """
        NascentUploadFile.__init__(
            self, filename, digest, size, component_and_section,
            priority, fsroot, policy, logger)
        self.package = package
        self.version = version
        self.changes = changes

        valid_components = [component.name for component in
                            getUtility(IComponentSet)]
        valid_sections = [section.name for section in getUtility(ISectionSet)]

        if self.section not in valid_sections:
            # We used to reject invalid sections; when testing stuff we
            # were forced to accept a package with a broken section
            # (linux-meta_2.6.12.16_i386). Result: packages with invalid
            # sections now get put into misc -- cprov 20060119
            default_section = 'misc'
            self.logger.warn("Unable to grok section %r, overriding it with %s"
                      % (self.section, default_section))
            self.section = default_section

        if self.component not in valid_components:
            raise UploadError(
                "%s: Component %r is not valid" % (
                self.filename, self.component))


    @property
    def converted_component(self):
        return getUtility(IComponentSet)[self.component]

    @property
    def converted_section(self):
        return getUtility(ISectionSet)[self.section]

    def verify(self):
        raise NotImplementedError


class SourceUploadFile(PackageUploadFile):
    """XXX

    XXX: compare to DSCUploadFile
    """
    def verify(self):
        """Verify the uploaded source file.

        Should not raise anything unless something unexpected happens. All
        errors should be accumulated in the rejection message.
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


class UBinaryUploadFile(PackageUploadFile):
    """Represents an uploaded binary package file."""
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

    format = BinaryPackageFormat.UDEB

    # These are divined when parsing the package file in verify(), and
    # then used to locate or create the relevant sources and build.
    control = None
    sourcepackagerelease = None
    source_name = None
    source_version = None

    def __init__(self, *args, **kwargs):
        PackageUploadFile.__init__(self, *args, **kwargs)

        if self.priority not in self.priority_map:
            default_priority = 'extra'
            self.logger.warn(
                 "Unable to grok priority %r, overriding it with %s"
                 % (self.priority, default_priority))
            self.priority = default_priority

        # Yeah, this is weird. Where else can I discover this without
        # unpacking the deb file, though?
        binary_match = re_isadeb.match(self.filename)
        self.architecture = binary_match.group(3)

    #
    #
    #

    @property
    def is_archindep(self):
        return self.architecture.lower() == 'all'

    @property
    def archtag(self):
        archtag = self.architecture
        if archtag == 'all':
            return self.changes.filename_archtag
        return archtag

    @property
    def converted_priority(self):
        """Checks whether the priority indicated is valid"""
        return self.priority_map[self.priority]

    #
    #
    #

    def verify(self):
        """Verify the contents of the .deb or .udeb as best we can.

        Should not raise anything itself but makes little effort to catch
        exceptions raised in anything it calls apart from where apt_pkg or
        apt_inst may go bonkers. Those are generally caught and swallowed.
        """
        self.logger.debug("Verifying binary %s" % self.filename)
        # First thing we need to do is extract the control information.
        # We can only really rely on what's in the control file, so this
        # is why the UBinaryUploadFile has this weird dependency on
        # verify() being called to be API complete.
        deb_file = open(self.full_filename, "r")
        try:
            control_file = apt_inst.debExtractControl(deb_file)
            control_lines = apt_pkg.ParseSection(control_file)
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

        self.control = {}
        for key in control_lines.keys():
            self.control[key] = control_lines.Find(key)

        # XXX: we never use the Maintainer information in the control
        # file for anything. Should we? -- kiko, 2007-02-15

        #
        # Check Package
        #
        binary_match = re_isadeb.match(self.filename)
        control_package = control_lines.Find("Package");
        if control_package not in self.changes.binaries:
            yield UploadError(
                "%s: control file lists name as %r, which isn't in changes "
                "file." % (self.filename, control_package))

        if not re_valid_pkg_name.match(control_package):
            yield UploadError("%s: invalid package name %r." % (
                self.filename, control_package))


        # Ensure the filename matches the contents of the .deb
        # First check the file package name matches the deb contents.
        file_package = binary_match.group(1)
        if control_package != file_package:
            yield UploadError(
                "%s: package part of filename %r does not match "
                "package name in the control fields %r"
                % (self.filename, file_package, control_package))


        #
        # Check Version
        #
        control_version = control_lines.Find("Version");
        if not re_valid_version.match(control_version):
            yield UploadError("%s: invalid version number %r." % (
                self.filename, control_version))

        if control_version != self.version:
            yield UploadError("%s: version number %r in control file "
                "doesn't match version %r in changes file." % (
                self.filename, control_version, self.version))

        filename_version = binary_match.group(2)
        changes_version_chopped = re_no_epoch.sub('', self.version)
        if filename_version != changes_version_chopped:
            yield UploadError("%s: should be %s according to changes file."
                % (filename_version, changes_version_chopped))

        #
        # Check Architecture
        #
        control_arch = control_lines.Find('Architecture')
        valid_archs = [a.architecturetag
                       for a in self.policy.distrorelease.architectures]
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

        control_depends = control_lines.Find('Depends', "--unset-marker--")
        if not control_depends:
            yield UploadError(
                "%s: Depends field present and empty." % self.filename)

        #
        # Check Section and Priority
        #

        # Check the section & priority match those in the .changes Files entry
        control_component, control_section = self.split_component_and_section(
            control_lines.Find("Section"))
        if ((control_component, control_section) !=
            (self.component, self.section)):
            yield UploadError(
                "%s control file lists section as %s/%s but changes file "
                "has %s/%s." % (self.filename, control_component,
                                control_section, self.component,
                                self.section))
        control_priority = control_lines.Find("Priority")
        if control_priority and self.priority != control_priority:
            yield UploadError(
                "%s control file lists priority as %s but changes file has %s."
                % (self.filename, control_priority, self.priority))

        #
        # Fish our Source details
        #

        control_source = self.control.get("Source", None)
        if control_source is not None and "(" in control_source:
            src_match = re_extract_src_version.match(control_source)
            self.source_name = src_match.group(1)
            self.source_version = src_match.group(2)
        else:
            self.source_name = self.control.get("Package")
            self.source_version = self.control.get("Version")

        # Debian packages are in fact 'ar' files. Thus we run '/usr/bin/ar'
        # to look at the contents of the deb files to confirm they make sense.
        ar_process = subprocess.Popen(
            ["/usr/bin/ar", "t", self.full_filename],
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
        if data_tar == "data.tar.bz2":
            # Packages using bzip2 must Pre-Depend on dpkg >= 1.10.24
            found = False
            control_pre_depends = control_lines.Find("Pre-Depends", "")
            for parsed_dep in apt_pkg.ParseDepends(control_pre_depends):
                # apt_pkg is weird and returns a list containing lists
                # containing a single tuple.
                assert len(parsed_dep) == 1
                dep, version, constraint = parsed_dep[0]
                if dep != "dpkg":
                    continue
                if ((constraint == ">=" and
                     apt_pkg.VersionCompare(version, "1.10.24") < 0) or
                    (constraint == ">>" and
                     apt_pkg.VersionCompare(version, "1.10.23") < 0)):
                    yield UploadError(
                        "%s uses bzip2 compression but pre-depends "
                        "on an old version of dpkg: %s"
                        % (self.filename, version))
                break
            else:
                yield UploadError(
                    "%s uses bzip2 compression but doesn't Pre-Depend "
                    "on dpkg (>= 1.10.24)" % self.filename)
        elif data_tar == "data.tar.gz":
            # No tests are needed for tarballs, yay
            pass
        else:
            yield UploadError(
                "%s: third chunk is %s, expected data.tar.gz or "
                "data.tar.bz2" % (self.filename, data_tar))

        # That's all folks.

    def find_sourcepackagerelease(self):
        """XXX

        Explain why this is separate from verify.
        """
        distrorelease = self.policy.distrorelease
        spphs = distrorelease.getPublishedReleases(
                        self.source_name, version=self.source_version, 
                        include_pending=True)
        if spphs:
            # We know there's only going to be one release because
            # version is unique.
            assert len(spphs) == 1
            sourcepackagerelease = spphs[0].sourcepackagerelease
        else:
            # XXX cprov 20060809: Building from ACCEPTED is special
            # condition, not really used in production. We should
            # remove the support for this use case, see further
            # info in bug #55774.
            self.logger.debug("No source published, checking the ACCEPTED queue")
            q = distrorelease.getQueueItems(status=DistroReleaseQueueStatus.ACCEPTED,
                                            name=self.source_name,
                                            version=self.source_version)
            if q:
                assert len(q) == 1
                sourcepackagerelease = q[0].sourcepackagerelease

        if sourcepackagerelease is None:
            # At this point, we can't really do much more to try
            # building this package. If we look in the NEW queue it is
            # possible that multiple versions of the package exist there
            # and we know how bad that can be. Time to give up!
            raise UploadError(
                "Unable to find source package %s/%s in %s" % (
                self.source_name, self.source_version, distrorelease.name))

        return sourcepackagerelease

    def verify_sourcepackagerelease(self, sourcepackagerelease):
        """XXX

        Explain mixed-mode.
        """
        assert 'source' in self.changes.architectures
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

    def find_build(self, sourcepackagerelease):
        """Find and return a build for the given archtag, cached on policy.

        To find the right build, we try these steps, in order, until we have
        one:
        - Check first if a build id was provided. If it was, load that build.
        - Try to locate an existing suitable build, and use that. We also,
        in this case, change this build to be FULLYBUILT.
        - Create a new build in FULLYBUILT status.
        """
        build_id = getattr(self.policy.options, 'buildid', None)
        if build_id is None:
            dar = self.policy.distrorelease[self.archtag]

            # Check if there's a suitable existing build.
            build = sourcepackagerelease.getBuildByArch(dar)
            if build is not None:
                build.buildstate = BuildStatus.FULLYBUILT
            else:
                # No luck. Make one.
                # XXX: how can this happen?! oh, security?
                build = sourcepackagerelease.createBuild(
                    dar, self.policy.pocket, status=BuildStatus.FULLYBUILT)
                self.logger.debug("Build %s created" % build.id)
        else:
            build = getUtility(IBuildSet).getByBuildID(build_id)

            # Sanity check; raise an error if the build we've been
            # told to link to makes no sense (ie. is not for the right
            # source package).
            if (build.sourcepackagerelease != sourcepackagerelease or
                build.pocket != self.policy.pocket):
                raise UploadError("Attempt to upload binaries specifying "
                                  "build %s, where they don't fit" % build_id)
            self.logger.debug("Build %s found" % build.id)

        return build

    def store_in_database(self, build):
        """Insert this binary release and build into the database."""
        bpns = getUtility(IBinaryPackageNameSet)

        # Reencode everything we are supplying, because old packages
        # contain latin-1 text and that sucks.
        encoded = {}
        for k, v in self.control.items():
            encoded[k] = guess_encoding(v)

        desclines = encoded['Description'].split("\n")
        summary = desclines[0]
        description = "\n".join(desclines[1:])

        # XXX: dsilvers: 20051014: erm, need to work shlibdeps out
        # bug 3160
        shlibdeps = ""
        # XXX: dsilvers: 20051014: erm, source should have a copyright
        # but not binaries. bug 3161
        copyright = ""
        licence = ""

        is_essential = encoded.get('Essential', '').lower() == 'yes'
        architecturespecific = not self.is_archindep
        installedsize = int(self.control.get('Installed-Size','0'))

        binary = build.createBinaryPackageRelease(
            binarypackagename=bpns.getOrCreateByName(self.package),
            version=self.version,
            summary=summary,
            description=description,
            binpackageformat=self.format,
            component=self.converted_component,
            section=self.converted_section,
            priority=self.converted_priority,
            shlibdeps=shlibdeps,
            depends=encoded.get('Depends', ''),
            recommends=encoded.get('Recommends', ''),
            suggests=encoded.get('Suggests', ''),
            conflicts=encoded.get('Conflicts', ''),
            replaces=encoded.get('Replaces', ''),
            provides=encoded.get('Provides', ''),
            essential=is_essential, 
            installedsize=installedsize,
            copyright=copyright,
            licence=licence,
            architecturespecific=architecturespecific)

        library_file = self.librarian.create(self.filename,
             self.size, open(self.full_filename, "rb"), self.content_type)
        binary.addFile(library_file)
        return binary


class BinaryUploadFile(UBinaryUploadFile):

    format = BinaryPackageFormat.DEB

    def verify(self):
        for error in UBinaryUploadFile.verify(self):
            yield error

        self.logger.debug("Verifying timestamps in %s" % (
            self.filename))

        future_cutoff = time.time() + self.policy.future_time_grace

        earliest_year = time.strptime(str(self.policy.earliest_year), "%Y")
        past_cutoff = time.mktime(earliest_year)

        tar_checker = TarFileDateChecker(future_cutoff, past_cutoff)

        tar_checker.reset()
        try:
            deb_file = open(self.full_filename, "rb")
            apt_inst.debExtract(deb_file, tar_checker.callback,
                                "control.tar.gz")
            deb_file.seek(0)
            try:
                apt_inst.debExtract(deb_file, tar_checker.callback,
                                    "data.tar.gz")
            except SystemError, e:
                # If we can't find a data.tar.gz,
                # look for data.tar.bz2 instead.
                if re.search(r"Cannot f[ui]nd chunk data.tar.gz$",
                                 str(e)):
                    deb_file.seek(0)
                    apt_inst.debExtract(deb_file,tar_checker.callback,
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
                ts = time.ctime(tar_checker.future_files[first_file])
                yield UploadError(
                    "%s: has %s file(s) with a time stamp too "
                    "far into the future (e.g. %s [%s])."
                     % (self.filename, len(future_files), first_file, ts))

            ancient_files = tar_checker.ancient_files.keys()
            if ancient_files:
                first_file = ancient_files[0]
                ts = time.ctime(tar_checker.ancient_files[first_file])
                yield UploadError(
                    "%s: has %s file(s) with a time stamp too "
                    "far into the future (e.g. %s [%s])."
                     % (self.filename, len(ancient_files), first_file, ts))

        except Exception, e:
            # There is a very large number of places where we
            # might get an exception while checking the timestamps.
            # Many of them come from apt_inst/apt_pkg and they are
            # terrible in giving sane exceptions. We thusly capture
            # them all and make them into rejection messages instead
            yield UploadError("%s: deb contents timestamp check failed: %s"
                 % (self.filename, e))


