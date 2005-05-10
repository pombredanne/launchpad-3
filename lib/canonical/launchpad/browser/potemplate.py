# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import tarfile
from sets import Set
from StringIO import StringIO

from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.publisher.browser import FileUpload

from canonical.launchpad import helpers
from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import ILaunchBag
from canonical.launchpad.components.poexport import POExport
from canonical.launchpad.components.poparser import POSyntaxError, \
    POInvalidInputError

from canonical.launchpad.browser.pofile import ViewPOFile


class POTemplateSubsetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        # We are not using this context directly, only for traversals.
        return self.request.response.redirect('../+translations')


class ViewPOTemplate:

    statusLegend = ViewPageTemplateFile(
        '../templates/portlet-rosetta-status-legend.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.request_languages = helpers.request_languages(self.request)
        self.name = self.context.potemplatename.name
        self.title = self.context.potemplatename.title
        self.description = self.context.potemplatename.description
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

        Yields a ViewPOFile object for each language this template has
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
            yield ViewPOFile(pofile, self.request)

    def submitForm(self):
        """Called from the page template to do any processing needed if a form
        was submitted with the request."""

        if self.request.method == 'POST':
            if 'EDIT' in self.request.form:
                self.edit()
            elif 'UPLOAD' in self.request.form:
                self.upload()

        return ''

    def editAttributes(self):
        """Use form data to change a PO template's name or title."""

        # Early returns are used to avoid the redirect at the end of the
        # method, which prevents the status message from being shown.

        # XXX Dafydd Harries 2005/01/28
        # We should check that there isn't a template with the new name before
        # doing the rename.

        if 'name' in self.request.form:
            name = self.request.form['name']

            if name == '':
                self.status_message = 'The name field cannot be empty.'
                return

            self.context.name = name

        if 'title' in self.request.form:
            title = self.request.form['title']

            if title == '':
                self.status_message = 'The title field cannot be empty.'
                return

            self.context.title = title

        # Now redirect to view the template. This lets us follow the template
        # in case the user changed the name.
        self.request.response.redirect('../' + self.context.name)

    def upload(self):
        """Handle a form submission to change the contents of the template."""

        # Get the launchpad Person who is doing the upload.
        owner = getUtility(ILaunchBag).user

        file = self.request.form['file']

        if type(file) is not FileUpload:
            if file == '':
                self.request.response.redirect('../' + self.context.name)
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

        filename = file.filename

        if filename.endswith('.pot'):
            potfile = file.read()

            try:
                self.context.attachRawFileData(potfile, owner)
            except (POSyntaxError, POInvalidInputError):
                # The file is not correct.
                self.status_message = (
                    'There was a problem parsing the file you uploaded.'
                    ' Please check that it is correct.')

            self.context.attachRawFileData(potfile, owner)
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
        for poFile in self.context.poFiles:
            if poFile.variant is not None:
                raise RuntimeError("PO files with variants are not supported.")

            code = poFile.language.code.encode('utf-8')
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
        old_url = self.request.getURL
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
