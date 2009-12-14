# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser code for PO templates."""

__metaclass__ = type

__all__ = [
    'POTemplateAdminView',
    'POTemplateBreadcrumb',
    'POTemplateEditView',
    'POTemplateFacets',
    'POTemplateExportView',
    'POTemplateMenu',
    'POTemplateNavigation',
    'POTemplateSetNavigation',
    'POTemplateSubsetNavigation',
    'POTemplateSubsetURL',
    'POTemplateSubsetView',
    'POTemplateURL',
    'POTemplateUploadView',
    'POTemplateView',
    'POTemplateViewPreferred',
    ]

import cgi
import datetime
import operator
import os.path
import pytz
from zope.component import getUtility
from zope.interface import implements
from zope.publisher.browser import FileUpload

from canonical.lazr.utils import smartquote

from canonical.launchpad import helpers, _
from canonical.launchpad.webapp.breadcrumb import Breadcrumb
from canonical.launchpad.webapp.interfaces import ILaunchBag, NotFoundError
from lp.translations.browser.poexportrequest import BaseExportView
from lp.registry.browser.productseries import ProductSeriesFacets
from lp.translations.browser.translations import TranslationsMixin
from lp.registry.browser.sourcepackage import SourcePackageFacets
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.translations.interfaces.pofile import IPOFileSet
from lp.translations.interfaces.potemplate import (
    IPOTemplate,
    IPOTemplateSet,
    IPOTemplateSubset)
from lp.translations.interfaces.translationimporter import (
    ITranslationImporter)
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue)
from canonical.launchpad.webapp import (
    action, canonical_url, enabled_with_permission, GetitemNavigation,
    LaunchpadView, LaunchpadEditFormView, Link, Navigation, NavigationMenu,
    StandardLaunchpadFacets)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from canonical.launchpad.webapp.menu import structured


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
            # XXX CarlosPerelloMarin 2006-04-20 bug=40275: We should
            # check the kind of POST we got.  A logout will also be a
            # POST and we should not create a POFile in that case.
            pofile = self.context.newPOFile(name)
            pofile.setOwnerIfPrivileged(user)
            return pofile


class POTemplateFacets(StandardLaunchpadFacets):
    usedfor = IPOTemplate

    def __init__(self, context):
        StandardLaunchpadFacets.__init__(self, context)
        target = context.translationtarget
        if IProductSeries.providedBy(target):
            self._is_product_series = True
            self.target_facets = ProductSeriesFacets(target)
        elif ISourcePackage.providedBy(target):
            self._is_product_series = False
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

    def calendar(self):
        calendar_link = self.target_facets.calendar()
        calendar_link.target = self.target
        return calendar_link

    def branches(self):
        branches_link = self.target_facets.branches()
        if not self._is_product_series:
            branches_link.target = self.target
        return branches_link


class POTemplateMenu(NavigationMenu):
    """Navigation menus for `IPOTemplate` objects."""
    usedfor = IPOTemplate
    facet = 'translations'
    # XXX: henninge 2009-04-22 bug=365112: The order in this list was
    # rearranged so that the last item is public. The desired order is:
    # links = ['overview', 'upload', 'download', 'edit', 'administer']
    links = ['overview', 'edit', 'administer', 'upload', 'download']

    def overview(self):
        text = 'Overview'
        return Link('', text)

    @enabled_with_permission('launchpad.Edit')
    def upload(self):
        text = 'Upload'
        return Link('+upload', text)

    def download(self):
        text = 'Download'
        return Link('+export', text)

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Settings'
        return Link('+edit', text)

    @enabled_with_permission('launchpad.TranslationsAdmin')
    def administer(self):
        text = 'Administer'
        return Link('+admin', text)


class POTemplateSubsetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        # We are not using this context directly, only for traversals.
        self.request.response.redirect('../+translations')


