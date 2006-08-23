# (c) Canonical Software Ltd. 2004-2006, all rights reserved.

__all__ = ['Poolifier', 'DiskPoolEntry', 'DiskPool', 'POOL_DEBIAN']

POOL_DEBIAN = object()

import os
import tempfile
import random

from canonical.librarian.utils import sha1_from_path
from canonical.launchpad.interfaces import (
    AlreadyInPool, NotInPool, NeedsSymlinkInPool, PoolFileOverwriteError)


class Poolifier(object):
    """The Poolifier takes a (source name, component) tuple and tells you
    where in the pool it should live.

    E.g.

    Source: mozilla-thunderbird
    Component: main
    Location: main/m/mozilla-thunderbird

    Source: libglib2.0
    Component: main
    Location: main/libg/libglib2.0
    """

    def __init__(self, style=POOL_DEBIAN, component=None):
        self._style = style
        if style is not POOL_DEBIAN:
            raise ValueError, "Unknown style"
        self._component = component

    def poolify(self, source, component=None):
        """Poolify a given source and component name. If the component is
        not supplied, the default set with the component() call is used.
        if that has not been supplied then an error is raised"""

        if component is None:
            component = self._component
        if component is None:
            raise ValueError, "poolify needs a component"

        if self._style is POOL_DEBIAN:
            if source.startswith("lib"):
                return "%s/%s/%s" % (component, source[:4], source)
            else:
                return "%s/%s/%s" % (component, source[:1], source)

    def component(self, component):
        """Set the default component for the poolify call"""
        self._component = component

    def unpoolify(self, path):
        """Take a path and unpoolify it.

        Return a tuple of component, source, filename
        """
        if self._style is POOL_DEBIAN:
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
        # XXX: dsilvers: 20060315: Note that os.path.commonprefix does not
        # require that the common prefix be full path elements. As a result
        # the common prefix of /foo/bar/baz and /foo/barbaz is /foo/bar.
        # This isn't an issue here in the pool code but it could be a
        # problem if this code is transplanted elsewhere.
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
    def __init__(self, source=''):
        self.defcomp = ''
        self.comps = set()
        self.source = source
        self.sha1 = None

