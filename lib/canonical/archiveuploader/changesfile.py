# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

""" ChangesFile class

Classes representing Changes and DSC files, which encapsulate collections of
files uploaded.
"""

__metaclass__ = type

__all__ = [
    'ChangesFile'
    ]

import os
import re

from canonical.archiveuploader.dscfile import DSCFile, SignableTagFile
from canonical.archiveuploader.nascentuploadfile import (
    UploadError, UploadWarning, CustomUploadFile, DebBinaryUploadFile,
    UdebBinaryUploadFile, BaseBinaryUploadFile, SourceUploadFile,
    splitComponentAndSection)
from canonical.archiveuploader.utils import (
    re_isadeb, re_issource, re_changes_file_name)
from canonical.archiveuploader.tagfiles import (
    parse_tagfile, TagFileParseError)
from canonical.launchpad.interfaces import SourcePackageUrgency


class ChangesFile(SignableTagFile):
    """Changesfile model."""

    mandatory_fields = set([
        "source", "binary", "architecture", "version", "distribution",
        "maintainer", "files", "changes"])

    # Map urgencies to their dbschema values.
    # Debian policy only permits low, medium, high, emergency.
    # Britney also uses critical which it maps to emergency.
    urgency_map = {
        "low": SourcePackageUrgency.LOW,
        "medium": SourcePackageUrgency.MEDIUM,
        "high": SourcePackageUrgency.HIGH,
        "critical": SourcePackageUrgency.EMERGENCY,
        "emergency": SourcePackageUrgency.EMERGENCY
        }

    dsc = None
    maintainer = None
    changed_by = None
    filename_archtag = None
    files = None

    def __init__(self, filepath, policy, logger):
        """Process the given changesfile.

        Does:
            * Verification of required fields
            * Verification of the required Format
            * Parses maintainer and changed-by
            * Checks name of changes file
            * Checks signature of changes file

        If any of these checks fail, UploadError is raised, and it's
        considered a fatal error (no subsequent processing of the upload
        will be done).

        Logger and Policy are instances built in uploadprocessor.py passed
        via NascentUpload class.
        """
        self.filepath = filepath
        self.policy = policy
        self.logger = logger

        try:
            self._dict = parse_tagfile(
                self.filepath, allow_unsigned=self.policy.unsigned_changes_ok)
        except (IOError, TagFileParseError), error:
            raise UploadError("Unable to parse the changes %s: %s" % (
                self.filename, error))

        for field in self.mandatory_fields:
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

        match_changes = re_changes_file_name.match(self.filename)
        if match_changes is None:
            raise UploadError(
                '%s -> inappropriate changesfile name, '
                'should follow "<pkg>_<version>_<arch>.changes" format'
                % self.filename)
        self.filename_archtag = match_changes.group(3)

        if policy.unsigned_changes_ok:
            self.logger.debug("Changes file can be unsigned.")
        else:
            self.processSignature()

    def processAddresses(self):
        """Parse addresses and build person objects.

        Process 'maintainer' and 'changed_by' addresses separately and return
        an iterator over all exceptions generated while processing them.
        """
        if self.signer:
            # We only set the maintainer attribute up if we received a
            # signed upload.  This is desireable because it avoids us
            # doing ensurePerson() for buildds and sync owners.
            try:
                self.maintainer = self.parseAddress(self._dict['maintainer'])
            except UploadError, error:
                yield error

        try:
            self.changed_by = self.parseAddress(self._dict['changed-by'])
        except UploadError, error:
            yield error

    def isCustom(self, component_and_section):
        """Check if given 'component_and_section' matches a custom upload.

        We recognize an upload as custom if it is taget to a section like
        'raw-<something>'.
        Further checks will be performed in CustomUploadFile class.
        """
        component_name, section_name = splitComponentAndSection(
            component_and_section)
        if section_name.startswith('raw-'):
            return True
        return False

    def processFiles(self):
        """Build objects for each file mentioned in this changesfile.

        This method is an error generator, i.e, it returns an iterator over all
        exceptions that are generated while processing all mentioned files.
        """
        files = []
        for fileline in self._dict['files'].strip().split("\n"):
            # files lines from a changes file are always of the form:
            # CHECKSUM SIZE [COMPONENT/]SECTION PRIORITY FILENAME
            digest, size, component_and_section, priority_name, filename = (
                fileline.strip().split())
            source_match = re_issource.match(filename)
            binary_match = re_isadeb.match(filename)
            filepath = os.path.join(self.dirname, filename)
            try:
                if self.isCustom(component_and_section):
                    # This needs to be the first check, because
                    # otherwise the tarballs in custom uploads match
                    # with source_match.
                    file_instance = CustomUploadFile(
                        filepath, digest, size, component_and_section,
                        priority_name, self.policy, self.logger)
                elif source_match:
                    package = source_match.group(1)
                    if filename.endswith("dsc"):
                        file_instance = DSCFile(
                            filepath, digest, size, component_and_section,
                            priority_name, package, self.version, self,
                            self.policy, self.logger)
                        # Store the DSC because it is very convenient
                        self.dsc = file_instance
                    else:
                        file_instance = SourceUploadFile(
                            filepath, digest, size, component_and_section,
                            priority_name, package, self.version, self,
                            self.policy, self.logger)
                elif binary_match:
                    package = binary_match.group(1)
                    if filename.endswith("udeb"):
                        file_instance = UdebBinaryUploadFile(
                            filepath, digest, size, component_and_section,
                            priority_name, package, self.version, self,
                            self.policy, self.logger)
                    else:
                        file_instance = DebBinaryUploadFile(
                            filepath, digest, size, component_and_section,
                            priority_name, package, self.version, self,
                            self.policy, self.logger)
                else:
                    yield UploadError(
                        "Unable to identify file %s (%s) in changes."
                        % (filename, component_and_section))
                    continue
            except UploadError, error:
                yield error
            else:
                files.append(file_instance)

        self.files = files

    def verify(self):
        """Run all the verification checks on the changes data.

        This method is an error generator, i.e, it returns an iterator over all
        exceptions that are generated while verifying the changesfile
        consistency.
        """
        self.logger.debug("Verifying the changes file.")

        if len(self.files) == 0:
            yield UploadError("No files found in the changes")

        raw_urgency = self._dict['urgency'].lower()
        if not self.urgency_map.has_key(raw_urgency):
            yield UploadWarning(
                "Unable to grok urgency %s, overriding with 'low'"
                % (raw_urgency))
            self._dict['urgency'] = "low"

        if not self.policy.unsigned_changes_ok:
            assert self.signer is not None, (
                "Policy does not allow unsigned changesfile")

    #
    # useful properties
    #
    @property
    def filename(self):
        """Return the changesfile name."""
        return os.path.basename(self.filepath)

    @property
    def dirname(self):
        """Return the current upload path name."""
        return os.path.dirname(self.filepath)

    def _getFilesByType(self, upload_filetype):
        """Look up for specific type of processed uploaded files.

        It ensure the files mentioned in the changes are already processed.
        """
        assert self.files is not None, "Files must but processed first."
        return [upload_file for upload_file in self.files
                if isinstance(upload_file, upload_filetype)]

    @property
    def binary_package_files(self):
        """Return a list of BaseBinaryUploadFile initialized in this context."""
        return self._getFilesByType(BaseBinaryUploadFile)

    @property
    def source_package_files(self):
        """Return a list of SourceUploadFile initialized in this context."""
        return self._getFilesByType(SourceUploadFile)

    @property
    def custom_files(self):
        """Return a list of CustomUploadFile initialized in this context."""
        return self._getFilesByType(CustomUploadFile)

    @property
    def suite_name(self):
        """Returns the targeted suite name.

        For example, 'hoary' or 'hoary-security'.
        """
        return self._dict['distribution']

    @property
    def architectures(self):
        """Return set of strings specifying architectures listed in file.

        For instance ['source', 'all'] or ['source', 'i386', 'amd64']
        or ['source'].
        """
        return set(self._dict['architecture'].split())

    @property
    def binaries(self):
        """Return set of binary package names listed."""
        return set(self._dict['binary'].strip().split())

    @property
    def converted_urgency(self):
        """Return the appropriate SourcePackageUrgency item."""
        return self.urgency_map[self._dict['urgency'].lower()]

    @property
    def version(self):
        """Return changesfile claimed version."""
        return self._dict['version']

    @property
    def changes_comment(self):
        """Return changesfile 'change' comment."""
        return self._dict['changes']

    @property
    def date(self):
        """Return changesfile date."""
        return self._dict['date']

    @property
    def source(self):
        """Return changesfiel claimed source name"""
        return self._dict['source']

    @property
    def architecture_line(self):
        """Return changesfile archicteture line."""
        return self._dict['architecture']

    @property
    def filecontents(self):
        """Return files section contents."""
        return self._dict['filecontents']

    @property
    def simulated_changelog(self):
        """Build and return a changelog entry for this changesfile.

        it includes the change comments followed by the author identification.
        {{{
        <CHANGES_COMMENT>
         -- <CHANGED-BY>  <DATE>
        }}}
        """
        changes_author = (
            '\n -- %s   %s' %
            (self.changed_by['rfc822'], self.date))
        return self.changes_comment + changes_author


