# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: d20d2ded-7987-4383-b5b8-4d8cd0c857ba

__all__ = ['Poolifier', 'AlreadyInPool', 'NotInPool', 'DiskPoolEntry',
           'DiskPool', 'POOL_DEBIAN']

POOL_DEBIAN = object()

from sets import Set
import os

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
        """Take a path and unpoolify it, returning a tuple of
        component,source,leafname"""
        if self._style is POOL_DEBIAN:
            p = path.split("/")
            if len(p) < 3 or len(p) > 4:
                raise ValueError("Path %s is not in a valid pool form" % path)
            if len(p) == 4:
                return p[0], p[2], p[3]
            return p[0], p[2], None

class AlreadyInPool:
    """Raised when an attempt is made to add a file already in the pool."""

class NotInPool:
    """Raised when an attempt is made to remove a non-existent file."""

class DiskPoolEntry:
    def __init__(self, source=''):
        self.defcomp = ''
        self.comps = Set()
        self.source = source

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

    def pathFor(self, comp, source, leaf = None):
        if leaf:
            return os.path.join(self.rootpath,
                                self.poolifier.poolify(source, comp),
                                leaf)
        return os.path.join(self.rootpath,
                            self.poolifier.poolify(source, comp))

    def _checkpath(self, component, source):
        """Ensure that the path exists for this source in this component."""
        p = self.pathFor(component,source)
        if not os.path.exists(p):
            os.makedirs(p)
        self.components.setdefault(component,{})

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

    def openForAdd(self, component, sourcename, leafname):
        """Open leafname for adding in the pool, making dirs as needed.
        Raises AlreadyInPool if the file is already there.
        """
        self._checkpath(component,sourcename)
        if leafname in self.files:
            # We already have this leaf; if it's in the component
            # specified then we stop now.
            if leafname not in self.components[component]:
                # Okay, let's make a symlink into this component
                self.debug("Making symlink in %s for %s/%s" %
                           (component, sourcename, leafname))
                targetpath = self.pathFor(component, sourcename, leafname)
                sourcepath = self.pathFor(self.files[leafname].defcomp,
                                           sourcename, leafname)
                if not os.path.exists(os.path.dirname(targetpath)):
                    os.makedirs(os.path.dirname(targetpath))
                os.symlink(sourcepath, targetpath)
                self.files[leafname].comps.add(component)
                self.components[component][leafname] = True
            raise AlreadyInPool()
        self.debug("Making new file in %s for %s/%s" %
                   (component, sourcename, leafname))
                   
        targetpath = self.pathFor(component, sourcename, leafname)
        if not os.path.exists(os.path.dirname(targetpath)):
            os.makedirs(os.path.dirname(targetpath))
        self.components[component][leafname] = False
        self.files[leafname] = DiskPoolEntry(sourcename)
        self.files[leafname].defcomp = component
        return file(targetpath,"w")
    
    def removeFile(self, component, sourcename, leafname):
        """Remove a file from a given component.
        """
        if leafname not in self.components[component]:
            raise NotInPool()
        # Okay, it's there, if it's a symlink then we need to remove
        # it simply.
        if self.components[component][leafname]:
            self.debug("Removing %s %s/%s as it is a symlink" %
                       (component, sourcename, leafname))
            os.remove(self.pathFor(component, sourcename, leafname))
            # remove it from the component
            self.components[component].pop(leafname)
            # remove the component from the symlink set
            self.files[leafname].comps.remove(component)
            return
        # It's not a symlink, this means we need to check.
        if len(self.files[leafname].comps) == 0:
            self.debug("Removing only instance of %s/%s from %s" %
                       (sourcename, leafname, component))
            # It's the only instance...
            os.remove(self.pathFor(component, sourcename, leafname))
            # Remove it from the component
            self.components[component].pop(leafname)
            # Remove it from the file list
            self.files.pop(leafname)
            return
        # It is not a symlink and it's not the only entry for it
        # We have to shuffle the symlinks around
        comps = self.files[leafname].comps
        targetcomponent = comps.pop()
        comps.add(targetcomponent)
        self._shufflesymlinks(leafname, targetcomponent)
        # And now it's not the primary component any more.
        self.removeFile(component, sourcename, leafname)

    def _shufflesymlinks(self, leafname, targetcomponent):
        """Shuffle the symlinks for leafname so that targetcomponent contains
        the real file and the rest are symlinks to the right place..."""
        self.debug("Shuffling symlinks so primary for %s is in %s" %
                   (leafname, targetcomponent))
        if targetcomponent == self.files[leafname].defcomp:
            # Nothing to do, it's already the primary component
            return
        if targetcomponent not in self.files[leafname].comps:
            raise ValueError("Target component %s not in set of %s" %
                             (targetcomponent,leafname))
        # Okay, so first up, we unlink the targetcomponent symlink
        targetpath=self.pathFor(targetcomponent, self.files[leafname].source,
                                 leafname)
        os.remove(targetpath)
        # Now we rename the source file into the target component
        os.rename(self.pathFor(self.files[leafname].defcomp,
                                self.files[leafname].source,
                                leafname),
                  targetpath)
        # Update the data structures...
        self.components[self.files[leafname].defcomp][leafname] = True
        self.components[targetcomponent][leafname] = False
        self.files[leafname].comps.add(self.files[leafname].defcomp)
        self.files[leafname].defcomp = targetcomponent
        self.files[leafname].comps.remove(targetcomponent)
        # Now we make the symlinks on the FS...
        for comp in self.files[leafname].comps:
            newpath = self.pathFor(comp, self.files[leafname].source, leafname)
            try:
                os.remove(newpath)
            except OSError:
                # Do nothing because it's almost certainly a not found
                pass
            os.symlink(targetpath, newpath)

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

