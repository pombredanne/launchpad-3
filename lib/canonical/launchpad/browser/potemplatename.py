# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser views and traversal functions for potemplatenames."""

__metaclass__ = type

__all__ = [
    'POTemplateNameSetView',
    'POTemplateNameView',
    'POTemplateNameEditView',
    'POTemplateNameAddView',
    'POTemplateNameSetNavigation'
    ]

from datetime import datetime

from zope.app.i18n import ZopeMessageIDFactory as _
from zope.component import getUtility
from zope.app.form.browser.add import AddView

from canonical.launchpad.webapp import canonical_url, Navigation
from canonical.launchpad.interfaces import IPOTemplateNameSet
from canonical.launchpad.browser.editview import SQLObjectEditView


class POTemplateNameSetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        form = self.request.form
        self.text = form.get('text')
        self.searchrequested = self.text is not None
        self.results = None
        self.matches = 0

    def searchresults(self):
        """Use searchtext to find the list of Products that match
        and then present those as a list. Only do this the first
        time the method is called, otherwise return previous results.
        """
        if self.results is None:
            self.results = self.context.search(text=self.text)
        self.matches = self.context.searchCount(text=self.text)
        return self.results


class POTemplateNameSetNavigation(Navigation):

    usedfor = IPOTemplateNameSet

    def traverse(self, name):
        if name.isdigit():
            return self.context.get(int(name))
        else:
            return None


# A View Class for POTemplateName
class POTemplateNameView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def potemplates(self):
        potemplates = []

        for potemplate in self.context.potemplates:

            potemplate_view = {
                'description': potemplate.description,
                'url': canonical_url(potemplate)
                }

            potemplates.append(potemplate_view)

        # Sort the list

        L = [(item['url'], item)
             for item in potemplates]
        L.sort()

        potemplates = [item
                       for itemkey, item in L]

        return potemplates


class POTemplateNameEditView(POTemplateNameView, SQLObjectEditView):
    """View class that lets you edit a POTemplateName object."""

    def __init__(self, context, request):
        POTemplateNameView.__init__(self, context, request)
        SQLObjectEditView.__init__(self, context, request)

    def changed(self):
        formatter = self.request.locale.dates.getFormatter(
            'dateTime', 'medium')
        status = _("Updated on ${date_time}")
        status.mapping = {'date_time': formatter.format(
            datetime.utcnow())}
        self.update_status = status

class POTemplateNameAddView(AddView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # retrieve submitted values from the form
        name = data.get('name')
        title = data.get('title')
        description = data.get('description')
        translationdomain = data.get('translationdomain')

        potemplatenameset = getUtility(IPOTemplateNameSet)
        potemplatename = potemplatenameset.new(
            name=name, title=title, description=description,
            translationdomain=translationdomain)

        self._nextURL = "%d" % potemplatename.id

    def nextURL(self):
        return self._nextURL
