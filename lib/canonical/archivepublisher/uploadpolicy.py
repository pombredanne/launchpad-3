# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Policy management for the upload handler."""

__metaclass__ = type

__all__ = ["findPolicyByName", "findPolicyByOptions", "UploadPolicyError"]

from zope.component import getUtility
from canonical.launchpad.interfaces import (
    IDistributionSet, IComponentSet)

from canonical.lp.dbschema import (
    PackagePublishingPocket, DistributionReleaseStatus)

# Number of seconds in an hour (used later)
HOURS = 3600


def policy_options(optparser):
    """Add to the optparser all the options which can be used by the policy
    objects herein.
    """

    optparser.add_option("-C", "--context", action="store",
                         dest="context", metavar="CONTEXT", default="insecure",
                         help="The context in which to consider the upload.")

    optparser.add_option("-d", "--distro", action="store",
                         dest="distro", metavar="DISTRO", default="ubuntu",
                         help="Distribution to give back from")

    optparser.add_option("-r", "--release", action="store", default=None,
                         dest="distrorelease", metavar="DISTRORELEASE",
                         help="Distribution to give back from.")

    optparser.add_option("-b", "--buildid", action="store", type="int",
                         dest="buildid", metavar="BUILD",
                         help="The build ID to which to attach this upload.")

    optparser.add_option("-a", "--announce", action="store",
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

    def __init__(self):
        """Prepare a policy..."""
        self.name = 'abstract'
        self.distro = None
        self.distrorelease = None
        self.pocket = None
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
        if options.distrorelease is not None:
            self.setDistroReleaseAndPocket(options.distrorelease)

    def setDistroReleaseAndPocket(self, dr_name):
        """Set the distrorelease and pocket from the provided name."""
        if self.distrorelease is not None:
            # We never override the policy
            return
        self.distroreleasename = dr_name
        (self.distrorelease,
         self.pocket) = self.distro.getDistroReleaseAndPocket(dr_name)

    @property
    def announcelist(self):
        """Return the announcement list address."""
        announce_list = getattr(self.options, 'announcelist', None)
        if (announce_list is None and
            getattr(self, 'distrorelease', None) is not None):
            announce_list = self.distrorelease.changeslist
        return announce_list

    def considerSigner(self, signer, signingkey):
        """Consider the signer."""
        # We do nothing here but our subclasses may override us.

    def checkUpload(self, upload):
        """Mandatory policy checks on NascentUploads."""
        if not self.distrorelease.canUploadToPocket(self.pocket):
            upload.reject(
                "Not permitted to upload to the %s pocket in a "
                "release in the '%s' state." % (
                self.pocket.name, self.distrorelease.releasestatus.name))

        # all policies permit upload of a single custom
        if upload.single_custom:
            # refuses any further checks
            return
        # Currently the only check we make is that if the upload is binaryful
        # we don't allow more than one build.
        # XXX: dsilvers: 20051014: We'll want to refactor to remove this limit
        # but it's not too much of a hassle for now.
        # bug 3158
        considered_archs = [arch_name for arch_name in upload.archs
                            if not arch_name.endswith("_translations")]
        if upload.binaryful:
            max = 1
            if upload.sourceful:
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
                upload.reject("Policy permits only one build per upload.")

        # execute policy specific checks
        self.policySpecificChecks(upload)

    def policySpecificChecks(self, upload):
        """Implement any policy-specific checks in child."""
        raise NotImplemented(
            "Policy specific checks must be implemented in child policies.")

    def filterRecipients(self, upload, recipients):
        """Filter any recipients we feel we need to.

        Individual policies may override this if they see fit.

        The default is to return all the recipients unchanged.
        """
        return recipients

    def filterInterpolations(self, upload, interpolations):
        """Filter any interpolations we feel necessary.

        Individual policies may override this if they see fit.

        The default is to return all the interpolations unchanged.
        """
        return interpolations

    def getDefaultPermittedComponents(self):
        """Return the set of components this distrorelease permits.

        By default all components registered since the upload will pass
        through the 'override engine' later.
        """
        return set(
            component.name for component in getUtility(IComponentSet))

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

# XXX: dsilvers: 20051019: use the component architecture for these instead
# of reinventing the registration/finder again? bug 3373
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


    def policySpecificChecks(self, upload):
        """The insecure policy does not allow SECURITY uploads for now."""
        if self.pocket == PackagePublishingPocket.SECURITY:
            upload.reject(
                "This upload queue does not permit SECURITY uploads.")

    def autoApprove(self, upload):
        """The insecure policy only auto-approves RELEASE pocket stuff.

        Additionally, we only auto-approve if the distrorelease is not FROZEN.
        """
        if self.pocket == PackagePublishingPocket.RELEASE:
            if (self.distrorelease.releasestatus !=
                DistributionReleaseStatus.FROZEN):
                return True
        return False

AbstractUploadPolicy._registerPolicy(InsecureUploadPolicy)


class PPAUploadPolicy(AbstractUploadPolicy):
    """The insecure upload policy is used by the poppy interface."""

    def __init__(self):
        AbstractUploadPolicy.__init__(self)
        self.name = 'ppa'
        self.can_upload_binaries = False
        self.can_upload_mixed = False

    def getDefaultPermittedComponents(self):
        """Return the set of components this distrorelease permits."""
        return set(
            component.name for component in getUtility(IComponentSet))

    def policySpecificChecks(self, upload):
        """Allow the upload only if it is for the RELEASE pocket."""
        if self.pocket != PackagePublishingPocket.RELEASE:
            upload.reject(
                "PPA uploads must be for the RELEASE pocket.")

    def autoApprove(self, upload):
        """For now we'll approve everything."""
        return True

    def autoApproveNew(self, upload):
        """For now we'll approve of everything."""
        return True


# Register this as the 'insecure' policy
AbstractUploadPolicy._registerPolicy(PPAUploadPolicy)


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
        # XXX: dsilvers: 20051014: Implement this to check the buildid etc.
        # bug 3135
        pass

AbstractUploadPolicy._registerPolicy(BuildDaemonUploadPolicy)


class SyncUploadPolicy(AbstractUploadPolicy):
    """This policy is invoked when processing uploads from the sync process."""

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
        # XXX: dsilvers: 20051014: Implement this to check the sync
        # bug 3135
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


class SecurityUploadPolicy(AbstractUploadPolicy):
    """The security-upload policy allows unsigned changes and binary uploads."""

    def __init__(self):
        AbstractUploadPolicy.__init__(self)
        self.name = "security"
        self.unsigned_dsc_ok = True
        self.unsigned_changes_ok = True
        self.can_upload_mixed = False
        self.can_upload_binaries = True

    def policySpecificChecks(self, upload):
        """Deny uploads to any pocket other than the security pocket."""
        if self.pocket != PackagePublishingPocket.SECURITY:
            upload.reject(
                "Not permitted to do security upload to non SECURITY pocket")

AbstractUploadPolicy._registerPolicy(SecurityUploadPolicy)
