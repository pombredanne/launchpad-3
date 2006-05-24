# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: d20d2ded-7987-4383-b5b8-4d8cd0c857ba

__all__ = ['Poolifier', 'AlreadyInPool', 'PoolFileOverwriteError',
           'NotInPool', 'DiskPoolEntry', 'DiskPool', 'POOL_DEBIAN']

POOL_DEBIAN = object()

from sets import Set
import os
import tempfile

from canonical.launchpad.helpers import sha1_from_path

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

    def __init__(self, style = POOL_DEBIAN, component = None):
        self._style = style
        if style is not POOL_DEBIAN:
            raise ValueError, "Unknown style"
        self._component = component

    def poolify(self, source, component = None):
        """Poolify a given source and component name. If the component is
        not supplied, the default set with the component() call is used.
        if that has not been supplied then an error is raised"""

        if component is None:
            component = self._component
        if component is None:
            raise ValueError, "poolify needs a component"

        if self._style is POOL_DEBIAN:
            if source.startswith("lib"):
                return "%s/%s/%s" % (component,source[:4],source)
            else:
                return "%s/%s/%s" % (component,source[:1],source)

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
        if mode == "w":
            mode = "wb"
        assert mode == "wb"
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


class PoolPredicatedViolation(Exception):
    """An attempt was made to do something the pool doesn't allow.

    Base class for exceptions raised where the action would violate
    a predicate of the pool's design.
    """


class AlreadyInPool(PoolPredicatedViolation):
    """File is already in the pool with the same content.

    No further action required
    """


class NeedsSymlinkInPool(PoolPredicatedViolation):
    """Symbolic link is required to publish the file in pool.

    File is already present in pool with the same content, but
    in other location (different component, most of the cases)
    Callsite must explicitly call diskpool.makeSymlink(..) method
    in order to publish the file in the new location.
    """


class NotInPool(Exception):
    """Raised when an attempt is made to remove a non-existent file."""


class PoolFileOverwriteError(Exception):
    """Raised when an attempt is made to overwrite a file in the pool.

    The proposed file has different content as the one in pool.
    This exception is unexpected and when it happens we keep the original
    file in pool and prints a warning in the publisher log. It probably
    requires manual intervention in the archive.
    """


class DiskPoolEntry:
    def __init__(self, source=''):
        self.defcomp = ''
        self.comps = Set()
        self.source = source
        self.sha1 = None

