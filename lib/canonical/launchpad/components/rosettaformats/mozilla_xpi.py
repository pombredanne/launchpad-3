# Copyright 2006 Canonical Ltd.  All rights reserved.

from UserDict import DictMixin
from StringIO import StringIO
from zope.interface import implements
from canonical.librarian.interfaces import ILibrarianClient
from canonical.launchpad.database import LibraryFileAlias
from canonical.launchpad.interfaces import ITranslationImport
from canonical.lp.dbschema import RosettaImportStatus

import os

class LocalizableFile (DictMixin):
    """Class for reading translatable messages from different files.

    It behaves as an iterator over all the messages in the file.
    """

    def __init__(self):
        self._data = {}

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

    def getLastTranslator(self):
        return None




class MozillaZipFile (LocalizableFile):
    """Class for reading translatable messages from Mozilla XPI/JAR files.

    It behaves as an iterator over all messages in the file, indexed by 
    msgid's.  It handles embedded jar, dtd and properties files.
    """

    def __init__(self, file):
        LocalizableFile.__init__(self)
        self.last_translator = None

        from zipfile import ZipFile, ZipInfo

        zip = ZipFile(file, 'r')
        for file in zip.namelist():
            if file.endswith('.properties'):
                data = zip.read(file)
                pf = PropertyFile(filename=file, file=StringIO(data))
                self._data.update(pf)
            elif file.endswith('.dtd'):
                data = zip.read(file)
                dtdf = DtdFile(filename=file, file=StringIO(data))
                self._data.update(dtdf)
            elif file.endswith('.jar'):
                data = zip.read(file)
                jarf = MozillaZipFile(StringIO(data))
                self._data.update(jarf)
            elif file == 'install.rdf':
                import re
                data = zip.read(file)
                match = re.match('<em:contributor>(.*)</em:contributor>')
                if match:
                    self.last_translator = match.group(1)

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
        if self.messages.has_key(name):
            print >>sys.stderr, "Warning: there is already a message with key '%s'." % name
            self.messages[name]['sourcerefs'].append(self.filename)
            if self.lastcomment:
                self.messages[name]['comments'].append(self.lastcomment)
        else:
            self.messages[name] = { 'sourcerefs' : [ self.filename ],
                                    'content' : value,
                                    'order' : self.started,
                                    'comments' : [ ] }
            if self.lastcomment:
                self.messages[name]['comments'] = [ self.lastcomment]
            self.started += 1

        self.lastcomment = None

class DtdFile (LocalizableFile):
    """Class for reading translatable messages from a .dtd file.

    It behaves as an iterator over messages in the file, indexed by entity
    names from the .dtd file.
    """
    def __init__(self, filename, file):
        self._data = {}

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

    def __init__(self, filename, file):
        """Constructs a dictionary from a .properties file.

        It expects a file-like object "file".
        "filename" is used for source code references.
        """
        self.filename = filename
        self._data = {}
        data = file.read()

        # .properties files are defined to be unicode-escaped, but
        # also allow direct UTF-8
        udata = data.decode('utf-8')

        count = 0
        lastcomment = 0

        lines = udata.split("\n")
        for line in lines:
            # Ignore empty and comment lines
            if not len(line.strip()) or line[0]=='#' or line[0]=='!':
                continue
            (key, value) = line.split('=', 1)

            # Now, to "normalize" all to the same encoding, we encode to
            # unicode-escape first, and then decode it to unicode
            # XXX: Danilo 2006-08-01: we _might_ get performance
            # improvements if we reimplement this to work directly,
            # though, it will be hard to beat C-based de/encoder
            value = value.encode('unicode_escape').decode('unicode_escape')

            if self._data.has_key(key):
                print >>sys.stderr, "Warning: there is already a message with key '%s'." % name
                self._data[key]['sourcerefs'].append(filename)
                if lastcomment:
                    self._data[key]['comments'].append(lastcomment)
            else:
                count += 1
                self._data[key] = { 'sourcerefs' : [ filename ],
                                    'content' : value,
                                    'order' : count,
                                    'comments' : [] }
                if lastcomment:
                    self._data[key]['comments'] = [ lastcomment]

