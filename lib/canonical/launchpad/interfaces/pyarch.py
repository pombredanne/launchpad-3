# Author: David Allouche <david.allouche@canonical.com>
# Copyright (C) 2004 Canonical Software
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

__all__ = ['ArchiveAlreadyRegistered', 'ArchiveNotRegistered',
           'ArchiveLocationDoublyRegistered', 'RevisionNotRegistered',
           'RevisionAlreadyRegistered', 'VersionNotRegistered',
           'VersionAlreadyRegistered', 'BranchAlreadyRegistered',
           'CategoryAlreadyRegistered', 'IBranch',
           'RCSTypeEnum', 'NamespaceError',
           'IArchive', 'IArchiveLocation',
           'IArchiveCollection'
           ]

__docformat__ = "restructuredtext en"

from zope.interface import Interface, Attribute
from zope.schema import Choice, Datetime, Int, Text, TextLine, Float
from canonical.launchpad.fields import Title

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

class INamespaceObject(Interface):

    """Interface provided by objects associated to names in the Arch namespace.

    Namespace objects are associated to a fullname and compare equal if and
    only if their are of the same type and are associated to the same fullname.

    FIXME: how to express the contract for equality comparison?
    """

    fullname = Attribute("""Fully qualified name of this namespace object.

    :type: str
    """)

    def exists():
        """Does this namespace exists?

        Within the Arch model, history cannot be changed: created archive
        entries cannot be deleted. However, it is possible to ``unregister`` an
        archive, or to find references to archives whose location is not known.
        Thus, existence cannot always be decided. Testing for the existence of
        a name in a non-registered archive raises
        `errors.ArchiveNotRegistered`.

        :return: whether this namespace object exists.
        :rtype: bool
        :raise errors.ArchiveNotRegistered: the archive name is not registered,
            so existence cannot be decided.
        :raise util.ExecProblem: there was a problem accessing the archive.
        """

    def __str__():
        """Fully-qualified name.

        Returns the value of the fullname attribute.

        :rtype: str
        """

    def __eq__(x):
        """Compare types and fully-qualified names.

        :return: Wether objects have the same types and names.
        :rtype: bool
        """

    def __ne__(x):
        """Compare types and fully-qualified names.

        :return: Whether objects have different types or names.
        :rtype: bool
        """


### Interfaces for archive iteration aspect ###

class IRevisionIterable(Interface):

    """Interface provided by objects which can be iterated for revisions."""

    def iter_revisions(reverse=False):
        """Iterate over archive revisions.

        :param reverse: reverse order, recent revisions first.
        :type reverse: bool
        :return: all existing revisions in this namespace.
        :rtype: iterator of `arch.Revision`
        """

    def iter_library_revisions(reverse=False):
        """Iterate over library revisions.

        :param reverse: reverse order, recent revisions first.
        :type reverse: bool
        :return: revisions in this namespace which are present in the
            revision library.
        :rtype: iterator of `arch.Revision`
        """


class IVersionIterable(IRevisionIterable):

    """Interface provided by objects which can be iterated for versions.

    Since versions can be iterated for revisions, this interface inherits from
    `IRevisionIterable`.
    """

    def iter_versions(reverse=False):
        """Iterate over archive versions.

        :param reverse: reverse order, higher versions first.
        :type reverse: bool
        :return: all existing versions in this namespace.
        :rtype: iterator of `arch.Version`
        """

    def iter_library_versions(reverse=False):
        """Iterate over library revisions.

        :param reverse: reverse order, higher versions first.
        :type reverse: bool
        :return: versions in this namespace which are present in the
            revision library.
        :rtype: iterator of `arch.Version`
        """


class IBranchIterable(IVersionIterable):

    """Interface provided by objects which can be iterated for branches.

    Since branches can be iterated for versions, this interface inherits from
    `IVersionIterable`.
    """

    def iter_branches():
        """Iterate over archive branches.

        :return: all existing branches in this namespace.
        :rtype: iterator of `arch.Branch`
        """

    def iter_library_branches():
        """Iterate over library branches.

        :return: branches in this namespace which are present in the
            revision library.
        :rtype: iterator of `arch.Branch`
        """


class ICategoryIterable(IBranchIterable):

    """Interface provided by objects which can be iterated for categories.

    Since categories can be iterated for branches, this interface inherits from
    `IBranchIterable`.
    """

    def iter_categories():
        """Iterate over archive categories.

        :return: all existing categories in this namespace.
        :rtype: iterator of `arch.Category`
        """

    def iter_library_categories():
        """Iterate over library categories.

        :return: categories in this namespace which are present in the
            revision library.
        :rtype: iterator of `arch.Category`
        """


