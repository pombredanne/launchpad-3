# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Policy management for the upload handler."""

__metaclass__ = type

__all__ = ["findPolicyByName", "findPolicyByOptions", "UploadPolicyError"]

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    ArchivePurpose, DistroSeriesStatus, IDistributionSet,
    ILaunchpadCelebrities, PackagePublishingPocket)

# Number of seconds in an hour (used later)
HOURS = 3600


def policy_options(optparser):
    """Add to the optparser all the options which can be used by the policy
    objects herein.
    """

    optparser.add_option(
        "-C", "--context", action="store", dest="context",
        metavar="CONTEXT", default="insecure",
        help="The context in which to consider the upload.")

    optparser.add_option(
        "-d", "--distro", action="store",
        dest="distro", metavar="DISTRO", default="ubuntu",
        help="Distribution to give back from")

    optparser.add_option(
        "-s", "--series", action="store", default=None,
        dest="distroseries", metavar="DISTROSERIES",
        help="Distro series to give back from.")

    optparser.add_option(
        "-b", "--buildid", action="store", type="int",
        dest="buildid", metavar="BUILD",
        help="The build ID to which to attach this upload.")

    optparser.add_option(
        "-a", "--announce", action="store",
        dest="announcelist", metavar="ANNOUNCELIST",
        help="Override the announcement list")


class UploadPolicyError(Exception):
    """Raised when a specific policy violation occurs."""


class AbstractUploadPolicy:
    """Encapsulate the policy of an upload to a launchpad archive.

    An upload policy consists of a list of attributes which are used to
    verify an upload is permissible (e.g. whether or not there must be
    a valid signature on the .changes file). The policy also contains the
    tests themselves and they operate on NascentUpload instances in order
    to verify them.
    """

    policies = {}
    options = None

    def __init__(self):
        """Prepare a policy..."""
        self.name = 'abstract'
        self.distro = None
        self.distroseries = None
        self.pocket = None
        self.archive = None
        self.unsigned_changes_ok = False
        self.unsigned_dsc_ok = False
        self.create_people = True
        self.can_upload_source = True
        self.can_upload_binaries = True
        self.can_upload_mixed = True
        # future_time_grace is in seconds. 28800 is 8 hours
        self.future_time_grace = 8 * HOURS
        # The earliest year we accept in a deb's file's mtime
        self.earliest_year = 1984

    def setOptions(self, options):
        """Store the options for later."""
        self.options = options
        # Extract and locate the distribution though...
        self.distro = getUtility(IDistributionSet)[options.distro]
        if options.distroseries is not None:
            self.setDistroSeriesAndPocket(options.distroseries)

    def setDistroSeriesAndPocket(self, dr_name):
        """Set the distroseries and pocket from the provided name.

        It also sets self.archive to the distroseries main_archive.
        """
        if self.distroseries is not None:
            assert self.archive is not None, "Archive must be set."
            # We never override the policy
            return

        self.distroseriesname = dr_name
        (self.distroseries,
         self.pocket) = self.distro.getDistroSeriesAndPocket(dr_name)

        if self.archive is None:
            self.archive = self.distroseries.main_archive

    @property
    def announcelist(self):
        """Return the announcement list address."""
        announce_list = getattr(self.options, 'announcelist', None)
        if (announce_list is None and
            getattr(self, 'distroseries', None) is not None):
            announce_list = self.distroseries.changeslist
        return announce_list

    def checkUpload(self, upload):
        """Mandatory policy checks on NascentUploads."""
        if upload.is_ppa:
            if self.pocket != PackagePublishingPocket.RELEASE:
                upload.reject(
                    "PPA uploads must be for the RELEASE pocket.")
        elif (self.archive.purpose == ArchivePurpose.PARTNER and
              self.pocket != PackagePublishingPocket.RELEASE and
              self.pocket != PackagePublishingPocket.PROPOSED):
            # Partner uploads can only go to the release or proposed
            # pockets.
            upload.reject(
                "Partner uploads must be for the RELEASE or PROPOSED pocket.")
        else:
            # Uploads to the partner archive are allowed in any distroseries
            # state.
            # XXX julian 2005-05-29 bug=117557:
            # This is a greasy hack until bug #117557 is fixed.
            if (self.distroseries and
                self.archive.purpose != ArchivePurpose.PARTNER and
                not self.distroseries.canUploadToPocket(self.pocket)):
                upload.reject(
                    "Not permitted to upload to the %s pocket in a "
                    "series in the '%s' state." % (
                    self.pocket.name, self.distroseries.status.name))

        # reject PPA uploads by default
        self.rejectPPAUploads(upload)

        # execute policy specific checks
        self.policySpecificChecks(upload)

    def rejectPPAUploads(self, upload):
        """Reject uploads targeted to PPA.

        We will only allow it on 'insecure' and 'buildd' policy because we
        ensure the uploads are signed.
        """
        if upload.is_ppa:
            upload.reject(
                "PPA upload are not allowed in '%s' policy" % self.name)

    def policySpecificChecks(self, upload):
        """Implement any policy-specific checks in child."""
        raise NotImplemented(
            "Policy specific checks must be implemented in child policies.")

    def autoApprove(self, upload):
        """Return whether the upload should be automatically approved.

        This is called only if the upload is a recognised package; if it
        is new, autoApproveNew is used instead.
        """
        # The base policy approves of everything.
        return True

    def autoApproveNew(self, upload):
        """Return whether the NEW upload should be automatically approved."""
        return False

    @classmethod
    def _registerPolicy(cls, policy_type):
        """Register the given policy type as belonging to its given name."""
        policy_name = policy_type().name
        cls.policies[policy_name] = policy_type

    @classmethod
    def findPolicyByName(cls, policy_name):
        """Return a new policy instance for the given policy name."""
        return cls.policies[policy_name]()

    @classmethod
    def findPolicyByOptions(cls, options):
        """Return a new policy instance given the options dictionary."""
        policy = cls.policies[options.context]()
        policy.setOptions(options)
        return policy

