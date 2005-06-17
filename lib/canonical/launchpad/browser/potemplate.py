# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import tarfile
from sets import Set
from StringIO import StringIO
from datetime import datetime

from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.i18n import ZopeMessageIDFactory as _
from zope.publisher.browser import FileUpload
from zope.app.form.browser.add import AddView
from zope.app.publisher.browser import BrowserView

from canonical.launchpad import helpers
from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import ILaunchBag, IPOTemplateSet, \
    IPOTemplateNameSet, IPersonSet, RawFileAttachFailed, IPOExportRequestSet
from canonical.launchpad.components.poexport import POExport
from canonical.launchpad.browser.pofile import POFileView
from canonical.launchpad.browser.editview import SQLObjectEditView

class POTemplateSubsetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        # We are not using this context directly, only for traversals.
        return self.request.response.redirect('../+translations')


class POTemplateView:

    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-potemplate-actions.pt')

    detailsPortlet = ViewPageTemplateFile(
        '../templates/portlet-potemplate-details.pt')

    forPortlet = ViewPageTemplateFile(
        '../templates/portlet-potemplate-for.pt')

    relativesPortlet = ViewPageTemplateFile(
        '../templates/potemplate-portlet-relateds.pt')

    statusLegend = ViewPageTemplateFile(
        '../templates/portlet-rosetta-status-legend.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.request_languages = helpers.request_languages(self.request)
        self.description = self.context.potemplatename.description
        self.user = getUtility(ILaunchBag).user
        # XXX carlos 01/05/05 please fix up when we have the
        # MagicURLBox

        # We will be constructing a URL path using a list.
        L = []
        if self.context.productrelease:
            L.append('products')
            L.append(self.context.productrelease.product.name)
            L.append(self.context.productrelease.version)
            L.append('+pots')
            L.append(self.context.potemplatename.name)
            self.what = self.context.productrelease.product.name
            self.what += ' ' + self.context.productrelease.version
        elif self.context.distrorelease and self.context.sourcepackagename:
            L.append('distros')
            L.append(self.context.distrorelease.distribution.name)
            L.append(self.context.distrorelease.name)
            L.append('+sources')
            L.append(self.context.sourcepackagename.name)
            L.append('+pots')
            L.append(self.context.potemplatename.name)
            self.what = self.context.sourcepackagename.name + ' in '
            self.what += self.context.distrorelease.distribution.name + ' '
            self.what += self.context.distrorelease.name
        else:
            raise NotImplementedError('We only understand POTemplates '
                'linked to source packages and product releases.')
        # The URL path is to start and end with '/'.
        self.URL = '/%s/' % '/'.join(L)
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
            tarball = helpers.string_to_tarfile(file.read())
            pot_paths, po_paths = helpers.examine_tarfile(tarball)

            error = helpers.check_tar(tarball, pot_paths, po_paths)

            if error is not None:
                self.status_message = error
                return

            self.status_message = (
                helpers.import_tar(self.context, owner, tarball, pot_paths, po_paths))
        else:
            self.status_message = (
                'The file you uploaded was not recognised as a file that '
                'can be imported.')


class POTemplateEditView(POTemplateView, SQLObjectEditView):
    """View class that lets you edit a POTemplate object."""
    def __init__(self, context, request):
        POTemplateView.__init__(self, context, request)
        SQLObjectEditView.__init__(self, context, request)

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
            productrelease=self.context)
        # Create the new POTemplate
        potemplate = potemplatesubset.new(
            potemplatename=potemplatename, contents=content,
            owner=owner)

        # Update the other fields
        potemplate.description = description
        potemplate.iscurrent = iscurrent
        potemplate.path = path
        potemplate.filename = filename

        self._nextURL = "%s" % potemplate.potemplatename.name

    def nextURL(self):
        return self._nextURL


