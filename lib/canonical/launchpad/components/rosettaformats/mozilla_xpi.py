# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'MozillaSupport'
    ]

from UserDict import DictMixin
from StringIO import StringIO

from zope.interface import implements
from zope.component import getUtility

from canonical.librarian.interfaces import ILibrarianClient
from canonical.launchpad.interfaces import ITranslationImport
from canonical.lp.dbschema import RosettaImportStatus, RosettaFileFormat
from canonical.launchpad.scripts import logger

import os

class LocalizableFile (DictMixin):
    """Class for reading translatable messages from different files.

    It behaves as an iterator over all the messages in the file.
    """

    def __init__(self, logger=None):
        self._data = []
        self._msgids = []
        self.logger = logger

    def __getitem__(self, key):
        return self._data.__getitem__(key)

    def __delitem__(self, key):
        return self._data.__delitem__(key)

    def __setitem__(self, key, value):
        return self._data.__setitem__(key, value)

    def keys(self):
        return self._data.keys()

    def iteritems(self):
        return self._data.iteritems()

    def __iter__(self):
        return self._data.__iter__()

    def __contains__(self, key):
        return self._data.__contains__(key)

    def extend(self, newdata):
        for message in newdata:
            if not message['msgid'] in self._msgids:
                self._msgids.append(message['msgid'])
                self._data.append(message)
            elif self.logger is not None:
                self.logger.info(
                    "Duplicate message ID '%s'." % message['msgid'])

    def getLastTranslator(self):
        return None


class MozillaZipFile (LocalizableFile):
    """Class for reading translatable messages from Mozilla XPI/JAR files.

    It behaves as an iterator over all messages in the file, indexed by
    msgid's.  It handles embedded jar, dtd and properties files.
    """

    def __init__(self, file, logger=None):
        LocalizableFile.__init__(self, logger=logger)
        self.last_translator = None
        self.logger = logger

        from zipfile import ZipFile, ZipInfo

        zip = ZipFile(file, 'r')
        for file in zip.namelist():
            if file.endswith('.properties'):
                data = zip.read(file)
                pf = PropertyFile(filename=file, file=StringIO(data),
                                  logger=logger)
                self.extend(pf)
            elif file.endswith('.dtd'):
                data = zip.read(file)
                dtdf = DtdFile(filename=file, file=StringIO(data),
                               logger=logger)
                self.extend(dtdf)
            elif file.endswith('.jar'):
                data = zip.read(file)
                jarf = MozillaZipFile(StringIO(data), logger)
                self.extend(jarf)
            elif file == 'install.rdf':
                import re
                data = zip.read(file)
                match = re.match('<em:contributor>(.*)</em:contributor>', data)
                if match:
                    self.last_translator = match.groups()[0]

    def getLastTranslator(self):
        return self.last_translator



from xml.parsers.xmlproc import dtdparser, xmldtd, utils
class MozillaDtdConsumer (xmldtd.WFCDTD):
    """Mozilla DTD translatable message parser.

    Extracts all entities along with comments and source references.
    """
    def __init__(self, parser, filename, messages):
        self.started = 0
        self.lastcomment = None
        self.messages = messages
        self.filename = filename
        xmldtd.WFCDTD.__init__(self, parser)

    def dtd_start(self):
        self.started = 1

    def dtd_end(self):
        self.started = 0

    def handle_comment(self, contents):
        if not self.started: return
        if contents.strip().startswith('LOCALIZATION NOTE'):
            self.lastcomment = contents

    def new_general_entity(self, name, value):
        if not self.started: return
        self.messages.append({ 'msgid' : name,
                               'sourcerefs' : [ "%s(%s)" % (self.filename,
                                                            name) ],
                               'content' : value,
                               'order' : self.started,
                               'comment' : self.lastcomment })
        self.started += 1
        self.lastcomment = None

class DtdFile (LocalizableFile):
    """Class for reading translatable messages from a .dtd file.

    It behaves as an iterator over messages in the file, indexed by entity
    names from the .dtd file.
    """
    def __init__(self, filename, file, logger=None):
        self._data = []
        self.logger = logger

        parser=dtdparser.DTDParser()
        parser.set_error_handler(utils.ErrorCounter())
        dtd = MozillaDtdConsumer(parser, filename, self._data)
        parser.set_dtd_consumer(dtd)
        parser.parse_string(file.read())



