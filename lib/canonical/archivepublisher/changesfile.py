# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""
Classes representing Changes and DSC files, which encapsulate collections of
files uploaded.
"""

import re
import os

from canonical.lp.dbschema import (
    SourcePackageUrgency)

from canonical.archivepublisher.tagfiles import (
    parse_tagfile, TagFileParseError)
from canonical.archivepublisher.dscfile import (
    DSCFile, SignableTagFile)
from canonical.archivepublisher.nascentuploadfile import (
    UploadError, UploadWarning, CustomUploadFile, BinaryUploadFile,
    UBinaryUploadFile, SourceUploadFile, re_isadeb, re_issource)

re_changes_file_name = re.compile(r"([^_]+)_([^_]+)_([^\.]+).changes")


class ChangesFile(SignableTagFile):
    """XXX"""
    mandatory_fields = set([
        "source", "binary", "architecture", "version", "distribution",
        "maintainer", "files", "changes"])

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
        self.full_filename = os.path.join(self.fsroot, filename)

        try:
            self._dict = parse_tagfile(self.full_filename,
                allow_unsigned=policy.unsigned_changes_ok)
        except (IOError, TagFileParseError), e:
            raise UploadError("Unable to parse the changes %s: %s" % (
                filename, e))

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
                    file_instance = CustomUploadFile(
                        filename, digest, size, component_and_section,
                        priority, self.fsroot, self.policy, self.logger)
                elif source_match:
                    package = source_match.group(1)
                    if filename.endswith("dsc"):
                        file_instance = DSCFile(
                            filename, digest, size,
                            component_and_section, priority, package,
                            self.version, self, self.fsroot, self.policy,
                            self.logger)
                        # Store the DSC because it is very convenient
                        self.dsc = file_instance
                    else:
                        file_instance = SourceUploadFile(
                            filename, digest, size,
                            component_and_section, priority, package,
                            self.version, self, self.fsroot,
                            self.policy, self.logger)
                elif binary_match:
                    package = binary_match.group(1)
                    if filename.endswith("udeb"):
                        file_instance = UBinaryUploadFile(
                            filename, digest, size, component_and_section,
                            priority, package, self.version, self,
                            self.fsroot, self.policy, self.logger)
                    else:
                        file_instance = BinaryUploadFile(
                            filename, digest, size, component_and_section,
                            priority, package, self.version, self,
                            self.fsroot, self.policy, self.logger)
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
        if not self.urgency_map.has_key(raw_urgency):
            yield UploadWarning("Unable to grok urgency %s, overriding with 'low'"
                                % ( raw_urgency))
            self._dict['urgency'] = "low"

        if not self.policy.unsigned_changes_ok:
            assert self.signer is not None

    #
    #
    #

    @property
    def binary_package_files(self):
        binaries = []
        for file in self.files:
            if isinstance(UBinaryUploadFile):
                binaries.append(file)
        return binaries

    @property
    def distrorelease_and_pocket(self):
        """Returns a string like hoary or hoary-security."""
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
        return self._dict['version']

    @property
    def changes_text(self):
        return self._dict['changes']

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
    def simulated_changelog(self):
        # rebuild the changes author line as specified in bug # 30621,
        # new line containing:
        # ' -- <CHANGED-BY>  <DATE>'
        changes_author = (
            '\n -- %s   %s' %
            (self.changed_by['rfc822'], self.date))
        return self.changes_text + changes_author


