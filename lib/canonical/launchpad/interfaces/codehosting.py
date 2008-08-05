# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Internal Codehosting API interfaces."""

__metaclass__ = type
__all__ = [
    'IBranchDetailsStorage',
    'IBranchDetailsStorageApplication',
    'IBranchFileSystem',
    'IBranchFileSystemApplication',
    ]

from zope.interface import Interface

from canonical.launchpad.webapp.interfaces import ILaunchpadApplication


class IBranchDetailsStorageApplication(ILaunchpadApplication):
    """Branch details application root."""


class IBranchDetailsStorage(Interface):
    """An interface for updating the status of branches in Launchpad.

    Published at `XXX`.
    """

    def getBranchPullQueue(branch_type):
        """Get the list of branches to be pulled by the supermirror.

        :param branch_type: One of 'HOSTED', 'MIRRORED', or 'IMPORTED'.

        :raise UnknownBranchTypeError: if the branch type is unrecognized.

        :returns: a list of (branch_id, pull_url, unique_name) triples, where
        unique_name is ~owner_name/product_name/branch_name, and product_name
        is '+junk' if there is no product associated with the branch.
        """

    def startMirroring(branchID):
        """Notify Launchpad that the given branch has started mirroring.

        The last_mirror_attempt field of the given branch record will be
        updated appropriately.

        :param branchID: The database ID of the given branch.
        :returns: True if the branch status was successfully updated.
        """

    def mirrorComplete(branchID, lastRevisionID):
        """Notify Launchpad that the branch has been successfully mirrored.

        In the Launchpad database, the last_mirrored field will be updated to
        match the last_mirror_attempt value, the mirror_failures counter will
        be reset to zero and the next_mirror_time will be set to NULL.

        :param branchID: The database ID of the given branch.
        :param lastRevisionID: The last revision ID mirrored.
        :returns: True if the branch status was successfully updated.
        """

    def mirrorFailed(branchID, reason):
        """Notify Launchpad that the branch could not be mirrored.

        The mirror_failures counter for the given branch record will be
        incremented and the next_mirror_time will be set to NULL.

        :param branchID: The database ID of the given branch.
        :param reason: A string giving the reason for the failure.
        :returns: True if the branch status was successfully updated.
        """

    def recordSuccess(name, hostname, date_started, date_completed):
        """Notify Launchpad that a mirror script has successfully completed.

        Create an entry in the ScriptActivity table with the provided data.

        :param name: Name of the script.
        :param hostname: Where the script was running.

        :param date_started: When the script started, as an UTC time tuple.
        :param date_completed: When the script completed (now), as an UTC time
            tuple.
        :returns: True if the ScriptActivity record was successfully inserted.
        """


class IBranchFileSystemApplication(ILaunchpadApplication):
    """Blah."""


class IBranchFileSystem(Interface):
    """An interface for dealing with hosted branches in Launchpad.

    Published at `...`.

    The code hosting service uses this to register branches, to retrieve
    information about a user's branches, and to update their status.
    """

    def getBranchesForUser(personID):
        """Return all branches owned by a particular user, grouped by product.

        :returns: a list like::
            [(product id, product name, [(branch id, branch name), ...]), ...]
        """

    def getBranchInformation(loginID, personName, productName, branchName):
        """Return the database ID and permissions for a branch.

        :param loginID: The login ID for the person asking for the branch
            information. This is used for branch privacy checks.
        :param personName: The owner of the branch.
        :param productName: The product that the branch belongs to. '+junk' is
            allowed.
        :param branchName: The name of the branch.

        :returns: (branch_id, permissions), where 'permissions' is 'w' if the
            user represented by 'loginID' can write to the branch, and 'r' if
            they cannot. If the branch doesn't exist, return ('', '').
        """

    def getDefaultStackedOnBranch(login_id, product_name):
        """Return the URL for the default stacked-on branch of a product.

        :param login_id: The login ID for the person asking for the branch
            information. This is used for branch privacy checks.
        :param product_name: The name of a `Product`.
        :return: An absolute path to a branch on Launchpad. If there is no
            default stacked-on branch configured, return the empty string.
        """

    def fetchProductID(productName):
        """Return the database ID for a product name.

        :returns: a product ID.
        """

    def createBranch(loginID, personName, productName, branchName):
        """Register a new hosted branch in Launchpad.

        This is called by the bazaar.launchpad.net server when a user pushes a
        new branch to it.  See also
        https://launchpad.canonical.com/SupermirrorFilesystemHierarchy.

        Note that this function raises instances of exactly
        twisted.web.xmlrpc.Fault; while raising subclasses would perhaps be
        clearer, the client side would only see a Fault, so we do that on the
        server side too for consistency.

        :param loginID: the person ID of the user creating the branch.
        :param personName: the unique name of the owner of the branch.
        :param productName: the unique name of the product that the branch
            belongs to.
        :param branchName: the name for this branch, to be used in URLs.
        :returns: the ID for the new branch.
        :raises twisted.web.xmlrpc.Fault: If the branch cannot be created.
            The faultCode will be PERMISSION_DENIED_FAULT_CODE or
            NOT_FOUND_FAULT_CODE and the faultString will be a description
            suitable to display to the user.
        """

    def requestMirror(loginID, branchID):
        """Mark a branch as needing to be mirrored.

        :param loginID: the person ID of the user requesting the mirror.
        :param branchID: a branch ID.
        """