### Interfaces for archive containement aspect ###

class IArchiveItem(INamespaceObject):

    """Interface for archive components.

    IArchiveItem defines the features common to all objects which are
    structural components of `arch.Archive`.
    """

    archive = Attribute("""Archive which contains this object.

    :type: `arch.Archive`
    """)

    nonarch = Attribute("""Non-arch part of this object's name.

    :type: str
    """)


class ICategoryItem(IArchiveItem):

    """Interface for archive components below category.

    ICategoryItem defines the features common to all objects which are
    structural components of `arch.Category`.

    Since `arch.Category` implements `IArchiveItem`, this interface inherits
    from `IArchiveItem`.
    """

    category = Attribute("""Category which contains this object.

    :type: `arch.Category`
    """)


class IBranchItem(ICategoryItem):

    """Interface for archive components below branch.

    IBranchItem defines the features common to all objects which are structural
    components of `arch.Branch`.

    Since `arch.Branch` implements `ICategoryItem`, this interface inherits
    from `ICategoryItem`.
    """

    branch = Attribute("""Branch which contains this object.

    :type: `arch.Branch`
    """)


class IVersionItem(IBranchItem):

    """Interface for archive components below version.

    IVersionItem defines the features of `arch.Revision` which relate to its
    containment within other archive objects.
    """

    version = Attribute("""Version which contains this revision.

    :type: `arch.Version`
    """)

    patchlevel = Attribute("""Patch-level part of this object's name.

    :type: str
    """)


### Interface for misc. features of archive objects ###

class ISetupable(IArchiveItem):

    """Interface for container archive components."""

    def setup():
        """Create this namespace in the archive."""


class IPackage(ISetupable, IRevisionIterable):

    """Interface for ordered container archive components."""

    def as_revision():
        """Latest revision in this package.

        :rtype: `Revision`
        """


### Archive interfaces ###

class IArchiveCollection(Interface):
    """Provide access to the Arch archive objects available to the client."""

    def __getitem__(key):
        """retrieve an archive
        :param key: archive name, like "jdoe@example.com--2003"
        :type key: str
        :raise errors.NamespaceError: invalid archive name
        """
    def __setitem__(key, value):
        """add an archive
        :param key: archive name, like "jdoe@example.com--2003"
        :type key: str
        :param value: an Archive instance
        :type value: Archive
        :raise errors.NamespaceError: invalid archive name
        """
    def __delitem__(key):
        """remove an archive
        :param key: archive name, like "jdoe@example.com--2003"
        :type key: str
        :raise errors.NamespaceError: invalid archive name
        """
    def __iter__():
        """iterate over the archives"""
    def create(name, locations=[]):
        """Create archive.

        name: archive name (e.g. "david@allouche.net--2003b")
        locations: archive resource specifications:
        URL of the archive
        signed flag
        listing flag

        return: an Archive instance for the given name.
        TODO: move to IArchiveCollection.create and nuke make_archive.
        """


class IArchive(ICategoryIterable):

    """Interface for Arch archives.

    In the Arch revision control system, archives are the units of
    storage. They store revisions organized in categories, branches
    and versions, and are associated to a `name` and a `location`.

    :see: `ICategory`, `IBranch`, `IVersion`, `IRevision`
    """

    name = Attribute("""Logical name of the archive.

    :type: str
    """)

    location = Attribute("""
    URI of the archive, specifies location and access method.

    For example "http://ddaa.net/arch/2004", or
    "sftp://user@sourcecontrol.net/public_html/2004".

    :type: str
    """)

    def __getitem__(category):
        """Instanciate a Category belonging to this archive.

        :param category: unqualified category name
        :type category: `str`
        :rtype: `Category`
        """

    def is_registered():
        pass

    def unregister():
        """Unregister this archive.

        :precondition: `self.exists()`
        :postcondition: not `self.exists()`
        :raises util.ExecProblem: archive is not registered
        :see: `register_archive`
        """

    def make_mirror(name, location, signed=False, listing=False):
        """Create and register a new mirror of this archive.

        :param name: name of the new mirror (for example
            'david@allouche.net--2003b-MIRROR').
        :type name: str
        :param location: writeable URI were to create the archive mirror.
        :type location: str
        :param signed: create GPG signatures for the archive contents.
        :type signed: bool
        :param listing: maintains ''.listing'' files to enable HTTP access.
        :type listing: bool

        :return: New archive mirror object.
        :rtype: `Archive`

        :precondition: `self.exists()`
        :precondition: ``name`` is not a registered archive name
        :precondition: ``location`` does not exist and can be created
        :postcondition: Archive(name).exists()

        :raise errors.NamespaceError: ``name`` is not a valid archive name.
        :raise util.ExecProblem: `self.exists()` is not ``True``, ``name`` is
            already registered, ``location`` already exists or there was a
            problem creating it.
        """

