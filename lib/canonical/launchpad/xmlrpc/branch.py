# Copyright 2006 Canonical Ltd.  All rights reserved.

# Disable pylint 'should have "self" as first argument' warnings.
# pylint: disable-msg=E0213

"""Branch XMLRPC API."""

__metaclass__ = type
__all__ = [
    'BranchSetAPI', 'IBranchSetAPI', 'IPublicCodehostingAPI',
    'PublicCodehostingAPI']

import os

from zope.component import getUtility
from zope.interface import Interface, implements

from canonical.config import config
from canonical.launchpad.interfaces import (
    BranchCreationException, BranchCreationForbidden, BranchType, IBranch,
    IBranchSet, IBugSet,
    ILaunchBag, IPersonSet, IProductSet, NotFoundError)
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.webapp import LaunchpadXMLRPCView, canonical_url
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.uri import URI
from canonical.launchpad.xmlrpc import faults


class IBranchSetAPI(Interface):
    """An XMLRPC interface for dealing with branches.

    This XML-RPC interface was introduced to support Bazaar 0.8-2, which is
    included in Ubuntu 6.06. This interface cannot be removed until Ubuntu
    6.06 is end-of-lifed.
    """

    def register_branch(branch_url, branch_name, branch_title,
                        branch_description, author_email, product_name):
        """Register a new branch in Launchpad."""

    def link_branch_to_bug(branch_url, bug_id, whiteboard):
        """Link the branch to the bug."""


class BranchSetAPI(LaunchpadXMLRPCView):

    implements(IBranchSetAPI)

    def register_branch(self, branch_url, branch_name, branch_title,
                        branch_description, author_email, product_name):
        """See IBranchSetAPI."""
        owner = getUtility(ILaunchBag).user
        assert owner is not None, (
            "register_branch shouldn't be accessible to unauthenicated"
            " requests.")
        if product_name:
            product = getUtility(IProductSet).getByName(product_name)
            if product is None:
                return faults.NoSuchProduct(product_name)
        else:
            product = None

        # Branch URLs in Launchpad do not end in a slash, so strip any
        # slashes from the end of the URL.
        branch_url = branch_url.rstrip('/')

        branch_set = getUtility(IBranchSet)
        existing_branch = branch_set.getByUrl(branch_url)
        if existing_branch is not None:
            return faults.BranchAlreadyRegistered(branch_url)

        try:
            unicode_branch_url = branch_url.decode('utf-8')
            url = IBranch['url'].validate(unicode_branch_url)
        except LaunchpadValidationError, exc:
            return faults.InvalidBranchUrl(branch_url, exc)

        # We want it to be None in the database, not ''.
        if not branch_description:
            branch_description = None
        if not branch_title:
            branch_title = None

        if not branch_name:
            branch_name = branch_url.split('/')[-1]

        if author_email:
            author = getUtility(IPersonSet).getByEmail(author_email)
        else:
            author = owner
        if author is None:
            return faults.NoSuchPerson(
                type="author", email_address=author_email)

        try:
            if branch_url:
                branch_type = BranchType.MIRRORED
            else:
                branch_type = BranchType.HOSTED
            branch = branch_set.new(
                branch_type=branch_type,
                name=branch_name, registrant=owner, owner=owner,
                product=product, url=branch_url, title=branch_title,
                summary=branch_description, author=author)
            if branch_type == BranchType.MIRRORED:
                branch.requestMirror()
        except BranchCreationForbidden:
            return faults.BranchCreationForbidden(product.displayname)
        except BranchCreationException, err:
            return faults.BranchNameInUse(err)

        return canonical_url(branch)

    def link_branch_to_bug(self, branch_url, bug_id, whiteboard):
        """See IBranchSetAPI."""
        branch = getUtility(IBranchSet).getByUrl(url=branch_url)
        if branch is None:
            return faults.NoSuchBranch(branch_url)
        try:
            bug = getUtility(IBugSet).get(bug_id)
        except NotFoundError:
            return faults.NoSuchBug(bug_id)
        if not whiteboard:
            whiteboard = None

        # Since this API is controlled using launchpad.AnyPerson there must be
        # an authenticated person, so use this person as the registrant.
        registrant = getUtility(ILaunchBag).user
        bug.addBranch(branch, registrant=registrant, whiteboard=whiteboard)
        return canonical_url(bug)


class IPublicCodehostingAPI(Interface):
    """The public codehosting API."""

    def resolve_lp_path(path):
        """Expand the path segment of an lp: URL into a list of branch URLs.

        This method is added to support Bazaar 0.93. It cannot be removed
        until we stop supporting Bazaar 0.93.

        :return: A dict containing a single 'urls' key that maps to a list of
            URLs. Clients should use the first URL in the list that they can
            support.
        """


