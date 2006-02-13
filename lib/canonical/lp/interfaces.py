# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute

class IBatchNavigator(Interface):

    batch = Attribute("The IBatch for which navigation links are provided.")

    def prevBatchURL():
        """Return a URL to the previous chunk of results."""

    def nextBatchURL():
        """Return a URL to the next chunk of results."""

    def batchPageURLs():
        """Return a list of links representing URLs to pages of
        results."""


class ITableBatchNavigator(IBatchNavigator):
    """A batch navigator for tabular listings."""

    # This attribute reads well in ZPT, e.g.:
    #
    # <tal:foo condition="batch_nav/show_column/foo">
    show_column = Attribute(
        "A dict keyed by column name. If the value is True, that column will "
        "be shown in the list, otherwise it won't.")
