# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
"""XML-RPC interfaces for the Authserver.

The interfaces here are purely for documentation purposes.  They describe the
XML-RPC methods published by this server.

Some terminology:
    :id: a numeric ID for a person.
    :loginID: any one of an email address, a nickname, or a numeric id for a
        person.
    :user dict: a dictionary of information about a person.  Refer to the
        interface docstrings for their contents.
"""

__all__ = [
    'IBranchDetailsStorage',
    'IHostedBranchStorage',
    'IUserDetailsStorage',
    'IUserDetailsStorageV2',
    'READ_ONLY',
    'WRITABLE'
    ]


from zope.interface import Interface


READ_ONLY = 'r'
WRITABLE = 'w'


class IUserDetailsStorage(Interface):
    """A storage for details about users.

    Published at `http://$authserver_host/`. (i.e. the root)

    Many of the methods defined here return *user dicts*.  A user dict is a
    dictionary containing:
        :id:             person id (integer, doesn't change ever)
        :displayname:    full name, for display
        :emailaddresses: list of email addresses, preferred email first, the
                         rest alphabetically sorted.
        :wikiname:       the wikiname of this user on
                         http://www.ubuntulinux.com/wiki/
        :salt:           salt of a SSHA digest, base64-encoded.
    """

    def getUser(loginID):
        """Get a user

        :param loginID: A login ID (an email address, nickname, or numeric
            person ID from a user dict).

        :returns: user dict if loginID exists, otherwise empty dict
        """

    def authUser(loginID, sshaDigestedPassword):
        """Authenticate a user

        :param loginID: A login ID, same as for getUser.
        :returns: user dict if authenticated, otherwise empty dict
        """

    def getSSHKeys(archiveName):
        """Retrieve SSH public keys for a given push mirror archive

        :param archive: an archive name.
        :returns: list of 2-tuples of (key type, key text).  This list will be
            empty if the user has no keys or does not exist.
        """


class IUserDetailsStorageV2(Interface):
    """A storage for details about users.

    Published at `http://$authserver_host/v2`.

    Many of the methods defined here return *user dicts*.  A user dict is a
    dictionary containing:
        :id:             person id (integer, doesn't change ever)
        :displayname:    full name, for display
        :emailaddresses: list of email addresses, preferred email first, the
                         rest alphabetically sorted.
        :wikiname:       the wikiname of this user on
                         http://www.ubuntulinux.com/wiki/
        :teams:          a list of team dicts for each team the user is a member
                         of (including the user themself).

    A *team dict* contains:
        :id:            team id (integer, doesn't change ever)
        :name:          nickname for the team
        :displayname:   full name of the team, for display

    Differences from version 1 (IUserDetailsStorage):
        - no salts in user dicts
        - no SSHA digests, just cleartext passwords
        - teams in user dicts.
    """

    def getUser(loginID):
        """Get a user

        :param loginID: A login ID (an email address, nickname, or numeric
            person ID from a user dict).

        :returns: user dict if loginID exists, otherwise empty dict
        """

    def authUser(loginID, password):
        """Authenticate a user

        :param loginID: A login ID, same as for getUser.
        :param password: A password, in clear text.
        :returns: user dict if authenticated, otherwise empty dict
        """

    def getSSHKeys(archiveName):
        """Retrieve SSH public keys for a given push mirror archive

        :param archive: an archive name.
        :returns: list of 2-tuples of (key type, key text).  This list will be
            empty if the user has no keys or does not exist.
        """


class IHostedBranchStorage(Interface):
    """An interface for dealing with hosted branches in Launchpad.

    Published at `http://$authserver_host/v2`.

    The sftp://bazaar.launchpad.net/ service uses this to register branches, to
    retrieve information about a user's branches, and to update their status.
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

    def fetchProductID(productName):
        """Return the database ID for a product name.

        :returns: a product ID.
        """

    def createBranch(loginID, personName, productName, branchName):
        """Register a new hosted branch in Launchpad.

        This is called by the bazaar.launchpad.net server when a user pushes a
        new branch to it.  See also
        https://launchpad.canonical.com/SupermirrorFilesystemHierarchy.

        :param loginID: the person ID of the user creating the branch.
        :param personName: the unique name of the owner of the branch.
        :param productName: the unique name of the product that the branch
            belongs to.
        :param branchName: the name for this branch, to be used in URLs.
        :returns: the ID for the new branch.
        """

    def requestMirror(branchID):
        """Mark a branch as needing to be mirrored.

        :param branchID: a branch ID.
        """


class IBranchDetailsStorage(Interface):
    """An interface for updating the status of branches in Launchpad.

    Published at `http://$authserver_host/branch`.
    """

    def getBranchPullQueue(branch_type):
        """Get the list of branches to be pulled by the supermirror.

        :param branch_type: One of 'HOSTED', 'MIRRORED', or 'IMPORTED'.

        :raise UnknownBranchTypeError: if the branch type is unrecognized.

        :returns: a list of (branch_id, pull_url, unique_name) triples, where
        unique_name is owner_name/product_name/branch_name, and product_name is
        '+junk' if there is no product associated with the branch.
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
        be reset to zero and the mirror_request_time will be set to NULL.

        :param branchID: The database ID of the given branch.
        :param lastRevisionID: The last revision ID mirrored.
        :returns: True if the branch status was successfully updated.
        """

    def mirrorFailed(branchID, reason):
        """Notify Launchpad that the branch could not be mirrored.

        The mirror_failures counter for the given branch record will be
        incremented and the mirror_request_time will be set to NULL.

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
