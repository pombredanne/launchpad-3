# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Browser code for PO templates."""

__metaclass__ = type

__all__ = [
    'POTemplateAdminView',
    'POTemplateEditView',
    'POTemplateFacets',
    'POTemplateExportView',
    'POTemplateNavigation',
    'POTemplateSetNavigation',
    'POTemplateSOP',
    'POTemplateSubsetNavigation',
    'POTemplateSubsetURL',
    'POTemplateSubsetView',
    'POTemplateURL',
    'POTemplateView',
    'POTemplateViewPreferred',
    ]

import operator
import os.path
from zope.component import getUtility
from zope.interface import implements
from zope.publisher.browser import FileUpload

from canonical.launchpad import helpers
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.launchpad import StructuralObjectPresentation
from canonical.launchpad.browser.poexportrequest import BaseExportView
from canonical.launchpad.browser.productseries import (
    ProductSeriesSOP, ProductSeriesFacets)
from canonical.launchpad.browser.translations import TranslationsMixin
from canonical.launchpad.browser.sourcepackage import (
    SourcePackageSOP, SourcePackageFacets)
from canonical.launchpad.interfaces import (
    IPOTemplate, IPOTemplateSet, ILaunchBag, IPOFileSet, IPOTemplateSubset,
    ITranslationImporter, ITranslationImportQueue, IProductSeries,
    ISourcePackage, NotFoundError)
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, canonical_url, enabled_with_permission,
    GetitemNavigation, Navigation, LaunchpadView, ApplicationMenu)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData


class POTemplateNavigation(Navigation):

    usedfor = IPOTemplate

    def traverse(self, name):
        """Return the IPOFile associated with the given name."""

        assert self.request.method in ['GET', 'HEAD', 'POST'], (
            'We only know about GET, HEAD, and POST')

        user = getUtility(ILaunchBag).user

        # We do not want users to see the 'en' potemplate because
        # we store the messages we want to translate as English.
        if name == 'en':
            raise NotFoundError(name)

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
    usedfor = IPOTemplate

    def __init__(self, context):
        StandardLaunchpadFacets.__init__(self, context)
        target = context.translationtarget
        if IProductSeries.providedBy(target):
            self.target_facets = ProductSeriesFacets(target)
        elif ISourcePackage.providedBy(target):
            self.target_facets = SourcePackageFacets(target)
        else:
            # We don't know yet how to handle this target.
            raise NotImplementedError

        # Enable only the menus that the translation target uses.
        self.enable_only = self.target_facets.enable_only

        # From an IPOTemplate URL, we reach its translationtarget (either
        # ISourcePackage or IProductSeries using self.target.
        self.target = '../../'

    def overview(self):
        overview_link = self.target_facets.overview()
        overview_link.target = self.target
        return overview_link

    def translations(self):
        translations_link = self.target_facets.translations()
        translations_link.target = self.target
        return translations_link

    def bugs(self):
        bugs_link = self.target_facets.bugs()
        bugs_link.target = self.target
        return bugs_link

    def answers(self):
        answers_link = self.target_facets.answers()
        answers_link.target = self.target
        return answers_link

    def specifications(self):
        specifications_link = self.target_facets.specifications()
        specifications_link.target = self.target
        return specifications_link

    def bounties(self):
        bounties_link = self.target_facets.bounties()
        bounties_link.target = self.target
        return bounties_link

    def calendar(self):
        calendar_link = self.target_facets.calendar()
        calendar_link.target = self.target
        return calendar_link

    def branches(self):
        branches_link = self.target_facets.branches()
        branches_link.target = self.target
        return branches_link


class POTemplateSOP(StructuralObjectPresentation):

    def __init__(self, context):
        StructuralObjectPresentation.__init__(self, context)
        target = context.translationtarget
        if IProductSeries.providedBy(target):
            self.target_sop = ProductSeriesSOP(target)
        elif ISourcePackage.providedBy(target):
            self.target_sop = SourcePackageSOP(target)
        else:
            # We don't know yet how to handle this target.
            raise NotImplementedError

    def getIntroHeading(self):
        return self.target_sop.getIntroHeading()

    def getMainHeading(self):
        return self.target_sop.getMainHeading()

    def listChildren(self, num):
        return self.target_sop.listChildren(num)

    def countChildren(self):
        return self.parent.countChildren()

    def listAltChildren(self, num):
        return self.parent.listAltChildren(num)

    def countAltChildren(self):
        return self.parent.countAltChildren()


