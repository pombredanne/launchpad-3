# zope imports
from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

# depending on apps
from canonical.rosetta.browser import request_languages
from canonical.rosetta.browser import TemplateLanguages

class POTemplateSubsetView(object):
    statusLegend = ViewPageTemplateFile(
        '../templates/portlet-rosetta-status-legend.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        # List of languages the user is interested on based on their browser,
        # IP address and launchpad preferences.
        self.languages = request_languages(self.request)
        # Cache value for the return value of self.templates
        self._template_languages = None
        # List of the templates we have in this subset.
        self._templates = list(self.context)
        self.status_message = None
        # Whether there is more than one PO template.
        self.has_multiple_templates = len(self._templates) > 1

    def templates(self):
        if self._template_languages is None:
            self._template_languages = []
            for template in self._templates:
                # As we are using this view code for different pages, we need
                # to know our baseurl so the pagetemplate has the right links
                # to show the translation form and the potemplate details.
                if (self.context.sourcepackagename is None and
                    self.context.distrorelease is not None):
                    baseurl = '../+sources/%s/+rosetta/%s/' % (
                                template.sourcepackagename.name,
                                template.potemplatename.name)
                else:
                    baseurl = '%s/' % template.potemplatename.name

                self._template_languages.append(
                    TemplateLanguages(template, self.languages, baseurl))

        return self._template_languages
