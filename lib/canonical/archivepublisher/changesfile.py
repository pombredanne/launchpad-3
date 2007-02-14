
import re
import os
import errno
import shutil
import apt_pkg
import subprocess
import tempfile

from zope.component import getUtility

from canonical.encoding import guess as guess_encoding

from canonical.lp.dbschema import (
    SourcePackageUrgency, PersonCreationRationale)

from canonical.librarian.utils import copy_and_close

from canonical.launchpad.interfaces import (
    NotFoundError, IGPGHandler, GPGVerificationError, IGPGKeySet,
    IPersonSet, ISourcePackageNameSet, IComponentSet, ISectionSet)

from canonical.archivepublisher.tagfiles import (
    parse_tagfile, TagFileParseError)
from canonical.archivepublisher.nascentuploadfile import (
    UploadError, UploadWarning, CustomUploadedFile, DSCUploadedFile,
    BinaryNascentUploadedFile, SourceNascentUploadFile,
    NascentUploadedFile, re_isadeb, re_no_epoch,
    re_valid_pkg_name, re_valid_version)
from canonical.archivepublisher.utils import (
    prefix_multi_line_string, safe_fix_maintainer, ParseMaintError)


changes_mandatory_fields = set([
    "source", "binary", "architecture", "version", "distribution",
    "maintainer", "files", "changes"
    ])

dsc_mandatory_fields = set([
    "source", "version", "binary", "maintainer", "architecture",
    "files"
    ])

# Map urgencies to their dbschema values.
# Debian policy only permits low,medium,high,emergency
# Britney also uses critical which it maps to emergency
urgency_map = {
    "low": SourcePackageUrgency.LOW,
    "medium": SourcePackageUrgency.MEDIUM,
    "high": SourcePackageUrgency.HIGH,
    "critical": SourcePackageUrgency.EMERGENCY,
    "emergency": SourcePackageUrgency.EMERGENCY
    }

re_no_revision = re.compile(r"-[^-]+$")
re_strip_revision = re.compile(r"-([^-]+)$")
re_changes_file_name = re.compile(r"([^_]+)_([^_]+)_([^\.]+).changes")
re_issource = re.compile(r"(.+)_(.+?)\.(orig\.tar\.gz|diff\.gz|tar\.gz|dsc)$")


class SignableTagFile:
    fingerprint = None
    signingkey = None
    signer = None
    def process_signature(self):
        """Verify the signature on the filename.

        Stores the fingerprint, the IGPGKey used to sign, the owner of
        the key and a dictionary containing 

        Raise UploadError if the signing key cannot be found in launchpad
        or if the GPG verification failed for any other reason.

        Returns the key owner (person object), the key (gpgkey object) and
        the pyme signature as a three-tuple
        """
        filename = self.filename
        full_path = os.path.join(self.fsroot, filename)
        self.logger.debug("Verifying signature on %s" % full_path)
        assert os.path.exists(full_path)

        try:
            sig = getUtility(IGPGHandler).getVerifiedSignatureResilient(
                file(full_path, "rb").read())
        except GPGVerificationError, e:
            raise UploadError(
                "GPG verification of %s failed: %s" % (filename, str(e)))

        key = getUtility(IGPGKeySet).getByFingerprint(sig.fingerprint)
        if key is None:
            raise UploadError("Signing key %s not registered in launchpad."
                              % sig.fingerprint)

        if key.active == False:
            raise UploadError("File %s is signed with a deactivated key %s"
                              % (filename, key.keyid))

        self.fingerprint = sig.fingerprint
        self.signingkey = key
        self.signer = key.owner
        self.signer_address = self.parse_address("%s <%s>" % (
            self.signer.displayname, self.signer.preferredemail.email))

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
            (rfc822, rfc2047, name, email) = safe_fix_maintainer(addr, fieldname)
        except ParseMaintError, e:
            raise UploadError(str(e))

        if self.policy.create_people:
            package = self._dict['source']
            # XXX: The distrorelease property may raise an UploadError
            # in case there's no distrorelease with a name equal to
            # distrorelease_and_pocket() or even a raw Exception in some
            # tests, but we don't want the upload to fail at this point
            # nor catch the exception here, so we'll hardcode the distro
            # here for now and leave the rationale without a specific
            # release.
            # -- Guilherme Salgado, 2006-10-03
            release = 'Ubuntu'
            person = getUtility(IPersonSet).ensurePerson(
                email, name, PersonCreationRationale.SOURCEPACKAGEUPLOAD,
                comment=('when the %s package was uploaded to %s'
                         % (package, release)))
        else:
            person = getUtility(IPersonSet).getByEmail(email)

        if person is None:
            raise UploadError("Unable to identify '%s':<%s> in launchpad" % (
                name, email))

        return {
            "rfc822": rfc822,
            "rfc2047": rfc2047,
            "name": name,
            "email": email,
            "person": person
            }


