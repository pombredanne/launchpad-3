# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Browser code for PO templates."""

__metaclass__ = type

__all__ = [
    'POTemplateSubsetView', 'POTemplateView', 'POTemplateViewPreferred',
    'POTemplateEditView', 'POTemplateAdminView', 'POTemplateExportView', 
    'POTemplateSubsetURL', 'POTemplateURL', 'POTemplateSetNavigation',
    'POTemplateSubsetNavigation', 'POTemplateNavigation'
    ]

import operator

from zope.component import getUtility
from zope.interface import implements
from zope.publisher.browser import FileUpload

from canonical.launchpad import helpers
from canonical.launchpad.interfaces import (
    IPOTemplate, IPOTemplateSet, ILaunchBag, IPOFileSet, 
    IPOTemplateSubset, ITranslationImportQueue)
from canonical.launchpad.browser.pofile import (
    POFileView, BaseExportView, POFileAppMenus)
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, canonical_url, enabled_with_permission,
    GetitemNavigation, Navigation, LaunchpadView)
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from canonical.lp.dbschema import RosettaFileFormat


class POTemplateNavigation(Navigation):

    usedfor = IPOTemplate

    def traverse(self, name):
        """Return the IPOFile associated with the given name."""

        assert self.request.method in ['GET', 'HEAD', 'POST'], (
            'We only know about GET, HEAD, and POST')

        user = getUtility(ILaunchBag).user

        pofile = self.context.getPOFileByLang(name)

        if pofile is not None:
            # Already have a valid POFile entry, just return it.
            return pofile
        elif self.request.method in ['GET', 'HEAD']:
            # It's just a query, get a fake one so we don't create new
            # POFiles just because someone is browsing the web.
            return self.context.getDummyPOFile(name, requester=user)
        else:
            # It's a POST.
            # XXX CarlosPerelloMarin 2006-04-20: We should check the kind of
            # POST we got, a Log out action will be also a POST and we should
            # not create an IPOFile in that case. See bug #40275 for more
            # information.
            return self.context.newPOFile(name, requester=user)


class POTemplateFacets(StandardLaunchpadFacets):
    # XXX 20061004 mpt: A POTemplate is not a structural object. It should
    # inherit all navigation from its product or distro release.

    usedfor = IPOTemplate

    defaultlink = 'translations'

    enable_only = ['overview', 'translations']

    def _parent_url(self):
        """Return the URL of the thing this PO template is attached to."""

        if self.context.distrorelease:
            source_package = self.context.distrorelease.getSourcePackage(
                self.context.sourcepackagename)
            return canonical_url(source_package)
        else:
            return canonical_url(self.context.productseries)

    def overview(self):
        target = self._parent_url()
        text = 'Overview'
        return Link(target, text)

    def translations(self):
        target = ''
        text = 'Translations'
        return Link(target, text)


class POTemplateAppMenus(POFileAppMenus):
    usedfor = IPOTemplate

    links = ['overview', 'upload', 'download', 'edit', 'administer']

    def download(self):
        text = 'Download translations'
        return Link('+export', text, icon='download')

    def edit(self):
        text = 'Change details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def administer(self):
        text = 'Administer'
        return Link('+admin', text, icon='edit')


class POTemplateSubsetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        # We are not using this context directly, only for traversals.
        self.request.response.redirect('../+translations')