class IArchiveLocation(Interface):

    """Store a location for an archive."""

    url = Attribute("""The URL for this archive location.

    :type: str
    """)

    GPGSigned = Attribute("""Is the archive signed or not?

    :type: boolean
    """)

    archive = Attribute("""The archive we're a location for.

    :type: Archive
    """)

    def unregister():

        """Unregister me from the database."""

class ICategoryFactory(Interface):

    """Create Arch category model objects."""

    def __call__(name):

        """Create a category object from its name.

        :param name: fully-qualified category name, like
          "jdoe@example.com--2004/frob"
        :type name: str
        :raise errors.NamespaceError: ``name`` is not a valid category name.
        """


class ICategory(ISetupable, IBranchIterable):

    """Interface for Arch categories.

    :see: `IArchive`, `IBranch`, `IVersion`, `IRevision`
    """

    def __getitem__(branch):
        pass


class IBranchFactory(Interface):

    """Create Arch branch model objects."""

    def __call__(name):
        """Create a Branch object from its name.

        :param name: fully-qualified branch name, like
            "jdoe@example.com--2004/frob--devo" or
            "jdoe@example.com--2004/frob".
        :type name: str
        :raise errors.NamespaceError: ``name`` is not a valid branch name.
        """


class IBranch(ICategoryItem, IPackage, IVersionIterable):

    """Interface for Arch branches.

    :see: `IArchive`, `ICategory`, `IVersion`, `IRevision`
    """

    def __getitem__(version):
        pass

    def as_version():
        """Last version in this branch.

        :rtype: `Version`
        :precondition: `self.exists()` returns ``True``
        :precondition: `self.iter_versions` yields at least one object.
        """

    '''extension interfaces for launchpad, to move into a sub interface'''
    id = Int(title=_('The database identifier for this branch.'))

    title = Title(title=_('Branch Title'), required=True,
                  description = _("""The title of the Branch. This will be
                  displayed on any report listing different branches. It
                  should be a very brief (one line, less than 70 characters)
                  title describing the purpose of the branch."""))
    archnamespace = Int(title=_('The ArchNameSpace object for this branch'),
                    required=True, readonly=False)


class IVersionFactory(Interface):

    """Create Arch version model objects."""

    def __call__(name):
        """Create a Version object from its name.

        :param name: fully-qualified version name, like
           "jdoe@example.com--2004/frob--devo--1.2".
        :type name: str

        :note: Nameless branches have no "branch" part in their name.
        """

class IVersion(IBranchItem, IPackage, IRevisionIterable):

    """Interface for Arch versions.

    :see: `IArchive`, `ICategory`, `IBranch`, `IRevision`
    """

    def __getitem__(level):
        pass

    def iter_merges(other, reverse=False):
        """Iterate over merge points in this version.

        :param other: list merges with that version.
        :type other: `Version`
        :param reverse: reverse order, recent revisions first.
        :type reverse: bool

        :return: Iterator of tuples (R, T) where R are revisions in this
            version and T are iterators of revisions in the ``other`` version.
        :rtype: iterator

        :bug: The tree of iterators must be traversed in depth-first order. The
           iterators will yield incorrect results when traversed breadth-first.
        """

    def iter_cachedrevs():
        """Iterate over the cached revisions in this version.

        :rtype: iterator of `Revision`
        """

class IRevisionFactory(Interface):

    """Create Arch revision model objects."""

    def __call__(name):
        """Create a Revision object from its name.

        :param name: fully-qualified revision, like
            "jdoe@example.com--2004/frob--devo--1.2--patch-2".
        :type name: str

        :note: Nameless branches have no "branch" part in their name.
        """

