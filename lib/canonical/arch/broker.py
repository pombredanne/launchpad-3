# arch-tag: 27f07153-69b6-4ddb-b704-eaabcca57e3e
# Author: Rob Weir <rob.weir@canonical.com>
# Copyright (C) 2004 Canonical Software

from arch import NameParser

from zope.interface import implements, classProvides
from canonical.launchpad.interfaces import INamespaceObject, ISourceTreeAPI, \
                                           ISourceTreeFactory, IFileName, \
                                           IArchiveItem, ICategoryItem, \
                                           IRevisionFactory, IPatchlog, \
                                           ICategoryFactory, ICategory, \
                                           ILogMessage, IArchSourceTree \
                                           IDirName, IPathNameFactory, \
                                           IArchiveLocation, IArchive, \
                                           IBranchItem, IVersionItem, \
                                           IBranch, IBranchFactory, \
                                           ISetupable, IPackage, \
                                           IArchiveCollection, \
                                           IVersion,IRevision, \
                                           IRevisionIterable, \
                                           ICategoryIterable, \
                                           IVersionIterable


from canonical.launchpad import database

default_location = "/tmp/"

###############################################################################
### NamespaceObject

class NamespaceObject(object):
    """
    Implement canonical.launchpad.interfaces.INamespaceObject against the
    Soyuz database.
    """

    implements(INamespaceObject)

    def __init__(self, fullname):
        """Set our own name"""
        self._fullname = fullname

    def fullname(self):
        return self._fullname

    # Fullname is the *fully-qualified name of the object*
    # eg rob@bah/baz--bor--0 is the fullname of a Version
    fullname = property(fullname)

    _eq_interface = None
 
    def __eq__(self,  x):
        """Are we not equal to x?"""
        return x is not None \
               and (id(x) == id(self)
                    or (self._eq_interface.providedBy(x)
                        and self.fullname == x.fullname))

    def __ne__(self, x):
        """Are we not equal to x?"""
        return not self.__eq__(x)


###############################################################################
### Iteration base classes

class RevisionIterable(object):

    implements(IRevisionIterable)

    def iter_revisions(self, reverse=False):
        raise NotImplementedError, "Not implemented yet"

    def iter_library_revisions(self, reverse=False):
        raise NotImplementedError, "Not implemented yet"


class VersionIterable(RevisionIterable):

    implements(IVersionIterable)

    def iter_versions(self, reverse=False):
        raise NotImplementedError, "Not implemented yet"

    def iter_library_versions(self, reverse=False):
        raise NotImplementedError, "Not implemented yet"


class BranchIterable(VersionIterable):

    implements(IBranchIterable)

    def iter_branches(self):
        raise NotImplementedError, "Not implemented yet"

    def iter_library_branches(self):
        raise NotImplementedError, "Not implemented yet"


class CategoryIterable(BranchIterable):

    implements(ICategoryIterable)
    
    def iter_categories(self):
        raise NotImplementedError, "Not implemented yet"

    def iter_library_categories(self):
        raise NotImplementedError, "Not implemented yet"


###############################################################################
### Containement base classes

class ArchiveItem(NamespaceObject):

    implements(IArchiveItem)

    def archive(self):
        pass # Not implement yet

    archive = property(archive)

    def nonarch(self):
        pass # Not implement yet

    nonarch = property(nonarch)


class CategoryItem(ArchiveItem):

    implements(ICategoryItem)

    def __init__(self):
        ArchiveItem.__init__(self)
        self._category = "category"

    def category(self):
        return self._category

    category = property(category)


class BranchItem(CategoryItem):

    implements(IBranchItem)

    def __init__(self):
        CategoryItem.__init__(self)
        self._branch = "branch"

    def branch(self):
        return self._branch

    branch = property(branch)


class VersionItem(BranchItem):

    implements(IVersionItem)

    def __init__(self):
        BranchItem.__init__(self)
        self._version = "0"

    def version(self):
        return self._version

    version = property(version)


###############################################################################
### Misc base classes

class Setupable(ArchiveItem):

    implements(ISetupable)
    
    def setup():
        raise NotImplemented, "Not implemented yet"


