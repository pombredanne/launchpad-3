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

from canonical.archiveuploader.changesfile import ChangesFile
from canonical.archiveuploader.dscfile import DSCFile
from canonical.archiveuploader.nascentuploadfile import (
    UploadError, UploadWarning, CustomUploadFile, SourceUploadFile,
    BaseBinaryUploadFile)
from canonical.launchpad.interfaces import (
    ArchivePurpose, IBinaryPackageNameSet, IDistributionSet,
    ILibraryFileAliasSet, ISourcePackageNameSet, NotFoundError,
    PackagePublishingPocket, QueueInconsistentStateError)
from canonical.launchpad.scripts.processaccepted import (
    close_bugs_for_queue_item)


class FatalUploadError(Exception):
    """A fatal error occurred processing the upload; processing aborted."""


class EarlyReturnUploadError(Exception):
    """An error occurred that prevented further error collection."""


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
            # XXX cprov 2007-03-26: we should really be emailing this
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
            self.policy.setDistroSeriesAndPocket(self.changes.suite_name)
        except NotFoundError:
            self.reject(
                "Unable to find distroseries: %s" % self.changes.suite_name)

        # We need to process changesfile addresses at this point because
        # we depend on an already initialised policy (distroseries
        # and pocket set) to have proper person 'creation rationale'.
        self.run_and_reject_on_error(self.changes.processAddresses)

        self.run_and_reject_on_error(self.changes.processFiles)

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

        signer_components = self.getAutoAcceptedComponents()
        if not self.is_new:
            # check rights for OLD packages, the NEW ones goes
            # straight to queue
            self.verify_acl(signer_components)

        # Override archive location if necessary.
        self.overrideArchive()

        # Perform policy checks.
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
                files_archindep = (
                    files_archindep or uploaded_file.is_archindep)
                files_archdep = (
                    files_archdep or not uploaded_file.is_archindep)
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
        considered_archs = [
            arch_name for arch_name in self.changes.architectures
            if not arch_name.endswith("_translations")]
        max = 1
        if self.sourceful:
            # When sourceful, the tools add 'source' to the architecture
            # list in the upload.
            max = self.policy.distroseries.architecturecount + 1
        if 'all' in considered_archs:
            # Sometimes we get 'i386 all' which would count as two archs
            # so if 'all' is present, we bump the permitted number up
            # by one.
            max += 1
        if len(considered_archs) > max:
            self.reject("Upload has more architetures than it is supported.")

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
                raise AssertionError(
                    "Unknown error occurred: %s" % str(error))

    def run_and_reject_on_error(self, callable):
        """Run given callable and raise EarlyReturnUploadError on errors."""
        self.run_and_collect_errors(callable)
        if self.is_rejected:
            raise EarlyReturnUploadError(
                "An error occurred that prevented further processing.")

    @property
    def is_ppa(self):
        """Whether or not the current upload is target for a PPA."""
        # XXX julian 2007-05-29 bug=117557: When self.policy.distroseries
        # is None, this will causes a rejection for the wrong reasons
        # (a code exception instead of a bad distro).
        if not self.policy.distroseries:
            # Greasy hack until above bug is fixed.
            return False
        return self.policy.archive.purpose == ArchivePurpose.PPA

    def reject(self, msg):
        """Add the provided message to the rejection message."""
        self.rejections.append(msg)

    @property
    def rejection_message(self):
        """Aggregate rejection messages."""
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
        """Aggregates warning messages.

        Return a text header containing all the warnings raised during the
        upload processing or None, if no warnings were issued.
        """
        if not self.warnings:
            return None
        warning_header = (
            "\nUpload Warnings:\n%s" % '\n'.join(self.warnings))
        return warning_header

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

    def getAutoAcceptedComponents(self):
        """Check rights of the current upload submmiter.

        Work out what components the signer is permitted to upload to and
        verify that all files are either NEW or are targetted at those
        components only for normal distribution uploads.

        Ensure the signer is the onwer of the targeted archive for PPA
        uploads.
        """
        # If we have no signer, there's no ACL we can apply
        if self.changes.signer is None:
            self.logger.debug("No signer, therefore ACL not processed")
            return

        # verify PPA uploads
        if self.is_ppa:
            if not self.changes.signer.inTeam(self.policy.archive.owner):
                self.reject("Signer has no upload rights to this PPA")
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
        if self.is_ppa:
            self.logger.debug("Do verify signer ACL for PPA")
            return

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

            if self.is_ppa:
                archive = self.policy.archive
            else:
                archive = None
            candidates = self.policy.distroseries.getPublishedReleases(
                source_name, include_pending=True, pocket=pocket,
                archive=archive)
            if candidates:
                return candidates[0]

        return None

    def getBinaryAncestry(self, uploaded_file, try_other_archs=True):
        """Return the last published binary (ancestry) for given file.

        Return the most recent IBPPH instance matching the uploaded file
        package name or None.

        This method may raise NotFoundError if it is dealing with an
        uploaded file targeted to an architecture not present in the
        distroseries in context. So callsites needs to be aware.
        """
        binary_name = getUtility(
            IBinaryPackageNameSet).queryByName(uploaded_file.package)

        if binary_name is None:
            return None

        if uploaded_file.architecture == "all":
            arch_indep = self.policy.distroseries.nominatedarchindep
            archtag = arch_indep.architecturetag
        else:
            archtag = uploaded_file.architecture

        # XXX cprov 2007-02-13: it raises NotFoundError for unknown
        # architectures. For now, it is treated in find_and_apply_overrides().
        # But it should be refactored ASAP.
        dar = self.policy.distroseries[archtag]

        # See the comment below, in getSourceAncestry
        lookup_pockets = [self.policy.pocket, PackagePublishingPocket.RELEASE]

        if self.is_ppa:
            archive = self.policy.archive
        else:
            archive = None

        for pocket in lookup_pockets:
            candidates = dar.getReleasedPackages(
                binary_name, include_pending=True, pocket=pocket,
                archive=archive)

            if candidates:
                return candidates[0]

            if not try_other_archs:
                continue

            # Try the other architectures...
            dars = self.policy.distroseries.architectures
            other_dars = [other_dar for other_dar in dars
                          if other_dar.id != dar.id]
            for other_dar in other_dars:
                candidates = other_dar.getReleasedPackages(
                    binary_name, include_pending=True, pocket=pocket,
                    archive=archive)

                if candidates:
                    return candidates[0]
        return None

    def _checkVersion(self, proposed_version, archive_version, filename):
        """Check if the proposed version is higher than the one in archive."""
        if apt_pkg.VersionCompare(proposed_version, archive_version) < 0:
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
        self.logger.debug("%s (source) exists in %s" % (
            override.sourcepackagerelease.title,
            override.pocket.name))

        uploaded_file.component_name = override.component.name
        uploaded_file.section_name = override.section.name

    def overrideBinary(self, uploaded_file, override):
        """Overrides the uploaded binary based on its override information.

        Override target component, section and priority.
        """
        self.logger.debug("%s (binary) exists in %s/%s" % (
            override.binarypackagerelease.title,
            override.distroarchseries.architecturetag,
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
                    # XXX cprov 2007-02-12: The current override mechanism is
                    # broken, since it modifies original contents of SPR/BPR.
                    # We could do better by having a specific override table
                    # that relates a SPN/BPN to a specific DR/DAR and carries
                    # the respective information to be overridden.
                    self.overrideSource(uploaded_file, ancestry)
                    uploaded_file.new = False
                else:
                    if self.is_ppa:
                        uploaded_file.component_name = 'main'
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
                    # XXX cprov 2007-02-12: see above.
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
                    if self.is_ppa:
                        uploaded_file.component_name = 'main'
                    else:
                        self.logger.debug(
                            "%s: (binary) NEW" % (uploaded_file.package))
                        uploaded_file.new = True

    #
    # Actually processing accepted or rejected uploads -- and mailing people
    #

    def do_accept(self, notify=True):
        """Accept the upload into the queue.

        This *MAY* in extreme cases cause a database error and thus
        actually end up with a rejection being issued. This could
        occur, for example, if we have failed to validate the input
        sufficiently and something trips a database validation
        constraint.

        :param notify: True to send an email, False to not send one.
        """
        if self.is_rejected:
            self.reject("Alas, someone called do_accept when we're rejected")
            self.do_reject(notify)
            return False
        try:
            maintainerfrom = None
            if self.changes.signer:
                maintainerfrom = self.changes.changed_by['rfc2047']

            self.storeObjectsInDatabase()

            # Send the email.
            # There is also a small corner case here where the DB transaction
            # may fail yet this email will be sent.  The chances of this are
            # very small, and at some point the script infrastructure will
            # only send emails when the script exits successfully.
            if notify:
                changes_file_object = open(self.changes.filepath, "r")
                self.queue_root.notify(
                    summary_text=self.warning_message,
                    announce_list=self.policy.announcelist,
                    changes_file_object=changes_file_object,
                    logger=self.logger)
                changes_file_object.close()
            return True

        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception, e:
            # Any exception which occurs while processing an accept will
            # cause a rejection to occur. The exception is logged in the
            # reject message rather than being swallowed up.
            self.reject("%s" % e)
            # Let's log tracebacks for uncaught exceptions ...
            self.logger.error(
                'Exception while accepting:\n %s' % e, exc_info=True)
            self.do_reject(notify)
            return False

    def do_reject(self, notify=True):
        """Reject the current upload given the reason provided."""
        assert self.is_rejected, "The upload is not rejected."

        # Bail out immediately if no email is really required.
        if not notify:
            return

        # We need to check that the queue_root object has been fully
        # initialised first, because policy checks or even a code exception
        # may have caused us to bail out early and not create one.  If it
        # doesn't exist then we can create a dummy one that contains just
        # enough context to be able to generate a rejection email.  Nothing
        # will end up in the DB as the transaction will get rolled back.

        if not self.queue_root:
            self.queue_root = self._createQueueEntry()

        try:
            self.queue_root.setRejected()
        except QueueInconsistentStateError:
            # These exceptions are ignored, we want to force the rejected
            # state.
            pass

        changes_file_object = open(self.changes.filepath, "r")
        self.queue_root.notify(summary_text=self.rejection_message,
            changes_file_object=changes_file_object, logger=self.logger)
        changes_file_object.close()

    def _createQueueEntry(self):
        """Return a PackageUpload object."""
        distroseries = self.policy.distroseries
        if not distroseries:
            # Upload was probably rejected with a bad distroseries, so we
            # can create a dummy one for the purposes of a rejection email.
            assert self.is_rejected, (
                "The upload is not rejected but distroseries is None.")
            distroseries = getUtility(
                IDistributionSet)['ubuntu'].currentseries
            return distroseries.createQueueEntry(
                PackagePublishingPocket.RELEASE, self.changes.filename,
                self.changes.filecontents, distroseries.main_archive,
                self.changes.signingkey)
        else:
            return distroseries.createQueueEntry(
                self.policy.pocket, self.changes.filename,
                self.changes.filecontents, self.policy.archive,
                self.changes.signingkey)

    #
    # Inserting stuff in the database
    #

    def storeObjectsInDatabase(self):
        """Insert this nascent upload into the database."""

        # Queue entries are created in the NEW state by default; at the
        # end of this method we cope with uploads that aren't new.
        self.logger.debug("Creating queue entry")
        distroseries = self.policy.distroseries
        self.queue_root = self._createQueueEntry()

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

            # Store the related builds after verifying they were built
            # from the same source.
            for considered_build in processed_builds:
                attached_builds = [build.build.id
                                   for build in self.queue_root.builds]
                if considered_build.id in attached_builds:
                    continue
                assert (considered_build.sourcepackagerelease.id == spr.id), (
                    "Upload contains binaries of different sources.")
                self.queue_root.addBuild(considered_build)

        if not self.is_new:
            # if it is known (already overridden properly), move it to
            # ACCEPTED state automatically
            if self.policy.autoApprove(self):
                self.logger.debug("Setting it to ACCEPTED")
                self.queue_root.setAccepted()
                # If it is a pure-source upload we can further process it
                # in order to have a pending publishing record in place.
                # This change is based on discussions for bug #77853 and aims
                # to fix a deficiency on published file lookup system.
                if ((self.queue_root.sources.count() == 1) and
                    (self.queue_root.builds.count() == 0) and
                    (self.queue_root.customfiles.count() == 0)):
                    self.logger.debug("Creating PENDING publishing record.")
                    self.queue_root.realiseUpload()
                    # Do not even try to close bugs for PPA uploads
                    if self.is_ppa:
                        return
                    # Closing bugs.
                    changesfile_object = open(self.changes.filepath, 'r')
                    close_bugs_for_queue_item(
                        self.queue_root,
                        changesfile_object=changesfile_object)
                    changesfile_object.close()
            else:
                self.logger.debug("Setting it to UNAPPROVED")
                self.queue_root.setUnapproved()

    def overrideArchive(self):
        """Override the archive set on the policy as necessary.

        In some circumstances we may wish to change the archive that the
        uploaded package is placed into based on various criteria.  This
        includes decisions such as moving the package to the partner
        archive if the package's component is 'partner'.

        PPA uploads with partner files and normal uploads with a mixture
        of partner and non-partner files will be rejected.
        """

        # Get a set of the components used in this upload:
        components = set(file.component_name for file in self.changes.files)

        partner_component_name = 'partner'
        if partner_component_name in components:
            # Reject partner uploads to PPAs.
            if self.is_ppa:
                self.reject("PPA does not support partner uploads.")

            # All files in the upload must be partner if any one of them is.
            if len(components) != 1:
                self.reject("Cannot mix partner files with non-partner.")
                return

            # See if there is an archive to override with.
            distribution = self.policy.distroseries.distribution
            archive = distribution.getArchiveByComponent(
                partner_component_name
                )

            # Check for data problems:
            if not archive:
                # Don't override the archive to None here or the rest of the
                # processing will throw exceptions.
                self.reject("Partner archive for distro '%s' not found" %
                    self.policy.distroseries.distribution.name)
            else:
                # Reset the archive in the policy to the partner archive.
                self.policy.archive = archive

