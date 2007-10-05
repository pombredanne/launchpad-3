# Copyright 2005 Canonical Ltd.  All rights reserved.

"""CVE views."""

__metaclass__ = type

__all__ = [
    'CveSetNavigation',
    'CveContextMenu',
    'CveSetContextMenu',
    'CveLinkView',
    'CveUnlinkView',
    'CveSetView',
    ]

from zope.component import getUtility

from canonical.launchpad.webapp.batching import BatchNavigator

from canonical.launchpad.interfaces import ICve, ICveSet, ILaunchBag, IBug
from canonical.launchpad.validators.cve import valid_cve

from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, GetitemNavigation)
from canonical.launchpad.webapp.generalform import GeneralFormView


class CveSetNavigation(GetitemNavigation):

    usedfor = ICveSet

    def breadcrumb(self):
        return "CVE reports"

class CveContextMenu(ContextMenu):

    usedfor = ICve
    links = ['linkbug', 'unlinkbug']

    def linkbug(self):
        text = 'Link to bug'
        return Link('+linkbug', text, icon='edit')

    def unlinkbug(self):
        enabled = bool(self.context.bugs)
        text = 'Remove bug link'
        return Link('+unlinkbug', text, icon='edit', enabled=enabled)


class CveSetContextMenu(ContextMenu):

    usedfor = ICveSet
    links = ['findcve', 'allcve']

    def allcve(self):
        text = 'All registered CVEs'
        return Link('+all', text)

    def findcve(self):
        text = 'Find CVEs'
        summary = 'Find CVEs in Launchpad'
        return Link('', text, summary)


class CveLinkView(GeneralFormView):
    """This view will be used for objects that can be linked to a CVE,
    currently that is only IBug.
    """

    def __init__(self, context, request):
        self._nextURL = canonical_url(context)
        GeneralFormView.__init__(self, context, request)

    def process(self, sequence):
        cve = getUtility(ICveSet)[sequence]
        if cve is None:
            return '%s is not a known CVE sequence number.' % sequence
        user = getUtility(ILaunchBag).user
        self.context.bug.linkCVE(cve, user)
        return 'CVE-%s added.' % sequence


class CveUnlinkView(GeneralFormView):
    """This view is used to unlink a CVE from a bug."""

    def __init__(self, context, request):
        self._nextURL = canonical_url(context)
        GeneralFormView.__init__(self, context, request)

    def process(self, sequence):
        cve = getUtility(ICveSet)[sequence]
        if cve is None:
            return '%s is not a known CVE sequence number.' % sequence
        user = getUtility(ILaunchBag).user
        self.context.bug.unlinkCVE(cve, user)
        return 'CVE-%s removed.' % sequence


class CveSetView:

    __used_for__ = ICveSet

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.notices = []
        self.results = None
        self.text = self.request.form.get('text', None)
        self.searchrequested = False

        if self.text:
            self.pre_search()

    def getAllBatched(self):
        return BatchNavigator(self.context.getAll(), self.request)

    def pre_search(self):
        # see if we have an exact match, and redirect if so; otherwise,
        # do a search for it.
        sequence = self.text
        if sequence[:4].lower() in ['cve-', 'can-']:
            sequence = sequence[4:].strip()
        if valid_cve(sequence):
            # try to find the CVE, and redirect to it if we do
            cveset = getUtility(ICveSet)
            cve = cveset[sequence]
            if cve:
                self.request.response.redirect(canonical_url(cve))
        self.searchrequested = True

    def searchresults(self):
        """Use searchtext to find the list of Products that match
        and then present those as a list. Only do this the first
        time the method is called, otherwise return previous results.
        """
        if self.results is None:
            self.results = self.context.search(text=self.text)
            self.matches = self.results.count()
        return self.results
