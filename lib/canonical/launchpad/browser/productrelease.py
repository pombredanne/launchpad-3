# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'ProductReleaseAddDownloadFileView',
    'ProductReleaseAddView',
    'ProductReleaseContextMenu',
    'ProductReleaseDeleteView',
    'ProductReleaseEditView',
    'ProductReleaseNavigation',
    'ProductReleaseRdfView',
    'ProductReleaseView',
    ]

import mimetypes

from zope.event import notify
from zope.lifecycleevent import ObjectCreatedEvent
from zope.app.form.browser import TextAreaWidget, TextWidget
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.formlib.form import FormFields
from zope.schema import Bool

from canonical.launchpad.interfaces import (
    IProductRelease, IProductReleaseFileAddForm)

from canonical.launchpad import _
from canonical.launchpad.browser.product import ProductDownloadFileMixin
from canonical.launchpad.webapp import (
    action, canonical_url, ContextMenu, custom_widget,
    enabled_with_permission, LaunchpadEditFormView, LaunchpadFormView,
    LaunchpadView, Link, Navigation, stepthrough)
from canonical.widgets import DateTimeWidget


class ProductReleaseNavigation(Navigation):

    usedfor = IProductRelease

    @stepthrough('+download')
    def download(self, name):
        return self.context.getFileAliasByName(name)

    @stepthrough('+file')
    def fileaccess(self, name):
        return self.context.getProductReleaseFileByName(name)


class ProductReleaseContextMenu(ContextMenu):

    usedfor = IProductRelease
    links = ['edit', 'add_file', 'administer', 'download', 'view_milestone']

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

    def view_milestone(self):
        text = 'View milestone'
        url = canonical_url(self.context.milestone)
        return Link(url, text)


class ProductReleaseAddView(LaunchpadFormView):
    """Create a product release.

    Also, deactivate the milestone it is attached to.
    """

    schema = IProductRelease
    label = "Register a release"
    field_names = [
        'datereleased',
        'release_notes',
        'changelog',
        ]

    custom_widget('datereleased', DateTimeWidget)
    custom_widget('release_notes', TextAreaWidget, height=7, width=62)
    custom_widget('changelog', TextAreaWidget, height=7, width=62)

    def initialize(self):
        if self.context.product_release is not None:
            self.request.response.addErrorNotification(
                _("A product release already exists for this milestone."))
            self.request.response.redirect(
                canonical_url(self.context.product_release) + '/+edit')
        else:
            super(ProductReleaseAddView, self).initialize()

    def setUpFields(self):
        super(ProductReleaseAddView, self).setUpFields()
        if self.context.visible is True:
            self.form_fields += FormFields(
                Bool(
                    __name__='dont_deactivate_milestone',
                    title=_("Don't deactivate milestone."),
                    description=_(
                        "Only select this if bugs or bluepints still need to "
                        "be targeted to this product release&rsquo;s "
                        "milestone.")),
                render_context=self.render_context)

    @action(_('Publish release'))
    def publishRelease(self, action, data):
        """Publish product release for this milestone."""
        newrelease = self.context.createProductRelease(
            self.user, changelog=data['changelog'],
            release_notes=data['release_notes'],
            datereleased=data['datereleased'])
        # Set Milestone.visible to false, since bugs & blueprints
        # should not be targeted to a milestone in the past.
        if data['dont_deactivate_milestone'] is True:
            pass
        elif data['dont_deactivate_milestone'] is False:
            self.context.visible = False
            self.request.response.addWarningNotification(
                _("The milestone for this product release was deactivated "
                  "so that bugs & blueprints cannot be targeted "
                  "to a milestone in the past."))
        else:
            raise AssertionError(
                "dont_deactivate_milestone must be True or False: %r"
                % data['dont_deactivate_milestone'])

        self.next_url = canonical_url(newrelease)
        notify(ObjectCreatedEvent(newrelease))


class ProductReleaseEditView(LaunchpadEditFormView):
    """Edit view for ProductRelease objects"""

    schema = IProductRelease
    label = "Edit project release details"
    field_names = [
        "datereleased",
        "release_notes",
        "changelog",
        ]

    custom_widget('datereleased', DateTimeWidget)
    custom_widget('release_notes', TextAreaWidget, height=7, width=62)
    custom_widget('changelog', TextAreaWidget, height=7, width=62)

    @action('Change', name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)


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
        self.request.response.setHeader(
            'Content-Disposition',
            'attachment; filename=%s-%s-%s.rdf' % (
                self.context.product.name,
                self.context.productseries.name,
                self.context.version))
        unicodedata = self.template()
        encodeddata = unicodedata.encode('utf-8')
        return encodeddata


class ProductReleaseAddDownloadFileView(LaunchpadFormView):
    """A view for adding a file to an `IProductRelease`."""
    schema = IProductReleaseFileAddForm

    custom_widget('description', TextWidget, width=62)

    @action('Upload', name='add')
    def add_action(self, action, data):
        form = self.request.form
        file_upload = form.get(self.widgets['filecontent'].name)
        signature_upload = form.get(self.widgets['signature'].name)
        filetype = data['contenttype']
        # XXX: BradCrittenden 2007-04-26 bug=115215 Write a proper upload
        # widget.
        if file_upload is not None and len(data['description']) > 0:
            # XXX Edwin Grubbs 2008-09-10 bug=268680
            # Once python-magic is available on the production servers,
            # the content-type should be verified instead of trusting
            # the extension that mimetypes.guess_type() examines.
            content_type, encoding = mimetypes.guess_type(
                file_upload.filename)

            if content_type is None:
                content_type = "text/plain"

            # signature_upload is u'' if no file is specified in
            # the browser.
            if signature_upload:
                signature_filename = signature_upload.filename
                signature_content = data['signature']
            else:
                signature_filename = None
                signature_content = None

            release_file = self.context.addReleaseFile(
                filename=file_upload.filename,
                file_content=data['filecontent'],
                content_type=content_type,
                uploader=self.user,
                signature_filename=signature_filename,
                signature_content=signature_content,
                file_type=filetype,
                description=data['description'])

            self.request.response.addNotification(
                "Your file '%s' has been uploaded."
                % release_file.libraryfile.filename)

        self.next_url = canonical_url(self.context)


class ProductReleaseView(LaunchpadView, ProductDownloadFileMixin):
    """View for ProductRelease overview."""
    __used_for__ = IProductRelease

    def initialize(self):
        self.form = self.request.form
        self.processDeleteFiles()

    def getReleases(self):
        """See `ProductDownloadFileMixin`."""
        return set([self.context])


class ProductReleaseDeleteView(LaunchpadFormView):
    """A view for deleting an `IProductRelease`."""
    label = 'Delete release'
    schema = IProductRelease
    field_names = []

    def canBeDeleted(self, action=None):
        """Can this release be deleted?

        Only releases which have no files associated with it can be deleted.
        """
        return self.context.files.count() == 0

    @action('Yes, Delete it', name='delete', condition=canBeDeleted)
    def add_action(self, action, data):
        self.request.response.addInfoNotification(
            "Release %s deleted." % self.context.version)
        self.next_url = canonical_url(self.context.productseries)
        self.context.destroySelf()
