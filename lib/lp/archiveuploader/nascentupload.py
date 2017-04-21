# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

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

import os

import apt_pkg
from zope.component import getUtility

from lp.app.errors import NotFoundError
from lp.archiveuploader.buildinfofile import BuildInfoFile
from lp.archiveuploader.changesfile import ChangesFile
from lp.archiveuploader.dscfile import DSCFile
from lp.archiveuploader.nascentuploadfile import (
    BaseBinaryUploadFile,
    CustomUploadFile,
    DdebBinaryUploadFile,
    DebBinaryUploadFile,
    SourceUploadFile,
    UdebBinaryUploadFile,
    )
from lp.archiveuploader.utils import (
    determine_source_file_type,
    UploadError,
    UploadWarning,
    )
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.sourcepackage import SourcePackageFileType
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from lp.services.librarian.interfaces import ILibraryFileAliasSet
from lp.soyuz.adapters.overrides import (
    BinaryOverride,
    FallbackOverridePolicy,
    FromExistingOverridePolicy,
    SourceOverride,
    )
from lp.soyuz.enums import PackageUploadStatus
from lp.soyuz.interfaces.binarypackagename import IBinaryPackageNameSet
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.queue import QueueInconsistentStateError


PARTNER_COMPONENT_NAME = 'partner'


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

    # Defined if we successfully do_accept() and storeObjectsInDatabase()
    queue_root = None

    def __init__(self, changesfile, policy, logger):
        """Setup a NascentUpload for the given ChangesFile.

        :param changesfile: the ChangesFile object to be uploaded.
        :param policy: the upload policy to be used.
        :param logger: the logger to be used.
        """
        self.policy = policy
        self.logger = logger

        self.rejections = []
        self.warnings = []
        self.librarian = getUtility(ILibraryFileAliasSet)

        self.changes = changesfile

    @classmethod
    def from_changesfile_path(cls, changesfile_path, policy, logger):
        """Create a NascentUpload from the given changesfile path.

        May raise UploadError due to unrecoverable problems building
        the ChangesFile object.

        :param changesfile_path: path to the changesfile to be uploaded.
        :param policy: the upload policy to be used.
        :param logger: the logger to be used.
        """
        changesfile = ChangesFile(changesfile_path, policy, logger)
        return cls(changesfile, policy, logger)

    def process(self, build=None):
        """Process this upload, checking it against policy, loading it into
        the database if it seems okay.

        No exceptions should be raised. In a few very unlikely events, an
        UploadError will be raised and sent up to the caller. If this happens
        the caller should call the reject method and process a rejection.
        """
        policy = self.policy
        self.logger.debug("Beginning processing.")

        try:
            policy.setDistroSeriesAndPocket(self.changes.suite_name)
        except NotFoundError:
            self.reject(
                "Unable to find distroseries: %s" % self.changes.suite_name)

        if policy.redirect_warning is not None:
            self.warn(policy.redirect_warning)

        # Make sure the changes file name is well-formed.
        self.run_and_reject_on_error(self.changes.checkFileName)

        # We need to process changesfile addresses at this point because
        # we depend on an already initialized policy (distroseries
        # and pocket set) to have proper person 'creation rationale'.
        self.run_and_reject_on_error(self.changes.processAddresses)

        self.run_and_reject_on_error(self.changes.processFiles)

        for uploaded_file in self.changes.files:
            self.run_and_check_error(uploaded_file.checkNameIsTaintFree)
            self.run_and_check_error(uploaded_file.checkSizeAndCheckSum)

        # Override archive location if necessary to cope with partner
        # uploads to a primary path. We consider an upload to be
        # targeted to partner if the .changes lists any files in the
        # partner component.
        self.overrideArchive()

        self._check_overall_consistency()
        if self.sourceful:
            self._check_sourceful_consistency()
        if self.binaryful:
            self._check_binaryful_consistency()
            self.run_and_collect_errors(self._matchDDEBs)

        self.run_and_collect_errors(self.changes.verify)

        self.logger.debug("Verifying files in upload.")
        for uploaded_file in self.changes.files:
            self.run_and_collect_errors(uploaded_file.verify)

        policy.validateUploadType(self)

        if self.sourceful and not self.changes.dsc:
            self.reject("Unable to find the DSC file in the source upload.")

        # Apply the overrides from the database. This needs to be done
        # before doing component verifications because the component
        # actually comes from overrides for packages that are not NEW.
        self.find_and_apply_overrides()
        self._overrideDDEBSs()

        # Check upload rights for the signer of the upload.
        self.verify_acl(build)

        # Perform policy checks.
        policy.checkUpload(self)

        # That's all folks.
        self.logger.debug("Finished checking upload.")

    #
    # Minor helpers
    #
    @property
    def filename(self):
        """Return the changesfile name."""
        return os.path.basename(self.changesfile.filepath)

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
            elif isinstance(uploaded_file, BuildInfoFile):
                files_sourceful = (
                    files_sourceful or uploaded_file.is_sourceful)
                if uploaded_file.is_binaryful:
                    files_binaryful = files_binaryful or True
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
        Ensures a sourceful upload has exactly one DSC. All further source
        checks are performed later by the DSC.
        """
        assert self.sourceful, (
            "Source consistency check called for a non-source upload")

        dsc = len([
            file for file in self.changes.files
            if determine_source_file_type(file.filename) ==
                SourcePackageFileType.DSC])

        # It is never sane to upload more than one source at a time.
        if dsc > 1:
            self.reject("Changes file lists more than one .dsc")
        if dsc == 0:
            self.reject("Sourceful upload without a .dsc")

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

    def _matchDDEBs(self):
        """Check and link DEBs and DDEBs in the upload.

        Matches each DDEB to its corresponding DEB, adding links in both
        directions. Unmatched or duplicated DDEBs result in upload errors.

        This method is an error generator, i.e, it returns an iterator over
        all exceptions that are generated while processing all mentioned
        files.
        """
        unmatched_ddebs = {}
        for uploaded_file in self.changes.files:
            if isinstance(uploaded_file, DdebBinaryUploadFile):
                ddeb_key = (uploaded_file.package, uploaded_file.version,
                            uploaded_file.architecture)
                if ddeb_key in unmatched_ddebs:
                    yield UploadError(
                        "Duplicated debug packages: %s %s (%s)" % ddeb_key)
                else:
                    unmatched_ddebs[ddeb_key] = uploaded_file

        for uploaded_file in self.changes.files:
            is_deb = isinstance(uploaded_file, DebBinaryUploadFile)
            is_udeb = isinstance(uploaded_file, UdebBinaryUploadFile)
            is_ddeb = isinstance(uploaded_file, DdebBinaryUploadFile)
            # We need exactly a DEB or UDEB, not a DDEB.
            if (is_deb or is_udeb) and not is_ddeb:
                try:
                    matching_ddeb = unmatched_ddebs.pop(
                        (uploaded_file.package + '-dbgsym',
                         uploaded_file.version,
                         uploaded_file.architecture))
                except KeyError:
                    continue
                uploaded_file.ddeb_file = matching_ddeb
                matching_ddeb.deb_file = uploaded_file

        if len(unmatched_ddebs) > 0:
            yield UploadError(
                "Orphaned debug packages: %s" % ', '.join(
                    '%s %s (%s)' % d for d in unmatched_ddebs))

    def _overrideDDEBSs(self):
        """Make sure that any DDEBs in the upload have the same overrides
        as their counterpart DEBs.  This method needs to be called *after*
        _matchDDEBS.

        This is required so that domination can supersede both files in
        lockstep.
        """
        for uploaded_file in self.changes.files:
            if (isinstance(uploaded_file, DdebBinaryUploadFile)
                    and uploaded_file.deb_file is not None):
                self.overrideBinaryFile(uploaded_file, uploaded_file.deb_file)
    #
    # Helpers for warnings and rejections
    #

    def run_and_check_error(self, callable):
        """Run the given callable and process errors and warnings.

        UploadError(s) and UploadWarnings(s) are handled.
        """
        try:
            callable()
        except UploadError as error:
            self.reject("".join(error.args))
        except UploadWarning as error:
            self.warn("".join(error.args))

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
                self.reject("".join(error.args))
            elif isinstance(error, UploadWarning):
                self.warn("".join(error.args))
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
        return self.policy.archive.is_ppa

    def getComponents(self):
        """Return a set of components present in the uploaded files."""
        return set(file.component_name for file in self.changes.files)

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
    def verify_acl(self, build=None):
        """Check the signer's upload rights.

        The signer must have permission to upload to either the component
        or the explicit source package, or in the case of a PPA must own
        it or be in the owning team.
        """
        # Binary uploads are never checked (they come in via the security
        # policy or from the buildds) so they don't need any ACL checks --
        # this goes for PPAs as well as other archives. The only uploaded file
        # that matters is the DSC file for sources because it is the only
        # object that is overridden and created in the database.
        if self.binaryful:
            return

        # The build can have an explicit uploader, which may be different
        # from the changes file signer. (i.e in case of daily source package
        # builds)
        if build is not None:
            uploader = build.getUploader(self.changes)
        else:
            uploader = self.changes.signer

        # If we have no signer, there's no ACL we can apply.
        if uploader is None:
            self.logger.debug("No signer, therefore ACL not processed")
            return

        source_name = getUtility(
            ISourcePackageNameSet).queryByName(self.changes.dsc.package)

        rejection_reason = self.policy.archive.checkUpload(
            uploader, self.policy.distroseries, source_name,
            self.changes.dsc.component, self.policy.pocket, not self.is_new)

        if rejection_reason is not None:
            self.reject(str(rejection_reason))

    #
    # Handling checking of versions and overrides
    #
    def checkVersion(self, proposed_version, archive_version, filename):
        """Check if the proposed version is higher than the one in archive."""
        if apt_pkg.version_compare(proposed_version, archive_version) < 0:
            self.reject("%s: Version older than that in the archive. %s <= %s"
                        % (filename, proposed_version, archive_version))

    def overrideSourceFile(self, uploaded_file, override):
        """Overrides the uploaded source based on its override information.

        Override target component and section.
        """
        if override.component is not None:
            uploaded_file.component_name = override.component.name
        if override.section is not None:
            uploaded_file.section_name = override.section.name

    def overrideBinaryFile(self, uploaded_file, override):
        """Overrides the uploaded binary based on its override information.

        Override target component, section and priority.
        """
        if override.component is not None:
            uploaded_file.component_name = override.component.name
        if override.section is not None:
            uploaded_file.section_name = override.section.name
        # Both, changesfiles and nascentuploadfile local maps, reffer to
        # priority in lower-case names, but the DBSCHEMA name is upper-case.
        # That's why we need this conversion here.
        if override.priority is not None:
            uploaded_file.priority_name = override.priority.name.lower()

    def find_and_apply_overrides(self):
        """Look for ancestry and overrides information.

        Anything not yet in the DB gets tagged as 'new' and won't count
        towards the permission check.
        """
        self.logger.debug("Finding and applying overrides.")

        # Fall back to just the RELEASE pocket if there is no ancestry
        # in the given pocket. The relationships are more complicated in
        # reality, but versions can diverge between post-release pockets
        # so we can't automatically check beyond this (eg. bug #83976).
        lookup_pockets = [self.policy.pocket]
        if PackagePublishingPocket.RELEASE not in lookup_pockets:
            lookup_pockets.append(PackagePublishingPocket.RELEASE)

        check_version = True
        if self.policy.archive.is_copy:
            # Copy archives always inherit their overrides from the
            # primary archive. We don't want to perform the version
            # check in this case, as the rebuild may finish after a new
            # version exists in the primary archive.
            check_version = False

        override_policy = self.policy.archive.getOverridePolicy(
            self.policy.distroseries, self.policy.pocket)

        if check_version:
            version_policy = FallbackOverridePolicy([
                FromExistingOverridePolicy(
                    self.policy.archive, self.policy.distroseries, pocket)
                for pocket in lookup_pockets])
        else:
            version_policy = None

        for uploaded_file in self.changes.files:
            upload_component = getUtility(IComponentSet)[
                uploaded_file.component_name]
            if isinstance(uploaded_file, DSCFile):
                self.logger.debug(
                    "Checking for %s/%s source ancestry"
                    % (uploaded_file.package, uploaded_file.version))
                spn = getUtility(ISourcePackageNameSet).getOrCreateByName(
                        uploaded_file.package)
                override = override_policy.calculateSourceOverrides(
                    {spn: SourceOverride(component=upload_component)})[spn]
                if version_policy is not None:
                    ancestor = version_policy.calculateSourceOverrides(
                        {spn: SourceOverride()}).get(spn)
                    if ancestor is not None and ancestor.version is not None:
                        self.checkVersion(
                            self.changes.dsc.dsc_version, ancestor.version,
                            uploaded_file.filename)
                if override.new != False:
                    self.logger.debug(
                        "%s: (source) NEW", uploaded_file.package)
                    uploaded_file.new = True
                # XXX wgrant 2014-07-23: We want to preserve the upload
                # component for PPA uploads, so we force the component
                # to main when we create publications later. Eventually
                # we should never mutate the SPR/BPR here, and just
                # store a dict of overrides.
                if not self.policy.archive.is_ppa:
                    self.overrideSourceFile(uploaded_file, override)
            elif isinstance(uploaded_file, BaseBinaryUploadFile):
                self.logger.debug(
                    "Checking for %s/%s/%s binary ancestry"
                    % (
                        uploaded_file.package,
                        uploaded_file.version,
                        uploaded_file.architecture,
                        ))

                # If we are dealing with a DDEB, use the DEB's
                # overrides. If there's no deb_file set, don't worry
                # about it. Rejection is already guaranteed.
                if (isinstance(uploaded_file, DdebBinaryUploadFile)
                    and uploaded_file.deb_file):
                    override_name = uploaded_file.deb_file.package
                else:
                    override_name = uploaded_file.package
                bpn = getUtility(IBinaryPackageNameSet).getOrCreateByName(
                    override_name)

                if uploaded_file.architecture == "all":
                    archtag = None
                else:
                    archtag = uploaded_file.architecture

                try:
                    spph = uploaded_file.findCurrentSourcePublication()
                    source_override = SourceOverride(component=spph.component)
                except UploadError:
                    source_override = None

                override = override_policy.calculateBinaryOverrides(
                    {(bpn, archtag): BinaryOverride(
                        component=upload_component,
                        source_override=source_override)})[(bpn, archtag)]
                if version_policy is not None:
                    ancestor = version_policy.calculateBinaryOverrides(
                        {(bpn, archtag): BinaryOverride(
                            component=upload_component)}).get((bpn, archtag))
                    if ancestor is not None and ancestor.version is not None:
                        self.checkVersion(
                            uploaded_file.control_version, ancestor.version,
                            uploaded_file.filename)
                if override.new != False:
                    self.logger.debug(
                        "%s: (binary) NEW", uploaded_file.package)
                    uploaded_file.new = True
                # XXX wgrant 2014-07-23: We want to preserve the upload
                # component for PPA uploads, so we force the component
                # to main when we create publications later. Eventually
                # we should never mutate the SPR/BPR here, and just
                # store a dict of overrides.
                if not self.policy.archive.is_ppa:
                    self.overrideBinaryFile(uploaded_file, override)

    #
    # Actually processing accepted or rejected uploads -- and mailing people
    #
    def do_accept(self, notify=True, build=None):
        """Accept the upload into the queue.

        This *MAY* in extreme cases cause a database error and thus
        actually end up with a rejection being issued. This could
        occur, for example, if we have failed to validate the input
        sufficiently and something trips a database validation
        constraint.

        :param notify: True to send an email, False to not send one.
        :param build: The build associated with this upload.
        """
        if self.is_rejected:
            self.reject("Alas, someone called do_accept when we're rejected")
            self.do_reject(notify)
            return False
        try:
            self.storeObjectsInDatabase(build=build)

            # Send the email.
            # There is also a small corner case here where the DB transaction
            # may fail yet this email will be sent.  The chances of this are
            # very small, and at some point the script infrastructure will
            # only send emails when the script exits successfully.
            if notify:
                changes_file_object = open(self.changes.filepath, "r")
                self.queue_root.notify(
                    summary_text=self.warning_message,
                    changes_file_object=changes_file_object,
                    logger=self.logger)
                changes_file_object.close()
            return True

        except (SystemExit, KeyboardInterrupt):
            raise
        except QueueInconsistentStateError as e:
            # A QueueInconsistentStateError is expected if the rejection
            # is a routine rejection due to a bad package upload.
            # Log at info level so LaunchpadCronScript doesn't generate an
            # OOPS.
            func = self.logger.info
            return self._reject_with_logging(e, notify, func)
        except Exception as e:
            # Any exception which occurs while processing an accept will
            # cause a rejection to occur. The exception is logged in the
            # reject message rather than being swallowed up.
            func = self.logger.error
            return self._reject_with_logging(e, notify, func)

    def _reject_with_logging(self, error, notify, log_func):
        """Helper to reject an upload and log it using the logger function."""
        self.reject("%s" % error)
        log_func('Exception while accepting:\n %s' % error, exc_info=True)
        self.do_reject(notify)
        return False

    def do_reject(self, notify=True):
        """Reject the current upload given the reason provided."""
        assert self.is_rejected, "The upload is not rejected."

        # Bail out immediately if no email is really required.
        if not notify:
            return

        # We need to check that the queue_root object has been fully
        # initialized first, because policy checks or even a code exception
        # may have caused us to bail out early and not create one.  If it
        # doesn't exist then we can create a dummy one that contains just
        # enough context to be able to generate a rejection email.  Nothing
        # will end up in the DB as the transaction will get rolled back.

        if not self.queue_root:
            self.queue_root = self._createQueueEntry()

        with open(self.changes.filepath, "r") as changes_file_object:
            self.queue_root.notify(
                status=PackageUploadStatus.REJECTED,
                summary_text=self.rejection_message,
                changes_file_object=changes_file_object, logger=self.logger)

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
                PackagePublishingPocket.RELEASE,
                distroseries.main_archive, self.changes.filename,
                self.changes.raw_content, signing_key=self.changes.signingkey)
        else:
            return distroseries.createQueueEntry(
                self.policy.pocket, self.policy.archive,
                self.changes.filename, self.changes.raw_content,
                signing_key=self.changes.signingkey)

    #
    # Inserting stuff in the database
    #
    def storeObjectsInDatabase(self, build=None):
        """Insert this nascent upload into the database."""

        # Queue entries are created in the NEW state by default; at the
        # end of this method we cope with uploads that aren't new.
        self.logger.debug("Creating queue entry")
        self.queue_root = self._createQueueEntry()

        # When binaryful and sourceful, we have a mixed-mode upload.
        # Mixed-mode uploads need special handling, and the
        # sourcepackagerelease here is short-circuited into the binary.
        # See the docstring in
        # UBinaryUploadFile.verify_sourcepackagerelease() for details.
        sourcepackagerelease = None
        if self.sourceful:
            assert self.changes.dsc, "Sourceful upload lacks DSC."
            if build is not None:
                self.changes.dsc.checkBuild(build)
            sourcepackagerelease = self.changes.dsc.storeInDatabase(build)
            package_upload_source = self.queue_root.addSource(
                sourcepackagerelease)
            ancestry = package_upload_source.getSourceAncestryForDiffs()
            if ancestry is not None:
                to_sourcepackagerelease = ancestry.sourcepackagerelease
                diff = to_sourcepackagerelease.requestDiffTo(
                    self.queue_root.findPersonToNotify(), sourcepackagerelease)
                self.logger.debug(
                    '%s %s requested' % (
                        diff.from_source.name, diff.title))

        if self.binaryful:
            for custom_file in self.changes.custom_files:
                libraryfile = custom_file.storeInDatabase()
                self.queue_root.addCustom(
                    libraryfile, custom_file.custom_type)

            # Container for the build that will be processed.
            processed_builds = []

            # Create the BPFs referencing DDEBs last. This lets
            # storeInDatabase find and link DDEBs when creating DEBs.
            bpfs_to_create = sorted(
                self.changes.binary_package_files,
                key=lambda file: file.ddeb_file is not None)
            for binary_package_file in bpfs_to_create:
                if self.sourceful:
                    # The reason we need to do this verification
                    # so late in the game is that in the
                    # mixed-upload case we only have a
                    # sourcepackagerelease to verify here!
                    assert sourcepackagerelease, (
                        "No sourcepackagerelease was found.")
                    binary_package_file.verifySourcePackageRelease(
                        sourcepackagerelease)
                else:
                    sourcepackagerelease = (
                        binary_package_file.findSourcePackageRelease())

                # Find the build for this particular binary package file.
                if build is None:
                    bpf_build = binary_package_file.findBuild(
                        sourcepackagerelease)
                else:
                    bpf_build = build
                if bpf_build.source_package_release != sourcepackagerelease:
                    raise AssertionError(
                        "Attempt to upload binaries specifying build %s, "
                        "where they don't fit." % bpf_build.id)
                binary_package_file.checkBuild(bpf_build)
                assert self.queue_root.pocket == bpf_build.pocket, (
                    "Binary was not build for the claimed pocket.")
                binary_package_file.storeInDatabase(bpf_build)
                if (self.changes.buildinfo is not None and
                        bpf_build.buildinfo is None):
                    self.changes.buildinfo.checkBuild(bpf_build)
                    bpf_build.addBuildInfo(
                        self.changes.buildinfo.storeInDatabase())
                processed_builds.append(bpf_build)

            # Store the related builds after verifying they were built
            # from the same source.
            for considered_build in processed_builds:
                attached_builds = [build.build.id
                                   for build in self.queue_root.builds]
                if considered_build.id in attached_builds:
                    continue
                assert (considered_build.source_package_release.id ==
                        sourcepackagerelease.id), (
                    "Upload contains binaries of different sources.")
                self.queue_root.addBuild(considered_build)

        # Uploads always start in NEW. Try to autoapprove into ACCEPTED
        # if possible, otherwise just move to UNAPPROVED unless it's
        # new.
        if ((self.is_new and self.policy.autoApproveNew(self)) or
            (not self.is_new and self.policy.autoApprove(self))):
            self.queue_root.acceptFromUploader(
                self.changes.filepath, logger=self.logger)
        elif not self.is_new:
            self.logger.debug("Setting it to UNAPPROVED")
            self.queue_root.setUnapproved()

    def overrideArchive(self):
        """Override the archive set on the policy as necessary.

        In some circumstances we may wish to change the archive that the
        uploaded package is placed into based on various criteria.  This
        includes decisions such as moving the package to the partner
        archive if the package's component is 'partner'.

        Uploads with a mixture of partner and non-partner files will be
        rejected.
        """

        # Get a set of the components used in this upload:
        components = self.getComponents()

        if PARTNER_COMPONENT_NAME in components:
            # All files in the upload must be partner if any one of them is.
            if len(components) != 1:
                self.reject("Cannot mix partner files with non-partner.")
                return

            # Partner uploads to PPAs do not need an override.
            if self.is_ppa:
                return

            # XXX: JonathanLange 2009-09-16: It would be nice to use
            # ISourcePackage.get_default_archive here, since it has the same
            # logic. However, I'm not sure whether we can get a SourcePackage
            # object.

            # See if there is an archive to override with.
            distribution = self.policy.distroseries.distribution
            archive = distribution.getArchiveByComponent(
                PARTNER_COMPONENT_NAME)

            # Check for data problems:
            if not archive:
                # Don't override the archive to None here or the rest of the
                # processing will throw exceptions.
                self.reject("Partner archive for distro '%s' not found" %
                    self.policy.distroseries.distribution.name)
            else:
                # Reset the archive in the policy to the partner archive.
                self.policy.archive = archive