class Package(Setupable, RevisionIterable):

    implements(IPackage)
    
    def as_revision():
        raise NotImplemented, "Not implemented yet"


###############################################################################
### Concrete Namespace classes

import UserDict
class Archives(object, UserDict.DictMixin):
    """I am a collection of all the archives available to the system"""
    implements(IArchiveCollection)

    def __getitem__(self, key):
        """retrieve an archive"""
        Archive._validate_name(key)
        return self.getMapper().findByName(key)

    def __setitem__(self, key, value):
        """Do not add an archive, just fail!"""
        raise TypeError, ("Archives does not setitem. "
                          "Use the 'create' method instead")

    def __delitem__(self, key):
        """Do not delete an archive, just fail!"""
        raise TypeError, ("Archives does not delitem.")

    def getMapper(self):
        """return the current mapper"""
        return database.ArchiveMapper()

    def keys(self):
        return [archive.name for archive in
                self.getMapper().findByMatchingName('%')]

    def create(self, name, locations=[]):
        """create an archive"""
        Archive._validate_name(name)
        archive=Archive(name)
        self.getMapper().insert(archive)
        # TODO populate the archive locations too.
        return archive


class ArchiveLocationRegistry(object):
    """I'm a list of the registered locations for an archive"""

    # TODO move these ENUM values to dbschema.py
    readwrite    = 0
    readonly     = 1
    mirrorTarget = 2
    
    def __init__(self, archive):
        self._mapper = database.ArchiveLocationMapper()
        self._archive = archive

    def _createLocation(self, url, type):
        """Add a location to the database"""
        location = ArchiveLocation(self._archive, url, type)
        self._mapper.insertLocation(location)
        return location

    def createReadWriteTargetLocation(self, url):
        """Create a ArchiveLocation for a read/write mirror"""
        return self._createLocation(url, ArchiveLocationRegistry.readwrite)

    def createReadOnlyTargetLocation(self, url):
        """Create a ArchiveLocation for a read-only archive"""
        return self._createLocation(url, ArchiveLocationRegistry.readonly)

    def createMirrorTargetLocation(self, url, create=False):
        """Create a ArchiveLocation for a mirror target"""
        if create:
            archive = arch.Archive(self._archive.name)
            archive.make_mirror(archive.name + "-MIRROR", location = default_location + archive.name, signed=False, listing=True)
        return self._createLocation(url, ArchiveLocationRegistry.mirrorTarget)

    def existsLocation(self, location):
        """Is location in the db?"""
        return self._mapper.locationExists(location)

    def _get(self, type):
        """Return all locations"""
        return self._mapper.get(self._archive, type=type)
        
    def _remove(self, type, name):
        raise NotImplemented, "Not implemented yet"

    def getMirrorTargetLocations(self):
        return self._get(2)

    def getReadOnlyLocations(self):
        return self._get(1)
    
    def getReadWriteLocations(self):
        return self._get(0)

    def removeMirrorTarget(self, location):
        raise NotImplemented, "Not implemented yet"
    
    def removeReadonlyTarget(self, location):
        raise NotImplemented, "Not implemented yet"
    
    def removeReadWriteTarget(self, location):
        raise NotImplemented, "Not implemented yet"


class ArchiveLocation(object):
    """I'm a single location of an archive"""

    implements(IArchiveLocation)
    
    def __init__(self, archive, url, type):
        """Create us, given an Archive and a url string"""
        self._mapper = database.ArchiveLocationMapper()
        self._url = url
        self._archive = archive
        self._type = type

    def url(self):
        """My registered location"""
        return self._url

    url = property(url)

    def archive(self):
        """The archive I belong to"""
        return self._archive

    archive = property(archive)

    def GPGSigned(self):
        """Am I GPG-signed?"""
        return self._mapper.isItSigned(self)

    GPGSigned = property(GPGSigned)

    def unregister(self):
        """Delete me from the database"""
        raise NotImplementedError, "Not implemented yet!"