class ChangesFile(SignableTagFile):
    """XXX"""
    dsc = None
    maintainer = None
    changed_by = None
    filename_archtag = None
    files = None
    def __init__(self, filename, fsroot, policy, logger):
        """XXX

        Does:
            * Verification of required fields
            * Verification of the required Format
            * Parses maintainer and changed-by
            * Checks name of changes file
            * Checks signature of changes file
        If any of these checks fail, UploadError is raised, and it's
        considered a fatal error (no subsequent processing of the upload
        will be done).
        """
        self.logger = logger
        self.filename = filename
        self.fsroot = fsroot
        self.policy = policy

        try:
            self._dict = parse_tagfile(os.path.join(self.fsroot, filename),
                allow_unsigned=policy.unsigned_changes_ok)
        except TagFileParseError, e:
            raise UploadError("Unable to parse the changes %s: %s" % (
                filename, e))

        for field in changes_mandatory_fields:
            if field not in self._dict:
                raise UploadError(
                    "Unable to find mandatory field '%s' in the changes "
                    "file." % field)

        try:
            format = float(self._dict["format"])
        except KeyError:
            # If format is missing, pretend it's 1.5
            format = 1.5

        if format < 1.5 or format > 2.0:
            raise UploadError(
                "Format out of acceptable range for changes file. Range "
                "1.5 - 2.0, format %g" % format)

        self.maintainer = self.parse_address(self._dict['maintainer'])
        self.changed_by = self.parse_address(self._dict['changed-by'])

        m = re_changes_file_name.match(filename)
        if m is None:
            raise UploadError(
                '%s -> inappropriate changesfile name, '
                'should follow "<pkg>_<version>_<arch>.changes" format'
                % filename)
        self.filename_archtag = m.group(3)

        if policy.unsigned_changes_ok:
            self.logger.debug("Changes file can be unsigned.")
        else:
            self.process_signature()

    def process_files(self):
        files = []
        for fileline in self._dict['files'].strip().split("\n"):
            # files lines from a changes file are always of the form:
            # CHECKSUM SIZE [COMPONENT/]SECTION PRIORITY FILENAME
            digest, size, component_and_section, priority, filename = fileline.strip().split()
            source_match = re_issource.match(filename)
            binary_match = re_isadeb.match(filename)
            try:
                if priority == '-':
                    # This needs to be the first check, because
                    # otherwise the tarballs in custom uploads match
                    # with source_match.
                    file_instance = CustomUploadedFile(
                        filename, digest, size, component_and_section,
                        priority, self.fsroot, self.policy, self.logger)
                elif source_match:
                    package = source_match.group(1)
                    version = source_match.group(2)
                    type = source_match.group(3)
                    if filename.endswith(".dsc"):
                        file_instance = DSCFile(
                            filename, digest, size,
                            component_and_section, priority, package,
                            version, type, self.fsroot, self.policy,
                            self.logger)
                        # Store the DSC because it is very convenient
                        self.dsc = file_instance
                    else:
                        file_instance = SourceNascentUploadFile(
                            filename, digest, size,
                            component_and_section, priority, package,
                            version, type, self, self.fsroot,
                            self.policy, self.logger)
                elif binary_match:
                    type = source_match.group(4)
                    file_instance = BinaryNascentUploadedFile(
                        filename, digest, size, component_and_section,
                        priority, type, self, self.fsroot, self.policy,
                        self.logger)
                else:
                    # XXX: byhand will fall into this category now. is
                    # that right?
                    yield UploadError("Unable to identify file %s (%s) "
                                      "in changes." % (filename, component_and_section))
                    continue
            except UploadError, e:
                yield e
            else:
                files.append(file_instance)

        self.files = files

    def verify(self):
        """Run all the verification checks on the changes data.

        # XXX: talk about yields
        """

        self.logger.debug("Verifying the changes file.")

        if len(self.files) == 0:
            yield UploadError("No files found in the changes")

        raw_urgency = self._dict['urgency'].lower()
        if not urgency_map.has_key(raw_urgency):
            yield UploadWarning("Unable to grok urgency %s, overriding with 'low'"
                                % ( raw_urgency))
            self._dict['urgency'] = "low"

        if not self.policy.unsigned_changes_ok:
            assert self.signer is not None
            # XXX: will this raise exceptions?
            self.policy.considerSigner(self.signer, self.signingkey)
    #
    #
    #

    @property
    def distrorelease_and_pocket(self):
        """Returns a string like hoary or hoary-security"""
        return self._dict['distribution']

    @property
    def architectures(self):
        """XXX"""
        return set(self._dict['architecture'].split())

    @property
    def binaries(self):
        """Extract the list of binary package names XXX and return them as a set."""
        return set(self._dict['binary'].strip().split())

    @property
    def urgency(self):
        """Return the appropriate SourcePackageUrgency item."""
        return urgency_map[self._dict['urgency'].lower()]

    @property
    def version(self):
        return self._dict['version']

    @property
    def changes_text(self):
        return self._dict['changes']

    @property
    def simulated_changelog(self):
        # rebuild the changes author line as specified in bug # 30621,
        # new line containing:
        # ' -- <CHANGED-BY>  <DATE>'
        changes_author = (
            '\n -- %s   %s' %
            (self.changed_by['rfc822'], self.date))
        return self.changes_text + changes_author

    @property
    def date(self):
        return self._dict['date']

    @property
    def source(self):
        return self._dict['source']

    @property
    def architecture_line(self):
        return self._dict['architecture']

    @property
    def filecontents(self):
        return self._dict['filecontents']

    @property
    def chopversion(self):
        return re_no_epoch.sub('', self._dict["version"])

    @property
    def chopversion2(self):
        return re_no_revision.sub('', self.chopversion)



