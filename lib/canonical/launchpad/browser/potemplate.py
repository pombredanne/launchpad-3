# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Browser code for PO templates."""

__metaclass__ = type

__all__ = [
    'POTemplateSubsetView', 'POTemplateView', 'POTemplateEditView',
    'POTemplateAdminView', 'POTemplateAddView', 'BaseExportView',
    'POTemplateExportView', 'POTemplateTranslateView',
    'POTemplateSubsetURL', 'POTemplateURL']

import tarfile
from sets import Set
from StringIO import StringIO
from datetime import datetime

from zope.component import getUtility
from zope.interface import implements
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.i18n import ZopeMessageIDFactory as _
from zope.publisher.browser import FileUpload
from zope.app.form.browser.add import AddView
from zope.app.publisher.browser import BrowserView

from canonical.lp.dbschema import RosettaFileFormat
from canonical.launchpad import helpers
from canonical.launchpad.webapp import canonical_url
from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import (
    ILaunchBag, IPOTemplateSet, IPOTemplateNameSet, IPersonSet,
    RawFileAttachFailed, IPOExportRequestSet, ICanonicalUrlData,
    ILaunchpadCelebrities)
from canonical.launchpad.components.poexport import POExport
from canonical.launchpad.browser.pofile import POFileView
from canonical.launchpad.browser.pofile import BaseExportView
from canonical.launchpad.browser.editview import SQLObjectEditView

class POTemplateSubsetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        # We are not using this context directly, only for traversals.
        return self.request.response.redirect('../+translations')


class POTemplateView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.request_languages = helpers.request_languages(self.request)
        self.description = self.context.potemplatename.description
        self.user = getUtility(ILaunchBag).user
        self.status_message = None

    def num_messages(self):
        N = self.context.messageCount()
        if N == 0:
            return "no messages at all"
        elif N == 1:
            return "1 message"
        else:
            return "%s messages" % N

    def pofiles(self):
        """Iterate languages shown when viewing this PO template.

        Yields a POFileView object for each language this template has
        been translated into, and for each of the user's languages.
        Where the template has no POFile for that language, we use
        a DummyPOFile.
        """
        # Languages the template has been translated into.
        translated_languages = Set(self.context.languages())

        # The user's languages.
        prefered_languages = Set(self.request_languages)

        # Merge the sets, convert them to a list, and sort them.
        languages = list(translated_languages | prefered_languages)
        languages.sort(lambda a, b: cmp(a.englishname, b.englishname))

        for language in languages:
            pofile = self.context.queryPOFileByLang(language.code)
            if not pofile:
                pofile = helpers.DummyPOFile(self.context, language)
            yield POFileView(pofile, self.request)

    def submitForm(self):
        """Called from the page template to do any processing needed if a form
        was submitted with the request."""

        if self.request.method == 'POST':
            if 'UPLOAD' in self.request.form:
                self.upload()

    def upload(self):
        """Handle a form submission to change the contents of the template."""

        file = self.request.form['file']

        if not isinstance(file, FileUpload):
            if file == '':
                self.status_message = 'Please, select a file to upload.'
            else:
                # XXX: Carlos Perello Marin 2004/12/30
                # Epiphany seems to have an aleatory bug with upload forms (or
                # perhaps it's launchpad because I never had problems with
                # bugzilla). The fact is that some uploads don't work and we
                # get a unicode object instead of a file-like object in
                # "file". We show an error if we see that behaviour. For more
                # info, look at bug #116.
                self.status_message = (
                    'There was an unknown error in uploading your file.')
            return

        filename = file.filename

        if filename.endswith('.pot'):
            potfile = file.read()

            try:
                # a potemplate is always "published" so published=True
                self.context.attachRawFileData(potfile, True, self.user)
                self.status_message = (
                    'Thank you for your upload. The template content will'
                    ' appear in Rosetta in a few minutes.')
            except RawFileAttachFailed, error:
                # We had a problem while uploading it.
                self.status_message = (
                    'There was a problem uploading the file: %s.' % error)

        elif helpers.is_tar_filename(filename):
            tarball = helpers.RosettaReadTarFile(stream=file)
            pot_paths, po_paths = tarball.examine()

            error = tarball.check_for_import(pot_paths, po_paths)

            if error is not None:
                self.status_message = error
                return

            self.status_message = tarball.do_import(
                self.context, self.user, pot_paths, po_paths)
        else:
            self.status_message = (
                'The file you uploaded was not recognised as a file that '
                'can be imported.')