class _NonexistentBranch:
    """Used to represent a branch that was requested but doesn't exist."""

    def __init__(self, unique_name):
        self.unique_name = unique_name
        self.branch_type = None


class PublicCodehostingAPI(LaunchpadXMLRPCView):
    """See `IPublicCodehostingAPI`."""

    implements(IPublicCodehostingAPI)

    supported_schemes = 'bzr+ssh', 'http'

    def _getBazaarHost(self):
        """Return the hostname for the codehosting server."""
        return URI(config.codehosting.supermirror_root).host

    def _getSeriesBranch(self, series):
        """Return the branch for the given series.

        :return: `faults.NoBranchForSeries` if there is no such branch, or if
            the branch is invisible to the user. Return the Branch object
            otherwise.
        """
        branch = series.series_branch
        if (branch is None
            or not check_permission('launchpad.View', branch)):
            return faults.NoBranchForSeries(series)
        return branch

    def _getBranchForProject(self, project_name):
        """Return the branch for the development focus of the given project.

        :param project_name: The name of a Launchpad project.
        :return: `faults.NoSuchProduct` if there's no project by that name.
            Return the Branch object otherwise.
        """
        project = getUtility(IProductSet).getByName(project_name)
        if project is None:
            return faults.NoSuchProduct(project_name)
        series = project.development_focus
        return self._getSeriesBranch(series)

    def _getBranchForSeries(self, project_name, series_name):
        """Return the branch for the given series on the given project.

        :param project_name: The name of a Launchpad project.
        :param series_name: The name of a series on that project.
        :return: The branch for that series. Otherwise, return an appropriate
            fault if the project or the series do not exist.
        """
        project = getUtility(IProductSet).getByName(project_name)
        if project is None:
            return faults.NoSuchProduct(project_name)
        series = project.getSeries(series_name)
        if series is None:
            return faults.NoSuchSeries(series_name, project)
        return self._getSeriesBranch(series)

    def _getBranch(self, unique_name):
        """Return the branch specified by the given unique name.

        :param unique_name: A string of the form "~user/project/branch".
        :return: The corresponding Branch object if the branch exists, a
            _NonexistentBranch stub object if the branch does not exist. If
            unique_name is invalid, return a `faults.InvalidBranchIdentifier`.
        """
        if unique_name[0] != '~':
            return faults.InvalidBranchIdentifier(unique_name)
        branch = getUtility(IBranchSet).getByUniqueName(unique_name)
        if check_permission('launchpad.View', branch):
            return branch
        else:
            return None

    def _getNonexistentBranch(self, unique_name):
        """Return an appropriate response for a non-existent branch.

        :param unique_name: A string of the form "~user/project/branch".
        :return: A _NonexistentBranch object if the user and project exist, an
            appropriate fault if either does not.
        """
        owner_name, project_name, branch_name = unique_name[1:].split('/')
        owner = getUtility(IPersonSet).getByName(owner_name)
        if owner is None:
            return faults.NoSuchPersonWithUsername(owner_name)
        if project_name != '+junk':
            project = getUtility(IProductSet).getByName(project_name)
            if project is None:
                return faults.NoSuchProduct(project_name)
        return _NonexistentBranch(unique_name)

    def _getResultDict(self, branch, suffix=None):
        """Return a result dict with a list of URLs for the given branch.

        :param branch: A Branch object or a _NonexistentBranch object.
        :param suffix: The section of the path that follows the branch
            specification.
        :return: {'urls': [list_of_branch_urls]}.
        """
        if branch.branch_type == BranchType.REMOTE:
            return dict(urls=[branch.url])
        else:
            result = dict(urls=[])
            host = self._getBazaarHost()
            for scheme in self.supported_schemes:
                path = '/' + branch.unique_name
                if suffix is not None:
                    path = os.path.join(path, suffix)
                result['urls'].append(
                    str(URI(host=host, scheme=scheme, path=path)))
            return result

    def resolve_lp_path(self, path):
        """See `IPublicCodehostingAPI`."""
        strip_path = path.strip('/')
        if strip_path == '':
            return faults.InvalidBranchIdentifier(path)
        path_segments = strip_path.split('/', 3)
        suffix = None
        if len(path_segments) == 1:
            [project_name] = path_segments
            result = self._getBranchForProject(project_name)
        elif len(path_segments) == 2:
            project_name, series_name = path_segments
            result = self._getBranchForSeries(project_name, series_name)
        elif len(path_segments) == 3:
            result = self._getBranch(strip_path)
        else:
            suffix = path_segments.pop()
            result = self._getBranch('/'.join(path_segments))

        if result is None:
            result = self._getNonexistentBranch(strip_path)

        if isinstance(result, faults.LaunchpadFault):
            return result
        else:
            return self._getResultDict(result, suffix)