class POTemplateView(LaunchpadView):

    def initialize(self):
        self.description = self.context.description
        """Get the requested languages and submit the form."""
        self.submitForm()

    @property
    def request_languages(self):
        # if this is accessed multiple times in a same request, consider
        # changing this to a cachedproperty
        return helpers.request_languages(self.request)

    def requestPoFiles(self):
        """Yield a POFile or DummyPOFile for each of the languages in the
        request, which includes country languages from the request IP,
        browser preferences, and/or personal Launchpad language prefs.
        """
        for language in self._sortLanguages(self.request_languages):
            yield self._getPOFileOrDummy(language)

    def num_messages(self):
        N = self.context.messageCount()
        if N == 0:
            return "no messages at all"
        elif N == 1:
            return "1 message"
        else:
            return "%s messages" % N

    def pofiles(self, preferred_only=False):
        """Iterate languages shown when viewing this PO template.

        Yields a POFileView object for each language this template has
        been translated into, and for each of the user's languages.
        Where the template has no POFile for that language, we use
        a DummyPOFile.
        """

        languages = self.request_languages
        if not preferred_only:
            # Union the languages the template has been translated into with
            # the user's selected languages.
            languages = set(self.context.languages()) | set(languages)

        for language in self._sortLanguages(languages):
            pofile = self._getPOFileOrDummy(language)
            pofileview = POFileView(pofile, self.request)
            # Initialize the view.
            pofileview.initialize()
            yield pofileview

    @property
    def has_pofiles(self):
        languages = set(self.context.languages()).union(self.request_languages)
        return len(languages) > 0

    def _sortLanguages(self, languages):
        return sorted(languages, key=operator.attrgetter('englishname'))

    def _getPOFileOrDummy(self, language):
        pofile = self.context.getPOFileByLang(language.code)
        if pofile is None:
            pofileset = getUtility(IPOFileSet)
            pofile = pofileset.getDummy(self.context, language)
        return pofile

    def submitForm(self):
        """Called from the page template to do any processing needed if a form
        was submitted with the request."""

        if self.request.method == 'POST':
            if 'UPLOAD' in self.request.form:
                self.upload()

    def upload(self):
        """Handle a form submission to change the contents of the template."""

        file = self.request.form.get('file')
        if not isinstance(file, FileUpload):
            if not file:
                self.request.response.addErrorNotification(
                    "Your upload was ignored because you didn't select a "
                    "file. Please select a file and try again.")
            else:
                # XXX: Carlos Perello Marin 2004/12/30
                # Epiphany seems to have an unpredictable bug with upload
                # forms (or perhaps it's launchpad because I never had
                # problems with bugzilla). The fact is that some uploads don't
                # work and we get a unicode object instead of a file-like
                # object in "file". We show an error if we see that behaviour.
                # For more info, look at bug #116.
                self.request.response.addErrorNotification(
                    "Your upload failed because there was a problem receiving"
                    " data. Please try again.")
            return

        filename = file.filename
        content = file.read()

        if len(content) == 0:
            self.request.response.addWarningNotification(
                "Ignored your upload because the uploaded file is empty.")
            return

        translation_import_queue = getUtility(ITranslationImportQueue)

        if (filename.endswith('.pot') or filename.endswith('.po')
            or filename=='en-US.xpi'):
            # Add it to the queue.
            if filename.endswith('.po'):
                # It's a .po file attached to the template at self.context,
                # we don't override its path.
                path = filename
            else:
                # It's a template, we override it to have exactly the same
                # path as the entry has in our database.
                path = self.context.path
            translation_import_queue.addOrUpdateEntry(
                path, content, True, self.user,
                sourcepackagename=self.context.sourcepackagename,
                distrorelease=self.context.distrorelease,
                productseries=self.context.productseries,
                potemplate=self.context,
                format=RosettaFileFormat.XPI)

            self.request.response.addInfoNotification(
                'Thank you for your upload. The file content will be imported'
                ' soon into Rosetta. You can track its status from the'
                ' <a href="%s">Translation Import Queue</a>' %
                    canonical_url(translation_import_queue))

        elif helpers.is_tar_filename(filename):
            # Add the whole tarball to the import queue.
            num = translation_import_queue.addOrUpdateEntriesFromTarball(
                content, True, self.user,
                sourcepackagename=self.context.sourcepackagename,
                distrorelease=self.context.distrorelease,
                productseries=self.context.productseries,
                potemplate=self.context)

            if num > 0:
                self.request.response.addInfoNotification(
                    'Thank you for your upload. %d files from the tarball'
                    ' will be imported soon into Rosetta. You can track its'
                    ' status from the <a href="%s">Translation Import Queue'
                    '</a>' % (num, canonical_url(translation_import_queue)
                        )
                    )
            else:
                self.request.response.addWarningNotification(
                    "Nothing has happened. The tarball you uploaded does not"
                    " contain any file that the system can understand.")
        else:
            self.request.response.addWarningNotification(
                "Ignored your upload because the file you uploaded was not"
                " recognised as a file that can be imported.")


class POTemplateViewPreferred(POTemplateView):
    def pofiles(self):
        return POTemplateView.pofiles(self, preferred_only=True)

