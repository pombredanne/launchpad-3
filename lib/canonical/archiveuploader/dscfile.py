# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

""" DSCFile and related.

Class representing a DSC file, which encapsulates collections of
files representing a source uploaded.
"""

__metaclass__ = type

__all__ = [
    'SignableTagFile',
    'DSCFile',
    'DSCUploadedFile',
    ]

import apt_pkg
import errno
import glob
import os
import shutil
import subprocess
import tempfile

from zope.component import getUtility

from canonical.archiveuploader.nascentuploadfile import (
    UploadWarning, UploadError, NascentUploadFile, SourceUploadFile)
from canonical.archiveuploader.tagfiles import (
    parse_tagfile, TagFileParseError)
from canonical.archiveuploader.utils import (
    prefix_multi_line_string, safe_fix_maintainer, ParseMaintError,
    re_valid_pkg_name, re_valid_version, re_issource)
from canonical.encoding import guess as guess_encoding
from canonical.launchpad.interfaces import (
    ArchivePurpose, GPGVerificationError, IGPGHandler, IGPGKeySet,
    IPersonSet, ISourcePackageNameSet, NotFoundError,
    PersonCreationRationale)
from canonical.librarian.utils import copy_and_close


class SignableTagFile:
    """Base class for signed file verification."""

    fingerprint = None
    signingkey = None
    signer = None

    def processSignature(self):
        """Verify the signature on the filename.

        Stores the fingerprint, the IGPGKey used to sign, the owner of
        the key and a dictionary containing

        Raise UploadError if the signing key cannot be found in launchpad
        or if the GPG verification failed for any other reason.

        Returns the key owner (person object), the key (gpgkey object) and
        the pyme signature as a three-tuple
        """
        self.logger.debug("Verifying signature on %s" % self.filename)
        assert os.path.exists(self.filepath), (
            "File not found: %s" % self.filepath)

        try:
            sig = getUtility(IGPGHandler).getVerifiedSignatureResilient(
                file(self.filepath, "rb").read())
        except GPGVerificationError, error:
            raise UploadError(
                "GPG verification of %s failed: %s" % (
                self.filename, str(error)))

        key = getUtility(IGPGKeySet).getByFingerprint(sig.fingerprint)
        if key is None:
            raise UploadError("Signing key %s not registered in launchpad."
                              % sig.fingerprint)

        if key.active == False:
            raise UploadError("File %s is signed with a deactivated key %s"
                              % (self.filename, key.keyid))

        self.fingerprint = sig.fingerprint
        self.signingkey = key
        self.signer = key.owner
        self.signer_address = self.parseAddress("%s <%s>" % (
            self.signer.displayname, self.signer.preferredemail.email))

    def parseAddress(self, addr, fieldname="Maintainer"):
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
            (rfc822, rfc2047, name, email) = safe_fix_maintainer(
                addr, fieldname)
        except ParseMaintError, error:
            raise UploadError(str(error))

        person = getUtility(IPersonSet).getByEmail(email)
        if person is None and self.policy.create_people:
            package = self._dict['source']
            version = self._dict['version']
            if self.policy.distroseries and self.policy.pocket:
                policy_suite = ('%s/%s' % (self.policy.distroseries.name,
                                           self.policy.pocket.name))
            else:
                policy_suite = '(unknown)'
            person = getUtility(IPersonSet).ensurePerson(
                email, name, PersonCreationRationale.SOURCEPACKAGEUPLOAD,
                comment=('when the %s_%s package was uploaded to %s'
                         % (package, version, policy_suite)))

        if person is None:
            raise UploadError("Unable to identify '%s':<%s> in launchpad"
                              % (name, email))

        return {
            "rfc822": rfc822,
            "rfc2047": rfc2047,
            "name": name,
            "email": email,
            "person": person
            }


