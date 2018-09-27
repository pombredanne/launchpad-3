# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utility for looking up Git repositories by name."""

__metaclass__ = type
__all__ = [
    'IGitLookup',
    'IGitRuleGrantLookup',
    'IGitTraversable',
    'IGitTraverser',
    ]

from zope.interface import Interface


class IGitTraversable(Interface):
    """A thing that can be traversed to find a thing with a Git repository."""

    def traverse(owner, name, segments):
        """Return the object beneath this one that matches 'name'.

        :param owner: The current `IPerson` context, or None.
        :param name: The name of the object being traversed to.
        :param segments: An iterator over remaining path segments.
        :return: A tuple of
            * an `IPerson`, or None;
            * an `IGitTraversable`;
            * an `IGitRepository`, or None; if this is non-None then
              traversing should stop.
        """


class IGitTraverser(Interface):
    """Utility for traversing to an object that can have a Git repository."""

    def traverse(segments, owner=None):
        """Traverse to the object referred to by a prefix of the 'segments'
        iterable, starting from 'owner' if given.

        :raises InvalidNamespace: If the path cannot be parsed as a
            repository namespace.
        :raises InvalidProductName: If the project component of the path is
            not a valid name.
        :raises NoSuchGitRepository: If there is a '+git' segment, but the
            following segment doesn't match an existing Git repository.
        :raises NoSuchPerson: If the first segment of the path begins with a
            '~', but we can't find a person matching the remainder.
        :raises NoSuchProduct: If we can't find a project that matches the
            project component of the path.
        :raises NoSuchSourcePackageName: If the source package referred to
            does not exist.

        :return: A tuple of::
            * an `IPerson`, or None;
            * an `IHasGitRepositories`;
            * an `IGitRepository`, or None;
            * a trailing path segment, or None.
        """

    def traverse_path(path):
        """Traverse to the object referred to by 'path'.

        All segments of 'path' must be consumed.

        :raises InvalidNamespace: If the path cannot be parsed as a
            repository namespace.
        :raises InvalidProductName: If the project component of the path is
            not a valid name.
        :raises NoSuchGitRepository: If there is a '+git' segment, but the
            following segment doesn't match an existing Git repository.
        :raises NoSuchPerson: If the first segment of the path begins with a
            '~', but we can't find a person matching the remainder.
        :raises NoSuchProduct: If we can't find a project that matches the
            project component of the path.
        :raises NoSuchSourcePackageName: If the source package referred to
            does not exist.

        :return: A tuple of::
            * an `IPerson`, or None;
            * an `IHasGitRepositories`;
            * an `IGitRepository`, or None.
        """


class IGitLookup(Interface):
    """Utility for looking up a Git repository by name."""

    def get(repository_id, default=None):
        """Return the repository with the given id.

        Return the default value if there is no such repository.
        """

    def getByHostingPath(path):
        """Get information about a given path on the hosting backend.

        :return: An `IGitRepository`, or None.
        """

    def getByUniqueName(unique_name):
        """Find a repository by its unique name.

        Unique names have one of the following forms:
            ~OWNER/PROJECT/+git/NAME
            ~OWNER/DISTRO/+source/SOURCE/+git/NAME
            ~OWNER/+git/NAME

        :return: An `IGitRepository`, or None.
        """

    def uriToPath(uri):
        """Return the path for the URI, if the URI is on codehosting.

        This does not ensure that the path is valid.

        :param uri: An instance of lazr.uri.URI
        :return: The path if possible; None if the URI is not a valid
            codehosting URI.
        """

    def getByUrl(url):
        """Find a repository by URL.

        Either from the URL on git.launchpad.net (various schemes) or the
        lp: URL (which relies on client-side configuration).
        """

    def getByPath(path):
        """Find a repository by its path.

        Any of these forms may be used, with or without a leading slash:
            Unique names:
                ~OWNER/PROJECT/+git/NAME
                ~OWNER/DISTRO/+source/SOURCE/+git/NAME
                ~OWNER/+git/NAME
            Owner-target default aliases:
                ~OWNER/PROJECT
                ~OWNER/DISTRO/+source/SOURCE
            Official aliases:
                PROJECT
                DISTRO/+source/SOURCE

        :return: A tuple of (`IGitRepository`, extra_path), or (None, _).
            'extra_path' may be used by applications that need to traverse a
            leading part of a path as a repository, such as external code
            browsers.
        """
