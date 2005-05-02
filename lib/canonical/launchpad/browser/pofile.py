# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import popen2
import os

from zope.component import getUtility
from zope.publisher.browser import FileUpload

from canonical.launchpad.interfaces import ILaunchBag
from canonical.launchpad.components.poexport import POExport
from canonical.launchpad.components.poparser import POHeader, POSyntaxError, \
    POInvalidInputError
from canonical.launchpad import helpers


class ViewPOFile:
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form
        self.status_message = None
        self.header = POHeader(msgstr=context.header)
        self.header.finish()

    def pluralFormExpression(self):
        plural = self.header['Plural-Forms']
        return plural.split(';', 1)[1].split('=',1)[1].split(';', 1)[0].strip();

    def completeness(self):
        return '%.2f%%' % self.context.translatedPercentage()

    def untranslated(self):
        return self.context.untranslatedCount()

    def editSubmit(self):
        if "SUBMIT" in self.request.form:
            if self.request.method != "POST":
                self.status_message = 'This form must be posted!'
                return

            self.header['Plural-Forms'] = 'nplurals=%s; plural=%s;' % (
                self.request.form['pluralforms'],
                self.request.form['expression'])
            self.context.header = self.header.msgstr.encode('utf-8')
            self.context.pluralforms = int(self.request.form['pluralforms'])
            self.submitted = True
            self.request.response.redirect('./')
        elif "UPLOAD" in self.request.form:
            if self.request.method != "POST":
                self.status_message = 'This form must be posted!'
                return
            file = self.form['file']

            if type(file) is not FileUpload:
                if file == '':
                    self.status_message = 'You forgot the file!'
                else:
                    # XXX: Carlos Perello Marin 03/12/2004: Epiphany seems to have an
                    # aleatory bug with upload forms (or perhaps it's launchpad because
                    # I never had problems with bugzilla). The fact is that some uploads
                    # don't work and we get a unicode object instead of a file-like object
                    # in "file". We show an error if we see that behaviour.
                    # For more info, look at bug #116
                    self.status_message = 'There was an unknow error getting the file.'
                return

            filename = file.filename

            if not filename.endswith('.po'):
                self.status_message =  'Dunno what this file is.'
                return

            pofile = file.read()

            user = getUtility(ILaunchBag).user

            try:
                self.context.attachRawFileData(pofile, user)
            except (POSyntaxError, POInvalidInputError):
                # The file is not correct.
                self.status_message = 'Please, review the po file seems to have a problem'
                return

            self.request.response.redirect('./')
            self.submitted = True


class ViewPOExport:
    def __call__(self):
        pofile = self.context
        poExport = POExport(pofile.potemplate)
        languageCode = pofile.language.code
        exportedFile = poExport.export(languageCode)

        self.request.response.setHeader('Content-Type', 'application/x-po')
        self.request.response.setHeader('Content-Length', len(exportedFile))
        self.request.response.setHeader('Content-Disposition',
                'attachment; filename="%s.po"' % languageCode)
        return exportedFile


class ViewMOExport:
    def __call__(self):
        pofile = self.context
        poExport = POExport(pofile.potemplate)
        languageCode = pofile.language.code
        exportedFile = poExport.export(languageCode)

        # XXX: It's ok to hardcode the msgfmt path?
        msgfmt = popen2.Popen3('/usr/bin/msgfmt -o - -', True)

        # We feed the command with our .po file from the stdin
        msgfmt.tochild.write(exportedFile)
        msgfmt.tochild.close()

        # Now we wait until the command ends
        status = msgfmt.wait()

        if os.WIFEXITED(status):
            if os.WEXITSTATUS(status) == 0:
                # The command worked
                output = msgfmt.fromchild.read()

                self.request.response.setHeader('Content-Type',
                    'application/x-gmo')
                self.request.response.setHeader('Content-Length',
                    len(output))
                self.request.response.setHeader('Content-disposition',
                    'attachment; filename="%s.mo"' % languageCode)
                return output
            else:
                # XXX: Perhaps we should be more "polite" if it fails
                return msgfmt.childerr.read()
        else:
            # XXX: Perhaps we should be more "polite" if it fails
            return "ERROR exporting the .mo!!"

