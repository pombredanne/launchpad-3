# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Public webservice interface for the collection of Launchpad branches."""

__metaclass__ = type
__all__ = [
    'IBranches',
    ]


from lazr.restful.declarations import (
    call_with, collection_default_content, export_as_webservice_collection,
    export_read_operation, operation_parameters, operation_returns_entry,
    REQUEST_USER)

from zope.schema import TextLine
from zope.interface import Interface

from canonical.launchpad import _
from lp.code.interfaces.branch import IBranch


class IBranches(Interface):
    """Top-level collection of branches."""

    export_as_webservice_collection(IBranch)

    @operation_parameters(
        unique_name=TextLine(title=_('Branch unique name'), required=True))
    # Actually IBranch. See _schema_circular_imports.
    @operation_returns_entry(IBranch)
    @export_read_operation()
    def getByUniqueName(unique_name):
        """Find a branch by its ~owner/product/name unique name.

        Return None if no match was found.
        """

    @operation_parameters(
        url=TextLine(title=_('Branch URL'), required=True))
    # Actually IBranch. See _schema_circular_imports.
    @operation_returns_entry(IBranch)
    @export_read_operation()
    def getByUrl(url):
        """Find a branch by URL.

        Either from the external specified in Branch.url, from the URL on
        http://bazaar.launchpad.net/ or the lp: URL.

        Return None if no match was found.
        """

    @call_with(user=REQUEST_USER)
    @collection_default_content()
    def getBranches(user, limit=50):
        """Return a collection of branches."""