class DiskPool:
    """Scan a pool on the filesystem and record information about it."""

    def __init__(self, poolifier, rootpath, logger):
        self.poolifier = poolifier
        self.rootpath = rootpath
        if not rootpath.endswith("/"):
            self.rootpath += "/"
        self.files_in_components = {}
        self.pool_entries = {}
        self.logger = logger

    def debug(self, *args, **kwargs):
        self.logger.debug(*args, **kwargs)

    def pathFor(self, comp, source, file=None):
        path = os.path.join(
            self.rootpath, self.poolifier.poolify(source, comp))
        if file:
            return os.path.join(path, file)
        return path

    def scan(self):
        """Scan the filesystem and build the internal representation ready
        for manipulation later."""
        self.debug("Beginning scan of pool in %s" % self.rootpath)
        for dirpath, dirnames, filenames in os.walk(self.rootpath):
            # We're only interested in files, if there's no file
            # then carry on.
            if len(filenames) == 0:
                continue
            subpath = dirpath[len(self.rootpath):]
            self.debug("Considering files in %s" % subpath)
            component, source, ignored = self.poolifier.unpoolify(subpath)
            files_in_component = self.files_in_components.setdefault(
                component, {})
            for filename in filenames:
                files_in_component[filename] = os.path.islink(
                    os.path.join(dirpath, filename))
                pool_entry = self.pool_entries.setdefault(
                    filename, DiskPoolEntry(source))
                if not files_in_component[filename]:
                    self.debug(
                        "Recorded primary component for %s" % filename)
                    pool_entry.defcomp = component
                else:
                    self.debug(
                        "Recorded secondary component for %s" % filename)
                    pool_entry.comps.add(component)
        # Now two data structures are filled
        # files_in_components is a dict of:
        #
        #    component -> dict of filename -> islink
        #
        # pool_entries is a dict of:
        #
        #    filename -> DiskPoolEntry

    def makeSymlink(self, component, sourcename, filename):
        """Create a symbolic link in the archive.

        This method also updates the internal representation of the
        archive files.
        """
        targetpath = self.pathFor(component, sourcename, filename)

        assert not os.path.exists(targetpath)
        assert filename in self.pool_entries

        pool_entry = self.pool_entries[filename]
        sourcepath = self.pathFor(pool_entry.defcomp, sourcename, filename)

        self.debug("Making symlink from %s to %s" %
                   (targetpath, sourcepath))

        dirpath = os.path.dirname(targetpath)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        relative_symlink(sourcepath, targetpath)
        pool_entry.comps.add(component)
        self.files_in_components[component][filename] = True

    def getAndCacheFileHash(self, component, sourcename, filename):
        """Return the SHA1 sum of the requested archive file.

        It also updates its value in the internal cache.
        """
        pool_entry = self.pool_entries[filename]

        if not pool_entry.sha1:
            targetpath = self.pathFor(component, sourcename, filename)
            pool_entry.sha1 = sha1_from_path(targetpath)
        return pool_entry.sha1

    def checkBeforeAdd(self, component, sourcename, filename, current_sha1):
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
        # XXX cprov 20060524: This piece of code is dangerous, because
        # it can add forbidden directories in the pool if something
        # went wrong in the upload checks, as new component directory
        # for the 'non-free' debian section. We certainly can find a better
        # way to have safe directories creation and a consistent data
        # structure. My point is, this code should not be necessary at this
        # point of the procedure.

        # create directory component if necessary
        path = self.pathFor(component, sourcename)
        if not os.path.exists(path):
            os.makedirs(path)

        # end of XXX

        # pre-built self.files_in_components data structure
        self.files_in_components.setdefault(component, {})

        if filename not in self.pool_entries:
            # Early return means the file is new and can be added.
            return None

        pool_entry = self.pool_entries[filename]

        pool_sha1 = self.getAndCacheFileHash(
            pool_entry.defcomp, sourcename, filename)

        if current_sha1 != pool_sha1:
            # we already have the same filename in the same path (component)
            # and their sha1sum differ. raise error.
            # When the sha1sums differ at this point, a serious inconsistency
            # has been detected. This can happen, for instance, when we
            # allow people to upload two packages with the same version
            # number but different diff or original tarballs.
            # This situation will arise only if one of the upstream checks
            # fails to catch this sort of broken semantics.
            raise PoolFileOverwriteError(
                '%s != %s' % (current_sha1, pool_sha1))

        if filename not in self.files_in_components[component]:
            # file is present, but it's in some other path (component)
            raise NeedsSymlinkInPool()

        # the file is already present in the archive, in the right path and
        # has the correct content, no add is requires and the archive is safe
        raise AlreadyInPool()

    def openForAdd(self, component, sourcename, filename):
        """Open filename for adding in the pool, making dirs as needed.

        Raises AlreadyInPool if the file is already there.
        """
        # XXX: The division between openForAdd and checkBeforeAdd is done
        # mainly to avoid requiring the pool to know about the librarian,
        # since it would need to open, copy and close the library file
        # internally (probably as part of a checkAndOpenIfNecessary-style
        # method). This may not be the best separation and this could be
        # revisited in the future.
        #   -- kiko, 2006-06-09
        self.debug("Making new file in %s for %s/%s" %
                   (component, sourcename, filename))

        targetpath = self.pathFor(component, sourcename, filename)

        assert not os.path.exists(targetpath)

        # This means we have never published this source or binary package
        # name before.
        if not os.path.exists(os.path.dirname(targetpath)):
            os.makedirs(os.path.dirname(targetpath))

        self.files_in_components[component][filename] = False
        self.pool_entries[filename] = DiskPoolEntry(sourcename)
        self.pool_entries[filename].defcomp = component
        return _diskpool_atomicfile(targetpath, "wb", rootpath=self.rootpath)

    def removeFile(self, component, sourcename, filename):
        """Remove a file from a given component; return bytes freed.

        This method handles three situations:

        1) We request to remove a symlink

        2) We request to remove the main file and there are no
           symlinks left.

        3) We request to remove the main file and there are symlinks
           left.
        """
        files_in_component = self.files_in_components[component]

        if filename not in files_in_component:
            raise NotInPool()

        # Okay, it's there, if it's a symlink then we need to remove
        # it simply.
        pool_entry = self.pool_entries[filename]
        is_symlink = files_in_component[filename]
        if is_symlink:
            self.debug("Removing %s %s/%s as it is a symlink"
                       % (component, sourcename, filename))
            # ensure we are removing a symbolic link and
            # it is published in one or more components
            link_path = self.pathFor(component, sourcename, filename)
            assert os.path.islink(link_path)
            assert len(pool_entry.comps) > 1
            # XXX cprov 20060612: since _reallyRemove deletes the
            # pool_entries information to a filename, it's impossible
            # to remove two symlinks for a publication in the sane run.
            # To do this currently we need to rebuild data model calling
            # self.scan().
            self._reallyRemove(component, sourcename, filename)
            return

        assert component == pool_entry.defcomp

        # It's not a symlink, this means we need to check.
        if len(pool_entry.comps) == 0:
            self.debug("Removing only instance of %s/%s from %s" %
                       (sourcename, filename, component))
        else:
            # The target for removal is the real file, and there are symlinks
            # pointing to it. In order to avoid breakage, we need to first
            # shuffle the symlinks, so that the one we want to delete will
            # just be one of the links, and becomes safe. It doesn't matter
            # which of the current links becomes the real file here, we'll
            # tidy up later in sanitiseLinks.
            targetcomponent = iter(pool_entry.comps).next()
            self._shufflesymlinks(filename, targetcomponent)

        return self._reallyRemove(component, sourcename, filename)

    def _reallyRemove(self, component, sourcename, filename):
        """Remove file and return file size.

        Remove the file from the filesystem and from DiskPool's data
        structures.
        """
        fullpath = self.pathFor(component, sourcename, filename)
        assert os.path.exists(fullpath)

        pool_entry = self.pool_entries[filename]
        self.files_in_components[component].pop(filename)

        if not pool_entry.comps:
            # This file is going away; we just removed its last copy
            assert component == pool_entry.defcomp
            self.pool_entries.pop(filename)
        else:
            # We're just removing a symlink
            pool_entry.comps.remove(component)

        size = os.lstat(fullpath).st_size
        os.remove(fullpath)
        return size

    def _shufflesymlinks(self, filename, targetcomponent):
        """Shuffle the symlinks for filename so that targetcomponent contains
        the real file and the rest are symlinks to the right place..."""
        if targetcomponent == self.pool_entries[filename].defcomp:
            # We're already in the right place.
            return

        if targetcomponent not in self.pool_entries[filename].comps:
            raise ValueError(
                "Target component '%s' is not in set of components for %s" %
                             (targetcomponent, filename))

        self.debug("Shuffling symlinks so primary for %s is in %s" %
                   (filename, targetcomponent))

        # Okay, so first up, we unlink the targetcomponent symlink.
        targetpath = self.pathFor(
            targetcomponent, self.pool_entries[filename].source, filename)
        os.remove(targetpath)
        
        # Now we rename the source file into the target component.
        sourcepath = self.pathFor(
            self.pool_entries[filename].defcomp,
            self.pool_entries[filename].source,
            filename)

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
        # ZTM isn't handled propperly scripts/publish-distro.py. Things are
        # commited mid-procedure & bare exception is caught.

        # Update the data structures...
        self.files_in_components[
            self.pool_entries[filename].defcomp][filename] = True
        self.files_in_components[targetcomponent][filename] = False
        self.pool_entries[filename].comps.add(
            self.pool_entries[filename].defcomp)
        self.pool_entries[filename].defcomp = targetcomponent
        self.pool_entries[filename].comps.remove(targetcomponent)
        # Now we make the symlinks on the FS...
        for comp in self.pool_entries[filename].comps:
            newpath = self.pathFor(
                comp, self.pool_entries[filename].source, filename)
            try:
                os.remove(newpath)
            except OSError:
                # Do nothing because it's almost certainly a not found.
                pass
            relative_symlink(targetpath, newpath)

    def sanitiseLinks(self, preferredcomponents):
        """Ensure real files are in most preferred components.

        Go through the files and ensure that wherever a file is in more
        than one component it ends up with the real file in the most
        preferred component and every other component uses a symlink to
        that one.

        It's important that the real files be in the most preferred
        components because partial mirrors may only take a subset of
        components, and these partial mirrors must not have broken
        symlinks where they should have working files.
        
        """
        self.debug("Sanitising symlinks according to %r" % (
            preferredcomponents))

        for filename, pool_entry in self.pool_entries.items():
            if not pool_entry.comps:
                # There are no symlink components in this item, skip it.
                continue
            
            for comp in preferredcomponents:
                if comp == pool_entry.defcomp:
                    # Most preferred component is already the file
                    break
                if comp in pool_entry.comps:
                    # Most preferred component is a symlink; shuffle
                    self._shufflesymlinks(filename, comp)
                    break
