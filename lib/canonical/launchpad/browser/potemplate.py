# zope imports
from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

# depending on apps
from canonical.rosetta.browser import request_languages
from canonical.rosetta.browser import TemplateLanguages

# Database imports.
from canonical.launchpad.interfaces import IBinaryPackageSet

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

    def title(self):
        if self.context.distrorelease:
            release_name = self.context.distrorelease.displayname

            if self.context.sourcepackagename:
                package_name = self.context.sourcepackagename.name

                return "%s in %s" % (package_name, release_name)
            else:
                return release_name
        else:
            return self.context.productrelease.product.displayname

    def isDistroReleaseSubset(self):
        return (self.context.distrorelease is not None and
            self.context.sourcepackagename is None)

    def presentDistroReleasePOTemplate(self, template):
        '''Convert a PO template linked to a distribution to a dictionary.

        It's assumed that the PO template passed in is linked to a
        distribution; i.e. that both template.distrorelease and
        template.sourcepackagename are not None.
        '''

        binary_package_set = getUtility(IBinaryPackageSet)
        description = ''

        # If the PO template is associated with a binarypackagename, try to
        # find a binary package with that binarypackagename in the release
        # this page is for, and if one exists, use its short description as
        # the description for the template.

        if template.binarypackagename is not None:
            binarypackages = list(binary_package_set.getByNameInDistroRelease(
                distroreleaseID=template.distrorelease.id,
                name=template.binarypackagename.name))

            if binarypackages:
                description = binarypackages[0].shortdesc

        return {
            'title': template.title,
            'description': description,
            'sourcepackagename': template.sourcepackagename.name,
            'potemplatename': template.potemplatename.name,
            }

    def distroReleaseTemplates(self):
        '''Return a list of dictionaries for a distro release PO template
        subset.

        Each dictionary represents a single PO template.

        It's assumed that the context object for this view is a distro release
        PO template subset; that is that self.context.distrorelease is not
        None, and that self.context.sourcepackagename is None.
        '''

        return [
            self.presentDistroReleasePOTemplate(template)
            for template in self._templates]