class POTemplateEditView(POTemplateView, SQLObjectEditView):
    """View class that lets you edit a POTemplate object."""
    def __init__(self, context, request):
        # Restrict the info we show to the user depending on the
        # permissions he has.
        self.prepareForm()

        POTemplateView.__init__(self, context, request)
        SQLObjectEditView.__init__(self, context, request)

    def prepareForm(self):
        """Removed the widgets the user is not allowed to change."""
        user = getUtility(ILaunchBag).user
        if user is not None:
            # We do this check because this method can be called before we
            # know which user is getting this view (when we show them the
            # login form.
            admins = getUtility(ILaunchpadCelebrities).admin
            rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_expert
            if not (user.inTeam(admins) or user.inTeam(rosetta_experts)):
                # The user is just a maintainer, we show only the fields
                # 'name', 'description' and 'owner'.
                self.fieldNames = ['name', 'description', 'owner']

    def changed(self):
        formatter = self.request.locale.dates.getFormatter(
            'dateTime', 'medium')
        status = _("Updated on ${date_time}")
        status.mapping = {'date_time': formatter.format(
            datetime.utcnow())}
        self.update_status = status


class POTemplateAdminView(POTemplateEditView):
    """View class that lets you admin a POTemplate object."""


class POTemplateAddView(AddView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # retrieve submitted values from the form
        potemplatenameid = data.get('potemplatename')
        description = data.get('description')
        iscurrent = data.get('iscurrent')
        ownerid = data.get('owner')
        path = data.get('path')
        filename = data.get('filename')
        content = data.get('content')

        # Get the POTemplateName
        potemplatenameset = getUtility(IPOTemplateNameSet)
        potemplatename = potemplatenameset.get(potemplatenameid)

        # Get the Owner
        personset = getUtility(IPersonSet)
        owner = personset.get(ownerid)

        potemplateset = getUtility(IPOTemplateSet)
        potemplatesubset = potemplateset.getSubset(
            productseries=self.context)
        # Create the new POTemplate
        potemplate = potemplatesubset.new(
            potemplatename=potemplatename, contents=content,
            owner=owner)

        # Update the other fields
        potemplate.description = description
        potemplate.iscurrent = iscurrent
        potemplate.path = path
        potemplate.filename = filename

        self._nextURL = canonical_url(potemplate)

    def nextURL(self):
        return self._nextURL

class POTemplateExportView(BaseExportView):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self.formProcessed = False
        self.errorMessage = None

    def processForm(self):
        """Process a form submission requesting a translation export."""

        if self.request.method != 'POST':
            return

        pofiles = []
        what = self.request.form.get('what')

        if what == 'all':
            export_potemplate = True

            pofiles =  self.context.pofiles
        elif what == 'some':
            export_potemplate = 'potemplate' in self.request.form

            for key in self.request.form:
                if '@' in key:
                    code, variant = key.split('@', 1)
                else:
                    code = key
                    variant = None

                try:
                    pofile = self.context.getPOFileByLang(code, variant)
                except KeyError:
                    pass
                else:
                    pofiles.append(pofile)
        else:
            self.errorMessage = (
                'Please choose whether you would like all files or only some '
                'of them.')
            return

        format_name = self.request.form.get('format')

        try:
            format = RosettaFileFormat.items[format_name]
        except KeyError:
            raise RuntimeError("Unsupported format.")

        request_set = getUtility(IPOExportRequestSet)

        if export_potemplate:
            request_set.addRequest(self.user, self.context, pofiles, format)
        else:
            request_set.addRequest(self.user, None, pofiles, format)

        self.formProcessed = True

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


# This class is only a compatibility one so the old URL to translate with
# Rosetta redirects the user to the new URL and we don't break external links.
# For instance:
# https://launchpad.ubuntu.com/rosetta/products/bazaar/messages.pot/+translate?languages=es
# becomes:
# https://launchpad.ubuntu.com/rosetta/products/bazaar/messages.pot/es/+translate
# The other arguments are preserved.
class POTemplateTranslateView:
    """View class to forward users from old translation URL to the new one."""

    def __call__(self):
        parameters = {}
        old_url = self.request.getURL()
        if old_url.endswith('/'):
            new_url = old_url[:-len('/+translate/')]
        else:
            new_url = old_url[:-len('/+translate')]

        # Reuse the count, show and offset arguments.
        for name in ('count', 'show', 'offset'):
            if name in self.request.form:
                parameters[name] = self.request.form.get(name)

        # The languages argument is removed as it's part of the url path.
        if 'languages' in self.request.form:
            language = self.request.form.get('languages')
            if ',' in language:
                raise ValueError('Language unknown: %s', language)
            new_url = '%s/%s/+translate' % (new_url, language)

            if parameters:
                keys = parameters.keys()
                keys.sort()
                new_url = new_url + '?' + '&'.join(
                    [key + '=' + str(parameters[key])
                     for key in keys])
        self.request.response.redirect(new_url)


class POTemplateSubsetURL:
    implements(ICanonicalUrlData)

    def __init__(self, context):
        self.context = context

    @property
    def path(self):
        potemplatesubset = self.context
        if potemplatesubset.distrorelease is not None:
            assert potemplatesubset.productseries is None
            assert potemplatesubset.sourcepackagename is not None
            return '+sources/%s/+pots' % (
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