class PropertyFile (LocalizableFile):
    """Class for reading translatable messages from a .properties file.
    It behaves as an iterator over messages in the file, indexed by keys
    from the .properties file.
    """

    def __init__(self, filename, file, logger=None):
        """Constructs a dictionary from a .properties file.

        It expects a file-like object "file".
        "filename" is used for source code references.
        """
        self.filename = filename
        self._data = []
        self.logger = logger
        data = file.read()

        # .properties files are defined to be unicode-escaped, but
        # also allow direct UTF-8
        udata = data.decode('utf-8')

        count = 0
        lastcomment = None

        lines = udata.split("\n")
        for line in lines:
            # Ignore empty and comment lines
            if not len(line.strip()) or line[0]=='#' or line[0]=='!':
                if len(line.strip()) and line[0] in ('#', '!'):
                    if lastcomment:
                        lastcomment += ' ' + line[1:].strip()
                        if 'END LICENSE BLOCK' in lastcomment:
                            lastcomment = None
                    else:
                        lastcomment = line[1:].strip()
                else:
                    # reset comment on empty lines
                    lastcomment = None
                continue
            (key, value) = line.split('=', 1)

            # Now, to "normalize" all to the same encoding, we encode to
            # unicode-escape first, and then decode it to unicode
            # XXX: Danilo 2006-08-01: we _might_ get performance
            # improvements if we reimplement this to work directly,
            # though, it will be hard to beat C-based de/encoder
            value = value.encode('unicode_escape').decode('unicode_escape')

            count += 1
            self._data.append({ 'msgid' : key,
                                'sourcerefs' : [ "%s(%s)" % (self.filename,
                                                             key) ],
                                'content' : value,
                                'order' : count,
                                'comment' : lastcomment })
            lastcomment = None

class MozillaSupport:
    implements(ITranslationImport)

    def __init__(self, path, productseries=None, distrorelease=None,
                 sourcepackagename=None, is_published=False, file=None,
                 logger=None):
        self.basepath = path
        self.productseries = productseries
        self.distrorelease = distrorelease
        self.sourcepackagename = sourcepackagename
        self.is_published = is_published
        self.file = file
        self.logger = logger

    @property
    def allentries(self):
        """See ITranslationImport."""
        if not self.basepath.lower().endswith('.xpi'):
            return None

        entries = []

        content = self.file.read()

        if os.path.basename(self.basepath) == 'en-US.xpi':
            # We need PO template entry
            language = None

        else:
            # It's not en-US.xpi, so it's a translation
            # Lets strip ".xpi" off the name
            language = os.path.splitext(self.basepath)[0]

        entries.append( { 'path' : self.basepath,
                          'productseries' : self.productseries,
                          'distrorelease' : self.distrorelease,
                          'sourcepackagename' : self.sourcepackagename,
                          'is_published' : self.is_published,
                          'template' : self.sourcepackagename,
                          'language' : language,
                          'state' : RosettaImportStatus.NEEDS_REVIEW,
                          'format' : RosettaFileFormat.XPI } )
        return entries

    def getTemplate(self, path):
        mozimport = MozillaZipFile(StringIO(self.file.read()), self.logger)
        import sys

        messages = []
        for xpimsg in mozimport:
            msg = {}

            msgid = xpimsg['msgid']
            msg['msgid'] = msgid
            msg['msgid_plural'] = None

            msg['comment'] = None
            msg['filerefs'] = None
            msg['flags'] = []
            msg['obsolete'] = False
            msg['sourcecomment'] = None

            if (msgid.endswith('.accesskey') or
                msgid.endswith('.commandkey')):
                # Special case accesskeys and commandkeys:
                # these are single letter messages, lets display
                # the value as a source comment.
                msg['sourcecomment'] = u"Default key in en_US: '%s'" % (
                    xpimsg['content'])
                msg['msgstr'] = None
            else:
                # In other cases, store the content value as the 'en'
                # translation.
                msg['msgstr'] = { 0: xpimsg['content'] }

            if xpimsg['sourcerefs'] and len(xpimsg['sourcerefs']):
                msg['filerefs'] = u" ".join(xpimsg['sourcerefs'])

            # Add source comments
            if xpimsg['comment'] is not None:
                msg['sourcecomment'] = xpimsg['comment']
            messages.append(msg)

        return {
            "revisiondate" : None,
            "lasttranslatoremail" : None,
            "lasttranslatorname" : None,
            "header" : None,
            "format" : RosettaFileFormat.XPI,
            "messages" : messages
            }

    def getTranslation(self, path, language):
        mozimport = MozillaZipFile(StringIO(self.file.read()), self.logger)

        messages = []
        for xpimsg in mozimport:
            msg = {}
            msg['msgid'] = xpimsg['msgid']
            msg['msgid_plural'] = None
            msg['msgstr'] = { 0: xpimsg['content'] }

            msg['comment'] = None
            msg['filerefs'] = None
            msg['flags'] = []
            msg['obsolete'] = False
            msg['sourcecomment'] = None

            messages.append(msg)

        return {
            "revisiondate" : None,
            "lasttranslatoremail" : None,
            "lasttranslatorname" : None,
            "header" : None,
            "format" : RosettaFileFormat.XPI,
            "messages" : messages,
            }