class DiskPool:
    """Scan a pool on the filesystem and record information about it."""

    def __init__(self, poolifier, rootpath, logger):
        self.poolifier = poolifier
        self.rootpath = rootpath
        if not rootpath.endswith("/"):
            self.rootpath += "/"
        self.components={}
        self.files={}
        self.logger = logger

    def debug(self, *args, **kwargs):
        self.logger.debug(*args,**kwargs)

    def pathFor(self, comp, source, file=None):
        if file:
            return os.path.join(
                self.rootpath, self.poolifier.poolify(source, comp), file)
        return os.path.join(
            self.rootpath,self.poolifier.poolify(source, comp))

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
            C = self.components.setdefault(component,{})
            for f in filenames:
                C[f] = os.path.islink(os.path.join(dirpath,f))
                F = self.files.setdefault(f,DiskPoolEntry(source))
                if not C[f]:
                    self.debug("Recorded primary component for %s" % f)
                    F.defcomp = component
                else:
                    self.debug("Recorded secondary component for %s" % f)
                    F.comps.add(component)
        # Now two data structures are filled
        # components is a dict of component -> dict of filename -> islink
        # files is a dict of filename -> list of main component and list of
        # the components which contain links

    def makeSymlink(self, component, sourcename, filename):
        """Create a symbolic link in the archive.

        This method also updates the internal representation of the
        archive files.
        """
        targetpath = self.pathFor(component, sourcename, filename)
        pool_file = self.files[filename]
        sourcepath = self.pathFor(pool_file.defcomp, sourcename, filename)

        self.debug("Making symlink from %s to %s" %
                   (targetpath, sourcepath))

        if not os.path.exists(os.path.dirname(targetpath)):
            os.makedirs(os.path.dirname(targetpath))

        relative_symlink(sourcepath, targetpath)
        pool_file.comps.add(component)
        self.components[component][filename] = True

    def getAndCacheFileHash(self, component, sourcename, filename):
        """Return the SHA1 sum of the requested archive file.

        It also updates its value in the internal cache.
        """
        pool_file = self.files[filename]

        if not pool_file.sha1:
            targetpath = self.pathFor(component, sourcename, filename)
            pool_file.sha1 = sha1_from_path(targetpath)
        return pool_file.sha1

    def checkBeforeAdd(self, component, sourcename, filename, current_sha1):
        """Performs checks before add a file in the archive.

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
        # it can add not allowed directories in the pool if something
        # went wrong in the upload checks. We certainly can find a better
        # way to have safe directories creation and a consistent data
        # structure

        # create directory component if necessary
        path = self.pathFor(component, sourcename)
        if not os.path.exists(path):
            os.makedirs(path)
        # pre-built self.components data structure
        self.components.setdefault(component,{})


        if filename not in self.files:
            # Early return means the file is new and can be added.
            return None

        pool_file = self.files[filename]

        pool_sha1 = self.getAndCacheFileHash(
            pool_file.defcomp, sourcename, filename)

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

        if filename not in self.components[component]:
            # file is present, but it's in some other path (component)
            # let's check the content of the proposed and the original files.
            if current_sha1 != pool_sha1:
                # Same situation as above, if it happens we should refuse
                # to publish the file and look back to it's history and find
                # where the upload checks have been failed
                raise PoolFileOverwriteError(
                    '%s != %s' % (current_sha1, pool_sha1))
            # the contents do match, so request a symbolic link creation.
            raise NeedsSymlinkInPool()

        # the file is already present in the archive, in the right path and
        # has the correct content, no add is requires and the archive is safe
        raise AlreadyInPool()

    def openForAdd(self, component, sourcename, filename):
        """Open filename for adding in the pool, making dirs as needed.

        Raises AlreadyInPool if the file is already there.
        """
        self.debug("Making new file in %s for %s/%s" %
                   (component, sourcename, filename))

        targetpath = self.pathFor(component, sourcename, filename)
        if not os.path.exists(os.path.dirname(targetpath)):
            os.makedirs(os.path.dirname(targetpath))

        self.components[component][filename] = False
        self.files[filename] = DiskPoolEntry(sourcename)
        self.files[filename].defcomp = component
        return _diskpool_atomicfile(targetpath, "wb", rootpath=self.rootpath)

    def removeFile(self, component, sourcename, filename):
        """Remove a file from a given component.
        """
        if filename not in self.components[component]:
            raise NotInPool()
        # Okay, it's there, if it's a symlink then we need to remove
        # it simply.
        if self.components[component][filename]:
            self.debug("Removing %s %s/%s as it is a symlink" %
                       (component, sourcename, filename))
            os.remove(self.pathFor(component, sourcename, filename))
            # remove it from the component
            self.components[component].pop(filename)
            # remove the component from the symlink set
            self.files[filename].comps.remove(component)
            return
        # It's not a symlink, this means we need to check.
        if len(self.files[filename].comps) == 0:
            self.debug("Removing only instance of %s/%s from %s" %
                       (sourcename, filename, component))
            # It's the only instance...
            os.remove(self.pathFor(component, sourcename, filename))
            # Remove it from the component
            self.components[component].pop(filename)
            # Remove it from the file list
            self.files.pop(filename)
            return
        # It is not a symlink and it's not the only entry for it
        # We have to shuffle the symlinks around
        comps = self.files[filename].comps
        targetcomponent = comps.pop()
        comps.add(targetcomponent)
        self._shufflesymlinks(filename, targetcomponent)
        # And now it's not the primary component any more.
        self.removeFile(component, sourcename, filename)

    def _shufflesymlinks(self, filename, targetcomponent):
        """Shuffle the symlinks for filename so that targetcomponent contains
        the real file and the rest are symlinks to the right place..."""
        self.debug("Shuffling symlinks so primary for %s is in %s" %
                   (filename, targetcomponent))
        if targetcomponent == self.files[filename].defcomp:
            # Nothing to do, it's already the primary component
            return
        if targetcomponent not in self.files[filename].comps:
            raise ValueError("Target component %s not in set of %s" %
                             (targetcomponent,filename))
        # Okay, so first up, we unlink the targetcomponent symlink
        targetpath=self.pathFor(targetcomponent, self.files[filename].source,
                                 filename)
        os.remove(targetpath)
        # Now we rename the source file into the target component
        os.rename(self.pathFor(self.files[filename].defcomp,
                                self.files[filename].source,
                                filename),
                  targetpath)
        # Update the data structures...
        self.components[self.files[filename].defcomp][filename] = True
        self.components[targetcomponent][filename] = False
        self.files[filename].comps.add(self.files[filename].defcomp)
        self.files[filename].defcomp = targetcomponent
        self.files[filename].comps.remove(targetcomponent)
        # Now we make the symlinks on the FS...
        for comp in self.files[filename].comps:
            newpath = self.pathFor(comp, self.files[filename].source, filename)
            try:
                os.remove(newpath)
            except OSError:
                # Do nothing because it's almost certainly a not found
                pass
            relative_symlink(targetpath, newpath)

    def sanitiseLinks(self, preferredcomponents):
        """Go through the files and ensure that wherever a file is in more
        than one component it ends up with the real file in the preferred
        component and every other component uses a symlink to the right
        place."""
        self.debug("Sanitising symlinks according %r" % preferredcomponents)

        for f in self.files:
            smallest = len(preferredcomponents)+1
            if self.files[f].defcomp in preferredcomponents:
                smallest = preferredcomponents.index(self.files[f].defcomp)
            for comp in self.files[f].comps:
                try:
                    if preferredcomponents.index(comp) < smallest:
                        smallest = preferredcomponents.index(comp)
                except ValueError:
                    pass # Value not in list basically

            if smallest < len(preferredcomponents):
                self._shufflesymlinks(f, preferredcomponents[smallest])

