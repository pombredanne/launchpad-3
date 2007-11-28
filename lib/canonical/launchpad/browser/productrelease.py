# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'ProductReleaseContextMenu',
    'ProductReleaseEditView',
    'ProductReleaseAddView',
    'ProductReleaseRdfView',
    'ProductReleaseAddDownloadFileView',
    'ProductReleaseNavigation',
    'ProductReleaseView',
    ]

from StringIO import StringIO

# zope3
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.component import getUtility
from zope.app.form.browser import TextWidget
from zope.app.form.browser.add import AddView
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

# launchpad
from canonical.launchpad.interfaces import (
    IProductRelease, IProductReleaseSet,
    ILaunchBag, ILibraryFileAliasSet, IProductReleaseFileAddForm)

from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.product import download_file_url
from canonical.launchpad.webapp import (
    ContextMenu, LaunchpadFormView, LaunchpadView, Link, Navigation, action,
    canonical_url, custom_widget, enabled_with_permission, stepthrough)


class ProductReleaseNavigation(Navigation):

    usedfor = IProductRelease

    @stepthrough('+download')
    def download(self, name):
        newlocation = self.context.getFileAliasByName(name)
        return newlocation


class ProductReleaseContextMenu(ContextMenu):

    usedfor = IProductRelease
    links = ['edit', 'add_file', 'administer', 'download']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def add_file(self):
        text = 'Add download file'
        return Link('+adddownloadfile', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def administer(self):
        text = 'Administer'
        return Link('+review', text, icon='edit')

    def download(self):
        text = 'Download RDF metadata'
        return Link('+rdf', text, icon='download')


class ProductReleaseAddView(AddView):

    __used_for__ = IProductRelease

    _nextURL = '.'

    def nextURL(self):
        return self._nextURL

    def createAndAdd(self, data):
        prset = getUtility(IProductReleaseSet)
        user = getUtility(ILaunchBag).user
        newrelease = prset.new(
            data['version'], data['productseries'], user,
            codename=data['codename'], summary=data['summary'],
            description=data['description'], changelog=data['changelog'])
        self._nextURL = canonical_url(newrelease)
        notify(ObjectCreatedEvent(newrelease))


class ProductReleaseEditView(SQLObjectEditView):
    """Edit view for ProductRelease objects"""

    def changed(self):
        self.request.response.redirect('.')


class ProductReleaseRdfView(object):
    """A view that sets its mime-type to application/rdf+xml"""

    template = ViewPageTemplateFile('../templates/productrelease-rdf.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """Render RDF output, and return it as a string encoded in UTF-8.

        Render the page template to produce RDF output.
        The return value is string data encoded in UTF-8.

        As a side-effect, HTTP headers are set for the mime type
        and filename for download."""
        self.request.response.setHeader('Content-Type', 'application/rdf+xml')
        self.request.response.setHeader('Content-Disposition',
                                        'attachment; filename=%s-%s-%s.rdf' % (
                                            self.context.product.name,
                                            self.context.productseries.name,
                                            self.context.version))
        unicodedata = self.template()
        encodeddata = unicodedata.encode('utf-8')
        return encodeddata


class ProductReleaseAddDownloadFileView(LaunchpadFormView):
    schema = IProductReleaseFileAddForm

    custom_widget('description', TextWidget, width=62)

    @action('Add file', name='add')
    def add_action(self, action, data):
        file_upload = self.request.form.get(self.widgets['filecontent'].name)
        # XXX BradCrittenden 2007-04-26: Write a proper upload widget.
        if file_upload and data['description']:
            # replace slashes in the filename with less problematic dashes.
            filename = file_upload.filename.replace('/', '-')

            # create the alias for the file
            alias = getUtility(ILibraryFileAliasSet).create(
                        filename, len(data['filecontent']),
                        StringIO(data['filecontent']),
                        data['contenttype'])
            self.context.addFileAlias(alias=alias,
                                      uploader=self.user,
                                      description=data['description'])
            self.request.response.addNotification(
                "Your file '%s' has been uploaded." % filename)
        self.next_url = canonical_url(self.context)


class ProductReleaseView(LaunchpadView):
    """View for ProductRelease overview."""
    __used_for__ = IProductRelease

    def file_url(self, file_):
        """Create a download URL for the file."""
        return download_file_url(self.context, file_)