# XXX: dsilvers 2005-10-19 bug=3373: use the component architecture for
# these instead of reinventing the registration/finder again?
# Nice shiny top-level policy finder
findPolicyByName = AbstractUploadPolicy.findPolicyByName
findPolicyByOptions = AbstractUploadPolicy.findPolicyByOptions

class InsecureUploadPolicy(AbstractUploadPolicy):
    """The insecure upload policy is used by the poppy interface."""

    def __init__(self):
        AbstractUploadPolicy.__init__(self)
        self.name = 'insecure'
        self.can_upload_binaries = False
        self.can_upload_mixed = False

    def rejectPPAUploads(self, upload):
        """Insecure policy allows PPA upload."""
        return False

    def checkSignerIsUbuntero(self, upload):
        """Reject the upload if the upload signer is not an 'ubuntero'."""
        if not upload.changes.signer.is_ubuntero:
            upload.reject(
                "PPA uploads must be signed by an 'ubuntero'.")

    def checkSignerIsBetaTester(self, upload):
        """Reject the upload if the upload signer is not a 'beta-tester'.

        For being a 'beta-tester' a person must be a valid member of
        launchpad-beta-tester team/celebrity.
        """
        beta_testers = getUtility(
            ILaunchpadCelebrities).launchpad_beta_testers
        if not upload.changes.signer.inTeam(beta_testers):
            upload.reject(
                "PPA is only allowed for members of "
                "launchpad-beta-testers team.")

    def checkArchiveSizeQuota(self, upload):
        """Reject the upload if target archive size quota will be exceeded.

        This check will reject source upload exceeding the specified archive
        size quota.
        Binary upload will be skipped to avoid unnecessary hassle dealing
        with 'failed-to-upload' builds.
        """
        # Skip the check for binary uploads.
        if upload.binaryful:
            return

        # Calculate the incoming upload total size.
        upload_size = 0
        for uploadfile in upload.changes.files:
            upload_size += uploadfile.size

        # Reject the upload if the archive size is going to exceed
        # the authorized_size.
        proposed_size = self.archive.estimated_size + upload_size
        if proposed_size > self.archive.authorized_size:
            upload.reject(
                "PPA exceeded its size limit of %s bytes. Contact a "
                "Launchpad administrator if you really need more space." % (
                self.archive.authorized_size))

    def policySpecificChecks(self, upload):
        """The insecure policy does not allow SECURITY uploads for now.

        If the upload is target to any PPA it checks if the signer is
        'ubuntero' and if it is member of 'launchpad-beta-tests'.
        """
        if upload.is_ppa:
            # XXX cprov 2007-06-13: checks for PPA uploads are not yet
            # established. We may decide for only one of the checks.
            # Either in a specific team or having a ubuntero (or similar
            # flag). This code will be revisited before releasing PPA
            # publicly.
            self.checkSignerIsUbuntero(upload)
            #self.checkSignerIsBetaTester(upload)
            self.checkArchiveSizeQuota(upload)
        else:
            if self.pocket == PackagePublishingPocket.SECURITY:
                upload.reject(
                    "This upload queue does not permit SECURITY uploads.")

    def autoApprove(self, upload):
        """The insecure policy only auto-approves RELEASE pocket stuff.

        PPA uploads are always auto-approved.
        Other uploads (to main archives) are only auto-approved if the
        distroseries is not FROZEN (note that we already performed the
        IDistroSeries.canUploadToPocket check in the checkUpload base method).
        """
        if upload.is_ppa:
            return True

        if self.pocket == PackagePublishingPocket.RELEASE:
            if (self.distroseries.status !=
                DistroSeriesStatus.FROZEN):
                return True
        return False


