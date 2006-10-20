# (c) Canonical Software Ltd. 2004-2006, all rights reserved.

__all__ = ['DiskPoolEntry', 'DiskPool', 'poolify', 'unpoolify']

import os
import tempfile
import random

from canonical.archivepublisher import HARDCODED_COMPONENT_ORDER
from canonical.librarian.utils import sha1_from_path
from canonical.launchpad.interfaces import (
    AlreadyInPool, NotInPool, NeedsSymlinkInPool, PoolFileOverwriteError)


def poolify(source, component):
    """Poolify a given source and component name."""
    if source.startswith("lib"):
        return os.path.join(component, source[:4], source)
    else:
        return os.path.join(component, source[:1], source)


def unpoolify(self, path):
    """Take a path and unpoolify it.
    
    Return a tuple of component, source, filename
    """
    p = path.split("/")
    if len(p) < 3 or len(p) > 4:
        raise ValueError("Path %s is not in a valid pool form" % path)
    if len(p) == 4:
        return p[0], p[2], p[3]
    return p[0], p[2], None


def relative_symlink(src_path, dst_path):
    """os.symlink replacement that creates relative symbolic links."""
    path_sep = os.path.sep
    src_path = os.path.normpath(src_path)
    dst_path = os.path.normpath(dst_path)
    src_path_elems = src_path.split(path_sep)
    dst_path_elems = dst_path.split(path_sep)
    if os.path.isabs(src_path):
        if not os.path.isabs(dst_path):
            dst_path = os.path.abspath(dst_path)
        common_prefix = os.path.commonprefix([src_path_elems, dst_path_elems])
        backward_elems = ['..'] * (len(dst_path_elems)-len(common_prefix)-1)
        forward_elems = src_path_elems[len(common_prefix):]
        src_path = path_sep.join(backward_elems + forward_elems)
    os.symlink(src_path, dst_path)


class _diskpool_atomicfile:
    """Simple file-like object used by the pool to atomically move into place
    a file after downloading from the librarian.

    This class is designed to solve a very specific problem encountered in
    the publisher. Namely that should the publisher crash during the process
    of publishing a file to the pool, an empty or incomplete file would be
    present in the pool. Its mere presence would fool the publisher into
    believing it had already downloaded that file to the pool, resulting
    in failures in the apt-ftparchive stage.

    By performing a rename() when the file is guaranteed to have been
    fully written to disk (after the fd.close()) we can be sure that if
    the filename is present in the pool, it is definitely complete.
    """

    def __init__(self, targetfilename, mode, rootpath="/tmp"):
        # atomicfile implements the file object interface, but it is only
        # really used (or useful) for writing binary files, which is why we
        # keep the mode constructor argument but assert it's sane below.
        if mode == "w":
            mode = "wb"
        assert mode == "wb"

        assert not os.path.exists(targetfilename)

        self.targetfilename = targetfilename
        fd, name = tempfile.mkstemp(prefix=".temp-download.", dir=rootpath)
        self.fd = os.fdopen(fd, mode)
        self.tempname = name
        self.write = self.fd.write

    def close(self):
        """Make the atomic move into place having closed the temp file."""
        self.fd.close()
        os.chmod(self.tempname, 0644)
        # Note that this will fail if the target and the temp dirs are on
        # different filesystems.
        os.rename(self.tempname, self.targetfilename)


