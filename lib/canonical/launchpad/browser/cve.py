# Copyright 2005 Canonical Ltd.  All rights reserved.

"""CVE views."""

__metaclass__ = type

__all__ = [
    'CveView',
    'CveLinkView',
    'CveUnlinkView',
    'CveSetView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import ICve, ICveSet, ILaunchBag
from canonical.launchpad.validators.cve import valid_cve
from canonical.launchpad.webapp import canonical_url

from canonical.launchpad.browser.form import FormView

class CveView:

    __used_for__ = ICve
    
    def __init__(self, context, request):
        self.context = context
        self.request = request


class CveLinkView(FormView):
    """This view will be used for objects that can be linked to a CVE,
    currently that is only IBug.
    """

    schema = ICve
    fieldNames = ['sequence']
    _arguments = ['sequence',]

    def process(self, sequence):
        cve = getUtility(ICveSet)[sequence]
        if cve is None:
            return '%s is not a known CVE sequence number.' % sequence
        user = getUtility(ILaunchBag).user
        self._nextURL = canonical_url(self.context)
        self.context.linkCVE(cve, user)
        return 'CVE-%s added to bug #%d' % (sequence, self.context.id)


class CveUnlinkView(FormView):
    """This view is used to unlink a CVE from a bug."""

    schema = ICve
    fieldNames = ['sequence']
    _arguments = ['sequence',]

    def process(self, sequence):
        cve = getUtility(ICveSet)[sequence]
        if cve is None:
            return '%s is not a known CVE sequence number.' % sequence
        user = getUtility(ILaunchBag).user
        self._nextURL = canonical_url(self.context)
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

        # if we do not have text, we are done
        if not self.text:
            return

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