class DSCFile(NascentUploadedFile, SignableTagFile):
    """XXX"""
    fingerprint = None
    signingkey = None

    maintainer = None

    # Note that files is actually only set inside verify().
    files = None
    def __init__(self, filename, digest, size, component_and_section,
                 priority, package, version, type, fsroot, policy,
                 logger):
        """XXX

        Can raise UploadError.
        """
        NascentUploadedFile.__init__(
            self, filename, digest, size, component_and_section,
            priority, fsroot, policy, logger)

        self.package = package
        self.version = version
        self.type = type

        try:
            self._dict = parse_tagfile(self.full_filename,
                dsc_whitespace_rules=1,
                allow_unsigned=policy.unsigned_dsc_ok)
        except TagFileParseError, e:
            raise UploadError("Unable to parse the dsc %s: %s" % (filename, e))

        self.logger.debug("Performing DSC verification.")
        for mandatory_field in dsc_mandatory_fields:
            if mandatory_field not in self._dict:
                self.reject("Unable to find mandatory field %s in %s" % (
                    mandatory_field, filename))
                return False

        self.maintainer = self.parse_address(self._dict['maintainer'])

        # If format is not present, assume 1.0. At least one tool in
        # the wild generates dsc files with format missing, and we need
        # to accept them.
        if 'format' not in self._dict:
            self._dict['format'] = "1.0"

        if self.policy.unsigned_dsc_ok:
            self.logger.debug("DSC file can be unsigned.")
        else:
            self.process_signature()

    #
    #
    #

    @property
    def source(self):
        return self._dict['source']

    #
    #
    #

    def verify(self):
        """Verify the uploaded .dsc file.

        Should raise no exceptions unless unforseen issues occur. Errors will
        be accumulated in the rejection message.
        """
        files = []
        for fileline in self._dict['files'].strip().split("\n"):
            # DSC lines are always of the form: CHECKSUM SIZE FILENAME
            digest, size, filename = fileline.strip().split()
            if not re_issource.match(filename):
                yield UploadError("%s: File %s does not look sourceful." % (
                                  self.filename, filename))
            else:
                component_and_section = priority = "-"
                try:
                    file_instance = DSCUploadedFile(
                        filename, digest, size, component_and_section, priority,
                        self.fsroot, self.policy, self.logger)
                except UploadError, e:
                    yield e
                else:
                    files.append(file_instance)
        self.files = files

        source = self._dict['source']
        version = self._dict['version']
        if not re_valid_pkg_name.match(source):
            yield UploadError("%s: invalid source name %s" % (self.filename, source))
        if not re_valid_version.match(version):
            yield UploadError("%s: invalid version %s" % (self.filename, version))

        if self._dict['format'] != "1.0":
            yield UploadError("%s: Format is not 1.0. This is incompatible with "
                              "dpkg-source." % self.filename)

        # Validate the build dependencies
        for field_name in ['build-depends', 'build-depends-indep']:
            field = self._dict.get(field_name, None)
            if field is not None:
                if field.startswith("ARRAY"):
                    yield UploadError(
                        "%s: invalid %s field produced by a broken version of "
                        "dpkg-dev (1.10.11)" % (self.filename, field_name))
                try:
                    apt_pkg.ParseSrcDepends(field)
                except Exception, e:
                    # Swallow everything apt_pkg throws at us because
                    # it is not desperately pythonic and can raise odd
                    # or confusing exceptions at times and is out of
                    # our control.
                    yield UploadError(
                        "%s: invalid %s field; cannot be parsed by apt: %s" 
                        % (self.filename, field_name, e))

        # Verify the filename matches appropriately
        epochless_dsc_version = re_no_epoch.sub('', self._dict["version"])
        if epochless_dsc_version != self.version:
            yield UploadError("%s: version ('%s') in .dsc does not match version "
                             "('%s') in .changes." % (self.filename, 
                                epochless_dsc_version, self.version))

        for error in self.check_files():
            yield error

    def check_files(self):
        has_tar = False
        files_missing = False
        for sub_dsc_file in self.files:
            if sub_dsc_file.filename.endswith("tar.gz"):
                has_tar = True

            try:
                library_file = self.policy.distro.getFileByName(
                    sub_dsc_file.filename, source=True, binary=False)
            except NotFoundError, e:
                library_file = None
            else:
                # try to check dsc-mentioned file against its copy already
                # in librarian, if it's new (aka not found in librarian)
                # dismiss. It prevent us to have scary duplicated filenames
                # in Librarian and missapplied files in archive, fixes
                # bug # 38636 and friends.
                if sub_dsc_file.sha_digest != library_file.content.sha1:
                    yield UploadError("SHA1 sum of uploaded file does not "
                                      "match existent file in archive")
                    files_missing = True
                    continue

            if not sub_dsc_file.exists_on_disk:
                if library_file is None:
                    # XXX: explain
                    yield UploadError("Unable to find %s in upload or distribution."
                                      % (sub_dsc_file.filename))
                    files_missing = True
                    continue

                # Pump the file through.
                self.logger.debug("Pumping %s out of the librarian" % (
                    sub_dsc_file.filename))
                library_file.open()
                target_file = open(sub_dsc_file.full_filename, "wb")
                copy_and_close(library_file, target_file)

            try:
                sub_dsc_file.checkSizeAndCheckSum()
            except UploadError, e:
                yield e
                files_missing = True
                continue


            # XXX: we don't call verify on the sub_dsc_file. I'm not
            # sure that's a good or a bad thing, but it's the truth.

        if not has_tar:
            yield UploadError(
                "%s: does not mention any tar.gz or orig.tar.gz." % self.filename)

        if files_missing:
            yield UploadError(
                "Files specified in DSC are broken or missing, "
                "skipping package unpack verification.")
        else:
            for error in self.unpack_and_check_source():
                # Flatten out exceptions raised while checking source
                yield error

    def unpack_and_check_source(self):
        self.logger.debug("Verifying uploaded source package by unpacking it.")

        # Get a temporary dir together.
        tmpdir = tempfile.mkdtemp(dir=self.fsroot)

        # chdir into it
        cwd = os.getcwd()
        os.chdir(tmpdir)
        dsc_in_tmpdir = os.path.join(tmpdir, self.filename)

        files = self.files + [self]
        try:
            for source_file in files:
                os.symlink(source_file.full_filename,
                           os.path.join(tmpdir, source_file.filename))
            args = ["dpkg-source", "-sn", "-x", dsc_in_tmpdir]
            dpkg_source = subprocess.Popen(args, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)
            output, garbage = dpkg_source.communicate()
            result = dpkg_source.wait()
        finally:
            # When all is said and done, chdir out again so that we can
            # clean up the tree with shutil.rmtree without leaving the
            # process in a directory we're trying to remove.
            os.chdir(cwd)

        if result != 0:
            yield UploadError("dpkg-source failed for %s [return: %s]" % (
                              self.filename, result))
            yield UploadError(prefix_multi_line_string(output,
                              " [dpkg-source output:] "))

        self.logger.debug("Cleaning up source tree.")
        try:
            shutil.rmtree(tmpdir)
        except OSError, e:
            # XXX: dsilvers: 20060315: We currently lack a test for this.
            if errno.errorcode[e.errno] != 'EACCES':
                yield UploadError("%s: couldn't remove tmp dir %s: code %s" % (
                                  self.filename, tmpdir, e.errno))
            else:
                yield UploadWarning("%s: Couldn't remove tree, fixing up permissions." % 
                                    self.filename)
                result = os.system("chmod -R u+rwx " + tmpdir)
                if result != 0:
                    yield UploadError("chmod failed with %s" % result)
                shutil.rmtree(tmpdir)

        self.logger.debug("Done")

    def create_source_package_release(self, changes):
        spns = getUtility(ISourcePackageNameSet)
        arg_component = getUtility(IComponentSet)[self.component]
        arg_section = getUtility(ISectionSet)[self.section]

        # Reencode everything we are supplying, because old packages
        # contain latin-1 text and that sucks.
        encoded = {}
        for k, v in self._dict.items():
            encoded[k] = guess_encoding(v)

        release = self.policy.distrorelease.createUploadedSourcePackageRelease(
            sourcepackagename=spns.getOrCreateByName(self.source),
            version=changes.version,
            maintainer=self.maintainer['person'],
            builddepends=encoded.get('build-depends', ''),
            builddependsindep=encoded.get('build-depends-indep', ''),
            architecturehintlist=encoded.get('architecture', ''),
            creator=changes.changed_by['person'],
            urgency=changes.urgency,
            dsc=encoded['filecontents'],
            dscsigningkey=self.signingkey,
            manifest=None,
            dsc_maintainer_rfc822=encoded['maintainer'],
            dsc_format=encoded['format'],
            dsc_binaries=encoded['binary'],
            dsc_standards_version=encoded.get('standards-version', None),
            component=arg_component,
            changelog=guess_encoding(changes.simulated_changelog),
            section=arg_section,
            # dateuploaded by default is UTC:now in the database
            )



