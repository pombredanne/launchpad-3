# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""The processing of nascent uploads.

# XXX: documentation on general design
#   - want to log all possible errors to the end-user
#   - changes file holds all uploaded files in a tree
#   - changes.files and changes.dsc
#   - DSC represents a source upload, and creates sources
#   - but DSC holds DSCUploadedFiles, weirdly
#   - binary represents a binary upload, and creates binaries
#   - source files only exist for verify() purposes
#   - NascentUpload is a motor that creates the changes file, does
#     verifications, gets overrides, triggers creation or rejection and
#     prepares the email message
"""

__metaclass__ = type

import apt_pkg

from zope.component import getUtility

from canonical.config import config
from canonical.encoding import guess as guess_encoding

from canonical.lp.dbschema import (
    PackagePublishingPocket)

from canonical.launchpad.mail import format_address
from canonical.launchpad.interfaces import (
    ISourcePackageNameSet, IBinaryPackageNameSet, ILibraryFileAliasSet,
    NotFoundError)

from canonical.archivepublisher.changesfile import ChangesFile, DSCFile
from canonical.archivepublisher.nascentuploadfile import (
    UploadError, UploadWarning, CustomUploadFile,
    SourceUploadFile, BinaryUploadFile)
from canonical.archivepublisher.template_messages import (
    rejection_template, new_template, accepted_template, announce_template)


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
    rejection_message = ""
    warnings = ""

    # Defined in check_changes_consistency()
    sourceful = False
    binaryful = False
    archindep = False
    archdep = False

    # Defined in check_sourceful_consistency()
    native = False
    hasorig = False

    def __init__(self, policy, fsroot, changes_filename, logger):
        """XXX

        May raise FatalUploadError.
        """
        self.fsroot = fsroot
        self.policy = policy
        self.logger = logger

        self.librarian = getUtility(ILibraryFileAliasSet)
        try:
            self.changes = ChangesFile(changes_filename,
                            self.fsroot, self.policy, self.logger)
        except UploadError, e:
            # We can't run reject() because unfortunately we don't have
            # the address of the uploader to notify -- we broke in that
            # exact step.
            # XXX: we should really be emailing this rejection to
            # the archive admins. For now, this will end up in the
            # script log.
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
            self.policy.setDistroReleaseAndPocket(self.changes.distrorelease_and_pocket)
        except NotFoundError:
            self.reject("Unable to find distrorelease: %s"
                        % self.changes.distrorelease_and_pocket)

        self.run_and_collect_errors(self.changes.process_files)

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
            if (isinstance(uploaded_file, CustomUploadFile) and
                not self.single_custom):
                self.reject("Mixed custom upload detected.")

        if self.single_custom:
            if len(self.changes.files) > 1:
                self.reject("More than one file detected in custom upload.")
            self.logger.debug("Single Custom Upload detected.")
            return

        # Policy checks
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

        if self.sourceful and not self.changes.dsc:
            self.reject("Unable to find the dsc file in the sourceful upload?")

        # Apply the overrides from the database. This needs to be done
        # before doing component verifications because the component
        # actually comes from overrides for packages that are not NEW.
        self.find_and_apply_overrides()

        signer_components = self.process_signer_acl()
        if not self.is_new:
            # check rights for OLD packages, the NEW ones goes straight to queue
            self.verify_acl(signer_components)

        if not self.policy.distrorelease.canUploadToPocket(self.policy.pocket):
            self.reject(
                "Not permitted to upload to the %s pocket in a "
                "release in the '%s' state." % (
                self.policy.pocket.name,
                self.policy.distrorelease.releasestatus.name))

        # That's all folks.
        self.logger.debug("Finished checking upload.")


    #
    # Minor helpers
    #

    @property
    def single_custom(self):
        """Identify single custom uploads.

        Return True if the current upload is a single custom file.
        It is necessary to identify dist-upgrade section uploads.
        """
        # XXX: I'm not sure why single_custom is important. What if two
        # custom files are uploaded at once? What should happen? I don't
        # think that is handled correctly..
        return (len(self.changes.files) == 1 and 
                isinstance(self.changes.files[0], CustomUploadFile))

    @property
    def is_new(self):
        """Return true if any portion of the upload is NEW."""
        for uploaded_file in self.changes.files:
            if uploaded_file.new:
                return True
        return False

    @property
    def sender(self):
        return "%s <%s>" % (
            config.uploader.default_sender_name,
            config.uploader.default_sender_address)

    @property
    def default_recipient(self):
        return "%s <%s>" % (config.uploader.default_recipient_name,
                         config.uploader.default_recipient_address)

    #
    # Overall consistency checks
    #

    def _check_overall_consistency(self):
        """
        XXX

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
            elif isinstance(uploaded_file, BinaryUploadFile):
                files_binaryful = files_binaryful or True
                files_archindep = files_archindep or uploaded_file.is_archindep
                files_archdep = files_archdep or not uploaded_file.is_archindep
            elif isinstance(uploaded_file, (SourceUploadFile, DSCFile)):
                files_sourceful = True
            else:
                # This is already caught in ChangesFile.__init__
                raise AssertionError()

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
        """XXX"""
        assert self.sourceful

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
        """XXX"""
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
        try:
            callable()
        except UploadError, error:
            self.reject(str(error))
        except UploadWarning, error:
            self.warn(str(error))

    def run_and_collect_errors(self, callable):
        """XXX"""
        errors = callable()
        for error in errors:
            if isinstance(error, UploadError):
                self.reject(str(error))
            elif isinstance(error, UploadWarning):
                self.warn(str(error))
            else:
                raise AssertionError

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

    @property
    def is_rejected(self):
        """Returns whether or not this upload was rejected."""
        return len(self.rejection_message) > 0

    #
    # Signature and ACL stuff
    #

    def _components_valid_for(self, person):
        """Return the set of components this person could upload to."""

        possible_components = set(acl.component.name
                                  for acl in self.policy.distro.uploaders
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

    def process_signer_acl(self):
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
            self.reject("Signer has no upload rights at all to this "
                        "distribution.")

        return possible_components

    def verify_acl(self, signer_components):
        """Verify that the uploaded files are okay for their named components
        by the provided signer.
        """
        if self.changes.signer is None:
            self.logger.debug("No signer, therefore no point verifying signer "
                              "against ACL")
            return

        for uploaded_file in self.changes.files:
            if isinstance(uploaded_file, SourceUploadFile):
                # We don't do overrides on diff/tar
                continue
            if (uploaded_file.component not in signer_components and
                uploaded_file.new == False):
                self.reject("Signer is not permitted to upload to the "
                            "component '%s' of file '%s'" % (
                    uploaded_file.component, uploaded_file.filename))

    #
    # Handling checking of versions and overrides
    #

    def _checkVersion(self, proposed_version, archive_version,
                      filename=None):
        """Check if the proposed version is higher than that in the archive."""
        if apt_pkg.VersionCompare(proposed_version, archive_version) <= 0:
            self.reject("%s: Version older than that in the archive. %s <= %s"
                        % (filename, proposed_version, archive_version))

    def _getPublishedSources(self, uploaded_file, target_pocket):
        """Return the published sources (parents) for a given file."""
        sourcename = getUtility(ISourcePackageNameSet).getOrCreateByName(
            uploaded_file.package)
        # When looking for published sources, to verify that an uploaded
        # file has a usable version number, we must consider the special
        # case of the backports pocket.
        # Across the release, security and uploads pockets, we have one
        # sequence of versions, and any new upload must have a higher
        # version than the currently highest version across these pockets.
        # Backports has its own version sequence, all higher than the
        # highest we'll ever see in other pockets. So, it's not a problem
        # that the upload is a lower version than can be found in backports,
        # unless the upload is going to backports.
        # See bug 34089.

        if target_pocket is not PackagePublishingPocket.BACKPORTS:
            exclude_pocket = PackagePublishingPocket.BACKPORTS
            pocket = None
        else:
            exclude_pocket = None
            pocket = PackagePublishingPocket.BACKPORTS

        candidates = self.policy.distrorelease.getPublishedReleases(
            sourcename, include_pending=True, pocket=pocket,
            exclude_pocket=exclude_pocket)

        return candidates

    def _getPublishedBinaries(self, uploaded_file, archtag, target_pocket):
        """Return the published binaries (parents) for given file & pocket."""
        # Look up the binary package overrides in the relevant
        # distroarchrelease
        binaryname = getUtility(IBinaryPackageNameSet).queryByName(uploaded_file.package)
        if not binaryname:
            return []

        try:
            dar = self.policy.distrorelease[archtag]
        except NotFoundError:
            self.reject(
                "%s: Unable to find arch: %s" % (uploaded_file.package,
                                                 archtag))
            return None
        # Once again, consider the special case of backports. See comment
        # in _getPublishedSources and bug 34089.
        if target_pocket is not PackagePublishingPocket.BACKPORTS:
            exclude_pocket = PackagePublishingPocket.BACKPORTS
            pocket = None
        else:
            pocket = PackagePublishingPocket.BACKPORTS
            exclude_pocket = None

        candidates = dar.getReleasedPackages(
            binaryname, include_pending=True, pocket=pocket,
            exclude_pocket=exclude_pocket)

        if not candidates:
            # Try the other architectures...
            for dar in self.policy.distrorelease.architectures:
                candidates = dar.getReleasedPackages(
                    binaryname, include_pending=True, pocket=pocket,
                    exclude_pocket=exclude_pocket)
                if candidates:
                    break

        return candidates

    def _checkSourceBackports(self, uploaded_file):
        """Reject source upload if it is newer than that in BACKPORTS.

        If the proposed source version is newer than the newest version
        of the same source in BACKPORTS, the upload will be rejected.

        It must not be called for uploads in BACKPORTS pocket itself,

        It does nothing BACKPORTS does not contain any version of the
        proposed source.
        """
        assert self.policy.pocket != PackagePublishingPocket.BACKPORTS

        backports = self._getPublishedSources(
            uploaded_file, PackagePublishingPocket.BACKPORTS)

        if not backports:
            return

        first_backport = backports[-1].sourcepackagerelease.version
        proposed_version = uploaded_file.version

        if apt_pkg.VersionCompare(proposed_version, first_backport) >= 0:
            self.reject("%s: Version newer than that in BACKPORTS. %s >= %s"
                        % (uploaded_file.package, proposed_version,
                           first_backport))


    def _checkBinaryBackports(self, uploaded_file, archtag):
        """Reject binary upload if it is newer than that in BACKPORTS.

        If the proposed binary version is newer than the newest version
        of the same binary in BACKPORTS, the upload will be rejected.

        It must not be called for uploads in BACKPORTS pocket itself,

        It does nothing BACKPORTS does not contain any version of the
        proposed binary.
        """
        assert self.policy.pocket != PackagePublishingPocket.BACKPORTS

        backports = self._getPublishedBinaries(
            uploaded_file, archtag, PackagePublishingPocket.BACKPORTS)

        if not backports:
            return

        first_backport = backports[-1].binarypackagerelease.version
        proposed_version = uploaded_file.version

        if apt_pkg.VersionCompare(proposed_version, first_backport) >= 0:
            self.reject("%s: Version newer than that in BACKPORTS. %s >= %s"
                        % (uploaded_file.package, proposed_version,
                           first_backport))

    def find_and_apply_overrides(self):
        """Look in the db for each part of the upload to see if it's overridden
        or not.

        Anything not yet in the DB gets tagged as 'new' and won't count
        towards the permission check.
        """

        self.logger.debug("Finding and applying overrides.")

        for uploaded_file in self.changes.files:
            if isinstance(uploaded_file, (CustomUploadFile, SourceUploadFile)):
                # Source files are irrelevant, being represented by the
                # DSC, and custom files don't have overrides.
                continue

            if isinstance(uploaded_file, DSCFile):
                # Look up the source package overrides in the distrorelease
                # (any pocket would be enough)
                self.logger.debug("getPublishedReleases()")

                candidates = self._getPublishedSources(
                    uploaded_file, self.policy.pocket)

                if candidates:
                    self.logger.debug("%d possible source(s)"
                                      % len(candidates))
                    self.logger.debug("%s: (source) exists" % (
                        uploaded_file.package))
                    override = candidates[0]
                    proposed_version = self.changes.version
                    archive_version = override.sourcepackagerelease.version
                    self._checkVersion(proposed_version, archive_version,
                                       filename=uploaded_file.filename)
                    uploaded_file.component = override.component.name
                    uploaded_file.section = override.section.name
                    uploaded_file.new = False
                else:
                    self.logger.debug("%s: (source) NEW" % (
                        uploaded_file.package))
                    uploaded_file.new = True

                if self.policy.pocket != PackagePublishingPocket.BACKPORTS:
                    self._checkSourceBackports(uploaded_file)

            elif isinstance(uploaded_file, BinaryUploadFile):
                # XXX: this is actually is_binary!
                self.logger.debug("getPublishedReleases()")

                archtag = uploaded_file.architecture
                if archtag == "all":
                    archtag = self.changes.filename_archtag

                self.logger.debug("Checking against %s for %s"
                                  %(archtag, uploaded_file.package))

                candidates = self._getPublishedBinaries(
                    uploaded_file, archtag, self.policy.pocket)

                if candidates:
                    self.logger.debug("%d possible binar{y,ies}"
                                      % len(candidates))
                    self.logger.debug("%s: (binary) exists" % (
                        uploaded_file.package))
                    override = candidates[0]
                    proposed_version = uploaded_file.version
                    archive_version = override.binarypackagerelease.version
                    archtag = uploaded_file.architecture
                    if archtag == "all":
                        arch_indep = self.policy.distrorelease.nominatedarchindep
                        archtag = arch_indep.architecturetag
                    if (override.distroarchrelease ==
                        self.policy.distrorelease[archtag]):
                        self._checkVersion(
                            proposed_version, archive_version,
                            filename=uploaded_file.filename)

                    uploaded_file.component = override.component.name
                    uploaded_file.section = override.section.name
                    uploaded_file.priority = override.priority
                    uploaded_file.new = False
                else:
                    self.logger.debug("%s: (binary) NEW" % (
                        uploaded_file.package))
                    uploaded_file.new = True

                if self.policy.pocket != PackagePublishingPocket.BACKPORTS:
                    self._checkBinaryBackports(uploaded_file, archtag)
            else:
                # XXX: really? pass?
                pass

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
                "SUMMARY": self.build_summary(),
                "CHANGESFILE": guess_encoding(self.changes.filecontents),
                "DISTRO": self.policy.distro.title,
                "DISTRORELEASE": self.policy.distrorelease.name,
                "ANNOUNCE": self.policy.announcelist,
                "SOURCE": self.changes.source,
                "VERSION": self.changes.version,
                "ARCH": self.changes.architecture_line,
                }
            if self.changes.signer:
                interpolations['MAINTAINERFROM'] = self.changes.changed_by['rfc2047']

            recipients = self.build_recipients()

            interpolations['RECIPIENT'] = ", ".join(recipients)
            interpolations['DEFAULT_RECIPIENT'] = self.default_recipient

            self.store_objects_in_database()

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

            # Fallback, all the rest comming from 'insecure', 'secure',
            # and 'sync' policies should send acceptance & announcement
            # messages.
            return True, [
                accept_msg % interpolations,
                announce_msg % interpolations]

        except Exception, e:
            # Any exception which occurs while processing an accept will
            # cause a rejection to occur. The exception is logged in the
            # reject message rather than being swallowed up.
            self.reject("Exception while accepting: %s" % e)
            return False, self.do_reject()

    def do_reject(self, template=rejection_template):
        """Reject the current upload given the reason provided."""
        assert self.is_rejected

        interpolations = {
            "SENDER": self.sender,
            "CHANGES": self.changes.filename,
            "SUMMARY": self.rejection_message,
            "CHANGESFILE": guess_encoding(self.changes.filecontents)
            }
        recipients = self.build_recipients()
        interpolations['RECIPIENT'] = ", ".join(recipients)
        interpolations['DEFAULT_RECIPIENT'] = self.default_recipient
        outgoing_msg = template % interpolations

        return [outgoing_msg]

    def build_recipients(self):
        """Build self.recipients up to include every address we trust."""
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
            # We should only actually send mail to people that are
            # registered Launchpad user with preferred email;
            # this is a sanity check to avoid spamming the innocent.
            # Not that we do that sort of thing.
            if person is None or person.preferredemail is None:
                self.logger.debug("Could not find a person for <%r> or that "
                                  "person has no preferred email address set "
                                  "in launchpad" % recipients)
                continue
            recipient = format_address(person.displayname,
                                       person.preferredemail.email)
            self.logger.debug("Adding recipient: '%s'" % recipient)
            valid_recipients.append(recipient)
        return valid_recipients

    def build_summary(self):
        """List the files and build a summary as needed."""
        summary = []
        for uploaded_file in self.changes.files:
            if uploaded_file.new:
                summary.append("NEW: %s" % uploaded_file.filename)
            else:
                summary.append(" OK: %s" % uploaded_file.filename)
                if isinstance(uploaded_file, DSCFile):
                    summary.append("     -> Component: %s Section: %s" % (
                        uploaded_file.component,
                        uploaded_file.section))

        return "\n".join(summary)

    #
    # Inserting stuff in the database
    #

    def store_objects_in_database(self):
        """Insert this nascent upload into the database."""

        # Queue entries are created in the NEW state by default; at the
        # end of this method we cope with uploads that aren't new.
        self.logger.debug("Creating queue entry")
        distrorelease = self.policy.distrorelease
        queue_root = distrorelease.createQueueEntry(self.policy.pocket,
            self.changes.filename, self.changes.filecontents)

        # When binaryful and sourceful, we have a mixed-mode upload.
        # Mixed-mode uploads need special handling, and the spr here is
        # short-circuited into the binary. See the docstring in
        # UBinaryUploadFile.verify_sourcepackagerelease() for details.
        spr = None
        if self.sourceful:
            assert self.changes.dsc
            spr = self.changes.dsc.store_in_database()
            queue_root.addSource(spr)

        if self.binaryful:
            if self.single_custom:
                # Finally, add any custom files.
                uploaded_file = self.changes.files[0]
                libraryfile = uploaded_file.store_in_database()
                assert isinstance(uploaded_file, CustomUploadFile)
                libraryfile = self.librarian.create(
                    uploaded_file.filename, uploaded_file.size,
                    open(uploaded_file.full_filename, "rb"),
                    uploaded_file.content_type)
                queue_root.addCustom(libraryfile, uploaded_file.custom_type)
            else:
                for binary_package_file in self.changes.binary_package_files:
                    try:
                        if self.sourceful:
                            assert self.policy.can_upload_mixed
                            assert spr
                            binary_package_file.verify_sourcepackagerelease(spr)
                        else:
                            spr = binary_package_file.find_sourcepackagerelease()
                        build = binary_package_file.find_build(spr)
                        binary_package_file.store_in_database(build)
                    except UploadError, e:
                        self.reject("Error storing binaries: %s" % e)
                        return

                    # XXX: two questions: did we mean distrorelease or
                    # pocket here, and can we assert build.pocket ==
                    # self.policy.pocket?
                    #
                    # We cannot rely on the distrorelease coming in for a binary
                    # release because it is always set to 'autobuild' by the builder.
                    # We instead have to take it from the policy which gets instructed
                    # by the buildd master during the upload.
                    queue_root.pocket = build.pocket
                    queue_root.addBuild(build)

        if not self.is_new:
            # if it is known (already overridden properly), move it to
            # ACCEPTED state automatically
            if self.policy.autoApprove(self):
                self.logger.debug("Setting it to ACCEPTED")
                queue_root.setAccepted()
            else:
                self.logger.debug("Setting it to UNAPPROVED")
                queue_root.setUnapproved()

