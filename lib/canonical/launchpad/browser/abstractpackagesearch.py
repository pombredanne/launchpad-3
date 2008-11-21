# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'AbstractPackageSearchView'
    ]

from canonical.launchpad.webapp.batching import BatchNavigator

class AbstractPackageSearchView:
    """A common package search interface
    
    Used by DistributionPackageSearchView, DistroSeriesPackageSearchView and
    DistroArchSeriesPackageSearchView
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.text = self.request.get("text", None)
        self.matches = 0
        self.detailed = True
        self._results = None

        self.search_requested = False
        if self.text:
            self.search_requested = True
            results = self.search_results()
            self.matches = len(results)
            if self.matches > 5:
                self.detailed = False
            else:
                self.detailed = True

            self.batchnav = BatchNavigator(results, self.request)

    def search_results(self):
        """Search for packages matching the request text.
        
        Try to find the packages that match the given text, then present
        those as a list. Cache previous results so the search is only done
        once.
        """
        if self._results is None:
            self._results = self.context_specific_search()
        return self._results

    def context_specific_search(self):
        """Calls the context specific search.
        
        To be overridden by subclass.
        """
        raise TypeError(
            "do_context_specific_search needs to be implemented in sub-class"
            )
