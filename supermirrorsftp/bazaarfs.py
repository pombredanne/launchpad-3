# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""twisted.vfs backend for the supermirror filesystem -- implements the
hierarchy described in the SupermirrorFilesystemHierarchy spec.

Currently assumes twisted.vfs as of SVN revision 14976.
"""

__metaclass__ = type

from twisted.vfs.backends import adhoc, osfs
from twisted.vfs.ivfs import VFSError

# XXX: this belongs in twisted.vfs.
class PermissionError(VFSError):
    """The user does not have permission to perform the requested operation."""


class SFTPServerRoot(adhoc.AdhocDirectory):  # was SFTPServerForPushMirrorUser
    """For /
    
    Shows ~username and ~teamname directories for the user.
    """
    def __init__(self, avatar):
        adhoc.AdhocDirectory(self, name='/')
        self.avatar = avatar
        # Create the ~username directory
        self.putChild('~' + avatar.lpname,
                      SFTPServerUserDir(avatar, avatar.lpid))

        # Create the ~teamname directory
        for team in avatar.teams:
            self.putChild('~' + team['name'], 
                          SFTPServerUserDir(avatar, team['id'],
                                            junkAllowed=False))

    

class SFTPServerUserDir(osfs.OSDirectory):
    """For /~username
    
    Ensures subdirectories are a launchpad product name, or possibly '+junk' if
    this is not inside a team directory.

    Subdirectories on disk will be named after the numeric launchpad ID for that
    product, so that the contents will still be available if the product is
    renamed in the database.
    """
    def __init__(self, avatar, junkAllowed=True):
        osfs.OSDirectory.__init__(
            self, os.path.join(avatar.homeDirsRoot, avatar.lpid),
            name='~' + avatar.lpname)
        
        # Make this user/team's directory if it doesn't already exist.
        if not os.path.exists(self.realPath):
            self.create()
            
        self.avatar = avatar
        
    def rename(self, newName):
        raise PermissionError(
            "renaming user directory %r is not allowed." % self.name)

    def createFile(self, childName):
        raise PermissionError(
            "creating files in user directory %r is not allowed." % self.name)

    def createDirectory(self, childName):
        # Check that childName is either a product name registered in Launchpad,
        # or '+junk' (if self.junkAllowed).
        if childName == '+junk':
            if self.junkAllowed:
                productID = '+junk'
            else:
                raise PermissionError("Team directories cannot have +junk.")
        else:
            productID = self.avatar.productIDs.get(childName)
            if productID is None:
                msg = ( 
                    "Directories directly under a user directory must be named "
                    "after a product name registered in Launchpad "
                    "<https://launchpad.net>")
                if self.junkAllowed:
                    msg += ", or named '+junk'".
                else:
                    msg += "."
                raise PermissionError(msg)

        # Ok, we have a productID.  Create a directory for it.
        return osfs.createDirectory(self, productID)
                
    def remove(self):
        raise PermissionError(
            "removing user directory %r is not allowed." % self.name)

    def childDirFactory(self):
        # Subdirectories of this will be SFTPServerProductDirs
        def factory(realPath, name, parent):
            return SFTPServerProductDir(self.avatar, realPath, name, parent)
        return factory


class SFTPServerProductDir(osfs.OSDirectory):
    """For /~username/product
    
    Inside a product dir there can only be directories, which will be
    SFTPServerBranch instances.
    """
    def __init__(self, avatar, realPath, name, parent):
        osfs.OSDirectory.__init__(self, realPath, name, parent)
        self.avatar = avatar
            
    def childDirFactory(self):
        return SFTPServerBranch


class SFTPServerBranch(osfs.OSDirectory):
    """For /~username/product/branch, and below.
    
    Anything is allowed here, except for tricks like symlinks that point above
    this point.

    Can also be used for Bazaar 1.x branches.
    """