class Archive(NamespaceObject, CategoryIterable):
    """A database & file store backed arch Archive"""

    implements(IArchive)
    _eq_interface = IArchive

    def __init__(self, name):
        """Create a new Archive object from the named archive."""
        NamespaceObject.__init__(self, name)
        self._name = name
        self._mapper = database.ArchiveMapper()

    def _validate_name(archive_name):
        """Raise a NamespaceError if the given archive name is invalid."""
        from arch import NameParser
        if not NameParser.is_archive_name(archive_name):
            raise NamespaceError("invalid archive name: %s" % archive_name)
    _validate_name = staticmethod(_validate_name)

    def exists(self):
        # If it didn't exist, it would be a MissingArchive
        return True

    def name(self):
        """return the archive name"""
        return self._name

    name = property(name)

    def location(self):
        # ArchiveLocationRegistry objects know about different types of locations.
        return ArchiveLocationRegistry(self)

    location = property(location)

    def __getitem__(self, category_name):
        """Instanciate a Category object belonging to that archive.

        :param category_name: unqualified category name.
        :type category_name: str
        :rtype: `Category`
        """
        if not NameParser.is_category_name(category_name):
            raise NamespaceError('invalid category name: %s' % category_name)
        category = Category(category_name, self)
        mapper = database.CategoryMapper()
        if not mapper.exists(category):
            return MissingCategory(category_name, self)
        else:
            return category

    def is_registered(self):
        """Is there an archive location associated with the archive?"""
        # if we have at least one mention in the archivelocation table
        location = self.location
        if len(location.getMirrorTargetLocations()) + \
           len(location.getReadOnlyLocations()) + \
           len(location.getReadWriteLocations()) > 0:
            return True
        else:
            return False

    def unregister(self):
        """The location method should """
        raise RuntimeError("This is old and broken, do not use it.")

    def make_mirror(self, name, location, signed=False, listing=False):
        raise NotImplementedError, "Not implemented yet!"

    def create_category(self, name):
        """Creata a category object, inserting it if it doesn't exist."""
        mapper = database.CategoryMapper()
        category = Category(name, self)
        mapper.insert(category)
        return category

    def mirror_revision(self, revision):
        """Mirror revision to my mirror"""
        source_archive = arch.Archive(self.name)
        source_archive.mirror(limit=[revision.nonarch], fromto=(self.name, self.name + "-MIRROR"))
        

class MissingArchive(Archive):
    """I am a Special Case for missing archives"""

    def __init__(self, name):
        """Create a new Archive object from the named archive."""
        self._name = name
        Archive.__init__(self, name)
        
    def __getitem__(self, category_name):
        """Raise a TypeError."""
        raise TypeError, "MissingCategory cannot getitem."""
    
    def exists(self):
        return False


class Category(Setupable, BranchIterable):
    """FS & DB backed Category object"""
    classProvides(ICategoryFactory)
    implements(ICategory)
    _eq_interface = ICategory

    def __init__(self, name, archive):
        from arch import NameParser
        self._archive = archive
        self._name = name

        self._fullname = self._archive.name + "/" + self._name
            
        self._mapper = database.CategoryMapper()
        self._nonarch = name

    def __getitem__(self, name):
        """Return the asked-for branch object"""
        branch = Branch(name, self)
        mapper = database.BranchMapper()
        if not mapper.exists(branch):
            return MissingBranch(name, self)
        else:
            return branch

    def archive(self):
        return self._archive

    archive = property(archive)

    def nonarch(self):
        """The non-archive part of the name"""
        return self._nonarch

    nonarch = property(nonarch)

    def name(self):
        return self._name

    name = property(name)

    def exists(self):
        return True

    def setup(self):
        self._mapper.insert(self)

    def create_branch(self, name):
        """Creata a branch object, inserting it if it doesn't exist."""
        mapper = database.BranchMapper()
        branch = Branch(name, self)
        mapper.insert(branch)
        return branch

class MissingCategory(Category):
    def __init__(self, name, archive):
        Category.__init__(self, name, archive)
            
    def exists(self):
        return False

class Branch(CategoryItem, Package, VersionIterable):
    """DB-backed version of arch.Branch"""

    implements(IBranch)
    classProvides(IBranchFactory)
    _eq_interface = IBranch

    def __init__(self, name, category):