class IRevision(IVersionItem):

    """Interface for Arch revisions.

    :see: `IArchive`, `ICategory`, `IBranch`, `IVersion`
    :group Libray Methods: library_add, library_remove, library_find
    :group History Methods: get_ancestor, get_previous, iter_ancestors
    """

    patchlog = Attribute("""Patchlog associated to this revision.

    The `Patchlog` object is created in `__init__`, since log parsing is
    deferred that has little overhead and avoid parsing the log for a given
    revision several times. The patchlog data is read from the archive.

    :rtype: `Patchlog`
    :see: `ArchSourceTree.iter_logs`
    """)

    def library_add():
        """Add this revision to the library.

        :postcondition: self in self.version.library_revisions
        :raise util.ExecProblem: problem creating the revision
        """

    def library_remove():
        """Remove this revision from the library.

        :precondition: self in self.version.library_revisions
        :postcondition: self not in self.version.library_revisions
        :raise util.ExecProblem: revision not present in the library, or
            problem removing the revision.
        """

    def library_find():
        """The copy of this revision in the library.

        :rtype: `LibraryTree`
        :precondition: self in self.version.library_revisions
        :raise util.ExecProblem: revision not present in the library
        """

    ancestor = Attribute("""Parent revision.

    :return:
        - The previous namespace revision, if this revision is regular
          commit.
        - The tag origin, if this revision is a continuation
        - ``None`` if this revision is an import.

     :rtype: `Revision` or None
     """)

    previous = Attribute("""Previous namespace revision.

    :return: the previous revision in the same version, or None if this
        revision is a ``base-0``.
    :rtype: None
    """)

    def iter_ancestors(metoo=False):
        """Ancestor revisions.

        :param metoo: yield ``self`` as the first revision.
        :type metoo: bool
        :return: All the revisions in that line of development.
        :rtype: iterator of `Revision`
        """
    def cache(cache=None):
        """Cache a full source tree for this revision in its archive.

        :param cache: cache root for trees with pristines.
        :type cache: bool
        """
    def uncache():
        """Remove the cached tree of this revision from its archive."""


### Patch logs ###

class IPatchlogFactory(Interface):

    """Create Arch patchlog objects."""

    def __call__(revision, tree=None, fromlib=False):
        """Patchlog associated to the given revision.

        @tree may be set to an Arch source tree directory name. In this case
        the patchlog will be retrieved from this source tree. Otherwise, if
        @fromlib is true, the patchlog will be looked for in the revision
        library. As a last resort, the patchlog will be looked for in the
        archive.
        """


class IPatchlog(Interface):

    """Log entry associated to a revision.

    May be retrieved by Revision.patchlog or ArchSourceTree.iter_logs(). It
    provides an extensive summary of the associated changeset, a natural
    language description of the changes, and any number of user-defined
    extension headers.

    Patchlogs are formatted according to RFC-822, and are parsed using the
    standard email-handling facilities.

    Note that the patchlog text is not actually parsed before it is needed.
    That deferred evaluation feature is implemented in the _parse method.

    The fundamental accessors are `__getitem__`, which give the text of a named
    patchlog header, and `get_description` (and the `description` property)
    which give the text of the patchlog body, that is anything after the
    headers.

    Additional accessors (and properties) provide appropriate standard
    conversion to the standard headers.
    """

    def __getitem__(header):
        """Text of a patchlog header by name."""

    revision = Attribute("""Revision associated to this patchlog.""")

    summary = Attribute("""
    Patchlog summary, a one-line natural language description.
    """)

    description = Attribute("""
    Patchlog body, a long natural language description.
    """)

    date = Attribute("""
    Time of the associated revision.
    """)

    creator = Attribute("""
    User id of the the creator of the associated revision.
    """)

    continuation = Attribute("""
    Ancestor of tag revisions, None for commit/import revisions.
    """)

    new_patches = Attribute("""
    New-patches header as an iterable of Revision.
    """)

    merged_patches = Attribute("""
    Patches merged in the associated revision.

    An iterable over revisions named in the New-patches header, except the
    revision associated with the patchlog.
    """)

    new_files = Attribute("""
    Source files added in the associated revision.
    """)

    modified_files = Attribute("""
    Names of source files modified in the associated revision.
    """)

    removed_files = Attribute("""
    Names of source files removed in the associated revision.
    """)


class ILogMessageFactory(Interface):

    """Create Arch log messages."""

    def __call__(name):
        pass


