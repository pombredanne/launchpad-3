# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""The processing of nascent uploads.

Documentation on general design
  - want to log all possible errors to the end-user
  - changes file holds all uploaded files in a tree
  - changes.files and changes.dsc
  - DSC represents a source upload, and creates sources
  - but DSC holds DSCUploadedFiles, weirdly
  - binary represents a binary upload, and creates binaries
  - source files only exist for verify() purposes
  - NascentUpload is a motor that creates the changes file, does
    verifications, gets overrides, triggers creation or rejection and
    prepares the email message
"""

__metaclass__ = type

import apt_pkg
import os

from zope.component import getUtility

from canonical.archivepublisher.changesfile import ChangesFile
from canonical.archivepublisher.dscfile import DSCFile
from canonical.archivepublisher.nascentuploadfile import (
    UploadError, UploadWarning, CustomUploadFile, SourceUploadFile,
    BaseBinaryUploadFile)
from canonical.archivepublisher.template_messages import (
    rejection_template, new_template, accepted_template, announce_template)
from canonical.config import config
from canonical.encoding import guess as guess_encoding
from canonical.launchpad.mail import format_address
from canonical.launchpad.interfaces import (
    ISourcePackageNameSet, IBinaryPackageNameSet, ILibraryFileAliasSet,
    NotFoundError)
from canonical.lp.dbschema import PackagePublishingPocket


class FatalUploadError(Exception):
    """A fatal error occurred processing the upload; processing aborted."""


class NascentUpload:
    """Represents an upload being born. NascentUpload's responsibilities
    are:

        1. Instantiating the ChangesFile and supplying to it the relevant
           context.
        2. Checking consistency of the upload in overall terms: given all
           present binaries, sources and other bits and pieces, does this
           upload "make sense"?
        2. Collecting errors and warnings that occurred while processing
           the upload.
        3. Checking signer ACL and keyring constraints.
        4. Creating state in the database once we've decided the upload
           is good, and throwing it away otherwise.
        5. Sending email to concerned individuals.

    The collaborative international dictionary of English defines nascent as:

     1. Commencing, or in process of development; beginning to
        exist or to grow; coming into being; as, a nascent germ.
        [1913 Webster +PJC]

    A nascent upload is thus in the process of coming into being. Specifically
    a nascent upload is something we're trying to get into a shape we can
    insert into the database as a queued upload to be processed.
    """
    recipients = None

    # Defined in check_changes_consistency()
    sourceful = False
    binaryful = False
    archindep = False
    archdep = False

    # Defined in check_sourceful_consistency()
    native = False
    hasorig = False

    # Defined if we successfully do_accept() and storeObjectsInDatabase()
    queue_root = None

    def __init__(self, changesfile_path, policy, logger):
        """Setup a ChangesFile based on given changesfile path.

        May raise FatalUploadError due to unrecoverable problems building
        the ChangesFile object.
        Also store given and initialized Upload Policy, as 'policy'
        """
        self.changesfile_path = changesfile_path
        self.policy = policy
        self.logger = logger

        self.rejections = []
        self.warnings = []

        self.librarian = getUtility(ILibraryFileAliasSet)
        try:
            self.changes = ChangesFile(
                changesfile_path, self.policy, self.logger)
        except UploadError, e:
            # We can't run reject() because unfortunately we don't have
            # the address of the uploader to notify -- we broke in that
            # exact step.
            # XXX cprov 20070326: we should really be emailing this
            # rejection to the archive admins. For now, this will end
            # up in the script log.
            raise FatalUploadError(str(e))

    def process(self):
        """Process this upload, checking it against policy, loading it into
        the database if it seems okay.

        No exceptions should be raised. In a few very unlikely events, an
        UploadError will be raised and sent up to the caller. If this happens
        the caller should call the reject method and process a rejection.
        """
        self.logger.debug("Beginning processing.")

        try:
            self.policy.setDistroReleaseAndPocket(self.changes.suite_name)
        except NotFoundError:
            self.reject(
                "Unable to find distrorelease: %s" % self.changes.suite_name)

        # We need to process changesfile addresses at this point because
        # we depend on an already initialised policy (distrorelease
        # and pocket set) to have proper person 'creation rationale'.
        self.run_and_collect_errors(self.changes.processAddresses)

        self.run_and_collect_errors(self.changes.processFiles)

        for uploaded_file in self.changes.files:
            self.run_and_check_error(uploaded_file.checkNameIsTaintFree)
            self.run_and_check_error(uploaded_file.checkSizeAndCheckSum)

        self._check_overall_consistency()
        if self.sourceful:
            self._check_sourceful_consistency()
        if self.binaryful:
            self._check_binaryful_consistency()

        self.run_and_collect_errors(self.changes.verify)

        self.logger.debug("Verifying files in upload.")
        for uploaded_file in self.changes.files:
            self.run_and_collect_errors(uploaded_file.verify)

        if (len(self.changes.files) == 1 and
            isinstance(self.changes.files[0], CustomUploadFile)):
            self.logger.debug("Single Custom Upload detected.")
        else:
            if self.sourceful and not self.policy.can_upload_source:
                self.reject("Upload is sourceful, but policy refuses "
                            "sourceful uploads.")

            if self.binaryful and not self.policy.can_upload_binaries:
                self.reject("Upload is binaryful, but policy refuses "
                            "binaryful uploads.")

            if (self.sourceful and self.binaryful and
                not self.policy.can_upload_mixed):
                self.reject("Upload is source/binary but policy refuses "
                            "mixed uploads.")

            if self.sourceful and not self.changes.dsc:
                self.reject(
                    "Unable to find the dsc file in the sourceful upload?")

            # Apply the overrides from the database. This needs to be done
            # before doing component verifications because the component
            # actually comes from overrides for packages that are not NEW.
            self.find_and_apply_overrides()

        signer_components = self.processSignerAcl()
        if not self.is_new:
            # check rights for OLD packages, the NEW ones goes straight to queue
            self.verify_acl(signer_components)

        # Check if the policy distrorelese is already defined first.
        # If it's not, skip pocket upload rights check, the upload
        # is already rejected at this point.
        distrorelease = self.policy.distrorelease
        pocket = self.policy.pocket
        if distrorelease and not distrorelease.canUploadToPocket(pocket):
            self.reject(
                "Not permitted to upload to the %s pocket in a "
                "release in the '%s' state." % (
                self.policy.pocket.name,
                self.policy.distrorelease.releasestatus.name))

        # Perform policy checks
        self.policy.checkUpload(self)

        # That's all folks.
        self.logger.debug("Finished checking upload.")

    #
    # Minor helpers
    #
    @property
    def filename(self):
        """Return the changesfile name."""
        return os.path.basename(self.changesfile_path)

    @property
    def is_new(self):
        """Return true if any portion of the upload is NEW."""
        for uploaded_file in self.changes.files:
            if uploaded_file.new:
                return True
        return False

    @property
    def sender(self):
        """RFC822 sender header specified in LP configuration."""
        return "%s <%s>" % (
            config.uploader.default_sender_name,
            config.uploader.default_sender_address)

    @property
    def default_recipient(self):
        """RFC822 default recipient specified in LP configuration. """
        return "%s <%s>" % (config.uploader.default_recipient_name,
                            config.uploader.default_recipient_address)

    #
    # Overall consistency checks
    #

    def _check_overall_consistency(self):
        """Heuristics checks on upload contents and declared architecture.

        An upload may list 'powerpc' and 'all' in its architecture line
        and yet only upload 'powerpc' because of being built -B by a
        buildd.  As a result, we use the think_* variables as a screen.
        If the files_X value is true then think_X must also be true.
        However nothing useful can be said of the other cases.
        """
        think_sourceful = False
        think_binaryful = False
        think_archindep = False
        think_archdep = False

        changes_architectures = self.changes.architectures
        if 'source' in changes_architectures:
            think_sourceful = True
            changes_architectures.remove('source')

        if changes_architectures:
            think_binaryful = True

        if 'all' in changes_architectures:
            think_archindep = True
            changes_architectures.remove('all')

        if think_binaryful and len(changes_architectures) > 0:
            think_archdep = True

        files_sourceful = False
        files_binaryful = False
        files_archindep = False
        files_archdep = False

        for uploaded_file in self.changes.files:
            if isinstance(uploaded_file, CustomUploadFile):
                files_binaryful = files_binaryful or True
            elif isinstance(uploaded_file, BaseBinaryUploadFile):
                files_binaryful = files_binaryful or True
                files_archindep = files_archindep or uploaded_file.is_archindep
                files_archdep = files_archdep or not uploaded_file.is_archindep
            elif isinstance(uploaded_file, SourceUploadFile):
                files_sourceful = True
            else:
                # This is already caught in ChangesFile.__init__
                raise AssertionError("Unknown uploaded file type.")

        if files_sourceful != think_sourceful:
            self.reject("Mismatch in sourcefulness. (arch) %s != (files) %s"
                 % (think_sourceful, files_sourceful))
        if files_binaryful != think_binaryful:
            self.reject("Mismatch in binaryfulness. (arch) %s != (files) %s"
                 % (think_binaryful, files_binaryful))

        if files_archindep and not think_archindep:
            self.reject("One or more files uploaded with architecture "
                        "'all' but changes file does not list 'all'.")

        if files_archdep and not think_archdep:
            self.reject("One or more files uploaded with specific "
                        "architecture but changes file does not list it.")

        # Remember the information for later use in properties.
        self.sourceful = think_sourceful
        self.binaryful = think_binaryful
        self.archindep = think_archindep
        self.archdep = think_archdep

    def _check_sourceful_consistency(self):
        """Heuristic checks on a sourceful upload.

        Raises AssertionError when called for a non-sourceful upload.
        Ensures a sourceful upload has, at least:

         * One DSC
         * One or none DIFF
         * One or none ORIG
         * One or none TAR
         * If no DIFF is present it must have a TAR (native)

        'hasorig' and 'native' attributes are set when an ORIG and/or an
        TAR file, respectively, are present.
        """
        assert self.sourceful, (
            "Source consistency check called for a non-source upload")

        dsc = 0
        diff = 0
        orig = 0
        tar = 0

        for uploaded_file in self.changes.files:
            if uploaded_file.filename.endswith(".dsc"):
                dsc += 1
            elif uploaded_file.filename.endswith(".diff.gz"):
                diff += 1
            elif uploaded_file.filename.endswith(".orig.tar.gz"):
                orig += 1
            elif (uploaded_file.filename.endswith(".tar.gz")
                  and not isinstance(uploaded_file, CustomUploadFile)):
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

        self.native = bool(tar)
        self.hasorig = bool(orig)

    def _check_binaryful_consistency(self):
        """Heuristic checks on a binaryful upload.

        It copes with mixed_uploads (source + binaries).

        Check if the declared number of architectures corresponds to the
        upload contents.
        """
        # Currently the only check we make is that if the upload is binaryful
        # we don't allow more than one build.
        # XXX: dsilvers: 20051014: We'll want to refactor to remove this limit
        # but it's not too much of a hassle for now.
        # bug 3158
        considered_archs = [arch_name for arch_name in self.changes.architectures
                            if not arch_name.endswith("_translations")]
        max = 1
        if self.sourceful:
            # When sourceful, the tools add 'source' to the architecture
            # list in the upload. Thusly a sourceful upload with one build
            # has two architectures listed.
            max = 2
        if 'all' in considered_archs:
            # Sometimes we get 'i386 all' which would count as two archs
            # so if 'all' is present, we bump the permitted number up
            # by one.
            max += 1
        if len(considered_archs) > max:
            self.reject("Policy permits only one build per upload.")

    #
    # Helpers for warnings and rejections
    #

    def run_and_check_error(self, callable):
        """Run the given callable and process errors and warnings.

        UploadError(s) and UploadWarnings(s) are handled.
        """
        try:
            callable()
        except UploadError, error:
            self.reject(str(error))
        except UploadWarning, error:
            self.warn(str(error))

    def run_and_collect_errors(self, callable):
        """Run 'special' callable that generates a list of errors/warnings.

        The so called 'special' callables returns a generator containing all
        exceptions occurring during it's process.

        Currently it is used for {NascentUploadFile, ChangesFile}.verify()
        method.

        The rationale for this is that we want to collect as many
        errors/warnings as possible, instead of interrupting the checks
        when we find the first problem, when processing an upload.

        This methodology helps to avoid retrying an upload multiple times
        because there are multiple problems.
        """
        for error in callable():
            if isinstance(error, UploadError):
                self.reject(str(error))
            elif isinstance(error, UploadWarning):
                self.warn(str(error))
            else:
                raise AssertionError("Unknown error occurred: %s" % str(error))

    def reject(self, msg):
        """Add the provided message to the rejection message."""
        self.rejections.append(msg)

    @property
    def rejection_message(self):
        """Aggregates rejection messages."""
        return '\n'.join(self.rejections)

    @property
    def is_rejected(self):
        """Returns whether or not this upload was rejected."""
        return len(self.rejections) > 0

    def warn(self, msg):
        """Add the provided message to the warning message."""
        self.warnings.append(msg)

    @property
    def warning_message(self):
        """Aggregates warning messages."""
        return '\n'.join(self.warnings)

    #
    # Signature and ACL stuff
    #

    def _components_valid_for(self, person):
        """Return the set of components this person could upload to."""

        possible_components = set(
            acl.component.name for acl in self.policy.distro.uploaders
            if person in acl)

        if possible_components:
            self.logger.debug("%s (%d) is an uploader for %s." % (
                person.displayname, person.id,
                ', '.join(sorted(possible_components))))

        return possible_components

    def is_person_in_keyring(self, person):
        """Return whether or not the specified person is in the keyring."""
        self.logger.debug("Attempting to decide if %s is in the keyring." % (
            person.displayname))
        in_keyring = len(self._components_valid_for(person)) > 0
        self.logger.debug("Decision: %s" % in_keyring)
        return in_keyring

    def processSignerAcl(self):
        """Work out what components the signer is permitted to upload to and
        verify that all files are either NEW or are targetted at those
        components only.
        """

        # If we have no signer, there's no ACL we can apply
        if self.changes.signer is None:
            self.logger.debug("No signer, therefore ACL not processed")
            return

        possible_components = self._components_valid_for(self.changes.signer)

        if not possible_components:
            self.reject(
                "Signer has no upload rights at all to this distribution.")

        return possible_components

    def verify_acl(self, signer_components):
        """Verify that the uploaded files are okay for their named components
        by the provided signer.
        """
        if self.changes.signer is None:
            self.logger.debug(
                "No signer, therefore no point verifying signer against ACL")
            return

        for uploaded_file in self.changes.files:
            if not isinstance(uploaded_file, (DSCFile, BaseBinaryUploadFile)):
                # The only things that matter here are sources and
                # binaries, because they are the only objects that get
                # overridden and created in the database.
                continue
            if (uploaded_file.component_name not in signer_components and
                uploaded_file.new == False):
                self.reject(
                    "Signer is not permitted to upload to the component "
                    "'%s' of file '%s'" % (
                    uploaded_file.component.name, uploaded_file.filename))

    #
    # Handling checking of versions and overrides
    #

    def getSourceAncestry(self, uploaded_file):
        """Return the last published source (ancestry) for a given file.

        Return the most recent ISPPH instance matching the uploaded file
        package name or None.
        """
        # Only lookup uploads ancestries in target pocket and fallback
        # to RELEASE pocket
        # Upload ancestries found here will guide the auto-override
        # procedure and the version consistency check:
        #
        #  * uploaded_version > ancestry_version
        #
        # which is the *only right* check we can do automatically.
        # Post-release history and proposed content may diverge and can't
        # be properly automatically overridden.
        #
        # We are relaxing version constraints when processing uploads since
        # there are many corner cases when checking version consistency
        # against post-release pockets, like:
        #
        #  * SECURITY/UPDATES can be lower than PROPOSED/BACKPORTS
        #  * UPDATES can be lower than SECURITY
        #  * ...
        #
        # And they really depends more on the package contents than the
        # version number itself.
        # Version inconsistencies will (should) be identified during the
        # mandatory review in queue, anyway.
        # See bug #83976
        source_name = getUtility(
            ISourcePackageNameSet).queryByName(uploaded_file.package)

        if source_name is None:
            return None

        lookup_pockets = [self.policy.pocket, PackagePublishingPocket.RELEASE]
        for pocket in lookup_pockets:
            candidates = self.policy.distrorelease.getPublishedReleases(
                source_name, include_pending=True, pocket=pocket)
            if candidates:
                return candidates[0]
        return None

    def getBinaryAncestry(self, uploaded_file, try_other_archs=True):
        """Return the last published binary (ancestry) for given file.

        Return the most recent IBPPH instance matching the uploaded file
        package name or None.

        This method may raise NotFoundError if it is dealing with an
        uploaded file targeted to an architecture not present in the
        distrorelease in context. So callsites needs to be aware.
        """
        binary_name = getUtility(
            IBinaryPackageNameSet).queryByName(uploaded_file.package)

        if binary_name is None:
            return None

        if uploaded_file.architecture == "all":
            arch_indep = self.policy.distrorelease.nominatedarchindep
            archtag = arch_indep.architecturetag
        else:
            archtag = uploaded_file.architecture

        # XXX cprov 20070213: it raises NotFoundError for unknown
        # architectures. For now, it is treated in find_and_apply_overrides().
        # But it should be refactored ASAP.
        dar = self.policy.distrorelease[archtag]

        # See the comment below, in getSourceAncestry
        lookup_pockets = [self.policy.pocket, PackagePublishingPocket.RELEASE]
        for pocket in lookup_pockets:
            candidates = dar.getReleasedPackages(
                binary_name, include_pending=True, pocket=pocket)
            if candidates:
                return candidates[0]

            if not try_other_archs:
                continue

            # Try the other architectures...
            dars = self.policy.distrorelease.architectures
            other_dars = [other_dar for other_dar in dars
                          if other_dar.id != dar.id]
            for other_dar in other_dars:
                candidates = other_dar.getReleasedPackages(
                    binary_name, include_pending=True, pocket=pocket)
                if candidates:
                    return candidates[0]
        return None

    def _checkVersion(self, proposed_version, archive_version, filename):
        """Check if the proposed version is higher than that in the archive."""
        if apt_pkg.VersionCompare(proposed_version, archive_version) <= 0:
            self.reject("%s: Version older than that in the archive. %s <= %s"
                        % (filename, proposed_version, archive_version))

    def checkSourceVersion(self, uploaded_file, ancestry):
        """Check if the uploaded source version is higher than the ancestry.

        Automatically mark the package as 'rejected' using _checkVersion().
        """
        # At this point DSC.version should be equal Changes.version.
        # Anyway, we trust more in DSC.
        proposed_version = self.changes.dsc.dsc_version
        archive_version = ancestry.sourcepackagerelease.version
        filename = uploaded_file.filename
        self._checkVersion(proposed_version, archive_version, filename)

    def checkBinaryVersion(self, uploaded_file, ancestry):
        """Check if the uploaded binary version is higher than the ancestry.

        Automatically mark the package as 'rejected' using _checkVersion().
        """
        # We only trust in the control version, specially because the
        # 'version' from changesfile may not include epoch for binaries.
        # This is actually something that needs attention in our buildfarm,
        # because debuild does build the binary changesfile with a version
        # that includes epoch.
        proposed_version = uploaded_file.control_version
        archive_version = ancestry.binarypackagerelease.version
        filename = uploaded_file.filename
        self._checkVersion(proposed_version, archive_version, filename)

    def overrideSource(self, uploaded_file, override):
        """Overrides the uploaded source based on its override information.

        Override target component and section.
        """
        self.logger.debug("%s: (source) exists in %s" % (
            uploaded_file.package, override.pocket.name))

        uploaded_file.component_name = override.component.name
        uploaded_file.section_name = override.section.name

    def overrideBinary(self, uploaded_file, override):
        """Overrides the uploaded binary based on its override information.

        Override target component, section and priority.
        """
        self.logger.debug("%s: (binary) exists in %s/%s" % (
            uploaded_file.package, override.distroarchrelease.architecturetag,
            override.pocket.name))

        uploaded_file.component_name = override.component.name
        uploaded_file.section_name = override.section.name
        # Both, changesfiles and nascentuploadfile local maps, reffer to
        # priority in lower-case names, but the DBSCHEMA name is upper-case.
        # That's why we need this conversion here.
        uploaded_file.priority_name = override.priority.name.lower()

    def find_and_apply_overrides(self):
        """Look for ancestry and overrides information.

        Anything not yet in the DB gets tagged as 'new' and won't count
        towards the permission check.
        """
        self.logger.debug("Finding and applying overrides.")

        for uploaded_file in self.changes.files:
            if isinstance(uploaded_file, DSCFile):
                self.logger.debug(
                    "Checking for %s/%s source ancestry"
                    %(uploaded_file.package, uploaded_file.version))
                ancestry = self.getSourceAncestry(uploaded_file)
                if ancestry is not None:
                    self.checkSourceVersion(uploaded_file, ancestry)
                    # XXX cprov 20070212: The current override mechanism is
                    # broken, since it modifies original contents of SPR/BPR.
                    # We could do better by having a specific override table
                    # that relates a SPN/BPN to a specific DR/DAR and carries
                    # the respective information to be overridden.
                    self.overrideSource(uploaded_file, ancestry)
                    uploaded_file.new = False
                else:
                    self.logger.debug(
                        "%s: (source) NEW" % (uploaded_file.package))
                    uploaded_file.new = True

            elif isinstance(uploaded_file, BaseBinaryUploadFile):
                self.logger.debug(
                    "Checking for %s/%s/%s binary ancestry"
                    %(uploaded_file.package, uploaded_file.version,
                      uploaded_file.architecture))
                try:
                    ancestry = self.getBinaryAncestry(uploaded_file)
                except NotFoundError:
                    self.reject("%s: Unable to find arch: %s"
                                % (uploaded_file.package,
                                   uploaded_file.architecture))
                    ancestry = None
                if ancestry is not None:
                    # XXX cprov 20070212: see above.
                    self.overrideBinary(uploaded_file, ancestry)
                    uploaded_file.new = False
                    # For binary versions verification we should only
                    # use ancestries in the same architecture. If none
                    # was found we can go w/o any checks, since it's
                    # a NEW binary in this architecture, any version is
                    # fine. See bug #89846 for further info.
                    ancestry = self.getBinaryAncestry(
                        uploaded_file, try_other_archs=False)
                    if ancestry is not None:
                        self.checkBinaryVersion(uploaded_file, ancestry)
                else:
                    self.logger.debug(
                        "%s: (binary) NEW" % (uploaded_file.package))
                    uploaded_file.new = True

    #
    # Actually processing accepted or rejected uploads -- and mailing people
    #

    def do_accept(self, new_msg=new_template, accept_msg=accepted_template,
                  announce_msg=announce_template):
        """Accept the upload into the queue.

        This *MAY* in extreme cases cause a database error and thus
        actually end up with a rejection being issued. This could
        occur, for example, if we have failed to validate the input
        sufficiently and something trips a database validation
        constraint.
        """
        if self.is_rejected:
            self.reject("Alas, someone called do_accept when we're rejected")
            return False, self.do_reject()
        try:
            interpolations = {
                "MAINTAINERFROM": self.sender,
                "SENDER": self.sender,
                "CHANGES": self.changes.filename,
                "SUMMARY": self.getNotificationSummary(),
                "CHANGESFILE": guess_encoding(self.changes.filecontents),
                "DISTRO": self.policy.distro.title,
                "DISTRORELEASE": self.policy.distrorelease.name,
                "ANNOUNCE": self.policy.announcelist,
                "SOURCE": self.changes.source,
                "VERSION": self.changes.version,
                "ARCH": self.changes.architecture_line,
                }
            if self.changes.signer:
                interpolations['MAINTAINERFROM'] = self.changes.changed_by[
                    'rfc2047']

            recipients = self.getRecipients()

            interpolations['RECIPIENT'] = ", ".join(recipients)
            interpolations['DEFAULT_RECIPIENT'] = self.default_recipient

            self.storeObjectsInDatabase()

            # NEW, Auto-APPROVED and UNAPPROVED source uploads targeted to
            # section 'translations' should not generate any emails.
            if (self.sourceful and
                self.changes.dsc.section_name == 'translations'):
                self.logger.debug(
                    "Skipping acceptance and announcement, it is a language-"
                    "package upload.")
                return True, []

            # Unknown uploads
            if self.is_new:
                return True, [new_msg % interpolations]

            # Known uploads

            # UNAPPROVED uploads coming from 'insecure' policy only sends
            # acceptance message.
            if not self.policy.autoApprove(self):
                interpolations["SUMMARY"] += (
                    "\nThis upload awaits approval by a distro manager\n")
                return True, [accept_msg % interpolations]

            # Auto-APPROVED uploads to BACKPORTS skips announcement.
            # usually processed with 'sync' policy
            if self.policy.pocket == PackagePublishingPocket.BACKPORTS:
                self.logger.debug(
                    "Skipping announcement, it is a BACKPORT.")
                return True, [accept_msg % interpolations]

            # Auto-APPROVED binary uploads to SECURITY skips announcement.
            # usually processed with 'security' policy
            if (self.policy.pocket == PackagePublishingPocket.SECURITY
                and self.binaryful):
                self.logger.debug(
                    "Skipping announcement, it is a binary upload to SECURITY.")
                return True, [accept_msg % interpolations]

            # Fallback, all the rest comming from 'insecure', 'secure',
            # and 'sync' policies should send acceptance & announcement
            # messages.
            return True, [
                accept_msg % interpolations,
                announce_msg % interpolations]

        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception, e:
            # Any exception which occurs while processing an accept will
            # cause a rejection to occur. The exception is logged in the
            # reject message rather than being swallowed up.
            self.reject("Exception while accepting: %s" % e)
            return False, self.do_reject()

    def do_reject(self, template=rejection_template):
        """Reject the current upload given the reason provided."""
        assert self.is_rejected, "The upload is not rejected."

        interpolations = {
            "SENDER": self.sender,
            "CHANGES": self.changes.filename,
            "SUMMARY": self.rejection_message,
            "CHANGESFILE": guess_encoding(self.changes.filecontents)
            }
        recipients = self.getRecipients()
        interpolations['RECIPIENT'] = ", ".join(recipients)
        interpolations['DEFAULT_RECIPIENT'] = self.default_recipient
        outgoing_msg = template % interpolations

        return [outgoing_msg]

    def getRecipients(self):
        """Return a list of recipients including every address we trust."""
        recipients = []
        self.logger.debug("Building recipients list.")
        maintainer = self.changes.maintainer['person']
        changer = self.changes.changed_by['person']

        if self.changes.signer:
            recipients.append(self.changes.signer_address['person'])

            if (maintainer != self.changes.signer and
                self.is_person_in_keyring(maintainer)):
                self.logger.debug("Adding maintainer to recipients")
                recipients.append(maintainer)

            if (changer != self.changes.signer and changer != maintainer
                and self.is_person_in_keyring(changer)):
                self.logger.debug("Adding changed-by to recipients")
                recipients.append(changer)
        else:
            # Only autosync policy allow unsigned changes
            # We rely on the person running sync-tool about the identity
            # of the changer.
            self.logger.debug(
                "Changes file is unsigned, adding changer as recipient")
            recipients.append(changer)

        valid_recipients = []
        for person in recipients:
            if person is None or person.preferredemail is None:
                # We should only actually send mail to people that are
                # registered Launchpad user with preferred email; this
                # is a sanity check to avoid spamming the innocent.  Not
                # that we do that sort of thing.
                #
                # In particular, people that were created because of
                # policy.create_people won't get emailed. That's life.
                continue
            recipient = format_address(person.displayname,
                                       person.preferredemail.email)
            self.logger.debug("Adding recipient: '%s'" % recipient)
            valid_recipients.append(recipient)
        return valid_recipients

    def getNotificationSummary(self):
        """List the files and build the notification summary as needed."""
        summary = []
        for uploaded_file in self.changes.files:
            if uploaded_file.new:
                summary.append("NEW: %s" % uploaded_file.filename)
            else:
                summary.append(" OK: %s" % uploaded_file.filename)
                if isinstance(uploaded_file, DSCFile):
                    summary.append("     -> Component: %s Section: %s" % (
                        uploaded_file.component.name,
                        uploaded_file.section.name))

        return "\n".join(summary)

    #
    # Inserting stuff in the database
    #

    def storeObjectsInDatabase(self):
        """Insert this nascent upload into the database."""

        # Queue entries are created in the NEW state by default; at the
        # end of this method we cope with uploads that aren't new.
        self.logger.debug("Creating queue entry")
        distrorelease = self.policy.distrorelease
        self.queue_root = distrorelease.createQueueEntry(
            self.policy.pocket, self.changes.filename,
            self.changes.filecontents, self.changes.signingkey)

        # When binaryful and sourceful, we have a mixed-mode upload.
        # Mixed-mode uploads need special handling, and the spr here is
        # short-circuited into the binary. See the docstring in
        # UBinaryUploadFile.verify_sourcepackagerelease() for details.
        spr = None
        if self.sourceful:
            assert self.changes.dsc, "Sourceful upload lacks DSC."
            spr = self.changes.dsc.storeInDatabase()
            self.queue_root.addSource(spr)

        if self.binaryful:

            for custom_file in self.changes.custom_files:
                libraryfile = custom_file.storeInDatabase()
                self.queue_root.addCustom(
                    libraryfile, custom_file.custom_type)

            # Container for the build that will be processed.
            processed_builds = []

            for binary_package_file in self.changes.binary_package_files:
                if self.sourceful:
                    # The reason we need to do this verification
                    # so late in the game is that in the
                    # mixed-upload case we only have a
                    # sourcepackagerelease to verify here!
                    assert self.policy.can_upload_mixed, (
                        "Current policy does not allow mixed uploads.")
                    assert spr, "No sourcepackagerelease was found."
                    binary_package_file.verifySourcePackageRelease(spr)
                else:
                    spr = binary_package_file.findSourcePackageRelease()

                build = binary_package_file.findBuild(spr)
                assert self.queue_root.pocket == build.pocket, (
                    "Binary was not build for the claimed pocket.")
                binary_package_file.storeInDatabase(build)
                processed_builds.append(build)

            # Perform some checks on processed build(s) if there were any.
            # Ensure that only binaries for a single build were processed
            # Then add a respective DistroReleaseQueueBuild entry for it
            if len(processed_builds) > 0:
                unique_builds = set([b.id for b in processed_builds])
                assert len(unique_builds) == 1, (
                    "Upload contains binaries from different builds. "
                    "(%s)" % unique_builds)
                # Use any (the first) IBuild stored as reference.
                # They are all the same according the previous assertion.
                considered_build = processed_builds[0]
                self.queue_root.addBuild(considered_build)

        if not self.is_new:
            # if it is known (already overridden properly), move it to
            # ACCEPTED state automatically
            if self.policy.autoApprove(self):
                self.logger.debug("Setting it to ACCEPTED")
                self.queue_root.setAccepted()
                # If it is a pure-source upload we can further process it
                # in order to have a pending publishing record for it in place
                # This *hack* is based on discussions for bug #77853 and aims
                # to fix a deficiency on published file lookup system.
                if ((queue_root.sources.count() == 1) and
                    (queue_root.builds.count() == 0) and
                    (queue_root.customfiles.count() == 0)):
                    self.logger.debug("Creating PENDING publishing record.")
                    queue_root.realiseUpload()
            else:
                self.logger.debug("Setting it to UNAPPROVED")
                self.queue_root.setUnapproved()


