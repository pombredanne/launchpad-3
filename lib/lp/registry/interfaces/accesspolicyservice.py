# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for access policy service."""


__metaclass__ = type

__all__ = [
    'IAccessPolicyService',
    ]

from lazr.restful.declarations import (
    export_as_webservice_entry,
    export_read_operation,
    export_write_operation,
    operation_for_version,
    operation_parameters,
    )
from lazr.restful.fields import Reference

from lp import _
from lp.app.interfaces.services import IService
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.product import IProduct


class IAccessPolicyService(IService):

    # XXX 2012-02-24 wallyworld bug 939910
    # Need to export for version 'beta' even though we only want to use it in
    # version 'devel'
    export_as_webservice_entry(publish_web_link=False, as_of='beta')

    @export_read_operation()
    @operation_for_version('devel')
    def getAccessPolicies():
        """Return the access policy types."""

    @export_read_operation()
    @operation_parameters(
        product=Reference(IProduct, title=_('Product'), required=True))
    @operation_for_version('devel')
    def getProductObservers(product):
        """Return people/teams who can see product artifacts."""

    @export_write_operation()
    @operation_parameters(
        product=Reference(IProduct, title=_('Product'), required=True),
        observer=Reference(IPerson, title=_('Observer'), required=True))
    @operation_for_version('devel')
    def deleteProductObserver(product, observer):
        """Remove an observer from a product."""