class MozillaSupport:
    implements(ITranslationImport)

    def __init__(self, path, productseries=None, distrorelease=None,
                 sourcepackagename=None, is_published=False, file=None):
        self.basepath = path
        self.productseries = productseries
        self.distrorelease = distrorelease
        self.sourcepackagename = sourcepackagename
        self.is_published = is_published
        self.file = file

    @property
    def allentries(self):
        """See ITranslationImport."""
        if not self.basepath.lower().endswith('.xpi'):
            return None

        entries = []

        content = self.file.read()

        if os.path.basename(self.basepath) == 'en-US.xpi':
            # We need PO template entry

            # Add entry to librarian in the form of
            # productseries-distrorelease-sourcepackagename.en-US.xpi
            # XXX: will this not expire right away?
            #librarian_client.addFile(
            #    '%s-%s-%s.en-US.xpi' % (self.productseries,
            #                            self.distrorelease,
            #                            self.sourcepackagename),
            #    len(content),
            #    self.file,
            #    None)
            language = None

        else:
            # It's not en-US.xpi, so it's a translation
            # Lets strip ".xpi" off the name
            language = self.getRosettaLanguageForXpiLanguage(
                os.path.basename(self.basepath)[:-4])

        entries.append( { 'path' : self.basepath,
                          'productseries' : self.productseries,
                          'distrorelease' : self.distrorelease,
                          'sourcepackagename' : self.sourcepackagename,
                          'is_published' : self.is_published,
                          'template' : self.sourcepackagename,
                          'language' : language,
                          'state' : RosettaImportStatus.NEEDS_REVIEW } )
        return entries

    def getTemplate(self, path):
        file = librarian_client.getFileByAlias(self.content)

    def getTranslation(self, path, language):
        LibraryFileAlias()

    def getRosettaLanguageForXpiLanguage(self, xpilang):
        langdata = self.languagePackData(xpilang)
        if langdata:
            return langdata[0]
        else:
            # XXX: generate UUID as well?
            return xpilang

    def languagePackData(self, language):
        map = {
            'af-ZA' : ('af', "{95a05dab-bf44-4804-bb97-be2a3ee83acd}"),
            'ast-ES' : ('ast', "{b5cfaf65-895d-4d69-ba92-99438d6003e9}"),
            'bg-BG' : ('bg', "{b5962da4-752e-416c-9934-f97724f07051}"),
            'ca-AD' : ('ca', "{f3b38190-f8e0-4e8b-bf29-451fb95c0cbd}"),
            'cs-CZ' : ('cs', "{37b3f2ec-1229-4289-a6d9-e94d2948ae7e}"),
            'da-DK' : ('da', "{1f391bb4-a820-4e44-8b68-01b385d13f94}"),
            'de-DE' : ('de', "{69C47786-9BEF-49BD-B99B-148C9264AF72}"),
            'el-GR' : ('el', "{eb0c5e26-c8a7-4873-b633-0f453cb1debc}"),
            'en-GB' : ('en_GB', "{6c3a4023-ca27-4847-a410-2fe8a2401654}"),
            'es-AR' : ('es_AR', "{2fe2cb3b-f439-46f9-b0b9-cafad4e62185}"),
            'es-ES' : ('es', "{e4d01067-3443-405d-939d-a200ed3db577}"),
            'fi-FI' : ('fi', "{c5e1e759-ba2e-44b1-9915-51239d89c492}"),
            'fr-FR' : ('fr', "{5102ddd3-a33f-436f-b43c-f9468a8f8b32}"),
            'ga-IE' : ('ga', "{906b5382-9a34-4ab1-a627-39487b0678a9}"),
            'gu-IN' : ('gu', "{16baab125756b023981bc4a14bd77b5c}"),
            'he-IL' : ('he', "{9818f84c-1be1-4eea-aded-55f406c70e37}"),
            'hu-HU' : ('hu', "{cacb8e15-7f1b-4e71-a3c0-d63ce907366f}"),
            'it-IT' : ('it', "{9db167da-cba5-4d12-b045-5d2a5a36a88a}"),
            'ja-JP' : ('ja', "{02d61967-84bb-455b-a14b-76abc5864739}"),
            'ko-KR' : ('ko', "{dcff4b08-a6cc-4588-a941-852609855803}"),
            'mk-MK' : ('mk', "{376b068c-4aff-4f66-bb4c-fde345b63073}"),
            'nb-NO' : ('nb', "{4CD2763D-5532-4ddc-84D9-2E094695A680}"),
            'nl-NL' : ('nl', "{83532d50-69a7-46d7-9873-ed232d5b246b}"),
            'pa_IN' : ('pa', "{96f366b1-5194-4e30-9415-1f6fcaaaa583}"),
            'pl-PL' : ('pl', "{cbfb6154-47f6-47ea-b888-6440a4ba44e8}"),
            'pt-BR' : ('pt_BR', "{8cb7341c-bcb6-43ca-b214-c48967f2a77e}"),
            'pt-PT' : ('pt', "{6e528a74-5cca-40d1-mozia152-d1b2d415210b}"),
            'ro-RO' : ('ro', "{93ead120-1d61-4663-852d-ee631493168f}"),
            'ru-RU' : ('ru', "{9E20245A-B2EE-4ee6-815B-99C30B35D0D2}"),
            'sl-SI' : ('sl', "{ac25d192-0004-4228-8dc3-13a5461ca1c6}"),
            'sq-AL' : ('sq', "{5ea95deb-8819-4960-837f-46de0f22bf81}"),
            'sv-SE' : ('sv', "{A3E7CC55-B6E4-4a87-BD2E-657CA489F23A}"),
            'tr-TR' : ('tr', "{08c0f953-0736-4989-b921-3e7ddfaf556a}"),
            'uk-UA' : ('uk', "{f68df430-4534-4473-8ca4-d5de32268a8d}"),
            'zh-CN' : ('zh_CN', "{74d253f5-1463-4de4-bc6e-a7127c066416}"),
            'zh-TW' : ('zh_TW', "{0c7ce36c-a092-4a3d-9ac3-9891d2f2727e}")
            }
        if map.has_key(language):
            return map[language]
        return None