class DiskPoolEntry:
    """Represents a fully self-aware diskpool entry for a single file."""
    def __init__(self, rootpath, source, filename, logger):
        self.rootpath = rootpath
        self.source = source
        self.filename = filename
        self.logger = logger
        self._reset()

    def _reset(self):
        """Reset internal values representing state on the disk."""
        self.file_component = ''
        self.symlink_components = set()
        self.sha1 = None

    def debug(self, *args, **kwargs):
        self.logger.debug(*args, **kwargs)
        
    def pathFor(self, component):
        """Return the path for this file in the given component."""
        return os.path.join(self.rootpath,
                            poolify(self.source, component),
                            self.filename)
        
    def scan(self):
        """Scan the disk for instances of this file."""
        self._reset()
        for component in HARDCODED_COMPONENT_ORDER:
            path = self.pathFor(component)
            if os.path.islink(path):
                self.symlink_components.add(component)
            elif os.path.isfile(path):
                assert not self.file_component
                self.file_component = component
        if self.symlink_components:
            assert self.file_component

    def makeSymlink(self, component):
        """Make a symlink to this file in the given component.

        Don't call this method unless the file already exists in another
        component.

        """
        targetpath = self.pathFor(component)
        assert not os.path.exists(targetpath)
        assert self.file_component

        sourcepath = self.pathFor(self.file_component)

        self.debug("Making symlink from %s to %s" %
                   (targetpath, sourcepath))

        dirpath = os.path.dirname(targetpath)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        relative_symlink(sourcepath, targetpath)
        self.symlink_components.add(component)

    @property
    def file_hash(self):
        """Return the SHA1 sum of this file, and cache it."""
        if not self.sha1:
            targetpath = self.pathFor(self.file_component)
            self.sha1 = sha1_from_path(targetpath)
        return self.sha1

    def checkBeforeAdd(self, component, current_sha1):
        """Performs checks before adding a file in the archive.

        Raises AlreadyInPool if the proposed file is already in the archive
        with the same content and the same location.

        Raises NeedSymlinkInPool when the proposed file is already present
        in some other path in the archive and has the same content.The
        symlink must be performed in callsite

        Raises PoolFileOverwrite if the proposed file is already present
        somewhere in the archive with a different content. This is a serious
        archive corruption and must be analysed ad hoc.

        Returns None for unknown/new files, which could be straight added into
        the archive.
        """
        # create directory component if necessary (and component is allowed).
        path = os.path.dirname(self.pathFor(component))
        if not os.path.exists(path):
            assert component in HARDCODED_COMPONENT_ORDER
            os.makedirs(path)

        if not self.file_component:
            # Early return means the file is new and can be added.
            return None

        if current_sha1 != self.file_hash:
            # we already have the same filename and their sha1sum differ.
            # raise error.
            # When the sha1sums differ at this point, a serious inconsistency
            # has been detected. This can happen, for instance, when we
            # allow people to upload two packages with the same version
            # number but different diff or original tarballs.
            # This situation will arise only if one of the upstream checks
            # fails to catch this sort of broken semantics.
            raise PoolFileOverwriteError(
                '%s != %s' % (current_sha1, self.file_hash))

        if (component != self.file_component
            and component not in self.symlink_components):
            # file is present in a different component
            raise NeedsSymlinkInPool()

        # the file is already present in the archive, in the right path and
        # has the correct content, no add is requires and the archive is safe
        raise AlreadyInPool()

    def openForAdd(self, component):
        """Open this file for adding in the pool, making dirs as needed."""
        # XXX: The division between openForAdd and checkBeforeAdd is done
        # mainly to avoid requiring the pool to know about the librarian,
        # since it would need to open, copy and close the library file
        # internally (probably as part of a checkAndOpenIfNecessary-style
        # method). This may not be the best separation and this could be
        # revisited in the future.
        #   -- kiko, 2006-06-09
        self.debug("Making new file in %s for %s/%s" %
                   (component, self.source, self.filename))

        targetpath = self.pathFor(component)

        assert not os.path.exists(targetpath)

        # This means we have never published this source package
        # name in this component before.
        if not os.path.exists(os.path.dirname(targetpath)):
            os.makedirs(os.path.dirname(targetpath))

        self.file_component = component
        return _diskpool_atomicfile(targetpath, "wb", rootpath=self.rootpath)

    def removeFile(self, component):
        """Remove a file from a given component; return bytes freed.

        This method handles three situations:

        1) Remove a symlink

        2) Remove the main file and there are no symlinks left.

        3) Remove the main file and there are symlinks left.
        """
        if not self.file_component:
            raise NotInPool()

        # Okay, it's there, if it's a symlink then we need to remove
        # it simply.
        if component in self.symlink_components:
            self.debug("Removing %s %s/%s as it is a symlink"
                       % (component, self.source, self.filename))
            # ensure we are removing a symbolic link and
            # it is published in one or more components
            link_path = self.pathFor(component)
            assert os.path.islink(link_path)
            return self._reallyRemove(component)

        assert component == self.file_component

        # It's not a symlink, this means we need to check whether we
        # have symlinks or not.
        if len(self.symlink_components) == 0:
            self.debug("Removing only instance of %s/%s from %s" %
                       (self.source, self.filename, component))
        else:
            # The target for removal is the real file, and there are symlinks
            # pointing to it. In order to avoid breakage, we need to first
            # shuffle the symlinks, so that the one we want to delete will
            # just be one of the links, and becomes safe. It doesn't matter
            # which of the current links becomes the real file here, we'll
            # tidy up later in sanitiseLinks.
            targetcomponent = iter(self.symlink_components).next()
            self._shufflesymlinks(targetcomponent)

        return self._reallyRemove(component)

    def _reallyRemove(self, component):
        """Remove file and return file size.

        Remove the file from the filesystem and from our data
        structures.
        """
        fullpath = self.pathFor(component)
        assert os.path.exists(fullpath)

        if component == self.file_component:
            # Deleting the master file is only allowed if there
            # are no symlinks left.
            assert not self.symlink_components
            self.file_component = None
        elif component in self.symlink_components:
            self.symlink_components.remove(component)

        size = os.lstat(fullpath).st_size
        os.remove(fullpath)
        return size

    def _shufflesymlinks(self, targetcomponent):
        """Shuffle the symlinks for filename so that targetcomponent contains
        the real file and the rest are symlinks to the right place..."""
        if targetcomponent == self.file_component:
            # We're already in the right place.
            return

        if targetcomponent not in self.symlink_components:
            raise ValueError(
                "Target component '%s' is not a symlink for %s" %
                             (targetcomponent, self.filename))

        self.debug("Shuffling symlinks so primary for %s is in %s" %
                   (self.filename, targetcomponent))

        # Okay, so first up, we unlink the targetcomponent symlink.
        targetpath = self.pathFor(targetcomponent)
        os.remove(targetpath)
        
        # Now we rename the source file into the target component.
        sourcepath = self.pathFor(self.file_component)

        # XXX cprov 20060526: if it fails the symlinks are severely broken
        # or maybe we are writing them wrong. It needs manual fix !
        # Nonetheless, we carry on checking other candidates.
        # Use 'find -L . -type l' on pool to find out broken symlinks
        # Normally they only can be fixed by remove the broken links and
        # run a careful (-C) publication.

        # ensure targetpath doesn't exists and  the sourcepath exists
        # before rename them.
        assert not os.path.exists(targetpath)
        assert os.path.exists(sourcepath)
        os.rename(sourcepath, targetpath)

        # XXX cprov 20060612: it may cause problems to the database, since
        # ZTM isn't handled properly in scripts/publish-distro.py. Things are
        # commited mid-procedure & bare exception is caught.

        # Update the data structures.
        self.symlink_components.add(self.file_component)
        self.symlink_components.remove(targetcomponent)
        self.file_component = targetcomponent
        
        # Now we make the symlinks on the filesystem.
        for comp in self.symlink_components:
            newpath = self.pathFor(comp)
            try:
                os.remove(newpath)
            except OSError:
                # Do nothing because it's almost certainly a not found.
                pass
            relative_symlink(targetpath, newpath)

    def shuffleSymlinks(self, preferredcomponents):
        """Ensure the real file is in the most preferred component.

        If this file is in more than one component, ensure the real
        file is in the most preferred component and the other components
        use symlinks.

        It's important that the real file be in the most preferred
        component because partial mirrors may only take a subset of
        components, and these partial mirrors must not have broken
        symlinks where they should have working files.
        
        """
        if not self.symlink_components:
            return
        
        for comp in preferredcomponents:
            if comp == self.file_component:
                # Most preferred component is already the file
                break
            if comp in self.symlink_components:
                # Most preferred component is a symlink; shuffle
                self._shufflesymlinks(comp)
                break