class ILogMessage(Interface):

    """Log message for use with commit, import or tag operations.

    This is the write-enabled counterpart of Patchlog. When creating a new
    revision with import, commit or tag, a log message file can be used to
    specify a long description and custom headers.

    Commit and import can use the default log file of the source tree, with a
    special name. You can create the LogMessage object associated to the
    default log file with the WorkingTree.log_message method.

    For integration with external tools, it is useful to be able to parse an
    existing log file and write the parsed object back idempotently. We are
    lucky since this idempotence is provided by the standard email.Parser and
    email.Generator.
    """

    name = Attribute("FIXME")

    def load():
        """Read the log message from disk."""

    def save():
        """Write the log message to disk."""

    def clear():
        """Clear the in-memory log message.

        When creating a new log message file, this method must be used
        first before setting the message parts. That should help early
        detection of erroneous log file names.
        """

    def __getitem__(header):
        """Text of a patchlog header by name."""

    def __setitem__(header, text):
        """Set a patchlog header."""

    description = Attribute("""Body of the log message.""")


### File name utilities ###

class IPathNameFactory(Interface):

    """Create PathName objects."""

    def __call__(path='.'):
        pass


class IPathName(Interface):

    """String with extra methods for filename operations."""

    def __div__(path):
        pass

    def abspath():
        pass

    def dirname():
        pass

    def basename():
        pass

    def realpath():
        pass

    def splitname():
        pass


class IDirName(IPathName):

    """PathName further characterized as a directory name."""


class IFileName(IPathName):

    """PathName further characterized as a file name."""


### Source trees ###

class ISourceTreeAPI(Interface):

    """Interfaces for top level functions related to source trees."""

    def init_tree(directory, version=None, nested=False):
        """Initialize a new project tree.

        If 'version' is given, it will set the the tree-version and an empty
        log version will be created.

        If 'nested' is true, the command will succeed even if 'directory' is
        already within an Arch source tree.
        """

    def in_source_tree(directory=None):
        """Is directory inside a Arch source tree?

        If directory is omitted, use the current working directory.
        """

    def tree_root(directory=None):
        """Return the SourceTree containing the given directory.

        If directory is omitted, use the current working directory.
        """


class ISourceTreeFactory(Interface):

    def __call__(root=None):
        """Create a source tree object for the given root path.

        `ForeignTree` if root does not point to a Arch source tree.
        `LibraryTree` if root is a tree in the revision library. `WorkingTree`
        if root is a Arch source tree outside of the revision library.

        If root is omitted, use the tree-root of the current working directory.
        """

class IArchSourceTree(IDirName):

    """Read-only operations on arch source trees."""

    tree_version = Attribute("""WRITEME, read-only""")

    tagging_method = Attribute("""WRITEME""")

    def iter_inventory(source=False, precious=False, backups=False,
                       junk=False, unrecognized=False, trees=False,
                       directories=False, files=False, both=False):
        """Iterator to traverse the source tree inventory.

        The kind of files looked for is specified by setting to True exactly
        one of the following keyword arguments:

            source, precious, backups, junk, unrecognized, trees.

        Whether files, directory or both should be listed is specified by
        setting to True exactly one of the following keyword arguments:

            directories, files, both.

        If trees=True, yield SourceTree objects.
        Otherwise, yield FileName or DirName objects.
        """

    def iter_inventory_ids(source=False, precious=False, backups=False,
                           junk=False, unrecognized=False, trees=False,
                           directories=False, files=False, both=False):
        """Like iter_inventory but yields tuples (id, x). Where x is the value
        yielded by iter_inventory, and id is the arch file id."""

    def get_tree():
        """WRITEME"""

    def iter_log_versions(limit=None, reverse=False):
        """Iterate over versions this tree has a patchlog from.

        @limit may be an instance of Archive, Category, Branch or
        Version. Only versions present in the limit will be iterated.
        """

    def iter_logs(version=None, reverse=False):
        """Iterate over patchlogs present in this tree.

        @version may be a Version instance. Only patchlog from this version
        will be iterated. Defaults to the tree_version.
        """