class POTemplateEditView(SQLObjectEditView):
    """View class that lets you edit a POTemplate object."""

    def __init__(self, context, request):
        self.old_description = context.description
        self.user = getUtility(ILaunchBag).user

        SQLObjectEditView.__init__(self, context, request)

    def changed(self):
        context = self.context
        if self.old_description != context.description:
            self.user.assignKarma(
                'translationtemplatedescriptionchanged',
                product=context.product, distribution=context.distribution,
                sourcepackagename=context.sourcepackagename)

        # We need this because when potemplate name changes, canonical_url
        # for it changes as well.
        self.request.response.redirect(canonical_url(self.context))


class POTemplateAdminView(POTemplateEditView):
    """View class that lets you admin a POTemplate object."""

    def changed(self):
        """Redirect to the template view page."""

        # We need this because when potemplate name changes, canonical_url
        # for it changes as well.
        self.request.response.redirect(canonical_url(self.context))


class POTemplateExportView(BaseExportView):

    def processForm(self):
        """Process a form submission requesting a translation export."""

        if self.request.method != 'POST':
            return

        what = self.request.form.get('what')
        if what == 'all':
            export_potemplate = True

            pofiles =  self.context.pofiles
        elif what == 'some':
            pofiles = []
            export_potemplate = 'potemplate' in self.request.form

            for key in self.request.form:
                if '@' in key:
                    code, variant = key.split('@', 1)
                else:
                    code = key
                    variant = None

                pofile = self.context.getPOFileByLang(code, variant)
                if pofile is not None:
                    pofiles.append(pofile)
        else:
            self.request.response.addErrorNotification(
                'Please choose whether you would like all files or only some '
                'of them.')
            return

        format = self.validateFileFormat(self.request.form.get('format'))
        if not format:
            return

        if export_potemplate:
            self.request_set.addRequest(
                self.user, self.context, pofiles, format)
        elif pofiles:
            self.request_set.addRequest(self.user, None, pofiles, format)
        else:
            self.request.response.addErrorNotification(
                'Please select at least one pofile or the PO template.')
            return

        self.nextURL()


    def pofiles(self):
        """Return a list of PO files available for export."""

        class BrowserPOFile:
            def __init__(self, value, browsername):
                self.value = value
                self.browsername = browsername

        def pofile_sort_key(pofile):
            return pofile.language.englishname

        for pofile in sorted(self.context.pofiles, key=pofile_sort_key):
            if pofile.variant:
                variant = pofile.variant.encode('UTF-8')
                value = '%s@%s' % (pofile.language.code, variant)
                browsername = '%s ("%s" variant)' % (
                    pofile.language.englishname, variant)
            else:
                value = pofile.language.code
                browsername = pofile.language.englishname

            yield BrowserPOFile(value, browsername)


class POTemplateSubsetURL:
    implements(ICanonicalUrlData)

    rootsite = 'mainsite'

    def __init__(self, context):
        self.context = context

    @property
    def path(self):
        potemplatesubset = self.context
        if potemplatesubset.distrorelease is not None:
            assert potemplatesubset.productseries is None
            assert potemplatesubset.sourcepackagename is not None
            return '+source/%s/+pots' % (
                potemplatesubset.sourcepackagename.name)
        else:
            assert potemplatesubset.productseries is not None
            return '+pots'

    @property
    def inside(self):
        potemplatesubset = self.context
        if potemplatesubset.distrorelease is not None:
            assert potemplatesubset.productseries is None
            return potemplatesubset.distrorelease
        else:
            assert potemplatesubset.productseries is not None
            return potemplatesubset.productseries


class POTemplateURL:
    implements(ICanonicalUrlData)

    rootsite = None

    def __init__(self, context):
        self.context = context
        potemplate = self.context
        potemplateset = getUtility(IPOTemplateSet)
        if potemplate.distrorelease is not None:
            assert potemplate.productseries is None
            self.potemplatesubset = potemplateset.getSubset(
                distrorelease=potemplate.distrorelease,
                sourcepackagename=potemplate.sourcepackagename)
        else:
            assert potemplate.productseries is not None
            self.potemplatesubset = potemplateset.getSubset(
                productseries=potemplate.productseries)

    @property
    def path(self):
        potemplate = self.context
        return potemplate.name

    @property
    def inside(self):
        return self.potemplatesubset


class POTemplateSetNavigation(GetitemNavigation):

    usedfor = IPOTemplateSet


class POTemplateSubsetNavigation(GetitemNavigation):

    usedfor = IPOTemplateSubset