#        NamespaceObject.__init__(self, category.fullname + "--" + name)
        self._category = category
        self._name = name
        self._fullname = category.fullname + "--" + name

    def exists(self):
        return True

    def __getitem__(self, name):
        """Return the asked-for version object"""
        version = Version(name, self)
        mapper = database.VersionMapper()
        if not mapper.exists(version):
            return MissingVersion(name, self)
        else:
            version._sqlobject_branch = mapper.findByName("%s--%s" % (self.fullname, name))
            return version
             
    def as_version():
        """Get the last version from this branch"""
        raise NotImplementedError, "Not implemented yet!"

    def category(self):
        # Our parent object
        return self._category

    category = property(category)

    def name(self):
        # Our name.  eg if self.fullname = "rob@bah/baz--bah", self.name = "bah".
        return self._name

    name = property(name)

    def create_version(self, name):
        """Creata a version object, inserting it if it doesn't exist."""
        mapper = database.VersionMapper()
        version = Version(name, self)
        version._sqlobject_branch = mapper.insert(version)
        return version

class MissingBranch(Branch):
    """A branch that doesn't exist"""
    def exists(self):
        return False


class Version(BranchItem, Package, RevisionIterable):
    """Implementats canonical.launchpad.interfaces.IVersion, backed by the db"""

    implements(IVersion)
    _eq_interface = IVersion

    def __init__(self, name, branch):
        NamespaceObject.__init__(self, branch.fullname + "--" + name)
        self._name = name
        self._branch = branch

    def exists(self):
        return True

    def __getitem__(self, key):
        """Return the asked-for revision object"""
        revision = Revision(key, self)
        mapper = database.RevisionMapper()
        if not mapper.exists(revision):
            return MissingRevision(key, self)
        else:
            revision.get_changeset()
            return revision

    def iter_cachedrevs(self):
        raise NotImplementedError, "Not implemented yet!"

    def iter_merges(self, other, reverse=False):
        raise NotImplementedError, "Not implemented yet!"

    def category(self):
        return self._branch.category

    category = property(category)

    def branch(self):
        return self._branch

    branch = property(branch)

    def name(self):
        return self._name

    name = property(name)

    def create_revision(self, name):
        """Creata a Revision object, inserting it if it doesn't exist."""
        mapper = database.RevisionMapper()
        revision = Revision(name, self)
        mapper.insert(revision)
        return revision

class MissingVersion(Version):
    """A Version that doesn't exist."""
    def exists(self):
        return False


class Revision(VersionItem):
    """A Revision object backed by the database"""

    implements(IRevision)
    classProvides(IRevisionFactory)
    _eq_interface = IRevision

    def __init__(self, name, version):
        NamespaceObject.__init__(self, version.fullname + "--" + name)
        self._name = name
        self._version = version
        self._patchlog = None
        self._cset = None

    def exists(self):
        return True

    def set_patchlog(self, patchlog):
        self._patchlog = patchlog
        mapper = database.RevisionMapper()
        mapper.update_log(self, patchlog.summary)

    def patchlog(self):
        return self._patchlog

    patchlog = property(patchlog)

    def get_changeset(self):
        mapper = database.RevisionMapper()
        self._cset = mapper.changeset(self)

    def set_changeset(self, cset):
        self._cset = cset

    def changeset(self):
        return self._cset

    changeset = property(changeset)
    
    def ancestor(self):
        pass # Not implemented yet

    ancestor = property(ancestor)

    def previous(self):
        pass # Not implemented yet

    previous = property(previous)

    def library_add(self):
        raise NotImplementedError, "Not implemented yet!"

    def library_remove(self):
        raise NotImplementedError, "Not implemented yet!"

    def library_find(self):
        raise NotImplementedError, "Not implemented yet!"

    def iter_ancestors(self, metoo=False):
        raise NotImplementedError, "Not implemented yet!"

    def cache(self, cache=None):
        raise NotImplementedError, "Not implemented yet!"

    def uncache(self):
        raise NotImplementedError, "Not implemented yet!"

    def category(self):
        return self.version.branch.category

    category = property(category)

    def branch(self):
        return self.version.branch

    branch = property(branch)

    def version(self):
        return self._version

    version = property(version)

    def patchlevel(self):
        return self._name

    patchlevel = property(patchlevel)

    def name(self):
        return self._name

    name = property(name)

    def add_file(self, name, data, checksums):
        """Insert a file into the database"""
        database.RevisionMapper().insert_file(self, name, data, checksums)

    def clone_files(self, iterator):
        """iterate over files, insert them"""
        for file in iterator:
            self.add_file(file.name, file.data, file.checksums)

