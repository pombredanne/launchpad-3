# Copyright 2005 Canonical Ltd.  All rights reserved.

"""CVE views."""

__metaclass__ = type

__all__ = [
    'CveSetNavigation',
    'CveContextMenu',
    'CveSetContextMenu',
    'CveView',
    'CveLinkView',
    'CveUnlinkView',
    'CveSetView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import ICve, ICveSet, ILaunchBag, IBug
from canonical.launchpad.validators.cve import valid_cve
from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, GetitemNavigation)
from canonical.launchpad.webapp.generalform import GeneralFormView


class CveSetNavigation(GetitemNavigation):

    usedfor = ICveSet


class CveContextMenu(ContextMenu):

    usedfor = ICve
    links = ['linkbug', 'unlinkbug']

    def linkbug(self):
        text = 'Link to Bug'
        return Link('+linkbug', text, icon='edit')

    def unlinkbug(self):
        enabled = bool(self.context.bugs)
        text = 'Remove Bug Link'
        return Link('+unlinkbug', text, icon='edit', enabled=enabled)


class CveSetContextMenu(ContextMenu):

    usedfor = ICveSet
    links = ['allcve']

    def allcve(self):
        text = 'All Registered CVE'
        return Link('+all', text)


class CveView:

    __used_for__ = ICve

    def __init__(self, context, request):
        self.context = context
        self.request = request


class CveLinkView(GeneralFormView):
    """This view will be used for objects that can be linked to a CVE,
    currently that is only IBug.
    """

    def __init__(self, context, request):
        self._nextURL = canonical_url(context)
        context = IBug(context)
        GeneralFormView.__init__(self, context, request)

    def process(self, sequence):
        cve = getUtility(ICveSet)[sequence]
        if cve is None:
            return '%s is not a known CVE sequence number.' % sequence
        user = getUtility(ILaunchBag).user
        self.context.linkCVE(cve, user)
        return 'CVE-%s added to bug #%d' % (sequence, self.context.id)


class CveUnlinkView(GeneralFormView):
    """This view is used to unlink a CVE from a bug."""

    def __init__(self, context, request):
        self._nextURL = canonical_url(context)
        context = IBug(context)
        GeneralFormView.__init__(self, context, request)

    def process(self, sequence):
        cve = getUtility(ICveSet)[sequence]
        if cve is None:
            return '%s is not a known CVE sequence number.' % sequence
        user = getUtility(ILaunchBag).user
        self.context.unlinkCVE(cve, user)
        return 'CVE-%s removed from bug #%d' % (sequence, self.context.id)


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

    def pre_search(self):
        # see if we have a proper sequence
        sequence = self.text
        if sequence[:4].lower() in ['cve-', 'can-']:
            sequence = sequence[4:].strip()
        if valid_cve(sequence):
            # try to find the CVE, and redirect to it if we do
            cveset = getUtility(ICveSet)
            cve = cveset[sequence]
            if cve:
                self.request.response.redirect(canonical_url(cve))

        # ok, we have text, but it is not a valid sequence. lets try
        # searching
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