AbstractUploadPolicy._registerPolicy(InsecureUploadPolicy)


class BuildDaemonUploadPolicy(AbstractUploadPolicy):
    """The build daemon upload policy is invoked by the slave scanner."""

    def __init__(self):
        AbstractUploadPolicy.__init__(self)
        self.name = 'buildd'
        # We permit unsigned uploads because we trust our build daemons
        self.unsigned_changes_ok = True
        self.unsigned_dsc_ok = True
        self.can_upload_source = False
        self.can_upload_mixed = False

    def setOptions(self, options):
        AbstractUploadPolicy.setOptions(self, options)
        # We require a buildid to be provided
        if getattr(options, 'buildid', None) is None:
            raise UploadPolicyError("BuildID required for buildd context")

    def policySpecificChecks(self, upload):
        """The buildd policy should enforce that the buildid matches."""
        # XXX: dsilvers 2005-10-14 bug=3135:
        # Implement this to check the buildid etc.
        pass

    def rejectPPAUploads(self, upload):
        """Buildd policy allows PPA upload."""
        return False


AbstractUploadPolicy._registerPolicy(BuildDaemonUploadPolicy)


class SyncUploadPolicy(AbstractUploadPolicy):
    """This policy is invoked when processing sync uploads."""

    def __init__(self):
        AbstractUploadPolicy.__init__(self)
        self.name = "sync"
        # We don't require changes or dsc to be signed for syncs
        self.unsigned_changes_ok = True
        self.unsigned_dsc_ok = True
        # We don't want binaries in a sync
        self.can_upload_mixed = False
        self.can_upload_binaries = False

    def policySpecificChecks(self, upload):
        """Perform sync specific checks."""
        # XXX: dsilvers 2005-10-14 bug=3135:
        # Implement this to check the sync
        pass

AbstractUploadPolicy._registerPolicy(SyncUploadPolicy)


class AnythingGoesUploadPolicy(AbstractUploadPolicy):
    """This policy is invoked when processing uploads from the test process.

    We require a signed changes file but that's it.
    """

    def __init__(self):
        AbstractUploadPolicy.__init__(self)
        self.name = "anything"
        # We require the changes to be signed but not the dsc
        self.unsigned_dsc_ok = True

    def policySpecificChecks(self, upload):
        """Nothing, let it go."""
        pass

AbstractUploadPolicy._registerPolicy(AnythingGoesUploadPolicy)


class AbsolutelyAnythingGoesUploadPolicy(AnythingGoesUploadPolicy):
    """This policy is invoked when processing uploads from the test process.

    Absolutely everything is allowed, for when you don't want the hassle
    of dealing with inappropriate checks in tests.
    """

    def __init__(self):
        AnythingGoesUploadPolicy.__init__(self)
        self.name = "absolutely-anything"
        self.unsigned_changes_ok = True

    def policySpecificChecks(self, upload):
        """Nothing, let it go."""
        pass

AbstractUploadPolicy._registerPolicy(AbsolutelyAnythingGoesUploadPolicy)


class SecurityUploadPolicy(AbstractUploadPolicy):
    """The security-upload policy.

    It allows unsigned changes and binary uploads.
    """

    def __init__(self):
        AbstractUploadPolicy.__init__(self)
        self.name = "security"
        self.unsigned_dsc_ok = True
        self.unsigned_changes_ok = True
        self.can_upload_mixed = True
        self.can_upload_binaries = True

    def policySpecificChecks(self, upload):
        """Deny uploads to any pocket other than the security pocket."""
        if self.pocket != PackagePublishingPocket.SECURITY:
            upload.reject(
                "Not permitted to do security upload to non SECURITY pocket")

AbstractUploadPolicy._registerPolicy(SecurityUploadPolicy)
