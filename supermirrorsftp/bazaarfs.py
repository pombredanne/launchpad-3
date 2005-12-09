# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""twisted.vfs backend for the supermirror filesystem -- implements the
hierarchy described in the SupermirrorFilesystemHierarchy spec.

Currently assumes twisted.vfs as of SVN revision 14976.
"""

__metaclass__ = type

from twisted.internet import defer
from twisted.vfs.backends import adhoc, osfs
from twisted.vfs.ivfs import VFSError, PermissionError

import os


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

        # Create directories for products that have branches
        #[(product id, product name, [(branch id, branch name), ...]), ...]
        for productID, productName, branches in avatar.branches:
            self.putChild(productName, 
                          SFTPServerProductDir(avatar, lpid, productID,
                                               productName, branches, self))

        if junkAllowed and not self.exists('+junk'):
            self.putChild('+junk',
                          SFTPServerProductDir(avatar, lpid, None, '+junk',
                                               [], self))

        self.avatar = avatar
        self.userID = lpid
        self.junkAllowed = junkAllowed
        
    def rename(self, newName):
        raise PermissionError(
            "renaming user directory %r is not allowed." % self.name)

    def createFile(self, childName):
        raise PermissionError(
            "creating files in user directory %r is not allowed." % self.name)

    def createDirectory(self, childName):
        # XXX: this returns a Deferred, but the upstream VFS code is still
        # synchronous.  Upstream needs fixing.
        assert childName != '+junk'
        # Check that childName is a product name registered in Launchpad.
        deferred = self.avatar.fetchProductID(childName)
        def cb(productID):
            if productID is None:
                msg = ( 
                    "Directories directly under a user directory must be named "
                    "after a product name registered in Launchpad "
                    "<https://launchpad.net/>")
                if self.junkAllowed:
                    msg += ", or named '+junk'."
                else:
                    msg += "."
                return defer.fail(PermissionError(msg))
            productID = str(productID)
            productDir = SFTPServerProductDir(self.avatar, self.userID,
                                              productID, childName, [],
                                              self)
            self.putChild(childName, productDir)
            return productDir
        deferred.addCallback(cb)
        return deferred

    def remove(self):
        raise PermissionError(
            "removing user directory %r is not allowed." % self.name)


class SFTPServerProductDir(adhoc.AdhocDirectory):
    """For /~username/product
    
    Inside a product dir there can only be directories, which will be
    SFTPServerBranch instances.
    """
    def __init__(self, avatar, userID, productID, productName, branches,
                 parent):
        adhoc.AdhocDirectory.__init__(self, name=productName, parent=self)
        self.avatar = avatar
        self.userID = userID
        self.productID = productID
        self.productName = productName

        # Create directories for branches in this product
        for branchID, branchName in branches:
            self.putChild(branchName,
                          SFTPServerBranch(avatar, branchID, branchName,
                                           parent))
            
    def createDirectory(self, childName):
        deferred = self.avatar.createBranch(self.userID, self.productID,
                                            childName)
        def cb(branchID):
            branchID = str(branchID)
            branchDirectory = SFTPServerBranch(self.avatar, branchID, childName,
                                               self)
            self.putChild(childName, branchDirectory)
            return branchDirectory
        return deferred.addCallback(cb)
        

class SFTPServerBranch(osfs.OSDirectory):
    """For /~username/product/branch, and below.
    
    Anything is allowed here, except for tricks like symlinks that point above
    this point.

    Can also be used for Bazaar 1.x branches.
    """
    def __init__(self, avatar, branchID, branchName, parent):
        # XXX: this snippet is duplicated in a few places...
        h = "%08x" % int(branchID)
        path = '%s/%s/%s/%s' % (h[:2], h[2:4], h[4:6], h[6:]) 
        osfs.OSDirectory.__init__(self,
            os.path.join(avatar.homeDirsRoot, path), branchName, parent)