class DSCFile(SourceUploadFile, SignableTagFile):
    """Models a given DSC file and its content."""

    mandatory_fields = set([
        "source",
        "version",
        "binary",
        "maintainer",
        "architecture",
        "files"])

    # Note that files is actually only set inside verify().
    files = None
    # Copyrigth is only set inside unpackAndCheckSource().
    copyright = None

    def __init__(self, filepath, digest, size, component_and_section,
                 priority, package, version, changes, policy, logger):
        """Construct a DSCFile instance.

        This takes all NascentUploadFile constructor parameters plus package
        and version.

        Can raise UploadError.
        """
        SourceUploadFile.__init__(
            self, filepath, digest, size, component_and_section, priority,
            package, version, changes, policy, logger)
        try:
            self._dict = parse_tagfile(
                self.filepath, dsc_whitespace_rules=1,
                allow_unsigned=self.policy.unsigned_dsc_ok)
        except (IOError, TagFileParseError), error:
            raise UploadError(
                "Unable to parse the dsc %s: %s" % (self.filename, error))

        self.logger.debug("Performing DSC verification.")
        for mandatory_field in self.mandatory_fields:
            if mandatory_field not in self._dict:
                raise UploadError(
                    "Unable to find mandatory field %s in %s" % (
                    mandatory_field, self.filename))

        self.maintainer = self.parseAddress(self._dict['maintainer'])

        # If format is not present, assume 1.0. At least one tool in
        # the wild generates dsc files with format missing, and we need
        # to accept them.
        if 'format' not in self._dict:
            self._dict['format'] = "1.0"

        if self.policy.unsigned_dsc_ok:
            self.logger.debug("DSC file can be unsigned.")
        else:
            self.processSignature()

    #
    # Useful properties.
    #

    @property
    def source(self):
        """Return the DSC source name."""
        return self._dict['source']

    @property
    def dsc_version(self):
        """Return the DSC source version."""
        return self._dict['version']

    @property
    def format(self):
        """Return the DSC format."""
        return self._dict['format']

    @property
    def architecture(self):
        """Return the DSC source architecture."""
        return self._dict['architecture']

    @property
    def binary(self):
        """Return the DSC claimed binary line."""
        return self._dict['binary']


    #
    # DSC file checks.
    #

    def verify(self):
        """Verify the uploaded .dsc file.

        This method is an error generator, i.e, it returns an iterator over all
        exceptions that are generated while processing DSC file checks.
        """
        for error in SourceUploadFile.verify(self):
            yield error

        # Check size and checksum of the DSC file itself
        try:
            self.checkSizeAndCheckSum()
        except UploadError, error:
            yield error

        files = []
        for fileline in self._dict['files'].strip().split("\n"):
            # DSC lines are always of the form: CHECKSUM SIZE FILENAME
            digest, size, filename = fileline.strip().split()
            if not re_issource.match(filename):
                # DSC files only really hold on references to source
                # files; they are essentially a description of a source
                # package. Anything else is crack.
                yield UploadError("%s: File %s does not look sourceful." % (
                                  self.filename, filename))
                continue
            filepath = os.path.join(self.dirname, filename)
            try:
                file_instance = DSCUploadedFile(
                    filepath, digest, size, self.policy, self.logger)
            except UploadError, error:
                yield error
            else:
                files.append(file_instance)
        self.files = files

        if not re_valid_pkg_name.match(self.source):
            yield UploadError(
                "%s: invalid source name %s" % (self.filename, self.source))
        if not re_valid_version.match(self.dsc_version):
            yield UploadError(
                "%s: invalid version %s" % (self.filename, self.dsc_version))

        if self.format != "1.0":
            yield UploadError(
                "%s: Format is not 1.0. This is incompatible with "
                "dpkg-source." % self.filename)

        # Validate the build dependencies
        for field_name in ['build-depends', 'build-depends-indep']:
            field = self._dict.get(field_name, None)
            if field is not None:
                if field.startswith("ARRAY"):
                    yield UploadError(
                        "%s: invalid %s field produced by a broken version "
                        "of dpkg-dev (1.10.11)" % (self.filename, field_name))
                try:
                    apt_pkg.ParseSrcDepends(field)
                except (SystemExit, KeyboardInterrupt):
                    raise
                except Exception, error:
                    # Swallow everything apt_pkg throws at us because
                    # it is not desperately pythonic and can raise odd
                    # or confusing exceptions at times and is out of
                    # our control.
                    yield UploadError(
                        "%s: invalid %s field; cannot be parsed by apt: %s"
                        % (self.filename, field_name, error))

        # Verify if version declared in changesfile is the same than that
        # in DSC (including epochs).
        if self.dsc_version != self.version:
            yield UploadError(
                "%s: version ('%s') in .dsc does not match version "
                "('%s') in .changes."
                % (self.filename, self.dsc_version, self.version))

        for error in self.checkFiles():
            yield error

    def _getFileByName(self, filename):
        """Return the corresponding library file in the policy context.

        If the filename ends in '.orig.tar.gz', then we look for it in the
        distribution primary archive as well, with the PPA file taking
        precedence in case it's found in both archives.

        This is needed so that PPA uploaders don't have to waste bandwidth
        uploading huge upstream tarballs that are already published in the
        target distribution.

        Raises NotFoundError if the wanted file could not be found.
        """
        if (self.policy.archive.purpose == ArchivePurpose.PPA and
            filename.endswith('.orig.tar.gz')):
            archives = [self.policy.archive, self.policy.distro.main_archive]
        else:
            archives = [self.policy.archive]

        library_file = None
        for archive in archives:
            try:
                library_file = self.policy.distro.getFileByName(
                    filename, source=True, binary=False, archive=archive)
                self.logger.debug(
                    "%s found in %s" % (filename, archive.title))
                return library_file
            except NotFoundError:
                pass

        raise NotFoundError(filename)

    def checkFiles(self):
        """Check if mentioned files are present and match.

        We don't use the NascentUploadFile.verify here, only verify size
        and checksum.
        """
        has_tar = False
        files_missing = False
        for sub_dsc_file in self.files:
            if sub_dsc_file.filename.endswith("tar.gz"):
                has_tar = True

            try:
                library_file = self._getFileByName(sub_dsc_file.filename)
            except NotFoundError, error:
                library_file = None
            else:
                # try to check dsc-mentioned file against its copy already
                # in librarian, if it's new (aka not found in librarian)
                # dismiss. It prevent us to have scary duplicated filenames
                # in Librarian and missapplied files in archive, fixes
                # bug # 38636 and friends.
                if sub_dsc_file.digest != library_file.content.md5:
                    yield UploadError(
                        "MD5 sum of uploaded file does not match existing "
                        "file in archive")
                    files_missing = True
                    continue

            if not sub_dsc_file.exists_on_disk:
                if library_file is None:
                    # Raises an error if the mentioned DSC file isn't
                    # included in the upload neither published in the
                    # context Distribution.
                    yield UploadError(
                        "Unable to find %s in upload or distribution."
                        % (sub_dsc_file.filename))
                    files_missing = True
                    continue

                # Pump the file through.
                self.logger.debug("Pumping %s out of the librarian" % (
                    sub_dsc_file.filename))
                library_file.open()
                target_file = open(sub_dsc_file.filepath, "wb")
                copy_and_close(library_file, target_file)

            for error in sub_dsc_file.verify():
                yield error
                files_missing = True


        if not has_tar:
            yield UploadError(
                "%s: does not mention any tar.gz or orig.tar.gz."
                % self.filename)

        if files_missing:
            yield UploadError(
                "Files specified in DSC are broken or missing, "
                "skipping package unpack verification.")
        else:
            for error in self.unpackAndCheckSource():
                # Pass on errors found when unpacking the source.
                yield error

    def unpackAndCheckSource(self):
        """Verify uploaded source using dpkg-source."""
        self.logger.debug(
            "Verifying uploaded source package by unpacking it.")

        # Get a temporary dir together.
        tmpdir = tempfile.mkdtemp(dir=self.dirname)

        # chdir into it
        cwd = os.getcwd()
        os.chdir(tmpdir)
        dsc_in_tmpdir = os.path.join(tmpdir, self.filename)

        package_files = self.files + [self]
        try:
            for source_file in package_files:
                os.symlink(source_file.filepath,
                           os.path.join(tmpdir, source_file.filename))
            args = ["dpkg-source", "-sn", "-x", dsc_in_tmpdir]
            dpkg_source = subprocess.Popen(args, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)
            output, unused = dpkg_source.communicate()
            result = dpkg_source.wait()
        finally:
            # When all is said and done, chdir out again so that we can
            # clean up the tree with shutil.rmtree without leaving the
            # process in a directory we're trying to remove.
            os.chdir(cwd)

        if result != 0:
            dpkg_output = prefix_multi_line_string(output, "  ")
            yield UploadError(
                "dpkg-source failed for %s [return: %s]\n"
                "[dpkg-source output: %s]"
                % (self.filename, result, dpkg_output))

        # Copy debian/copyright file content. It will be stored in the
        # SourcePackageRelease records.

        # Check if 'dpkg-source' created only one directory.
        temp_directories = [dirname for dirname in os.listdir(tmpdir)
                            if os.path.isdir(dirname)]
        if len(temp_directories) > 1:
            yield UploadError(
                'Unpacked source contains more than one directory: %r'
                % temp_directories)

        # XXX cprov 20070713: We should access only the expected directory
        # name (<sourcename>-<no_epoch(no_revision(version))>).

        # Instead of trying to predict the unpacked source directory name,
        # we simply use glob to retrive everything like:
        # 'tempdir/*/debian/copyright'
        globpath = os.path.join(tmpdir, "*", "debian/copyright")
        for fullpath in glob.glob(globpath):
            if not os.path.exists(fullpath):
                continue
            self.logger.debug("Copying copyright contents.")
            self.copyright = open(fullpath).read().strip()

        if self.copyright is None:
            yield UploadWarning("No copyright file found.")

        self.logger.debug("Cleaning up source tree.")
        try:
            shutil.rmtree(tmpdir)
        except OSError, error:
            # XXX: dsilvers 2006-03-15: We currently lack a test for this.
            if errno.errorcode[error.errno] != 'EACCES':
                yield UploadError(
                    "%s: couldn't remove tmp dir %s: code %s" % (
                    self.filename, tmpdir, error.errno))
            else:
                yield UploadWarning(
                    "%s: Couldn't remove tree, fixing up permissions." %
                    self.filename)
                result = os.system("chmod -R u+rwx " + tmpdir)
                if result != 0:
                    yield UploadError("chmod failed with %s" % result)
                shutil.rmtree(tmpdir)

        self.logger.debug("Done")

    def storeInDatabase(self):
        """Store DSC information as a SourcePackageRelease record.

        It reencodes all fields extracted from DSC, the simulated_changelog
        and the copyright, because old packages contain latin-1 text and
        that sucks.
        """
        # Organize all the parameters requiring encoding transformation.
        pending = self._dict.copy()
        pending['simulated_changelog'] = self.changes.simulated_changelog
        pending['copyright'] = self.copyright

        # We have no way of knowing what encoding the original copyright
        # file is in, unfortunately, and there is no standard, so guess.
        encoded = {}
        for key, value in pending.items():
            if value is not None:
                encoded[key] = guess_encoding(value)
            else:
                encoded[key] = None

        source_name = getUtility(
            ISourcePackageNameSet).getOrCreateByName(self.source)

        release = self.policy.distroseries.createUploadedSourcePackageRelease(
            sourcepackagename=source_name,
            version=self.dsc_version,
            maintainer=self.maintainer['person'],
            builddepends=encoded.get('build-depends', ''),
            builddependsindep=encoded.get('build-depends-indep', ''),
            build_conflicts=encoded.get('build-conflicts', ''),
            build_conflicts_indep=encoded.get('build-conflicts-indep', ''),
            architecturehintlist=encoded.get('architecture', ''),
            creator=self.changes.changed_by['person'],
            urgency=self.changes.converted_urgency,
            dsc=encoded['filecontents'],
            dscsigningkey=self.signingkey,
            dsc_maintainer_rfc822=encoded['maintainer'],
            dsc_format=encoded['format'],
            dsc_binaries=encoded['binary'],
            dsc_standards_version=encoded.get('standards-version'),
            component=self.component,
            changelog_entry=encoded.get('simulated_changelog'),
            section=self.section,
            archive=self.policy.archive,
            copyright=encoded.get('copyright'),
            # dateuploaded by default is UTC:now in the database
            )

        # SourcePackageFiles should contain also the DSC
        source_files = self.files + [self]
        for uploaded_file in source_files:
            library_file = self.librarian.create(
                uploaded_file.filename,
                uploaded_file.size,
                open(uploaded_file.filepath, "rb"),
                uploaded_file.content_type,
                restricted=self.policy.archive.private)
            release.addFile(library_file)

        return release


class DSCUploadedFile(NascentUploadFile):
    """Represents a file referred to in a DSC.

    The DSC holds references to files, and it's easier to use regular
    NascentUploadFiles to represent them, since they are in many ways
    similar to a regular NU. However, there are the following warts:
        - Component, section and priority are set to a bogus value and
          do not apply.
        - The actual file instance isn't used for anything but
          validation inside DSCFile.verify(); there is no
          store_in_database() method.
    """
    def __init__(self, filepath, digest, size, policy, logger):
        component_and_section = priority = "--no-value--"
        NascentUploadFile.__init__(
            self, filepath, digest, size, component_and_section,
            priority, policy, logger)

    def verify(self):
        """Check Sub DSCFile mentioned size & checksum."""
        try:
            self.checkSizeAndCheckSum()
        except UploadError, error:
            yield error