class MissingRevision(Revision):
    def __init__(self, name, version):
        Revision.__init__(self, name, version)

    def exists(self):
        return False
    
class PatchlogFactory(object):

    def __call__(revision, tree=None, fromlib=False):
        raise NotImplementedError, "Not implemented yet!"

    implements(IPatchlog)

    def revision(self):
        pass # Not implemented yet

    revision = property(revision)

    def summary(self):
        pass # Not implemented yet

    summary = property(summary)
    
    def description(self):
        pass # Not implemented yet

    description = property(description)

    def date(self):
        pass # Not implemented yet

    date = property(date)
    
    def creator(self):
        pass # Not implemented yet
    
    creator = property(creator)

    def continuation(self):
        pass # Not implemented yet
    
    continuation = property(continuation)

    def new_patches(self):
        pass # Not implemented yet
    
    new_patches = property(new_patches)

    def merged_patches(self):
        pass # Not implemented yet
    
    merged_patches = property(merged_patches)
    
    def new_files(self):
        pass # Not implemented yet
    
    new_files = property(new_files)

    def modified_files(self):
        pass # Not implemented yet
        
    modified_files = property(modified_files)
    
    def removed_files(self):
        pass # Not implemented yet

    removed_files = property(removed_files)
        
    def __getitem__(self, header):
        raise NotImplementedError, "Not implemented yet!"

    
class LogMessageFactory(object):

    implements(ILogMessageFactory)

    def __call__(name):
        raise NotImplementedError, "Not implemented yet!"


class LogMessage(object):

    implements(ILogMessage)

    def name(self):
        pass # Not implemented yet

    name = property(name)

    def description(self):
        pass # Not implemented yet

    description = property(description)

    def load(self):
        raise NotImplementedError, "Not implemented yet!"
    
    def save(self):
        raise NotImplementedError, "Not implemented yet!"

    def clear():
        raise NotImplementedError, "Not implemented yet!"

    def __getitem__(self, header):
        raise NotImplementedError, "Not implemented yet!"

    def __setitem__(self, header, text):
        raise NotImplementedError, "Not implemented yet!"


class PathNameFactory(object):

    implements(IPathNameFactory)
    
    def __call__(path='.'):
        raise NotImplementedError, "Not implemented yet!"


class PathName(object):

    implements(IPathName)

    def __div__(self, path):
        raise NotImplementedError, "Not implemented yet!"

    def abspath(self):
        raise NotImplementedError, "Not implemented yet!"

    def dirname(self):
        raise NotImplementedError, "Not implemented yet!"

    def basename(self):
        raise NotImplementedError, "Not implemented yet!"

    def realpath(self):
        raise NotImplementedError, "Not implemented yet!"

    def splitname(self):
        raise NotImplementedError, "Not implemented yet!"


class DirName(PathName):
    implements(IDirName)
    pass

class FileName(PathName):
    implements(IFileName)
    pass


class SourceTreeAPI(object):

    implements(ISourceTreeAPI)
    
    def init_tree(self, directory, version=None, nested=False):
        raise NotImplementedError, "Not implemented yet!"

    def in_source_tree(self, directory=None):
        raise NotImplementedError, "Not implemented yet!"

    def tree_root(directory=None):
        raise NotImplementedError, "Not implemented yet!"


class SourceTreeFactory(object):

    implements(ISourceTreeFactory)

    def __call_(root=None):
        raise NotImplementedError, "Not implemented yet!"


class ArchSourceTree(DirName):

    implements(IArchSourceTree)

    def tree_version(self):
        pass # Not implemented yet

    tree_version = property(tree_version)

    def tagging_method(self):
        pass # Not implemented yet
	
    tagging_method = property(tagging_method)
