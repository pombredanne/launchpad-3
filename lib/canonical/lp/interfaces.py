from zope.interface import Interface

class IBatchNavigator(Interface):

    def prevBatchURL():
        """Return a URL to the previous chunk of results."""

    def nextBatchURL():
        """Return a URL to the next chunk of results."""

    def batchPageURLs():
        """Return a list of links representing URLs to pages of
        results."""
