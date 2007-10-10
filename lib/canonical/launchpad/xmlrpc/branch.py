# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Branch XMLRPC API."""

__metaclass__ = type
__all__ = [
    'BranchSetAPI', 'IBranchSetAPI', 'IPublicCodehostingAPI',
    'PublicCodehostingAPI']

from zope.component import getUtility
from zope.interface import Interface, implements
from zope.security.interfaces import Unauthorized

from canonical.config import config
from canonical.launchpad.interfaces import (
    BranchCreationForbidden, BranchType, IBranch, IBranchSet, IBugSet,
    ILaunchBag, IPersonSet, IProductSet, NotFoundError)
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.webapp import LaunchpadXMLRPCView, canonical_url
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.uri import URI
from canonical.launchpad.xmlrpc import faults


class IBranchSetAPI(Interface):
    """An XMLRPC interface for dealing with branches."""

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

        existing_branch = getUtility(IBranchSet).getByUrl(branch_url)
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

        if product is None:
            unique_name = '~%s/+junk/%s' % (owner.name, branch_name)
        else:
            unique_name = '~%s/%s/%s' % (owner.name, product.name, branch_name)
        if getUtility(IBranchSet).getByUniqueName(unique_name) is not None:
            return faults.BranchUniqueNameConflict(unique_name)

        try:
            if branch_url:
                branch_type = BranchType.MIRRORED
            else:
                branch_type = BranchType.HOSTED
            branch = getUtility(IBranchSet).new(
                branch_type=branch_type,
                name=branch_name, creator=owner, owner=owner, product=product,
                url=branch_url, title=branch_title,
                summary=branch_description, author=author)
            if branch_type == BranchType.MIRRORED:
                branch.requestMirror()
        except BranchCreationForbidden:
            return faults.BranchCreationForbidden(product.displayname)

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

        bug.addBranch(branch, whiteboard=whiteboard)
        return canonical_url(bug)


class IPublicCodehostingAPI(Interface):
    """The public codehosting API."""

    def resolve_lp_path(path):
        """Expand the given lp: into a hostname and path, along with allowed
        protocols for that resource.
        """

class PublicCodehostingAPI(LaunchpadXMLRPCView):
    """See `IPublicCodehostingAPI`."""

    implements(IPublicCodehostingAPI)

    # XXX: Move supported protocols to config param?
    supported_schemes = 'bzr+ssh', 'sftp', 'http'

    def _get_bazaar_host(self):
        return URI(config.codehosting.supermirror_root).host

    def _get_series_branch(self, series):
        branch = series.series_branch
        if (branch is None
            or not check_permission('launchpad.View', branch)):
            return faults.NoBranchForSeries(series)
        return branch

    def _get_branch_for_project(self, project_name):
        project = getUtility(IProductSet).getByName(project_name)
        if project is None:
            return faults.NoSuchProduct(project_name)
        series = project.development_focus
        return self._get_series_branch(series)

    def _get_branch_for_series(self, project_name, series_name):
        project = getUtility(IProductSet).getByName(project_name)
        if project is None:
            return faults.NoSuchProduct(project_name)
        series = project.getSeries(series_name)
        if series is None:
            return faults.NoSuchSeries(series_name, project)
        return self._get_series_branch(series)

    def _get_branch(self, unique_name):
        if unique_name[0] != '~':
            return faults.InvalidBranchIdentifier(unique_name)
        branch = getUtility(IBranchSet).getByUniqueName(unique_name)
        if branch is None:
            return faults.NoSuchBranch(unique_name)
        return branch

    def resolve_lp_path(self, path):
        strip_path = path.strip('/')
        if strip_path == '':
            return faults.InvalidBranchIdentifier(path)
        path_segments = strip_path.split('/')
        if len(path_segments) == 1:
            [project_name] = path_segments
            result = self._get_branch_for_project(project_name)
        elif len(path_segments) == 2:
            project_name, series_name = path_segments
            result = self._get_branch_for_series(project_name, series_name)
        elif len(path_segments) == 3:
            result = self._get_branch(strip_path)
        else:
            return faults.InvalidBranchIdentifier(path)
        if isinstance(result, faults.LaunchpadFault):
            return result
        else:
            try:
                return dict(
                    host=self._get_bazaar_host(),
                    path=result.unique_name,
                    supported_schemes=self.supported_schemes)
            except Unauthorized:
                return faults.NoSuchBranch(strip_path)