class IWorkingTree(IArchSourceTree):

    """Working source tree, Arch source tree which can be modified."""

    # TODO: "sync-tree" is ill-defined, must interface after fix

    tree_version = Attribute("WRITEME, read/write")

    tagging_method = Attribute("WRITEME, read/write")

    # TODO: "changes" is ill-named, must interface after rename

    def star_merge(from_=None):
        """WRITEME"""

    def undo(revision=None, output=None, quiet=False):
        """Undo and save changes in a project tree.

        Remove local changes since revision and save them as a
        changeset in path output (which must not already exist).
        Return the Changeset object.

        If revision is not specified, tree_version is used.

        If revision is specified as a Version, the latest ancestor of
        the project tree in that version is used.

        If output is not specified, an automatic name matching
        root/,,undo-* is used.
        """

    def redo(patch=None, keep=False, quiet=False):
        """Redo changes in a project tree.

        Apply patch to the project tree and delete patch.

        If patch is provided, it must be a Changeset object. Else, the highest
        numbered ,,undo-N directory in the project tree root is used.

        If keep is true, the patch directory is not deleted.
        """

    def add_tag(file):
        """WRITEME"""

    def move_tag(file):
        """WRITEME"""

    def move_file(file):
        """WRITEME"""

    def delete(file):
        """WRITEME"""

    def del_file(file):
        """WRITEME"""

    def del_tag(file):
        """WRITEME"""

    def import_(log=None):
        """Archive a full-source base-0 revision.

        If log is specified, it must be a LogMessage object or a file
        name as a string. If omitted, the default log message file of
        the tree is used.

        The --summary, --log-message and --setup options to tla are
        mere CLI convenience features and are not directly supported.
        """

    def commit(log=None, strict=False, seal=False, fix=False,
               out_of_date_ok=False, file_list=None):
        """Archive a changeset-based revision.

        If log is specified, it should be a LogMessage object. If
        ommited, the default log message file of the tree is used.

        strict, seal, fix and out_of_date_ok are boolean parameters
        equivalent to the tla options with similar names.

        If file_list is provided, it must be an iterable of strings,
        with at least one item, specifying names of files within the
        source tree. Only the changes in those files are commited. The
        file names can be absolute or relative to the tree root.

        The --summary and --log-message options to tla are mere CLI
        convenience features and are not directly supported.
        """

    def log_message(create=True):
        """Default log-message object used by import and commit.

        If `create` is False, and the standard log file does not already
        exists, return None. If `create` is True, use ``tla make-log`` if
        needed.
        """

    def add_log_version(version):
        """Add a patch log version to the project tree.

        Hum... does that have any use at all?
        """

    def remove_log_version(version):
        """Remove a patch log version from the project tree."""


    def replay():
        """Replay changesets into this working tree."""


### Changesets ###

class IChangesetFactory(Interface):

    """Create changeset objects."""

    def __call__(name):
        """WRITEME"""

class IChangeset(IDirName):

    """Arch whole-tree changeset."""

    def iter_mod_files(all=False):
        """Iterator over (id, orig, mod) tuples for files which are are
        patched, renamed, or have their permissions changed."""

    def iter_patched_files(all=False):
        """Iterate over (id, orig, mod) of patched files."""

    def patch_file(modname):
        """WRITEME"""

    def iter_renames():
        """Iterate over (id, orig, dest) triples representing renames.

        id is the persistant file tag, and the key of the dictionnary.
        orig is the name in the original tree.
        dest is the name in the modified tree.
        """

    def iter_created_files(all=False):
        """Iterator over tuples (id, dest) for created files."""

    def created_file(name):
        """WRITEME"""

    def iter_removed_files(all=False):
        """WRITEME"""

    def removed_file(self, name):
        """WRITEME"""

    def iter_created_dirs(self, all=False):
        """Iterator over tuples (id, dest) for created directories."""

    def iter_removed_dirs(self, all=False):
        """Iterator over tuples (id, orig) for removed directories."""


class IChangesetAPI(Interface):

    def changeset(orig, mod, dest):
        """Compute a whole-tree changeset.

        Create the output directory DESTINATION (it must not already exist).

        Compare the source trees ORIGINAL and MODIFIED (they may be source
        tree pathnames or instances or ArchSourceTree). Create a changeset
        tree in DESTINATION.
        """

### Miscellaneous ###

class IUserAPI(Interface):

    def my_id():
        """The current registered user id"""

    def set_my_id(new_id):
        """Set the current registered user id"""

    def default_archive():
        """Default Archive object or None."""


class IArchiveAPI(Interface):

    def make_archive(name, location, signed=False, listing=False):
        """Create and register new commitable archive.

        :param name: archive name (e.g. "david@allouche.net--2003b").
        :type name: `Archive` or str
        :param location: URL of the archive
        :type location: str
        :param signed: create GPG signatures for the archive contents.
        :type signed: bool
        :param listing: maintains ''.listing'' files to enable HTTP access.
        :type listing: bool

        :return: an `Archive` instance for the given name.
        :rtype: `Archive`

        :raise errors.NamespaceError: ``name`` is not a valid archive name.

        TODO: move to IArchiveCollection.create and nuke make_archive.
        """

    def register_archive(name, location):
        """Record the location of an archive.

        name: (string) archive name or None
        location: (string) URL of the archive
        return: Archive instance for the given (or guessed) name.

        If name is None, then the archive's name will be read automatically
        from the archive's meta data. This feature requires tla-1.1 or later.
        """

    def iter_archives():
        """Iterate over registered archives.
        TODO: this should be nuked and absorbed into IArchiveCollection. pyarch
        needs a Archives class to represent this."""

    def iter_library_archives():
        """Iterate over archives present in the revision library."""


    def make_continuation(source_revision, tag_version):
        """Setup tag_version and make a continuation tag of source_revision."""

    def get(revision, dir, link=False):
        """WRITEME"""

    def get_patch(revision, dir):
        """WRITEME"""


