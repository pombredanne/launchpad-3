# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Entitlement XMLRPC API."""

__metaclass__ = type
__all__ = ['IEntitlementSetAPI', 'EntitlementSetAPI']

import xmlrpclib

from zope.component import getUtility
from zope.interface import Interface, implements

from canonical.launchpad.interfaces import (
    IEntitlement, ILaunchBag, IProductSet, IPersonSet, NotFoundError)
from canonical.launchpad.webapp import LaunchpadXMLRPCView, canonical_url
from canonical.launchpad.xmlrpc import faults
from canonical.lp.dbschema import EntitlementStatus


class IEntitlementAPI(Interface):
    """An XMLRPC interface for dealing with entitlements."""

    def create_entitlement(person_id, entitlement_id, entitlement_type,
                           quota, state):
        """Create a new entitlement in Launchpad."""

    def update_entitlement(person_id, entitlement_id,
                           entitlement_type=None,
                           quota=None,
                           amount_used=None,
                           state=None):
        """Update an entitlement in Launchpad."""


class IEntitlementAPI(LaunchpadXMLRPCView):

    implements(IEntitlementAPI)

    def create_entitlement(self, person_id, external_id,
                           entitlement_type, quota,
                           state):
        """See IEntitlementAPI."""
        user = getUtility(ILaunchBag).user
        assert user is not None, (
            "Creating an entitlement is not accessible to "
            "unathenticated requests.")

        owner = getUtility(IPersonSet).get(person_id)
        if owner is None:
            return faults.NoSuchPersonOrTeam(name=person_id)

        if external_id is None:
            return faults.RequiredParameterMissing(
                parameter_name="external_id")

        if quota is None:
            return faults.RequiredParameterMissing(
                parameter_name="quota")

        if state is None:
            return faults.RequiredParameterMissing(
                parameter_name="state")


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

        branch = getUtility(IBranchSet).new(
            name=branch_name, owner=owner, product=product, url=branch_url,
            title=branch_title, summary=branch_description, author=author)

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