class POTemplateView(LaunchpadView, TranslationsMixin):

    SHOW_RELATED_TEMPLATES = 4

    label = "Translation status"

    def initialize(self):
        """Get the requested languages and submit the form."""
        self.description = self.context.description

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
        # because lp.translations.browser.pofile imports
        # lp.translations.browser.potemplate.
        from lp.translations.browser.pofile import POFileView

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
    def group_parent(self):
        """Return a parent object implementing `IHasTranslationGroups`."""
        if self.context.productseries is not None:
            return self.context.productseries.product
        else:
            return self.context.distroseries.distribution

    @property
    def has_translation_documentation(self):
        """Are there translation instructions for this project."""
        translation_group = self.group_parent.translationgroup
        return (translation_group is not None and
                translation_group.translation_guide_url is not None)

    @property
    def has_related_templates(self):
        by_source = self.context.relatives_by_source
        by_name = self.context.relatives_by_name
        return bool(by_source) or bool(by_name)

    @property
    def related_templates_by_source(self):
        by_source = list(
            self.context.relatives_by_source[:self.SHOW_RELATED_TEMPLATES])
        return by_source

    @property
    def more_templates_by_source(self):
        by_source_count = self.context.relatives_by_source.count()
        if (by_source_count > self.SHOW_RELATED_TEMPLATES):
            other = by_source_count - self.SHOW_RELATED_TEMPLATES
            if other == 1:
                return "one other template"
            else:
                return "%d other templates" % other
        else:
            return None

    @property
    def related_templates_by_name(self):
        by_name = list(
            self.context.relatives_by_name[:self.SHOW_RELATED_TEMPLATES])
        return by_name

    @property
    def has_more_templates_by_name(self):
        by_name_count = self.context.relatives_by_name.count()
        return by_name_count > self.SHOW_RELATED_TEMPLATES

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


class POTemplateUploadView(LaunchpadView, TranslationsMixin):
    """Upload translations and updated template."""

    label = "Upload translations"
    page_title = "Upload translations"

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    def initialize(self):
        """Get the requested languages and submit the form."""
        self.submitForm()

    def submitForm(self):
        """Process any uploaded files."""

        if self.request.method == 'POST':
            if 'UPLOAD' in self.request.form:
                self.upload()

    def upload(self):
        """Handle a form submission to change the contents of the template.

        Uploads may fail if there are already entries with the same path name
        and uploader (importer) in the queue and the new upload cannot be
        safely matched to any of them.  The user will be informed about the
        failure with a warning message."""
        # XXX henninge 20008-12-03 bug=192925: This code is duplicated for
        # productseries and pofile and should be unified.
        file = self.request.form.get('file')
        if not isinstance(file, FileUpload):
            if not file:
                self.request.response.addErrorNotification(
                    "Your upload was ignored because you didn't select a "
                    "file. Please select a file and try again.")
            else:
                # XXX: Carlos Perello Marin 2004-12-30 bug=116:
                # Epiphany seems to have an unpredictable bug with upload
                # forms (or perhaps it's launchpad because I never had
                # problems with bugzilla). The fact is that some uploads don't
                # work and we get a unicode object instead of a file-like
                # object in "file". We show an error if we see that behaviour.
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
        if ext in translation_importer.supported_file_extensions:
            # Add it to the queue.
            entry = translation_import_queue.addOrUpdateEntry(
                filename, content, True, self.user,
                sourcepackagename=self.context.sourcepackagename,
                distroseries=self.context.distroseries,
                productseries=self.context.productseries,
                potemplate=self.context)

            if entry is None:
                self.request.response.addWarningNotification(
                    "Upload failed.  The name of the file you "
                    "uploaded matched multiple existing "
                    "uploads, for different templates.  This makes it "
                    "impossible to determine which template the new "
                    "upload was for.  Try uploading to a specific "
                    "template: visit the page for the template that you "
                    "want to upload to, and select the upload option "
                    "from there.")
            else:
                self.request.response.addInfoNotification(
                    structured(
                    'Thank you for your upload.  It will be automatically '
                    'reviewed in the next few hours.  If that is not '
                    'enough to determine whether and where your file '
                    'should be imported, it will be reviewed manually by an '
                    'administrator in the coming few days.  You can track '
                    'your upload\'s status in the '
                    '<a href="%s/+imports">Translation Import Queue</a>' %(
                        canonical_url(self.context.translationtarget))))

        elif helpers.is_tar_filename(filename):
            # Add the whole tarball to the import queue.
            (num, conflicts) = (
                translation_import_queue.addOrUpdateEntriesFromTarball(
                    content, True, self.user,
                    sourcepackagename=self.context.sourcepackagename,
                    distroseries=self.context.distroseries,
                    productseries=self.context.productseries,
                    potemplate=self.context))

            if num > 0:
                if num == 1:
                    plural_s = ''
                    itthey = 'it'
                else:
                    plural_s = 's'
                    itthey = 'they'
                self.request.response.addInfoNotification(
                    structured(
                    'Thank you for your upload. %d file%s from the tarball '
                    'will be automatically '
                    'reviewed in the next few hours.  If that is not enough '
                    'to determine whether and where your file%s should '
                    'be imported, %s will be reviewed manually by an '
                    'administrator in the coming few days.  You can track '
                    'your upload\'s status in the '
                    '<a href="%s/+imports">Translation Import Queue</a>' %(
                        num, plural_s, plural_s, itthey,
                        canonical_url(self.context.translationtarget))))
                if len(conflicts) > 0:
                    if len(conflicts) == 1:
                        warning = (
                            "A file could not be uploaded because its "
                            "name matched multiple existing uploads, for "
                            "different templates.")
                        ul_conflicts = (
                            "The conflicting file name was:<br /> "
                            "<ul><li>%s</li></ul>" % cgi.escape(conflicts[0]))
                    else:
                        warning = (
                            "%d files could not be uploaded because their "
                            "names matched multiple existing uploads, for "
                            "different templates." % len(conflicts))
                        ul_conflicts = (
                            "The conflicting file names were:<br /> "
                            "<ul><li>%s</li></ul>" % (
                            "</li><li>".join(map(cgi.escape, conflicts))))
                    self.request.response.addWarningNotification(
                        structured(
                        warning + "  This makes it "
                        "impossible to determine which template the new "
                        "upload was for.  Try uploading to a specific "
                        "template: visit the page for the template that you "
                        "want to upload to, and select the upload option "
                        "from there.<br />"+ ul_conflicts))
            else:
                if len(conflicts) == 0:
                    self.request.response.addWarningNotification(
                        "Upload ignored.  The tarball you uploaded did not "
                        "contain any files that the system recognized as "
                        "translation files.")
                else:
                    self.request.response.addWarningNotification(
                        "Upload failed.  One or more of the files you "
                        "uploaded had names that matched multiple existing "
                        "uploads, for different templates.  This makes it "
                        "impossible to determine which template the new "
                        "upload was for.  Try uploading to a specific "
                        "template: visit the page for the template that you "
                        "want to upload to, and select the upload option "
                        "from there.")
        else:
            self.request.response.addWarningNotification(
                "Upload failed because the file you uploaded was not"
                " recognised as a file that can be imported.")


