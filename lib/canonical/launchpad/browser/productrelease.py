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

import cgi
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
from canonical.launchpad.webapp.menu import structured
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
        return Link('+adddownloadfile', text, icon='add')

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
                _("A project release already exists for this milestone."))
            self.request.response.redirect(
                canonical_url(self.context.product_release) + '/+edit')
        else:
            super(ProductReleaseAddView, self).initialize()

    def setUpFields(self):
        super(ProductReleaseAddView, self).setUpFields()
        if self.context.active is True:
            self.form_fields += FormFields(
                Bool(
                    __name__='keep_milestone_active',
                    title=_("Keep the %s milestone active." %
                            self.context.name),
                    description=_(
                        "Only select this if bugs or blueprints still need "
                        "to be targeted to this project release's "
                        "milestone.")),
                render_context=self.render_context)

    @action(_('Publish release'), name='publish')
    def publishRelease(self, action, data):
        """Publish product release for this milestone."""
        newrelease = self.context.createProductRelease(
            self.user, changelog=data['changelog'],
            release_notes=data['release_notes'],
            datereleased=data['datereleased'])
        # Set Milestone.active to false, since bugs & blueprints
        # should not be targeted to a milestone in the past.
        if data['keep_milestone_active'] is False:
            self.context.active = False
            milestone_link = '<a href="%s">%s milestone</a>' % (
                canonical_url(self.context), cgi.escape(self.context.name))
            self.request.response.addWarningNotification(structured(
                _("The %s for this project release was deactivated "
                  "so that bugs and blueprints cannot be associated with "
                  "this release." % milestone_link)))
        self.next_url = canonical_url(newrelease)
        notify(ObjectCreatedEvent(newrelease))

    @property
    def label(self):
        """The form label."""
        return 'Create a new release for %s' % (
            self.context.product.displayname)

    @property
    def releases(self):
        """The releases in this series, or None."""
        releases = self.context.productseries.releases
        if releases.count() == 0:
            return None
        return releases

    @property
    def cancel_url(self):
        return canonical_url(self.context)


class ProductReleaseEditView(LaunchpadEditFormView):
    """Edit view for ProductRelease objects"""

    schema = IProductRelease
    field_names = [
        "datereleased",
        "release_notes",
        "changelog",
        ]

    custom_widget('datereleased', DateTimeWidget)
    custom_widget('release_notes', TextAreaWidget, height=7, width=62)
    custom_widget('changelog', TextAreaWidget, height=7, width=62)

    @property
    def label(self):
        """The form label."""
        return 'Edit %s release details' % self.context.title

    @action('Change', name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)

    @property
    def cancel_url(self):
        return canonical_url(self.context)


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

    @property
    def label(self):
        """The form label."""
        return 'Add a download file to %s' % self.context.title

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

    @property
    def cancel_url(self):
        return canonical_url(self.context)


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
    schema = IProductRelease
    field_names = []

    @property
    def label(self):
        """The form label."""
        return 'Delete %s' % self.context.title

    @action('Delete this Release', name='delete')
    def add_action(self, action, data):
        for release_file in self.context.files:
            release_file.destroySelf()
        self.request.response.addInfoNotification(
            "Release %s deleted." % self.context.version)
        self.next_url = canonical_url(self.context.productseries)
        self.context.destroySelf()

    @property
    def cancel_url(self):
        return canonical_url(self.context)

