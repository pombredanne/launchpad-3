# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""twisted.vfs backend for the supermirror filesystem -- implements the
hierarchy described in the SupermirrorFilesystemHierarchy spec.

Currently assumes twisted.vfs as of SVN revision 15836.
"""

__metaclass__ = type

import os

from twisted.vfs.backends import adhoc, osfs
from twisted.vfs.ivfs import NotFoundError, PermissionError


# The directories allowed directly beneath a branch directory. These are the
# directories that Bazaar creates as part of regular operation.
ALLOWED_DIRECTORIES = ('.bzr', '.bzr.backup')
FORBIDDEN_DIRECTORY_ERROR = (
    "Cannot create '%s'. Only Bazaar branches are allowed.")


class SFTPServerRoot(adhoc.AdhocDirectory):  # was SFTPServerForPushMirrorUser
    """For /

    Shows ~username and ~teamname directories for the user.
    """
    def __init__(self, avatar):
        adhoc.AdhocDirectory.__init__(self, name='/')
        self.avatar = avatar
        # Create the ~username directory
        self.putChild('~' + avatar.lpname,
                      SFTPServerUserDir(avatar, avatar.lpid, avatar.lpname,
                                        parent=self))

        # Create the ~teamname directory
        for team in avatar.teams:
            if team['name'] == avatar.lpname:
                # skip the team of just the user
                continue
            self.putChild('~' + team['name'],
                          SFTPServerUserDir(avatar, team['id'], team['name'],
                                            parent=self, junkAllowed=False))

    def createDirectory(self, childName):
        raise PermissionError(
            "Branches must be inside a person or team directory.")

    def setListenerFactory(self, factory):
        self.listenerFactory = factory


class SFTPServerUserDir(adhoc.AdhocDirectory):
    """For /~username

    Ensures subdirectories are a launchpad product name, or possibly '+junk' if
    this is not inside a team directory.

    Subdirectories on disk will be named after the numeric launchpad ID for that
    product, so that the contents will still be available if the product is
    renamed in the database.
    """
    def __init__(self, avatar, lpid, lpname, parent=None, junkAllowed=True):
        adhoc.AdhocDirectory.__init__(self, name=lpname, parent=parent)

        # Create directories for products that have branches.
        # avatar.branches[lpid] is a list of the form:
        #    [(product id, product name, [(branch id, branch name), ...]), ...]
        for productID, productName, branches in avatar.branches[lpid]:
            if productID == '':
                productID = None
            if productName == '':
                productName = '+junk'
            if productID is None:
                assert productName == '+junk', (
                    "Product ID is None should mean Name is +junk, got %r"
                    % (productName,))

            self.putChild(productName,
                          SFTPServerProductDir(avatar, lpname, productID,
                                               productName, branches, self))

        # Make sure +junk exists if this is a user dir, even if there are no
        # branches in there yet.
        if junkAllowed and not self.exists('+junk'):
            self.putChild('+junk',
                          SFTPServerProductDir(avatar, lpname, None, '+junk',
                                               [], self))

        self.avatar = avatar
        self.userID = lpid
        self.userName = lpname
        self.junkAllowed = junkAllowed

    def rename(self, newName):
        raise PermissionError(
            "renaming user directory %r is not allowed." % self.name)

    def createFile(self, childName):
        raise PermissionError(
            "creating files in user directory %r is not allowed." % self.name)

    def createDirectory(self, childName):
        # XXX AndrewBennetts 2006-02-06: this returns a Deferred, but the
        # upstream VFS code is still synchronous.  Upstream needs fixing
        # (http://twistedmatrix.com/bugs/issue1223).  Luckily upstream SFTP code
        # still does the right thing despite this, but that's not guaranteed.
        assert childName != '+junk', "+junk already exists (if it's allowed)."
        # Check that childName is a product name registered in Launchpad.
        deferred = self.avatar.fetchProductID(childName)
        def cb(productID):
            if productID is None:
                raise PermissionError(
                    "Directories directly under a user directory must be "
                    "named after a project name registered in Launchpad "
                    "<https://launchpad.net/>.")
            productID = str(productID)
            productDir = SFTPServerProductDir(
                self.avatar, self.userName, productID, childName, [], self)
            self.putChild(childName, productDir)
            return productDir
        deferred.addCallback(cb)
        return deferred

    def child(self, childName):
        try:
            return adhoc.AdhocDirectory.child(self, childName)
        except NotFoundError:
            # If '+junk' is not found, then it isn't allowed in this
            # context.
            if childName == '+junk':
                raise
        # return a placeholder for the product dir that will delay
        # looking up the product ID til the user creates a branch
        # directory.
        return SFTPServerProductDirPlaceholder(childName, self)

    def remove(self):
        raise PermissionError(
            "removing user directory %r is not allowed." % self.name)


class SFTPServerProductDir(adhoc.AdhocDirectory):
    """For /~username/product

    Inside a product dir there can only be directories, which will be
    SFTPServerBranch instances.
    """
    def __init__(self, avatar, userName, productID, productName, branches,
                 parent):
        adhoc.AdhocDirectory.__init__(self, name=productName, parent=parent)
        self.avatar = avatar
        self.userName = userName
        self.productID = productID
        self.productName = productName

        # Create directories for branches in this product
        for branchID, branchName in branches:
            self.putChild(branchName,
                          SFTPServerBranch(avatar, branchID, branchName,
                                           parent))

    def createDirectory(self, childName):
        # XXX AndrewBennetts 2006-02-06: Same comment as
        # SFTPServerUserDir.createDirectory (see
        # http://twistedmatrix.com/bugs/issue1223)
        # XXX AndrewBennetts 2006-03-01 bug=33223:
        # We should ensure that if createBranch fails for some reason
        # (e.g. invalid name),that we report a useful error to the client.
        if self.exists(childName):
            return self.child(childName)
        deferred = self.avatar.createBranch(
            self.avatar.avatarId, self.userName, self.productName, childName)
        def cb(branchID):
            branchID = str(branchID)
            branchDirectory = SFTPServerBranch(
                self.avatar, branchID, childName, self)
            self.putChild(childName, branchDirectory)
            return branchDirectory
        return deferred.addCallback(cb)


class SFTPServerProductDirPlaceholder(adhoc.AdhocDirectory):
    """A placeholder for non-existant /~username/product directories.

    This node type is intended as a placeholder for an
    SFTPServerProductDir to allow pushing Bazaar branches without the
    '--create-prefix' option.

    Directory nodes of this type appear empty.  On a createDirectory()
    call, both the product and branch directories are created.

    If the product name does not exist, then the createDirectory()
    call will fail.
    """

    def __init__(self, productName, parent):
        adhoc.AdhocDirectory.__init__(self, name=productName, parent=parent)

    def createDirectory(self, childName):
        # XXX James Henstridge 2006-08-22: Same comment as
        # SFTPServerUserDir.createDirectory (see
        # http://twistedmatrix.com/bugs/issue1223)

        # Create the real ProductDir for this product.
        # If that succeeds, create the branch directory.
        deferred = self.parent.createDirectory(self.name)
        def cb(productdir):
            return productdir.createDirectory(childName)
        return deferred.addCallback(cb)


class WriteLoggingDirectory(osfs.OSDirectory):
    """VFS directory that keeps track of whether it has been written to.

    Useful within, say, an SFTP server to see if a particular directory has
    been written to as part of a connection.
    """

    def __init__(self, flagAsDirty, path, name=None, parent=None):
        """
        Create a new WriteLoggingDirectory.

        :type flagAsDirty: callable
        :param flagAsDirty: Called when the directory is written to.

        For other parameters, see osfs.OSDirectory.
        """
        osfs.OSDirectory.__init__(self, path, name, parent)
        self._flagAsDirty = flagAsDirty

    def childFileFactory(self):
        """Return a child file which uses the same listener.

        The listener is the '_flagAsDirty' callable, set by the constructor.
        """
        def childWithListener(path, name, parent):
            return WriteLoggingFile(self._flagAsDirty, path, name, parent)
        return childWithListener

    def childDirFactory(self):
        """Return a child directory which uses the same listener.

        The listener is the '_flagAsDirty' callable, set by the constructor.
        """
        def childWithListener(path, name, parent):
            return WriteLoggingDirectory(self._flagAsDirty, path, name, parent)
        return childWithListener

    def createDirectory(self, name):
        self.touch()
        return osfs.OSDirectory.createDirectory(self, name)

    def createFile(self, name, exclusive=True):
        self.touch()
        return osfs.OSDirectory.createFile(self, name, exclusive)

    def remove(self):
        self.touch()
        osfs.OSDirectory.remove(self)

    def rename(self, newName):
        self.touch()
        osfs.OSDirectory.rename(self, newName)

    def touch(self):
        self._flagAsDirty()


class WriteLoggingFile(osfs.OSFile):
    """osfs.OSFile that keeps track of whether it has been written to.
    """

    def __init__(self, listener, path, name=None, parent=None):
        self._flagAsDirty = listener
        osfs.OSFile.__init__(self, path, name, parent)

    def open(self, flags):
        if os.O_TRUNC & flags:
            self.touch()
        osfs.OSFile.open(self, flags)

    def touch(self):
        self._flagAsDirty()

    def writeChunk(self, offset, data):
        self.touch()
        osfs.OSFile.writeChunk(self, offset, data)


class NameRestrictedWriteLoggingDirectory(WriteLoggingDirectory):
    """`WriteLoggingDirectory` that is restricted to a small list of names.

    In particular, a NameRestrictedWriteLoggingDirectory can only have one of
    the names in `ALLOWED_DIRECTORIES`.
    """

    def __init__(self, flagAsDirty, path, name=None, parent=None):
        self._checkName(name)
        WriteLoggingDirectory.__init__(self, flagAsDirty, path, name, parent)

    def _checkName(self, name):
        if name not in ALLOWED_DIRECTORIES:
            raise PermissionError(FORBIDDEN_DIRECTORY_ERROR % (name,))

    def rename(self, new_name):
        self._checkName(new_name)
        return WriteLoggingDirectory.rename(self, new_name)


class SFTPServerBranch(WriteLoggingDirectory):
    """For /~username/product/branch, and below.

    Direct children are restricted by name. See
    `NameRestrictedWriteLoggingDirectory`.
    """

    def __init__(self, avatar, branchID, branchName, parent):
        self.branchID = branchID
        # XXX AndrewBennetts 2006-02-06: this snippet is duplicated in a few
        # places, such as librarian.storage._relFileLocation and
        # supermirror_rewritemap.split_branch_id.
        h = "%08x" % int(branchID)
        path = '%s/%s/%s/%s' % (h[:2], h[2:4], h[4:6], h[6:])

        self._listener = None
        WriteLoggingDirectory.__init__(self, self._flagAsDirty,
                                       os.path.join(avatar.homeDirsRoot, path),
                                       branchName, parent)
        if not os.path.exists(self.realPath):
            os.makedirs(self.realPath)

    def childDirFactory(self):
        def childWithListener(path, name, parent):
            return NameRestrictedWriteLoggingDirectory(
                self._flagAsDirty, path, name, parent)
        return childWithListener

    def createFile(self, name, exclusive=True):
        raise PermissionError(
            "Can only create Bazaar control directories directly beneath a "
            "branch directory.")

    def remove(self):
        raise PermissionError(
            "removing branch directory %r is not allowed." % self.name)

    def _flagAsDirty(self):
        if self._listener is None:
            # Find the root object and create a listener. One parent up is the
            # product, the next is the username and the third is the root of
            # the SFTP server.

            # XXX jml 2007-02-14: This is an awkward way of finding the root.
            # Replace with something that is clearer and requires fewer
            #  comments.
            root = self.parent.parent.parent
            self._listener = root.listenerFactory(self.branchID)
        self._listener()