### Name Parsing ###

class INamePartParser(Interface):

    """Parser for parts of Arch namespace names."""

    def is_archive_name(s):
        """Is this string a valid archive name?"""

    def is_category_name(s):
        """Is this string a valid category name?

        Currently does the same thing as is_branch_name, but that might
        change in the future when the namespace evolves and it is more
        expressive to have different functions.
        """

    def is_branch_name(s):
        """Is this string a valid category name?

        Currently does the same thing as is_category_name, but that might
        change in the future when the namespace evolves and it is more
        expressive to have different functions.
        """

    def is_version_id(s):
        """Is this string a valid version id?"""

    def is_patchlevel(s):
        """Is this string a valid unqualified patch-level name?"""


class INameParserFactory(Interface):

    """Create Arch name parsers."""

    def __call__(s):
        """WRITEME"""


class INameParser(INamePartParser):

    """Parser for names in Arch archive namespace."""

    def is_category():
        """WRITEME"""

    def is_package():
        """WRITEME"""

    def is_version():
        """WRITEME"""

    def has_archive():
        """WRITEME"""

    def has_category():
        """WRITEME"""

    def has_package():
        """WRITEME"""

    def has_version():
        """WRITEME"""

    def has_patchlevel():
        """WRITEME"""

    def get_archive():
        """WRITEME"""

    def get_nonarch():
        """WRITEME"""

    def get_category():
        """WRITEME"""

    def get_branch():
        """WRITEME"""

    def get_package():
        """WRITEME"""

    def get_version():
        """WRITEME"""

    def get_package_version():
        """WRITEME"""

    def get_patchlevel():
        """WRITEME"""

### Exceptions ###

try:

    from arch.errors import TreeRootError
    from arch.errors import NamespaceError
    from arch.errors import ArchiveNotRegistered
    # TODO place class ArchiveAlreadyRegistered(ValueError) into arch.errors
    class ArchiveAlreadyRegistered(ValueError):
        """attempt to add an already present archive"""
        def __init__(self, name):
            message = "archive already registered or present: %s" % name
            Exception.__init__(self, message)
            self.name = name

    class CategoryAlreadyRegistered(ValueError):
        """attempt to add an already present category"""
        def __init__(self, name):
            message = "category already registered or present: %s" % name
            Exception.__init__(self, message)
            self.name = name

    class BranchAlreadyRegistered(ValueError):
        """attempt to add an already present branch"""
        def __init__(self, name):
            message = "branch already  present: %s" % name
            Exception.__init__(self, message)
            self.name = name

    class VersionAlreadyRegistered(ValueError):
        """attempt to add an already present version"""
        def __init__(self, name):
            message = "version already  present: %s" % name
            Exception.__init__(self, message)
            self.name = name

    class RevisionAlreadyRegistered(ValueError):
        """attempt to add an already present revision"""
        def __init__(self, name):
            message = "revision already present: %s" % name
            Exception.__init__(self, message)
            self.name = name

    class ArchiveNotRegistered(ValueError):
        """attempt to delete a non-existent archive"""
        def __init__(self, name):
            message = "archive not registered: %s" % name
            Exception.__init__(self, message)
            self.name = name

    class VersionNotRegistered(ValueError):
        """attempt to delete a non-existent version"""
        def __init__(self, name):
            message = "version not in the database: %s" % name
            Exception.__init__(self, message)
            self.name = name

    class RevisionNotRegistered(ValueError):
        """a non-existent revision"""
        def __init__(self, name):
            message = "revision not in the database: %s" % name
            Exception.__init__(self, message)
            self.name = name

    class ArchiveLocationDoublyRegistered(Exception):
        """A URL was in the ArchArchiveLocation table *twice*."""
        def __init__(self, name):
            message = "%s is listed as two seperate locations" % (name,)
            Exception.__init__(self, message)
            self.name = name