class DiskPool:
    """Scan a pool on the filesystem and record information about it."""

    def __init__(self, rootpath, logger):
        self.rootpath = rootpath
        if not rootpath.endswith("/"):
            self.rootpath += "/"
        self.entries = {}
        self.logger = logger

    def debug(self, *args, **kwargs):
        self.logger.debug(*args, **kwargs)

    def getEntry(self, source, file):
        """Return the entry for source and file, creating if necessary."""
        entry = self.entries.get((source, file), None)
        if entry is None:
            entry = DiskPoolEntry(self.rootpath, source, file, self.logger)
            entry.scan()
            self.entries[(source, file)] = entry
        return entry

    def pathFor(self, comp, source, file=None):
        path = os.path.join(
            self.rootpath, poolify(source, comp))
        if file:
            return os.path.join(path, file)
        return path

    def scan(self):
        pass
    
    def makeSymlink(self, component, sourcename, filename):
        return self.getEntry(sourcename, filename).makeSymlink(component)
 
    def getAndCacheFileHash(self, component, sourcename, filename):
        return self.getEntry(sourcename, filename).file_hash
    
    def checkBeforeAdd(self, component, sourcename, filename, current_sha1):
        entry = self.getEntry(sourcename, filename)
        return entry.checkBeforeAdd(component, current_sha1)

    def openForAdd(self, component, sourcename, filename):
        entry = self.getEntry(sourcename, filename)
        return entry.openForAdd(component)
    
    def removeFile(self, component, sourcename, filename):
        entry = self.getEntry(sourcename, filename)
        return entry.removeFile(component)

    def _reallyRemove(self, component, sourcename, filename):
        entry = self.getEntry(sourcename, filename)
        return entry._reallyRemove(component)

    def _shufflesymlinks(self, filename, targetcomponent):
        entry = self.getEntry(None, filename)
        return entry._shufflesymlinks(targetcomponent)

    def sanitiseLinks(self, preferredcomponents):
        for entry in self.entries.values():
            entry.shuffleSymlinks(preferredcomponents)
