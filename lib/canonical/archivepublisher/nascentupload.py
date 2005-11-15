# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""The processing of nascent uploads.

See the docstring on NascentUpload for more information.
"""

__metaclass__ = type

__all__ = ['NascentUpload']

import os
import sys
import md5
import sha
import tempfile
import re
import subprocess
import apt_pkg
import apt_inst
import shutil
import time

from canonical.encoding import guess as guess_encoding
from canonical.cachedproperty import cachedproperty

from canonical.archivepublisher.template_messages import (
    rejection_template, new_template, accepted_template, announce_template)

from canonical.archivepublisher.tagfiles import (
    parse_tagfile, TagFileParseError)

from canonical.archivepublisher.utils import (
    fix_maintainer, ParseMaintError, prefix_multi_line_string)

from canonical.lp.dbschema import (
    SourcePackageUrgency, PackagePublishingPriority,
    DistroReleaseQueueCustomFormat, BinaryPackageFormat,
    BuildStatus, DistroReleaseQueueStatus)

from canonical.launchpad.interfaces import (
    IGPGHandler, GPGVerificationError, IGPGKeySet, IPersonSet,
    ISourcePackageNameSet, IBinaryPackageNameSet, ILibraryFileAliasSet,
    NotFoundError)

from sourcerer.deb.version import (
    Version as DebianVersion, BadUpstreamError, VersionError)

from canonical.config import config
from zope.component import getUtility
from canonical.database.constants import UTC_NOW

# This is a marker as per the comment in dbschema.py: ##CUSTOMFORMAT##
# Essentially if you change anything to do with custom formats, grep for
# the marker in the codebase and make sure the same changes are made
# everywhere which needs them.
custom_sections = {
    'raw-installer': DistroReleaseQueueCustomFormat.DEBIAN_INSTALLER,
    'raw-translations': DistroReleaseQueueCustomFormat.ROSETTA_TRANSLATIONS,
    }

changes_mandatory_fields = set([
    "source", "binary", "architecture", "version", "distribution",
    "maintainer", "files", "changes"
    ])

dsc_mandatory_fields = set([
    "format", "source", "version", "binary", "maintainer", "architecture",
    "files"
    ])

# Capitalised because we extract direct from the deb/udeb where the
# other mandatory fields lists are lowercased by parse_tagfile
deb_mandatory_fields = set([
    "Package", "Architecture", "Version"
    ])

re_no_epoch = re.compile(r"^\d+\:")
re_no_revision = re.compile(r"-[^-]+$")
re_taint_free = re.compile(r"^[-+~/\.\w]+$")

re_isadeb = re.compile(r"(.+?)_(.+?)_(.+)\.u?deb$")
re_issource = re.compile(r"(.+)_(.+?)\.(orig\.tar\.gz|diff\.gz|tar\.gz|dsc)$")
re_strip_revision = re.compile(r"-([^-]+)$")

re_valid_version = re.compile(r"^([0-9]+:)?[0-9A-Za-z\.\-\+~:]+$")
re_valid_pkg_name = re.compile(r"^[\dA-Za-z][\dA-Za-z\+\-\.]+$")

re_extract_src_version = re.compile(r"(\S+)\s*\((.*)\)")

re_changes_file_name = re.compile(r"([^_]+)_([^_]+)_([^\.]+).changes")

# Map urgencies to their dbschema values
# Debian policy only permits low,medium,high,emergency
# Britney also uses critical which it maps to emergency
urgency_map = {
    "low": SourcePackageUrgency.LOW,
    "medium": SourcePackageUrgency.MEDIUM,
    "high": SourcePackageUrgency.HIGH,
    "critical": SourcePackageUrgency.EMERGENCY,
    "emergency": SourcePackageUrgency.EMERGENCY
    }

# Map priorities to their dbschema values
priority_map = {
    "required": PackagePublishingPriority.REQUIRED,
    "important": PackagePublishingPriority.IMPORTANT,
    "standard": PackagePublishingPriority.STANDARD,
    "optional": PackagePublishingPriority.OPTIONAL,
    "extra": PackagePublishingPriority.EXTRA
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


def filechunks(file, chunk_size=256*1024):
    """Return an iterator which reads chunks of the given file."""
    return iter(lambda: file.read(chunk_size), '')

        
class UploadError(Exception):
    """All upload errors are returned in this form."""


class FileNotFound(UploadError):
    """Raised when an upload error is due to a missing file."""


class NascentUploadedFile:
    """A nascent uploaded file is a file on disk that is part of an upload.

    The filename, along with information about it, is kept here.
    """

    def __init__(self, fsroot, fileline, is_dsc=False):
        if is_dsc:
            # dsc files lines are always of the form:
            # CHECKSUM SIZE FILENAME
            cksum, size, filename = fileline.strip().split()
            section = priority = "-"
        else:
            # files lines from a changes file are always of the form:
            # CHECKSUM SIZE [COMPONENT/]SECTION PRIORITY FILENAME
            cksum, size, section, priority, filename = fileline.strip().split()
        self.fsroot = fsroot
        self.filename = filename
        self.full_filename = os.path.join(fsroot,filename)
        self._digest = cksum
        self._size = int(size)
        self.component, self.section = self._split_section(section)
        self.priority = priority
        self.new = False
        self._values_checked = False

    @staticmethod
    def _libType(fname):
        """Return a content type for this named file."""
        for ending, content_type in filename_ending_content_type_map.items():
            if fname.endswith(ending):
                return content_type
        return "application/octet-stream"

    @property
    def content_type(self):
        """The content type for this file ready for adding to the librarian.
        """
        return self._libType(self.filename)

    @property
    def custom_type(self):
        """The custom upload type for this file. (None if not custom)."""
        if self.custom:
            return custom_sections[self.section]
        return None

    @staticmethod
    def _split_section(section):
        """Split the component out of the section."""
        # XXX: dsilvers: 20051013: This may not be enough, check back later.
        # bug 3137
        if "/" not in section:
            return "main", section
        return section.split("/")

    @property
    def present(self):
        """Whether or not the file is present on disk."""
        return os.path.exists(self.full_filename)

    def checkValues(self):
        """Check the md5sum and size of the nascent file.

        Raise UploadError if the digest or size does not match or if the
        file is not found on the disk.
        
        Populate self._sha_digest with the calculated sha1 digest of the
        file on disk.
        """
        if self._values_checked:
            return
        if not os.path.exists(os.path.join(self.fsroot,self.filename)):
            raise FileNotFound(
                "File %s as mentioned in the changes file was not found." % (
                self.filename))

        # Read in the file and compute its md5 and sha1 checksums and remember
        # the size of the file as read-in.
        cksum = md5.md5()
        sha_cksum = sha.sha()
        ckfile = open(os.path.join(self.fsroot, self.filename), "r")
        size = 0
        for chunk in filechunks(ckfile):
            cksum.update(chunk)
            sha_cksum.update(chunk)
            size += len(chunk)
        ckfile.close()

        # Check the size and checksum match what we were told in __init__
        if cksum.hexdigest() != self._digest:
            raise UploadError(
                "File %s mentioned in the changes has a checksum mismatch. "
                "%s != %s" % (self.filename, cksum.hexdigest(), self._digest))
        if size != self._size:
            raise UploadError(
                "File %s mentioned in the changes has a size mismatch. "
                "%s != %s" % (self.filename, size, self._size))

        # Record the sha1 digest and note that we have checked things.
        self._sha_digest = sha_cksum.hexdigest()
        self._values_checked = True
        
    @property
    def digest(self):
        self.checkValues()
        return self._digest

    @property
    def sha_digest(self):
        self.checkValues()
        return self._sha_digest

    @property
    def size(self):
        self.checkValues()
        return self._size

    @property
    def custom(self):
        return self.priority == "-" and self.section in custom_sections


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


class NascentUpload:
    """A nascent upload is a set of files which may or may not comprise an
    upload to a launchpad managed archive.

    The collaborative international dictionary of English defines nascent as:
    
     1. Commencing, or in process of development; beginning to
        exist or to grow; coming into being; as, a nascent germ.
        [1913 Webster +PJC]

    A nascent upload is thus in the process of coming into being. Specifcally
    a nascent upload is something we're trying to get into a shape we can
    insert into the database as a queued upload to be processed.
    """

    def __init__(self, policy, fsroot, changes_filename, logger):
        self.fsroot = fsroot
        self.policy = policy
        self.changes_filename = os.path.join(fsroot, changes_filename)
        if not os.path.exists(self.changes_filename):
            raise FileNotFound(changes_filename)
        self.changes_basename = changes_filename
        self.sender = "%s <%s>" % (
            config.uploader.default_sender_name,
            config.uploader.default_sender_address)
        self.recipients = ["%s <%s>" % (
            config.uploader.default_recipient_name,
            config.uploader.default_recipient_address)
                           ]
        self.logger = logger
        self.rejection_message = ""
        self.warnings = ""
        self.librarian = getUtility(ILibraryFileAliasSet)
        self.signer = None
        self.permitted_components = self.policy.getDefaultPermittedComponents()
        self._arch_verified = False
        self._native_checked = False

    def reject(self, msg):
        """Add the provided message to the rejection message."""
        if len(self.rejection_message) > 0:
            self.rejection_message += "\n"
        self.rejection_message += msg

    def warn(self, msg):
        """Add the provided message to the warning message."""
        if len(self.warnings) > 0:
            self.warnings += "\n"
        self.warnings += msg

    @cachedproperty("_cached_changes")
    def changes(self):
        """A dict of the parsed changes file."""
        changes = parse_tagfile(
            self.changes_filename,
            allow_unsigned = self.policy.unsigned_changes_ok)
        format = float(changes["format"])
        if format < 1.5 or format > 2.0:
            raise UploadError(
                "Format out of acceptable range for changes file. Range "
                "1.5 - 2.0, format %g" % format)
        return changes

    @cachedproperty('_parsed_files')
    def files(self):
        """The set of NascentUploadedFile instances which comprise the Files
        field in the changes file.
        """
        return self._parse_files(self.changes['files'])

    def _parse_files(self, filelist, is_dsc=False):
        """Parse the provided file list and return a list of
        NascentUploadedFile instances.

        If is_dsc is true then we parse the files lines as though they are from
        a .dsc file, otherwise we assume they're from a .changes file.
        The specific fields looked for by NascentUploadedFile's constructor
        varies based on whether or not it is a dsc file line. See the
        __init__ method of NascentUploadedFile for more information about the
        format.

        The filelist itself is assumed to be a string, newline delimited, of
        lines to be converted into NascentUploadedFile instances.
        """
        return [NascentUploadedFile(self.fsroot, line, is_dsc)
                for line in filelist.strip().split("\n")]

    def _verify_architecture(self):
        """Verify the architecture line in the changes file.

        If the architecture line doesn't match the uploaded file set then
        we reject the upload. Because we want to gather as much information
        about an upload as possible when we reject it, we call self.reject
        which accumulates a rejection message rather than raising an exception.

        As a side-effect we also set up various attributes used later by some
        of the properties such as 'sourceful' or 'binaryful'
        """

        if self._arch_verified:
            return
        
        arch = self.changes['architecture']
        think_sourceful = False
        think_binaryful = False
        think_archindep = False
        think_archdep = False
        
        arch_contents = set(arch.split())
        
        if 'source' in arch_contents:
            think_sourceful = True
            arch_contents.remove('source')

        if arch != 'source':
            think_binaryful = True

        if 'all' in arch_contents:
            think_archindep = True
            arch_contents.remove('all')

        if think_binaryful and len(arch_contents) > 0:
            think_archdep = True

        files_sourceful = False
        files_binaryful = False
        files_archindep = False
        files_archdep = False

        for uploaded_file in self.files:
            if uploaded_file.custom:
                files_binaryful = True
            else:
                filename = uploaded_file.filename
                if filename.endswith(".deb") or filename.endswith(".udeb"):
                    files_binaryful = True
                    if (filename.endswith("_all.deb") or
                        filename.endswith("_all.udeb")):
                        files_archindep = True
                    else:
                        files_archdep = True
                elif (filename.endswith(".tar.gz") or
                      filename.endswith(".diff.gz") or
                      filename.endswith(".dsc")):
                    files_sourceful = True
                else:
                    raise UploadError("Unable to identify file %s in changes." % filename)

        if files_sourceful != think_sourceful:
            self.reject(
                "Mismatch in sourcefulness. (arch) %s != (files) %s" % (
                think_sourceful, files_sourceful))
        if files_binaryful != think_binaryful:
            self.reject(
                "Mismatch in binaryfulness. (arch) %s != (files) %s" % (
                think_binaryful, files_binaryful))

        if files_archindep != think_archindep:
            self.reject("Mismatch in architecture independence. "
                        "(arch) %s != (files) %s" %
                        (think_archindep, files_archindep))

        if files_archindep != think_archindep:
            self.reject("Mismatch in architecture dependence. "
                        "(arch) %s != (files) %s" %
                        (think_archindep, files_archindep))

        # Remember the information for later use in properties.
        self._sourceful = think_sourceful
        self._binaryful = think_binaryful
        self._archindep = think_archindep
        self._archdep = think_archdep
        # And make a "note-to-self" that we've done this
        self._arch_verified = True

    @cachedproperty
    def sourceful(self):
        self._verify_architecture()
        return self._sourceful

    @cachedproperty
    def binaryful(self):
        self._verify_architecture()
        return self._binaryful

    @cachedproperty
    def archindep(self):
        self._verify_architecture()
        return self._archindep
    
    @cachedproperty
    def archdep(self):
        self._verify_architecture()
        return self._archdep

    @property
    def archs(self):
        """Return the architecture tag set.

        For example, if the changes file had "source i386" then we return
        a list: ['source', 'i386']
        """
        return set(self.changes['architecture'].strip().split())
    
    @cachedproperty
    def native(self):
        self._check_native()
        return self._native

    @cachedproperty
    def hasorig(self):
        self._check_native()
        return self._has_orig

    def _check_native(self):
        """Check if this sourceful upload is native or not, remembering if
        we have an orig.tar.gz or not.

        Raise UploadError if an attempt to check a non-sourceful upload is
        made.
        """
        if self._native_checked:
            return True
        
        if not self.sourceful:
            raise UploadError("Attempted to ask a non-sourceful upload "
                              "if it is native or not.")
        
        dsc = 0
        diff = 0
        orig = 0
        tar = 0

        for uploaded_file in self.files:
            if uploaded_file.filename.endswith(".dsc"):
                dsc += 1
            elif uploaded_file.filename.endswith(".diff.gz"):
                diff += 1
            elif uploaded_file.filename.endswith(".orig.tar.gz"):
                orig += 1
            elif (uploaded_file.filename.endswith(".tar.gz")
                  and not uploaded_file.custom):
                tar += 1

        # Okay, let's check the sanity of the upload.

        if dsc > 1:
            self.reject("Changes file lists more than one .dsc")
        if diff > 1:
            self.reject("Changes file lists more than one .diff.gz")
        if orig > 1:
            self.reject("Changes file lists more than one orig.tar.gz")
        if tar > 1:
            self.reject("Changes file lists more than one native tar.gz")

        if dsc == 0:
            self.reject("Sourceful upload without a .dsc")
        if diff == 0 and tar == 0:
            self.reject("Sourceful upload without a diff or native tar")

        self._native = tar != 0
        self._has_orig = orig != 0
        self._native_checked = True
        
    def verify_sig(self, filename):
        """Verify the signature on the filename.

        We return both the fingerprint and the Person record if the key is
        found and the signature verified. If the signature is bad, we raise
        a failure to verify which will end up translated into a rejection
        of the upload.

        Raise UploadError if the signing key cannot be found in launchpad
        or if the GPG verification failed for any other reason.

        Returns the key owner (person object), the key (gpgkey object) and
        the pyme signature as a three-tuple
        """
        try:
            self.logger.debug("Verifying signature on %s" % filename)
            sig = getUtility(IGPGHandler).getVerifiedSignature(
                file(os.path.join(self.fsroot, filename), "rb").read())

            key = getUtility(IGPGKeySet).getByFingerprint(sig.fingerprint)

            if key is None:
                raise UploadError("Signing key not found within launchpad.")

            return key.owner, key, sig
            
        except GPGVerificationError, e:
            raise UploadError("GPG verification of %s failed: %s" % (filename,
                                                                    str(e)))

    def _find_signer(self):
        """Find the signer and signing key for the .changes file.

        While this returns nothing itself, it has the side effect of setting
        self.signer and self.signingkey (and if availabile,
        self.signer_address also)

        If on exit from this, self.signer is None, you cannot trust the rest
        of the values about the signer of the changes file. This is the case
        when the policy permits unsigned changes. Policies such as the buildd
        policy do this.
        """
        if self.policy.unsigned_changes_ok:
            self.signer = None
            self.signingkey = None
        else:
            self.logger.debug("Checking signature on changes file.")
            self.signer, self.signingkey, unwanted_sig = self.verify_sig(
                self.changes_basename)
            self.signer_address = self.parse_address("%s <%s>" % (
                self.signer.displayname, self.signer.preferredemail.email))
            assert self.signer_address['person'] == self.signer

    def parse_address(self, addr, fieldname="Maintainer"):
        """Parse an address, using the policy to decide if we should add a
        non-existent person or not.

        Raise an UploadError if the parsing of the maintainer string fails
        for any reason, or if the email address then cannot be found within
        the launchpad database.

        Return a dict containing the rfc822 and rfc2047 formatted forms of
        the address, the person's name, email address and person record within
        the launchpad database.
        """
        try:
            (rfc822, rfc2047, name, email) = fix_maintainer(str(addr),
                                                            fieldname)
        except ParseMaintError, e:
            raise UploadError(str(e))

        if self.policy.create_people:
            person = getUtility(IPersonSet).ensurePerson(email, name)
        else:
            person = getUtility(IPersonSet).getByEmail(email)

        if person is None:
            raise UploadError("Unable to identify %s <%s> in launchpad" % (
                name, email))

        return {
            "rfc822": rfc822,
            "rfc2047": rfc2047,
            "name": name,
            "email": email,
            "person": person
            }

    @cachedproperty
    def closes(self):
        """A list of the bug numbers closed (if any) by this upload.

        Raise UploadErorr if any of the entries in the Closes line do
        not parse as numbers.
        """
        bugs = []
        if 'closes' in self.changes:
            for elem in self.changes['closes'].strip().split():
                if not elem.isdigit():
                    raise UploadError("'%s' is not a number when parsing "
                                      "Closes line in the changes." % elem)
                bugs.append(int(elem))
        return bugs

    @property
    def binaries(self):
        """Extract the list of binaries and return them as a set."""
        return set(self.changes['binary'].strip().split())

    def verify_changes(self):
        """Run all the verification checks on the changes data.

        This may raise UploadError if something very bad is wrong with the
        changes file. Otherwise self.reject will have been called with
        what could be termed non-fatal errors.
        """

        self.logger.debug("Verifying the changes file.")

        # Prove we can parse.
        changes = self.changes
        # And extract the files
        files = self.files
        # And that there's > 0 files
        if len(files) == 0:
            raise UploadError("No files found in the changes")
        # Verify that the mandatory fields are present.
        for mandatory_field in changes_mandatory_fields:
            if mandatory_field not in changes:
                raise UploadError(
                    "Unable to find mandatory field '%s' in the changes "
                    "file." % mandatory_field)
        # Verify we can parse the maintainer.
        self.changes_maintainer = self.parse_address(changes['maintainer'])
        # Verify we can parse the changed-by
        self.changed_by = self.parse_address(changes['changed-by'])
        # Confirm that the 'closes' line is valid
        closes = self.closes
        # Prepare the no-epoch and no-epoch-no-revision version numbers
        changes["chopversion"] = re_no_epoch.sub('', changes["version"])
        changes["chopversion2"] = re_no_revision.sub(
            '', changes["chopversion"])
        # Verify we can translate the urgency.
        if not urgency_map.has_key(changes['urgency'].lower()):
            self.warn("Unable to grok urgency %s, overriding it with 'low'" % (
                changes['urgency']))
            changes['urgency'] = "low"
        # Store the architecture of the changes file away for later.
        m = re_changes_file_name.match(self.changes_basename)
        self.changes_filename_archtag = m.group(3)
        # Wahey, the changes are parsed all okay :-)

    @cachedproperty
    def distro(self):
        """Simply propogate the distro of the policy."""
        return self.policy.distro

    @cachedproperty
    def distrorelease(self):
        """The distrorelease pertaining to this upload.

        If the policy has not yet had its distrorelease set, resolving this
        property will set it.
        """
        dr_name = self.changes['distribution']
        try:
            self.policy.setDistroReleaseAndPocket(dr_name)
        except NotFoundError:
            raise UploadError("Unable to find distrorelease: %s" % dr_name)
        return self.policy.distrorelease
    
    @cachedproperty
    def pocket(self):
        """The pocket pertaining to this upload.

        If the policy has not yet had its distrorelease set, resolving this
        property will set it.
        """
        dr_name = self.changes['distribution']
        try:
            self.policy.setDistroReleaseAndPocket(dr_name)
        except NotFoundError:
            raise UploadError("Unable to find distrorelease: %s" % dr_name)
        return self.policy.pocket

    def verify_uploaded_deb_or_udeb(self, uploaded_file):
        """Verify the contents of the .deb or .udeb as best we can.

        Should not raise anything itself but makes little effort to catch
        exceptions raised in anything it calls apart from where apt_pkg or
        apt_inst may go bonkers. Those are generally caught and swallowed.
        """
        self.logger.debug("Verifying binary %s" % uploaded_file.filename)
        if not self.binaryful:
            self.reject("Found %s in an allegedly non-binaryful upload." % (
                uploaded_file.filename))
        deb_file = open(uploaded_file.full_filename, "r")
        # Extract the control information
        try:
            control = apt_pkg.ParseSection(apt_inst.debExtractControl(deb_file));
        except:
            # Swallow everything apt_pkg and apt_inst throw at us because they
            # are not desperately pythonic and can raise odd or confusing
            # exceptions at times and are out of our control.
            deb_file.close();
            self.reject("%s: debExtractControl() raised %s." % (
                uploaded_file.filename, sys.exc_type));
            return

        # Check for mandatory control fields
        for mandatory_field in deb_mandatory_fields:
            if control.Find(mandatory_field) is None:
                self.reject("%s: control file lacks %s field." % (
                    uploaded_file.filename, mandatory_field))

        # Ensure the package name matches one in the changes file
        if control.Find("Package", "") not in self.binaries:
            self.reject(
                "%s: control file lists name as `%s', which isn't in changes "
                "file." % (uploaded_file.filename,
                           control.Find("Package", "")))

        # Cache the control information for later.
        uploaded_file.control = {}
        for key in control.keys():
            uploaded_file.control[key] = control.Find(key)

        # Validate the package field
        package = control.Find("Package");
        if not re_valid_pkg_name.match(package):
            self.reject("%s: invalid package name '%s'." % (
                uploaded_file.filename, package));

        # Validate the version field
        version = control.Find("Version");
        if not re_valid_version.match(version):
            self.reject("%s: invalid version number '%s'." % (
                uploaded_file.filename, version));

        # Ensure the architecture of the .deb is valid in the target
        # distrorelease
        arch = control.Find('Architecture', "")
        valid_archs = self.distrorelease.architectures
        found_arch = False
        for valid_arch in valid_archs:
            if valid_arch.architecturetag == arch:
                found_arch = True
        if not found_arch and arch != "all":
            self.reject("%s: Unknown architecture: '%s'." % (
                uploaded_file.filename, arch))

        # Ensure the arch of the .deb is listed in the changes file
        if arch not in self.archs:
            self.reject("%s: control file lists arch as '%s' which isn't "
                        "in the changes file." % (uploaded_file.filename,
                                                  arch))

        # Sanity check the depends field.
        depends = control.Find('Depends')
        if depends == '':
            self.reject("%s: Depends field present and empty." % (
                uploaded_file.filename))

        # Check the section & priority match those in the .changes Files entry
        if (control.Find("Section") and
            uploaded_file.section != "" and
            uploaded_file.section != control.Find("Section")):
            self.reject("%s control file lists section as %s but changes file "
                        "has %s." % (uploaded_file.filename,
                                     control.Find("Section"),
                                     uploaded_file.section))
        if (control.Find("Priority") and
            uploaded_file.priority != "" and
            uploaded_file.priority != control.Find("Priority")):
            self.reject("%s control file lists priority as %s but changes file"
                        " has %s." % (uploaded_file.filename,
                                      control.Find("Priority"),
                                      uploaded_file.priority))

        # Check the filename ends with .deb or .udeb
        if not (uploaded_file.filename.endswith(".deb") or
                uploaded_file.filename.endswith(".udeb")):
            self.reject(
                "%s is neither a .deb or a .udeb" % uploaded_file.filename)

        uploaded_file.package = package
        uploaded_file.architecture = arch
        uploaded_file.version = version
        uploaded_file.maintainer = control.Find("Maintainer", "")
        uploaded_file.source = control.Find("Source", package)

        # Find the source version for the package.
        source = uploaded_file.source
        source_version = ""
        if "(" in source:
            src_match = re_extract_src_version.match(source)
            source = src_match.group(1)
            source_version = src_match.group(2)
        if not source_version:
            source_version = version

        uploaded_file.source_package = source
        uploaded_file.source_version = source_version
        if uploaded_file.filename.endswith(".udeb"):
            uploaded_file.type = "udeb"
        else:
            uploaded_file.type = "deb"

        # Ensure the filename matches the contents of the .deb
        deb_match = re_isadeb.match(uploaded_file.filename)
        # First check the file package name matches the deb contents.
        file_package = deb_match.group(1)
        if package != file_package:
            self.reject(
                "%s: package part of filename (%s) does not match "
                "package name in the control fields (%s)." % (
                uploaded_file.filename,
                file_package,
                package))

        # Next check the version matches.
        epochless_version = re_no_epoch.sub('', version)
        file_version = deb_match.group(2)
        if epochless_version != file_version:
            self.reject(
                "%s: version part of the filename (%s) does not match "
                "the version in the control fields (%s)." % (
                uploaded_file.filename,
                file_version,
                epochless_version))

        # Verify that the source versions match if present.
        if 'source' in self.archs:
            if source_version != self.changes['version']:
                self.reject(
                    "source version (%s) for %s does not match changes "
                    "version %s" % (
                    source_version,
                    uploaded_file.filename,
                    self.changes['version']))
        else:
            # Try and find the source in the distrorelease.
            dr = self.policy.distrorelease
            spn = getUtility(ISourcePackageNameSet).getOrCreateByName(source)
            releases = dr.getPublishedReleases(spn, self.policy.pocket)
            found = False
            for spr in releases:
                if spr.sourcepackagerelease.version == source_version:
                    self.policy.sourcepackagerelease = spr.sourcepackagerelease
                    found = True
            if not found:
                # XXX: dsilvers: 20051012: Perhaps check the NEW queue too?
                # bug 3138
                self.reject("Unable to find source package %s/%s in %s" % (
                    source, source_version, dr.name))

        # Debian packages are in fact 'ar' files. Thus we run '/usr/bin/ar'
        # to look at the contents of the deb files to confirm they make sense.
        ar_process = subprocess.Popen(
            ["/usr/bin/ar", "t", uploaded_file.full_filename],
            stdout=subprocess.PIPE)
        output = ar_process.stdout.read()
        result = ar_process.wait()
        if result != 0:
            self.reject("%s: 'ar t' invocation failed." % (
                uploaded_file.filename))
            self.reject(prefix_multi_line_string(output, " [ar output:] "))
        chunks = output.strip().split("\n")
        if len(chunks) != 3:
            self.reject("%s: found %d chunks, expecting 3. %r" % (
                uploaded_file.filename, len(chunks), chunks))

        debian_binary, control_tar, data_tar = chunks
        if debian_binary != "debian-binary":
            self.reject("%s: first chunk is %s, expected debian-binary" % (
                uploaded_file.filename, debian_binary))
        if control_tar != "control.tar.gz":
            self.reject("%s: second chunk is %s, expected control.tar.gz" % (
                uploaded_file.filename, control_tar))
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
                            "on dpkg (>= 1.10.24)" % uploaded_file.filename)
        elif data_tar != "data.tar.gz":
            self.reject("%s: third chunk is %s, expected data.tar.gz or "
                        "data.tar.bz2" % (uploaded_file.filename, data_tar))

        # That's all folks.

    def verify_uploaded_source_file(self, uploaded_file):
        """Verify the uploaded source file.

        Should not raise anything unless something unexpected happens. All
        errors should be accumulated in the rejection message.
        """
        self.logger.debug("Verifying source file %s" % uploaded_file.filename)
        if not self.sourceful:
            self.reject("Found file %s but upload allegedly non-sourceful" % (
                uploaded_file.filename))
            
        source_match = re_issource.match(uploaded_file.filename)
        uploaded_file.package = source_match.group(1)
        uploaded_file.version = source_match.group(2)
        uploaded_file.type = source_match.group(3)

        if self.changes['source'] != uploaded_file.package:
            self.reject("%s: changes file doesn't say %s for Source" % (
                uploaded_file.filename, uploaded_file.package))
            
        if uploaded_file.type == "orig.tar.gz":
            changes_version = self.changes['chopversion2']
        else:
            changes_version = self.changes['chopversion']
        if changes_version != uploaded_file.version:
            self.reject("%s: should be %s according to changes file." % (
                uploaded_file.filename, changes_version))

        if 'source' not in self.archs:
            self.reject("%s: changes file doesn't list 'source' in "
                        "Architecture field." % (uploaded_file.filename))

        self.dsc_signing_key=None
        if uploaded_file.type == 'dsc' and not self.policy.unsigned_dsc_ok:
            try:
                who, key, sig = self.verify_sig(uploaded_file.full_filename)
                uploaded_file.fingerprint = sig.fingerprint
                self.dsc_signing_key = key
            except UploadError, e:
                self.reject("%s: %s" % (uploaded_file.filename, str(e)))
        
    def verify_uploaded_files(self):
        """Verify each file provided in the upload passes some checks.

        No exceptions should be raised unless something unexpected happens.
        All errors should be accumulated in the rejection message.

        As a side effect, various attributes are set on the uploaded files
        such as whether or not they are sourceful, what their type is (deb,
        dsc, udeb, tar.gz, byhand etc) and also priorities are mapped to
        dbschemas.
        """
        self.logger.debug("Verifying files in upload.")
        for uploaded_file in self.files:
            # Verify the filename doesn't contain invalid chars.
            if not re_taint_free.match(uploaded_file.filename):
                self.reject("!!WARNING!! tainted filename: '%s'." % (file));
            # Can we read the file, does its md5/size match?
            uploaded_file.checkValues()
            if re_isadeb.match(uploaded_file.filename):
                uploaded_file.is_source=False
                self.verify_uploaded_deb_or_udeb(uploaded_file)
            elif re_issource.match(uploaded_file.filename):
                uploaded_file.is_source=True
                self.verify_uploaded_source_file(uploaded_file)
            else:
                # It's byhand.
                uploaded_file.is_source=False
                uploaded_file.type = "byhand"
                
        self.logger.debug("Performing overall file verification checks.")
        for uploaded_file in self.files:
            if uploaded_file.type == "byhand" or uploaded_file.custom:
                continue
            # Check the priority is mapable
            if uploaded_file.priority is None:
                self.reject("%s: Priority is 'None'" % uploaded_file.filename)
            if (uploaded_file.priority != "" and
                uploaded_file.priority != "-" and
                uploaded_file.priority not in priority_map):
                self.reject("Unable to map priority %r for file %s" % (
                    uploaded_file.priority, uploaded_file.filename))
            # Map the priority
            if (uploaded_file.priority != "" and
                uploaded_file.priority != "-" and
                uploaded_file.priority in priority_map):
                uploaded_file.priority = priority_map[uploaded_file.priority]
            
            # Validate the component and section. (needs the distrorelease)
            dr = self.distrorelease
            valid_components = set(
                component.name for component in dr.components)
            valid_sections = set(section.name for section in dr.sections)
            if uploaded_file.component not in valid_components:
                self.reject("%s: Component %s is not valid" % (
                    uploaded_file.filename, uploaded_file.component))
            if uploaded_file.section not in valid_sections:
                self.reject("%s: Section %s is not valid" % (
                    uploaded_file.filename, uploaded_file.section))

        # Finally verify that sourceful/binaryful match the policy
        if self.sourceful and not self.policy.can_upload_source:
            self.reject(
                "Upload is sourceful, but policy refuses sourceful uploads.")

        if self.binaryful and not self.policy.can_upload_binaries:
            self.reject(
                "Upload is binaryful, but policy refuses binaryful uploads.")

        if (self.sourceful and self.binaryful and
            not self.policy.can_upload_mixed):
            self.reject(
                "Upload is source/binary but policy refuses mixed uploads.")

    def _find_dsc(self):
        """Return the .dsc file from the files list."""
        for uploaded_file in self.files:
            if uploaded_file.type == "dsc":
                return uploaded_file
        return None
    
    def verify_uploaded_dsc(self):
        """Verify the uploaded .dsc file.

        Should raise no exceptions unless unforseen issues occur. Errors will
        be accumulated in the rejection message.
        """
        self.logger.debug("Performing DSC verification.")
        dsc_file = self._find_dsc()
        if dsc_file is None:
            self.reject("Unable to find the dsc file in the sourceful upload?")
            return False
        
        # Try to parse the dsc
        dsc = {}
        try:
            dsc.update(parse_tagfile(
                dsc_file.full_filename, dsc_whitespace_rules=1,
                allow_unsigned=self.policy.unsigned_dsc_ok))
        except TagFileParseError, e:
            self.reject("Unable to parse the dsc %s: %s" % (
                dsc_file.filename, e))

        # Mandatory fields.
        for mandatory_field in dsc_mandatory_fields:
            if mandatory_field not in dsc:
                self.reject("Unable to find mandatory field %s in %s" % (
                    mandatory_field, dsc_file.filename))
                return False

        self.dsc_contents = dsc
        self.dsc_files = self._parse_files(dsc['files'], is_dsc=True)
        dsc_files = self.dsc_files
        
        # Validate the 'Source' and 'Version' fields
        if not re_valid_pkg_name.match(dsc['source']):
            self.reject("%s: invalid source name %s" % (
                dsc_file.filename, dsc['source']))
        if not re_valid_version.match(dsc['version']):
            self.reject("%s: invalid version %s" % (
                dsc_file.filename, dsc['version']))

        # .dsc files must be version 1.0
        if dsc['format'] != "1.0":
            self.reject("%s: Format is not 1.0. This is incompatible with "
                        "dpkg-source." % dsc_file.filename)

        # Attempt to validate the maintainer.
        try:
            self.dsc_maintainer = self.parse_address(dsc['maintainer'])
        except UploadError, e:
            self.reject("%s: unable to parse maintainer field %s: %s" % (
                dsc_file.filename, dsc['maintainer'], e))

        # Validate the build dependencies
        for field_name in ['build-depends', 'build-depends-indep']:
            field = dsc.get(field_name)
            if field:
                if field.startswith("ARRAY"):
                    self.reject(
                        "%s: invalid %s field produced by a broken version of "
                        "dpkg-dev (1.10.11)" % (
                        dsc_file.filename,
                        field_name.title()))

                try:
                    apt_pkg.ParseSrcDepends(field)
                except:
                    # Swallow everything apt_pkg throws at us because
                    # it is not desperately pythonic and can raise odd
                    # or confusing exceptions at times and is out of
                    # our control.
                    reject("%s: invalid %s field. (cannot be parsed by apt)" %(
                        dsc_file.filename, field_name.title()))

        # Verify the filename matches appropriately
        epochless_dsc_version = re_no_epoch.sub('', dsc["version"]);
        changes_version = dsc_file.version
        if epochless_dsc_version != changes_version:
            self.reject("%s: version ('%s') in .dsc does not match version "
                        "('%s') in .changes." % (
                dsc_file.filename, epochless_dsc_version, changes_version));

        # Verify the file list.
        has_tar = False
        for sub_dsc_file in dsc_files:
            source_match = re_issource.match(sub_dsc_file.filename)
            if not source_match:
                self.reject("%s: File %s does not look sourceful." % (
                    dsc_file.filename, sub_dsc_file.filename))
                dsc_file_type = "UNKNOWN"
            else:
                dsc_file_type = source_match.group(3)
            if dsc_file_type == "orig.tar.gz" or dsc_file_type == "tar.gz":
                has_tar = True
        if not has_tar:
            self.reject("%s: does not mention any tar.gz or orig.tar.gz." % (
                        dsc_file.filename))

        # Confirm that the published versions are younger.
        try:
            version = DebianVersion(dsc['version'])
            spn = getUtility(ISourcePackageNameSet).getOrCreateByName(
                dsc['source'])
            self.spn = spn
            releases = self.distrorelease.getPublishedReleases(
                spn, self.policy.pocket)
            beaten = False
            for pub_record in releases:
                try:
                    pub_version = pub_record.sourcepackagerelease.version
                    pub_version = DebianVersion(pub_version)
                    if pub_version >= version:
                        beaten = True
                except BadUpstreamError:
                    # We beat the published version if we're parseable and
                    # they're not.
                    pass
            if beaten:
                self.reject("%s: Version younger than that in the archive." % (
                            dsc_file.filename))
                            
        except VersionError, e:
            self.reject("%s: Exception verifying version is newer: %s\n"
                        "%s: %s" % (
                dsc_file.filename, e, sys.exc_type, sys.exc_value))
        except NotFoundError, e:
            self.reject("%s: Exception verifying version is newer: %s\n"
                        "%s: %s" % (
                dsc_file.filename, e, sys.exc_type, sys.exc_value))
            

        # For any file mentioned in the upload which does not exist in the
        # upload, go ahead and find it from the database.
        for sub_dsc_file in dsc_files:
            if not sub_dsc_file.present:
                # The file is not present on disk, try downloading it.
                library_file = self.distro.getFileByName(sub_dsc_file.filename,
                                                         source=True,
                                                         binary=False)
                if library_file is None:
                    self.reject("Unable to find %s in the distribution." % (
                        sub_dsc_file.filename))
                else:
                    # Pump the file through.
                    self.logger.debug("Pumping %s out of the librarian" % (
                        sub_dsc_file.filename))
                    library_file.open()
                    target_file = open(sub_dsc_file.full_filename, "wb")
                    for chunk in filechunks(library_file):
                        target_file.write(chunk)
                    target_file.close()
                    library_file.close()
            try:
                sub_dsc_file.checkValues()
            except UploadError, e:
                self.reject("Unable to validate %s from %s: %s" % (
                    sub_dsc_file.filename, dsc_file.filename, e))

        # Since we verified the dsc okay, we can have a go at the source itself
        self.verify_uploaded_source()

    def verify_uploaded_source(self):
        """Verify that the source itself is unpackable etc.

        Should not raise any exceptions. Errors are logged in the rejection
        message.
        """
        self.logger.debug("Verifying uploaded source package by unpacking it.")
        # We can do nothing if not sourceful.
        if not self.sourceful:
            return

        # Nor indeed if we lack a dsc file
        dsc_file = self._find_dsc()
        if dsc_file is None:
            return
        
        # Get a temporary dir together.
        tmpdir = tempfile.mkdtemp(dir=self.fsroot)

        # chdir into it
        cwd = os.getcwd()
        os.chdir(tmpdir)

        self.dsc_files.append(dsc_file)
        
        try:
            for source_file in self.dsc_files:
                os.symlink(source_file.full_filename,
                           os.path.join(tmpdir, source_file.filename))
            args = ["dpkg-source", "-sn", "-x",
                    os.path.join(tmpdir,dsc_file.filename)]
            dpkg_source = subprocess.Popen(args, stdout=subprocess.PIPE)
            output = dpkg_source.stdout.read()
            result = dpkg_source.wait()
            if result != 0:
                self.reject("dpkg-source failed for %s [return code: %s]" % (
                    dsc_file.filename, result))
                self.reject(prefix_multi_line_string(
                    output, " [dpkg-source output:] "))
        finally:
            # When all is said and done, chdir out again so that we can
            # clean up the tree with shutil.rmtree without leaving the
            # process in a directory we're trying to remove.
            os.chdir(cwd)

        self.logger.debug("Cleaning up source tree.")
        # Now we've run it through, clean up.
        try:
            shutil.rmtree(tmpdir)
        except OSError, e:
            if errno.errorcode[e.errno] != 'EACCES':
                raise UploadError("%s: couldn't remove tmp dir %s" % (
                    dsc_file.filename, tmpdir))
            self.reject("%s: source tree could not be cleanly removed." % (
                dsc_file.filename))
            result = os.system("chmod -R u+rwx " + tmpdir)
            if result != 0:
                raise UploadError("chmod failed with %s" % result)
            shutil.rmtree(tmpdir)
        self.logger.debug("Done")

    def verify_deb_timestamps(self):
        """Verify that the data tarballs in the debs are in-range for time."""

        future_cutoff = time.time() + self.policy.future_time_grace
        past_cutoff = time.mktime(
            time.strptime(str(self.policy.earliest_year), "%Y"))
        tar_checker = TarFileDateChecker(future_cutoff, past_cutoff)

        for uploaded_file in self.files:
            if uploaded_file.type == "deb":
                self.logger.debug("Verifying timestamps in %s" % (
                    uploaded_file.filename))
                tar_checker.reset()
                try:
                    deb_file = open(uploaded_file.full_filename, "rb")
                    apt_inst.debExtract(deb_file, tar_checker.callback,
                                        "control.tar.gz")
                    deb_file.seek(0)
                    try:
                        apt_inst.debExtract(deb_file,tar_checker.callback,
                                            "data.tar.gz")
                    except SystemError, e:
                        # If we can't find a data.tar.gz,
                        # look for data.tar.bz2 instead.
                        if not re.match(r"Cannot f[ui]nd chunk data.tar.gz$",
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
                            uploaded_file.filename, len(future_files),
                            future_files[0],
                            time.ctime(
                            tar_checker.future_files[future_files[0]])))

                    ancient_files = tar_checker.ancient_files.keys()
                    if ancient_files:
                        self.reject("%s: has %s file(s) with a time stamp too "
                                    "far into the future (e.g. %s [%s])." % (
                            uploaded_file.filename, len(ancient_files),
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
                        uploaded_file.filename, sys.exc_type, sys.exc_value));

    def _components_valid_for(self, person):
        """Return the set of components this person could upload to."""
        
        possible_components = set()
        for acl in self.distro.uploaders:
            if person in acl:
                self.logger.debug("%s (%d) is in %s's uploaders." % (
                    person.displayname, person.id, acl.component.name))
                possible_components.add(acl.component.name)

        return possible_components
    
    def is_person_in_keyring(self, person):
        """Return whether or not the specified person is in the keyring."""
        self.logger.debug("Attempting to decide if %s is in the keyring." % (
            person.displayname))
        in_keyring = len(self._components_valid_for(person)) > 0
        self.logger.debug("Decision: %s" % in_keyring)
        return in_keyring

    def process_signer_acl(self):
        """Work out what components the signer is permitted to upload to and
        verify that all files are either NEW or are targetted at those
        components only.
        """

        # If we have no signer, there's no ACL we can apply
        if self.signer is None:
            return

        possible_components = self._components_valid_for(self.signer)

        if not possible_components:
            self.reject("Signer has no upload rights at all to this "
                        "distribution.")

        self.permitted_components = possible_components

    def find_and_apply_overrides(self):
        """Look in the db for each part of the upload to see if it's overridden
        or not.

        Anything not yet in the DB gets tagged as 'new' and won't count
        towards the permission check.
        """

        self.logger.debug("Finding and applying overrides.")
        
        for uploaded_file in self.files:
            if uploaded_file.is_source and uploaded_file.type == "dsc":
                # Look up the source package overrides in the distrorelease
                spn = getUtility(ISourcePackageNameSet).getOrCreateByName(
                    uploaded_file.package)
                possible = self.distrorelease.getPublishedReleases(
                    spn, self.policy.pocket)
                if possible:
                    self.logger.debug("%s: (source) exists" % (
                        uploaded_file.package))
                    # We have a set of possible overrides. The first in
                    # the set will be the most useful since it should be
                    # the most recently uploaded. We therefore use this one.
                    override = possible[0]
                    uploaded_file.component = override.component.name
                    uploaded_file.section = override.section.name
                    uploaded_file.new = False
                else:
                    self.logger.debug("%s: (source) NEW" % (
                        uploaded_file.package))
                    uploaded_file.new = True
            elif not uploaded_file.is_source:
                # Look up the binary package overrides in the relevant
                # distroarchrelease
                bpn = getUtility(IBinaryPackageNameSet).getOrCreateByName(
                    uploaded_file.package)
                # Cache the bpn for later.
                uploaded_file.bpn = bpn
                archtag = uploaded_file.architecture
                if archtag == "all":
                    archtag = self.changes_filename_archtag
                try:
                    dar = self.distrorelease[archtag]
                    possible = dar.getReleasedPackages(bpn, self.policy.pocket)
                    if possible:
                        self.logger.debug("%s: (binary) exists" % (
                            uploaded_file.package))
                        # We have a set of possible overrides. The
                        # first in the set will be the most useful
                        # since it should be the most recently
                        # uploaded. We therefore use this one.
                        override=possible[0]
                        uploaded_file.component = override.component.name
                        uploaded_file.section = override.section.name
                        uploaded_file.priority = override.priority
                        uploaded_file.new = False
                    else:
                        self.logger.debug("%s: (binary) NEW" % (
                            uploaded_file.package))
                        uploaded_file.new = True
                except NotFoundError:
                    self.reject("%s: Unable to find arch: %s" % (
                        uploaded_file.filename, archtag))
                                      

    def verify_acl(self):
        """Verify that the uploaded files are okay for their named components
        by the provided signer.
        """
        if self.signer is None:
            return

        for uploaded_file in self.files:
            if uploaded_file.is_source and uploaded_file.type != "dsc":
                # We don't do overrides on diff/tar
                continue
            if (uploaded_file.component not in self.permitted_components and
                uploaded_file.new == False):
                self.reject("Signer is not permitted to upload to the "
                            "component '%s' of file '%s'" % (
                    uploaded_file.component, uploaded_file.filename))

    def process(self):
        """Process this upload, checking it against policy, loading it into
        the database if it seems okay.

        No exceptions should be raised. In a few very unlikely events, an
        UploadError will be raised and sent up to the caller. If this happens
        the caller should call the reject method and process a rejection.
        """
        self.logger.debug("Beginning processing.")

        # Verify the changes information.
        
        self._find_signer()
        if self.signer is not None:
            self.policy.considerSigner(self.signer, self.signingkey)
        
        self.process_signer_acl()

        self.verify_changes()
        self.verify_uploaded_files()

        # If there are no possible components, then this uploader simply does
        # not have any rights on this distribution so stop now before we
        # go processing crap.
        if not self.permitted_components:
            self.reject("Unable to find a component acl OK for the uploader")
            return
        
        if self.sourceful:
            self.verify_uploaded_dsc()

        if self.binaryful:
            self.verify_deb_timestamps()

        # Apply the overrides from the database.
        self.find_and_apply_overrides()

        # Verify ACLs
        self.verify_acl()

        # And finally, check that the policy is happy overall
        self.policy.policySpecificChecks(self)

        # That's all folks.
        self.logger.debug("Finished checking upload.")
        
    @property
    def rejected(self):
        """Returns whether or not this upload was rejected."""
        return len(self.rejection_message) > 0

    def build_recipients(self):
        """Build self.recipients up to include every address we trust."""
        if self.signer:
            self.recipients.append(self.signer_address['rfc2047'])
            if (self.changes_maintainer['person'] != self.signer and
                self.is_person_in_keyring(self.changes_maintainer['person'])):
                self.recipients.append(self.changes_maintainer['rfc2047'])
            if (self.changed_by['person'] != self.signer and
                self.changed_by['person'] != self.changes_maintainer['person']
                and self.is_person_in_keyring(self.changed_by['person'])):
                self.recipients.append(self.changed_by['rfc2047'])

        self.recipients = self.policy.filterRecipients(self, self.recipients)

    def do_reject(self, template=rejection_template):
        """Reject the current upload given the reason provided."""
        assert self.rejected

        interpolations = {
            "FROM": self.sender,
            "CHANGES": self.changes_basename,
            "REJECTION": self.rejection_message
            }
        self.build_recipients()
        interpolations['TO'] = ", ".join(self.recipients)

        interpolations = self.policy.filterInterpolations(self,
                                                          interpolations)
        outgoing_msg = template % interpolations
        
        return [outgoing_msg]

    def build_summary(self):
        """List the files and build a summary as needed."""
        summary = []
        for uploaded_file in self.files:
            if uploaded_file.new:
                summary.append("NEW: %s" % uploaded_file.filename)
            else:
                summary.append(" OK: %s" % uploaded_file.filename)
        return "\n".join(summary)
    
    def is_new(self):
        """Return true if any portion of the upload is NEW."""
        for uploaded_file in self.files:
            if uploaded_file.new:
                return True
        return False

    def insert_source_into_db(self):
        """Insert the source into the database and inform the policy."""
        arg_sourcepackagename=self.spn.id
        arg_version=self.changes['version']
        arg_maintainer=self.dsc_maintainer['person'].id
        arg_dateuploaded=UTC_NOW
        arg_builddepends=guess_encoding(
            self.dsc_contents.get('build-depends', ''))
        arg_builddependsindep=guess_encoding(
            self.dsc_contents.get('build-depends-indep', ''))
        arg_architecturehintlist=guess_encoding(
            self.dsc_contents.get('architecture', ''))
        arg_component=self.distrorelease.getComponentByName(
            self._find_dsc().component).id
        arg_creator=self.changed_by['person'].id
        arg_urgency=urgency_map[self.changes['urgency'].lower()]
        arg_changelog=guess_encoding(self.changes['changes'])
        arg_dsc=guess_encoding(self.dsc_contents['filecontents'])
        arg_dscsigningkey=self.dsc_signing_key
        arg_section=self.distrorelease.getSectionByName(
            self._find_dsc().section).id
        arg_manifest=None
        self.policy.sourcepackagerelease = (
            self.distrorelease.createUploadedSourcePackageRelease(
            sourcepackagename=arg_sourcepackagename,
            version=arg_version,
            maintainer=arg_maintainer,
            dateuploaded=arg_dateuploaded,
            builddepends=arg_builddepends,
            builddependsindep=arg_builddependsindep,
            architecturehintlist=arg_architecturehintlist,
            component=arg_component,
            creator=arg_creator,
            urgency=arg_urgency,
            changelog=arg_changelog,
            dsc=arg_dsc,
            dscsigningkey=arg_dscsigningkey,
            section=arg_section,
            manifest=arg_manifest
            ))

        for uploaded_file in self.files:
            if not uploaded_file.is_source:
                continue
            library_file = self.librarian.create(
                uploaded_file.filename,
                uploaded_file.size,
                open(uploaded_file.full_filename, "rb"),
                uploaded_file.content_type)
            
            self.policy.sourcepackagerelease.addFile(library_file)

    def find_build(self, archtag):
        """Find and return a build for the given archtag."""
        if getattr(self.policy, 'build', None) is not None:
            return self.policy.build
        
        build_id = getattr(self.policy.options, 'buildid', None)
        if build_id is None:
            spr = self.policy.sourcepackagerelease
            build = spr.createBuild(self.distrorelease[archtag],
                                    status=BuildStatus.FULLYBUILT)
            self.policy.build = build
        else:
            self.policy.build = getUtility(IBuildSet).getBuildByID(build_id)
        
        return self.policy.build

    def insert_binary_into_db(self):
        """Insert this nascent upload's builds into the database."""
        for uploaded_file in self.files:
            if uploaded_file.is_source or uploaded_file.custom:
                continue
            desclines = uploaded_file.control['Description'].split("\n")
            summary = desclines[0]
            description = "\n".join(desclines[1:])
            format=BinaryPackageFormat.DEB
            if uploaded_file.type == "udeb":
                format=BinaryPackageFormat.UDEB
            build = self.find_build(uploaded_file.architecture)
            # Remember the distrorelease for use in the construction
            dr = self.distrorelease
            # Also remember the control data for the uploaded file
            control = uploaded_file.control
            binary = build.createBinaryPackageRelease(
                binarypackagename=uploaded_file.bpn.id,
                version=uploaded_file.control['Version'],
                summary=guess_encoding(summary),
                description=guess_encoding(description),
                binpackageformat=format,
                component=dr.getComponentByName(uploaded_file.component).id,
                section=dr.getSectionByName(uploaded_file.section).id,
                priority=uploaded_file.priority,
                # XXX: dsilvers: 20051014: erm, need to work this out
                # bug 3160
                shlibdeps='',
                depends=guess_encoding(control.get('Depends', '')),
                recommends=guess_encoding(control.get('Recommends', '')),
                suggests=guess_encoding(control.get('Suggests', '')),
                conflicts=guess_encoding(control.get('Conflicts', '')),
                replaces=guess_encoding(control.get('Replaces', '')),
                provides=guess_encoding(control.get('Provides', '')),
                essential=uploaded_file.control.get('Essential',
                                                    '').lower()=='yes',
                installedsize=int(control.get('Installed-Size','0')),
                # XXX: dsilvers: 20051014: erm, source should have a copyright
                # but not binaries. bug 3161
                copyright='',
                licence='',
                architecturespecific=control.get("Architecture",
                                                 "").lower()!='all'
                ) # the binarypackagerelease constructor
            
            library_file = self.librarian.create(
                uploaded_file.filename,
                uploaded_file.size,
                open(uploaded_file.full_filename, "rb"),
                uploaded_file.content_type)
            binary.addFile(library_file)
            
    def insert_into_queue(self):
        """Insert this nascent upload into the database."""
        if self.sourceful:
            self.insert_source_into_db()
        if self.binaryful:
            self.insert_binary_into_db()

        # Create a Queue item for us to attach our uploads to.
        status = DistroReleaseQueueStatus.ACCEPTED
        if self.is_new():
            status = DistroReleaseQueueStatus.NEW
        self.logger.debug("Creating a %s queue entry" % status.title)
        queue_root = self.distrorelease.createQueueEntry(
            self.policy.pocket, self.changes['filecontents'], status=status)
        # Next, if we're sourceful, add a source to the queue
        if self.sourceful:
            queue_root.addSource(self.policy.sourcepackagerelease)
        # If we're binaryful, add the build
        if self.binaryful:
            queue_root.addBuild(self.policy.build)
        # Finally, add any custom files.
        for uploaded_file in self.files:
            if uploaded_file.custom:
                queue_root.addCustom(
                    self.librarian.create(
                    uploaded_file.filename, uploaded_file.size,
                    open(uploaded_file.full_filename, "rb"),
                    uploaded_file.content_type),
                    uploaded_file.custom_type)
                                     
    def do_accept(self, new_msg=new_template, accept_msg=accepted_template,
                  announce_msg=announce_template):
        """Accept the upload into the queue.

        This *MAY* in extreme cases cause a database error and thus
        actually end up with a rejection being issued. This could
        occur, for example, if we have failed to validate the input
        sufficiently and something trips a database validation
        constraint.
        """
        if self.rejected:
            self.reject("Alas, someone called do_accept when we're rejected")
            return self.do_reject()
        try:
            interpolations = {
                "FROM": self.sender,
                "CHANGES": self.changes_basename,
                "SUMMARY": self.build_summary(),
                "CHANGESFILE": self.changes['filecontents'],
                "DISTRO": self.distro.name,
                "DISTRORELEASE": self.policy.distroreleasename,
                "ANNOUNCE": self.policy.announcelist,
                "SOURCE": self.changes['source'],
                "VERSION": self.changes['version'],
                "ARCH": self.changes['architecture'],
                "MAINTAINERFROM": self.sender
                }
            if self.signer:
                interpolations['MAINTAINERFROM'] = self.changed_by['rfc2047']
            if interpolations['ANNOUNCE'] is None:
                interpolations['ANNOUNCE'] = 'nowhere'
            self.build_recipients()
            interpolations['TO'] = ", ".join(self.recipients)

            interpolations = self.policy.filterInterpolations(
                self, interpolations)
            self.insert_into_queue()

            if self.is_new():
                return True, [new_msg % interpolations]
            else:
                return True, [accept_msg % interpolations,
                              announce_msg % interpolations]

        except Exception, e:
            # Any exception which occurs while processing an accept will
            # cause a rejection to occur. The exception is logged in the
            # reject message rather than being swallowed up.
            self.reject("Exception while accepting: %s" % e)
            return False, self.do_reject()
    