class POTemplateViewPreferred(POTemplateView):
    """View class that shows only users preferred templates."""

    def pofiles(self):
        return POTemplateView.pofiles(self, preferred_only=True)


class POTemplateEditView(LaunchpadEditFormView):
    """View class that lets you edit a POTemplate object."""

    schema = IPOTemplate
    field_names = ['description', 'priority', 'owner']
    label = 'Edit translation template details'
    page_title = 'Edit details'

    @action(_('Change'), name='change')
    def change_action(self, action, data):
        context = self.context
        old_description = context.description
        old_translation_domain = context.translation_domain
        self.updateContextFromData(data)
        if old_description != context.description:
            self.user.assignKarma(
                'translationtemplatedescriptionchanged',
                product=context.product, distribution=context.distribution,
                sourcepackagename=context.sourcepackagename)
        if old_translation_domain != context.translation_domain:
            # We only update date_last_updated when translation_domain field
            # is changed because is the only significative change that,
            # somehow, affects the content of the potemplate.
            UTC = pytz.timezone('UTC')
            context.date_last_updated = datetime.datetime.now(UTC)

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @property
    def next_url(self):
        return canonical_url(self.context)


class POTemplateAdminView(POTemplateEditView):
    """View class that lets you admin a POTemplate object."""
    field_names = [
        'name', 'translation_domain', 'description', 'header', 'iscurrent',
        'owner', 'productseries', 'distroseries', 'sourcepackagename',
        'from_sourcepackagename', 'sourcepackageversion', 'binarypackagename',
        'languagepack', 'path', 'source_file_format', 'priority',
        'date_last_updated']
    label = 'Administer translation template'
    page_title = "Administer"


class POTemplateExportView(BaseExportView):
    """Request downloads of a `POTemplate` and its translations."""

    label = "Download translations"
    page_title = "Download translations"

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    def processForm(self):
        """Process a form submission requesting a translation export."""
        what = self.request.form.get('what')
        if what == 'all':
            export_potemplate = True

            pofiles = self.context.pofiles
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
            value = pofile.getFullLanguageCode()
            browsername = pofile.getFullLanguageName()

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

    rootsite = 'translations'

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
            raise AssertionError('Unknown context for %s' % potemplate.title)

        if ((official_rosetta and potemplate.iscurrent) or
            check_permission('launchpad.TranslationsAdmin', self.context)):
            # The target is using officially Launchpad Translations and the
            # template is available to be translated, or the user is a is a
            # Launchpad administrator in which case we show everything.
            return potemplate
        else:
            raise NotFoundError(name)


class POTemplateBreadcrumb(Breadcrumb):
    """Breadcrumb for `IPOTemplate`."""

    @property
    def text(self):
        return smartquote('Template "%s"' % self.context.name)
