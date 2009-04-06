# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'ProductReleaseAddDownloadFileView',
    'ProductReleaseAddView',
    'ProductReleaseFromSeriesAddView',
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
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from canonical.launchpad.interfaces import (
    IProductRelease, IProductReleaseFileAddForm)

from canonical.lazr.interface import copy_field
from canonical.launchpad import _
from canonical.launchpad.browser.product import ProductDownloadFileMixin
from canonical.launchpad.webapp.menu import structured
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


class ProductReleaseAddViewBase(LaunchpadFormView):
    """Base class for creating a release from an existing or new milestone.

    Subclasses need to define the field_names a form action.
    """
    schema = IProductRelease

    custom_widget('datereleased', DateTimeWidget)
    custom_widget('release_notes', TextAreaWidget, height=7, width=62)
    custom_widget('changelog', TextAreaWidget, height=7, width=62)

    def _prependKeepMilestoneActiveField(self):
        keep_milestone_active_checkbox = FormFields(
            Bool(
                __name__='keep_milestone_active',
                title=_("Keep the milestone active."),
                description=_(
                    "Only select this if bugs or blueprints still need "
                    "to be targeted to this product release's milestone.")),
            render_context=self.render_context)
        self.form_fields = keep_milestone_active_checkbox + self.form_fields

    def _createRelease(self, milestone, data):
        """Create product release for this milestone."""
        newrelease = milestone.createProductRelease(
            self.user, changelog=data['changelog'],
            release_notes=data['release_notes'],
            datereleased=data['datereleased'])
        # Set Milestone.active to false, since bugs & blueprints
        # should not be targeted to a milestone in the past.
        if data['keep_milestone_active'] is False:
            milestone.active = False
            self.request.response.addWarningNotification(structured(
                _('The &ldquo;%s&rdquo; milestone for this product release '
                  'was deactivated so that bugs & blueprints cannot be '
                  'targeted to a milestone in the past.' % milestone.name)))
        self.next_url = canonical_url(newrelease.milestone.productseries)
        notify(ObjectCreatedEvent(newrelease))

    @property
    def label(self):
        """The form label."""
        return 'Register a new %s release' % self.context.product.name

    @property
    def cancel_url(self):
        return canonical_url(self.context)


class ProductReleaseAddView(ProductReleaseAddViewBase):
    """Create a product release.

    Also, deactivate the milestone it is attached to.
    """

    field_names = [
        'datereleased',
        'release_notes',
        'changelog',
        ]

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
        if self.context.active is True:
            self._prependKeepMilestoneActiveField()

    @action(_('Create release'), name='create')
    def createRelease(self, action, data):
        self._createRelease(self.context, data)


class ProductReleaseFromSeriesAddView(ProductReleaseAddViewBase):
    """Create a product release and select or add a milestone.

    Also, deactivate the milestone it is attached to.
    """

    field_names = [
        'datereleased',
        'release_notes',
        'changelog',
        ]

    def initialize(self):
        # The dynamically loaded milestone form needs this javascript
        # enabled in the main-template.pt.
        self.request.needs_datepicker_iframe = True
        super(ProductReleaseFromSeriesAddView, self).initialize()

    def setUpFields(self):
        super(ProductReleaseFromSeriesAddView, self).setUpFields()
        self._prependKeepMilestoneActiveField()
        self._prependMilestoneField()

    def _prependMilestoneField(self):
        """Add Milestone Choice field with custom terms."""
        terms = [
            SimpleTerm(milestone, milestone.name, milestone.name)
            for milestone in self.context.all_milestones
            if milestone.product_release is None]
        terms.insert(0, SimpleTerm(None, None, '- Select Milestone -'))
        milestone_field = FormFields(
            copy_field(
                IProductRelease['milestone'],
                __name__='milestone_for_release',
                vocabulary=SimpleVocabulary(terms)))
        self.form_fields = milestone_field + self.form_fields

    @property
    def milestone_form_uri(self):
        """URI for form displayed by the formoverlay widget."""
        return canonical_url(self.context) + '/+addmilestone/++form++'

    @property
    def series_api_uri(self):
        return canonical_url(self.context, path_only_if_possible=True)

    @action(_('Create release'), name='create')
    def createRelease(self, action, data):
        milestone = data['milestone_for_release']
        self._createRelease(milestone, data)


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

