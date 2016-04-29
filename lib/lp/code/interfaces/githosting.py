# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for communication with the Git hosting service."""

__metaclass__ = type
__all__ = [
    'IGitHostingClient',
    ]

from zope.interface import Interface


class IGitHostingClient(Interface):
    """Interface for the internal API provided by the Git hosting service."""

    def create(path, clone_from=None):
        """Create a Git repository.

        :param path: Physical path of the new repository on the hosting
            service.
        :param clone_from: If not None, clone the new repository from this
            other physical path.
        """

    def getProperties(path):
        """Get properties of this repository.

        :param path: Physical path of the repository on the hosting service.
        :return: A dict of properties.
        """

    def setProperties(path, **props):
        """Set properties of this repository.

        :param path: Physical path of the repository on the hosting service.
        :param props: Properties to set.
        """

    def getRefs(path):
        """Get all refs in this repository.

        :param path: Physical path of the repository on the hosting service.
        :return: A dict mapping ref paths to dicts representing the objects
            they point to.
        """

    def getCommits(path, commit_oids, logger=None):
        """Get details of a list of commits.

        :param path: Physical path of the repository on the hosting service.
        :param commit_oids: A list of commit OIDs.
        :param logger: An optional logger.
        :return: A list of dicts each of which represents one of the
            requested commits.  Non-existent commits will be omitted.
        """

    def getMergeDiff(path, base, head, logger=None):
        """Get the merge preview diff between two commits.

        :param path: Physical path of the repository on the hosting service.
        :param base: The OID of the base commit.
        :param head: The OID of the commit that we want to merge into
            'base'.
        :param logger: An optional logger.
        :return: A dict mapping 'commits' to a list of commits between
            'base' and 'head' (formatted as with `getCommits`), 'patch' to
            the text of the diff between 'base' and 'head', and 'conflicts'
            to a list of conflicted paths.
        """

    def detectMerges(path, target, sources, logger=None):
        """Detect merges of any of 'sources' into 'target'.

        :param path: Physical path of the repository on the hosting service.
        :param target: The OID of the merge proposal target commit.
        :param sources: The OIDs of the merge proposal source commits.
        :param logger: An optional logger.
        :return: A dict mapping merged commit OIDs from 'sources' to the
            first commit OID in the left-hand (first parent only) history of
            'target' that is a descendant of the corresponding source
            commit.  Unmerged commits are omitted.
        """

    def delete(path, logger=None):
        """Delete a repository.

        :param path: Physical path of the repository on the hosting service.
        :param logger: An optional logger.
        """

    def getBlob(self, path, filename, rev=None, logger=None):
        """Get a blob by file name from a repository.

        :param path: Physical path of the repository on the hosting service.
        :param filename: Relative path of a file in the repository.
        :param rev: An optional revision. Defaults to 'HEAD'.
        :param logger: An optional logger.
        :return: A dict with keys 'data' and 'size'.
        """