class POTemplateAppMenus(ApplicationMenu):
    usedfor = IPOTemplate
    facet = 'translations'
    links = ['status', 'upload', 'download', 'edit', 'administer']

    def status(self):
        text = 'Show translation status'
        return Link('', text)

    def upload(self):
        text = 'Upload a file'
        return Link('+upload', text, icon='edit')

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


class POTemplateView(LaunchpadView, TranslationsMixin):

    def initialize(self):
        self.description = self.context.description
        """Get the requested languages and submit the form."""
        self.submitForm()

    def requestPoFiles(self):
        """Yield a POFile or DummyPOFile for each of the languages in the
        request, which includes country languages from the request IP,
        browser preferences, and/or personal Launchpad language prefs.
        """
        for language in self._sortLanguages(self.translatable_languages):
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
        # This inline import is needed to workaround a circular import problem
        # because canonical.launchpad.browser.pofile imports
        # canonical.launchpad.browser.potemplate.POTemplateSOP
        from canonical.launchpad.browser.pofile import POFileView

        languages = self.translatable_languages
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
        languages = set(
            self.context.languages()).union(self.translatable_languages)
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
                # XXX: Carlos Perello Marin 2004-12-30
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
        root, ext = os.path.splitext(filename)
        translation_importer = getUtility(ITranslationImporter)
        if (ext in translation_importer.supported_file_extensions):
            # Add it to the queue.
            translation_import_queue.addOrUpdateEntry(
                filename, content, True, self.user,
                sourcepackagename=self.context.sourcepackagename,
                distroseries=self.context.distroseries,
                productseries=self.context.productseries,
                potemplate=self.context)

            self.request.response.addInfoNotification(
                'Thank you for your upload. The file content will be imported'
                ' soon into Launchpad. You can track its status from the'
                ' <a href="%s/+imports">Translation Import Queue</a>' %
                    canonical_url(self.context.translationtarget))

        elif helpers.is_tar_filename(filename):
            # Add the whole tarball to the import queue.
            num = translation_import_queue.addOrUpdateEntriesFromTarball(
                content, True, self.user,
                sourcepackagename=self.context.sourcepackagename,
                distroseries=self.context.distroseries,
                productseries=self.context.productseries,
                potemplate=self.context)

            if num > 0:
                self.request.response.addInfoNotification(
                    'Thank you for your upload. %d files from the tarball'
                    ' will be imported soon into Launchpad. You can track its'
                    ' status from the <a href="%s/+imports">Translation'
                    ' Import Queue<a>' % (
                        num, canonical_url(self.context.translationtarget)
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

        if export_potemplate:
            requested_templates = [self.context]
        else:
            requested_templates = None

        return (requested_templates, pofiles)

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

    def getDefaultFormat(self):
        return self.context.source_file_format


class POTemplateSubsetURL:
    implements(ICanonicalUrlData)

    rootsite = 'mainsite'

    def __init__(self, context):
        self.context = context

    @property
    def path(self):
        potemplatesubset = self.context
        if potemplatesubset.distroseries is not None:
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
        if potemplatesubset.distroseries is not None:
            assert potemplatesubset.productseries is None
            return potemplatesubset.distroseries
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
        if potemplate.distroseries is not None:
            assert potemplate.productseries is None
            self.potemplatesubset = potemplateset.getSubset(
                distroseries=potemplate.distroseries,
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


class POTemplateSubsetNavigation(Navigation):

    usedfor = IPOTemplateSubset

    def traverse(self, name):
        """Return the IPOTemplate associated with the given name."""

        assert self.request.method in ['GET', 'HEAD', 'POST'], (
            'We only know about GET, HEAD, and POST')

        # Get the requested potemplate.
        potemplate = self.context.getPOTemplateByName(name)
        if potemplate is None:
            # The template doesn't exist.
            raise NotFoundError(name)

        # Get whether the target for the requested template is officially
        # using Launchpad Translations.
        if potemplate.distribution is not None:
            official_rosetta = potemplate.distribution.official_rosetta
        elif potemplate.product is not None:
            official_rosetta = potemplate.product.official_rosetta
        else:
            official_rosetta = False

        if ((official_rosetta and potemplate.iscurrent) or
            check_permission('launchpad.Admin', self.context)):
            # The target is using officially Launchpad Translations and the
            # template is available to be translated, or is an admin which
            # is browsing the system, in which case we show everything.
            return potemplate
        else:
            raise NotFoundError(name)