class POTemplateExport:
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self.formProcessed = False
        self.errorMessage = None

    def processForm(self):
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

        request_set = getUtility(IPOExportRequestSet)

        if export_potemplate:
            request_set.addRequest(self.user, self.context, pofiles)
        else:
            request_set.addRequest(self.user, None, pofiles)

        self.formProcessed = True

    def pofiles(self):
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

class POTemplateTarExport:
    '''View class for exporting a tarball of translations.'''

    def make_tar_gz(self, poExporter):
        '''Generate a gzipped tar file for the context PO template. The export
        method of the given poExporter object is used to generate PO files.
        The contents of the tar file as a string is returned.
        '''

        # Create a new StringIO-backed gzipped tarfile.
        outputbuffer = StringIO()
        archive = tarfile.open('', 'w:gz', outputbuffer)

        # XXX
        # POTemplate.name and Language.code are unicode objects, declared
        # using SQLObject's StringCol. The name/code being unicode means that
        # the filename given to the tarfile module is unicode, and the
        # filename is unicode means that tarfile writes unicode objects to the
        # backing StringIO object, which causes a UnicodeDecodeError later on
        # when StringIO attempts to join together its buffers. The .encode()s
        # are a workaround. When SQLObject has UnicodeCol, we should be able
        # to fix this properly.
        # -- Dafydd Harries, 2005/01/20

        # Create the directory the PO files will be put in.
        directory = 'rosetta-%s' % self.context.name.encode('utf-8')
        dirinfo = tarfile.TarInfo(directory)
        dirinfo.type = tarfile.DIRTYPE
        archive.addfile(dirinfo)

        # Put a file in the archive for each PO file this template has.
        for pofile in self.context.pofiles:
            if pofile.variant is not None:
                raise RuntimeError("PO files with variants are not supported.")

            code = pofile.language.code.encode('utf-8')
            name = '%s.po' % code

            # Export the PO file.
            contents = poExporter.export(code)

            # Put it in the archive.
            fileinfo = tarfile.TarInfo("%s/%s" % (directory, name))
            fileinfo.size = len(contents)
            archive.addfile(fileinfo, StringIO(contents))

        archive.close()

        return outputbuffer.getvalue()

    def __call__(self):
        '''Generates a tarball for the context PO template, sets up the
        response (status, content length, etc.) and returns the PO template
        generated so that it can be returned as the body of the request.
        '''

        # This exports PO files for us from the context template.
        poExporter = POExport(self.context)

        # Generate the tarball.
        body = self.make_tar_gz(poExporter)

        self.request.response.setStatus(200)
        self.request.response.setHeader('Content-Type', 'application/x-tar')
        self.request.response.setHeader('Content-Length', len(body))
        self.request.response.setHeader('Content-Disposition',
            'attachment; filename="%s.tar.gz"' % self.context.name)

        return body


# This class is only a compatibility one so the old URL to translate with
# Rosetta redirects the user to the new URL and we don't break external links.
# For instance:
# https://launchpad.ubuntu.com/rosetta/products/bazaar/messages.pot/+translate?languages=es
# becomes:
# https://launchpad.ubuntu.com/rosetta/products/bazaar/messages.pot/es/+translate
# The other arguments are preserved.
class POTemplateTranslateView:
    """View class to forward users from old translation URL to the new one."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

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


class POTemplateAbsoluteURL(BrowserView):
    """The view for an absolute URL of a bug task."""
    def __str__(self):
        if self.context.productrelease:
            return "%s/products/%s/%s/+pots/%s/" % (
                self.request.getApplicationURL(),
                self.context.productrelease.product.name,
                self.context.productrelease.version,
                self.context.potemplatename.name)
        elif self.context.distrorelease:
            return "%s/distros/%s/%s/+sources/%s/+pots/%s/" % (
                self.request.getApplicationURL(),
                self.context.distrorelease.distribution.name,
                self.context.distrorelease.name,
                self.context.sourcepackagename.name,
                self.context.potemplatename.name)