except ImportError:

    # Fallback to local definitions.
    # Those definitions must be kept in sync with PyArch.

    class TreeRootError(Exception):
        """Could not find the Arch tree-root of a directory."""
        def __init__(self, dirname):
            message = "directory is not in a project tree: %s" % (dirname,)
            Exception.__init__(self, message)
            self.dirname = str(dirname)

    class NamespaceError(Exception):
        """Invalid Arch namespace name, or incorrect kind of name.

        A value that does not make sense in the Arch namespace was
        provided, or the wrong kind of name was used, for example a
        revision where a patchlevel is expected.
        """
        def __init__(self, name, expected=None):
            if expected is None:
                message = "invalid name: %s" % (name,)
            else:
                message = "invalid %s: %s" % (expected, name)
            Exception.__init__(self, message)
            self.name = name
            self.expected = expected

    class ArchiveNotRegistered(Exception):
        """Tried to access an unregistered archive."""
        def __init__(self, name):
            message = "archive not registered: %s" % (name,)
            Exception.__init__(self, message)
            self.name = name

    class ArchiveAlreadyRegistered(ValueError):
        """attempt to add an already present archive"""
        def __init__(self, name):
            message = "archive already registered or present: %s" % name
            Exception.__init__(self, message)
            self.name = name


### Interface declarations ###

def pyarch_implements():
    """Declares the implementation of interfaces in this module by PyArch."""
    import arch
    from zope.interface import classImplements
    from zope.interface import directlyProvides
    def plusDirectlyProvides(cls, *interfaces):
        # directlyProvides overrides, plusDirectlyProvides extends.
        from zope.interface import directlyProvidedBy
        directlyProvides(cls, directlyProvidedBy(cls), *interfaces)
    # namespace
    classImplements(arch.NamespaceObject, INamespaceObject)
    classImplements(arch.RevisionIterable, IRevisionIterable)
    classImplements(arch.VersionIterable, IVersionIterable)
    classImplements(arch.BranchIterable, IBranchIterable)
    classImplements(arch.CategoryIterable, ICategoryIterable)
    classImplements(arch.ArchiveItem, IArchiveItem)
    classImplements(arch.CategoryItem, ICategoryItem)
    classImplements(arch.BranchItem, IBranchItem)
    classImplements(arch.VersionItem, IVersionItem)
    classImplements(arch.Setupable, ISetupable)
    classImplements(arch.Package, IPackage)
    # obsoleted interface TODO implment IArchiveCollection for pyarch. plusDirectlyProvides(arch.Archive, IArchiveFactory)
    classImplements(arch.Archive, IArchive)
    plusDirectlyProvides(arch.Category, ICategoryFactory)
    classImplements(arch.Category, ICategory)
    plusDirectlyProvides(arch.Branch, IBranchFactory)
    classImplements(arch.Branch, IBranch)
    plusDirectlyProvides(arch.Version, IVersionFactory)
    classImplements(arch.Version, IVersion)
    plusDirectlyProvides(arch.Revision, IRevisionFactory)
    classImplements(arch.Revision, IRevision)
    # patch logs
    plusDirectlyProvides(arch.Patchlog, IPatchlogFactory)
    classImplements(arch.Patchlog, IPatchlog)
    plusDirectlyProvides(arch.LogMessage, ILogMessageFactory)
    classImplements(arch.LogMessage, ILogMessage)
    # file name utilities
    plusDirectlyProvides(arch.PathName, IPathNameFactory)
    classImplements(arch.PathName, IPathName)
    classImplements(arch.DirName, IDirName)
    classImplements(arch.FileName, IFileName)
    # source trees
    plusDirectlyProvides(arch, ISourceTreeAPI)
    plusDirectlyProvides(arch.SourceTree, ISourceTreeFactory)
    classImplements(arch.ArchSourceTree, IArchSourceTree)
    classImplements(arch.WorkingTree, IWorkingTree)
    # changesets
    plusDirectlyProvides(arch.Changeset, IChangesetFactory)
    classImplements(arch.Changeset, IChangeset)
    plusDirectlyProvides(arch, IChangesetAPI)
    # miscellaneous
    plusDirectlyProvides(arch, IUserAPI, IArchiveAPI)
    # name parsing
    plusDirectlyProvides(arch.NameParser, INamePartParser, INameParserFactory)
    classImplements(arch.NameParser, INameParser)


try:
    import arch
except ImportError:
    pass
else:
    pyarch_implements()

class RCSTypeEnum:
    cvs = 1
    svn = 2
    arch = 3
    package = 4
    bitkeeper = 5

RCSNames = {1: 'cvs', 2: 'svn', 3: 'arch', 4: 'package', 5: 'bitkeeper'}


