#!/usr/bin/python
#
# Read iso-codes data file and update the database with its contents
#
# based on code from the Debian iso-codes package:
# Copyright (C) 2004 Alastair McKinstry <mckinstry@debian.org>
# Released under the GPL.
#
# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: 657212c5-95f4-422a-ada4-544bf2827ab5

from xml.sax import saxutils, make_parser, saxlib, saxexts, ContentHandler
from xml.sax.handler import feature_namespaces
import sys, os, getopt, urllib2, locale, time, re, sets, psycopg, string

class XMLHandler(saxutils.DefaultHandler):
    def __init__(self, elementname, attributes, cnx, dbhook, hook=None):
         """ 
         nameslist is the elements to be printed in msgid strings,
         comment is the atrribute to be used in the comment line
         """
         self.elementname = elementname
         self.attributes = attributes
         self.cnx = cnx
         self.dbhook = dbhook
         self.hook = hook

    def startElement(self, name, attrs):
        if name != self.elementname:
            return

        data = {}
        for attrname in self.attributes:
            if attrs.has_key(attrname):
                data[self.attributes[attrname]] = attrs[attrname]

        if self.hook is not None:
            data = self.hook(data)
        if not data:
            return

        self.dbhook(self.cnx, data)

files = {
    'country': '/usr/share/xml/iso-codes/iso_3166.xml',
    'language': '/usr/share/xml/iso-codes/iso_639.xml',
    'spoken': '/usr/share/i18n/SUPPORTED',
    }

def insert_country(cnx, data):
    cr = cnx.cursor()

    # We check first if the entry already exists.
    # We assume that all countries have an iso3166code2 code
    cr.execute(
        """SELECT name FROM Country WHERE iso3166code2='%s'""" % (
        data['iso3166code2'].encode('utf-8')))

    # If it does not exists, it's inserted
    if cr.rowcount < 1:
        cr.execute(
            """INSERT INTO Country (%s) VALUES (%s)""" % (
                ','.join(data.keys()),
                ','.join([str(psycopg.QuotedString(value.encode('utf-8').strip())) for value in data.values()])))
    else:
        # It already exists, we should check if it needs any update
        # That's if the name != from data['name']
        country_row = cr.fetchone()
        if country_row[0] != data['name'].encode('utf-8'):
            # We need to update the name
            cr.execute(
                """UPDATE Country SET name='%s' WHERE iso3166code2='%s'""" %(
                data['name'].encode('utf-8'),
                data['iso3166code2'].encode('utf-8')))
            print ("%r has been updated" % data)

    cnx.commit()
    cr.close()


def import_countries(cnx):
    print
    print 'importing countries...'
    fields = {
        'alpha_2_code': 'iso3166code2',
        'alpha_3_code': 'iso3166code3',
        'name': 'name',
        'official_name': 'title',
        }

    p = make_parser()
    p.setErrorHandler(saxutils.ErrorPrinter())

    dh = XMLHandler('iso_3166_entry', fields, cnx, insert_country)
    p.setContentHandler(dh)
    p.parse(files['country'])


def two_or_three_letters(data):
    if data.has_key('code'):
        if data.has_key('code2'):
            del data['code2']
    else:
        if data.has_key('code2'):
            data['code'] = data['code2']
            del data['code2']
        else:
            return None
    return data

def get_plural_form_data(path):
    fh = file(path)
    forms = {}
    languages = []

    for line in fh:
        match = re.match('^languages: *(.*)$', line)

        if match:
            languages = match.group(1).split(',')
            continue

        match = re.match('^nplurals: *(.*)$', line)

        if match:
            for language in languages:
                if not language in forms:
                    forms[language] = {}

                forms[language]['nplurals'] = string.atoi(match.group(1))

            continue

        match = re.match('^plural: *(.*)$', line)

        if match:
            for language in languages:
                if not language in forms:
                    forms[language] = {}

                forms[language]['plural'] = match.group(1)

            continue

        if not ((line == "\n") or line.startswith('#')):
            raise "error parsing plural form data: \"%s\"" % line[:-1]

    return forms


def insert_language(cnx, data, plural_forms):
    # Ewwww!
    data['code'] = data['code'].encode('ascii')

    if data['code'] in plural_forms:
        data['pluralforms'] = plural_forms[data['code']]['nplurals']
        data['pluralexpression'] = plural_forms[data['code']]['plural']
    else:
        data['pluralforms'] = None
        data['pluralexpression'] = None

    cr = cnx.cursor()
    rosetta_trans = cnx.cursor()

    # We check first if the entry already exists.
    # We assume that all countries have an iso3166code2 code
    cr.execute(
        """SELECT englishname, pluralforms, pluralexpression FROM Language WHERE code='%s'""" % (
        data['code']))

    # We look for the native name for this language into Rosetta. We don't
    # care about the orig of the translation, we just get latest one and
    # assume that we never will have this msgid as a plural form (I don't
    # think it makes sense to have a language name with a plural form...)
    rosetta_trans.execute(
        """SELECT POTranslation.translation
            FROM POMsgID, POMsgSet, POTranslationSighting, POTranslation,
                 POFile, Language, POTemplate, Product
            WHERE
                Product.name = 'iso-codes' AND
                Product.id = POTemplate.product AND
                POTemplate.name = 'languages' AND
                POTemplate.id = POFile.potemplate AND
                Language.code = %(languagecode)s AND
                Language.id = POFile.language AND
                POFile.id = POMsgSet.pofile AND
                POMsgID.msgid = %(englishname)s AND
                POMsgID.id = POMsgSet.primemsgid AND
                POMsgSet.iscomplete = TRUE AND
                POMsgSet.obsolete = FALSE AND
                POMsgSet.fuzzy = FALSE AND
                POMsgSet.id = POTranslationSighting.pomsgset AND
                POTranslationSighting.active = TRUE AND
                POTranslationSighting.potranslation = POTranslation.id""",
        { 'languagecode': data['code'],
          'englishname': data['englishname'].encode('utf-8') })
    if rosetta_trans.rowcount > 0:
        data['nativename'] = rosetta_trans.fetchone()[0]

    rosetta_trans.close()

    # If it does not exists, it's inserted
    if cr.rowcount < 1:
        cr.execute(
            """INSERT INTO Language (%s) VALUES (%s)""" % (
                ','.join(data.keys()),
                ','.join([str(psycopg.QuotedString(value.encode('utf-8').strip())) for value in data.values()])))
    else:
        # It already exists, we should check if it needs any update
        # That's if the englishname != from data['englishname']
        language_row = cr.fetchone()
        if language_row[0] != data['englishname'].encode('utf-8'):
            rosetta_trans.execute(
                """SELECT POTranslation.translation
                    FROM POMsgID, POMsgSet, POTranslationSighting,
                         POTranslation, POFile, Language, POTemplate, Product
                    WHERE
                        Product.name = 'iso-codes' AND
                        Product.id = POTemplate.product AND
                        POTemplate.name = 'languages' AND
                        POTemplate.id = POFile.potemplate AND
                        Language.code = %(languagecode)s AND
                        Language.id = POFile.language AND
                        POFile.id = POMsgSet.pofile AND
                        POMsgID.msgid = %(englishname)s AND
                        POMsgID.id = POMsgSet.primemsgid AND
                        POMsgSet.iscomplete = TRUE AND
                        POMsgSet.obsolete = FALSE AND
                        POMsgSet.fuzzy = FALSE AND
                        POMsgSet.id = POTranslationSighting.pomsgset AND
                        POTranslationSighting.deprecated = FALSE AND
                        POTranslationSighting.potranslation = POTranslation.id""",
                { 'languagecode': data['code'].encode('utf-8'),
                  'englishname': language_row[0] })
            if rosetta_trans.rowcount > 0:
                # We need to update the englishname and the nativename
                cr.execute(
                    """UPDATE Language SET englishname='%s', nativename='%s'
                        WHERE code='%s'""" %(
                    data['englishname'].encode('utf-8'),
                    rosetta_trans.fetchone()[0],
                    data['code']))
            else:
                # We need to update the name and remove the old nativename
                cr.execute(
                    """UPDATE Language SET englishname='%s', nativename=NULL
                        WHERE code='%s'""" %(
                    data['englishname'].encode('utf-8'),
                    data['code']))
            print ("%r has been updated" % data)

        if (language_row[1] != data['pluralforms']) or (language_row[2] !=
                data['pluralexpression']):
            cr.execute(
                """UPDATE Language SET pluralforms=%(pluralforms)d,
                    pluralexpression=%(pluralexpression)s WHERE code=%(code)s""", data)

    cnx.commit()
    cr.close()

def import_languages(cnx, plural_forms):
    print
    print 'importing languages...'
    fields = {
        'iso_639_1_code': 'code',
        'iso_639_2T_code': 'code2',
        'name': 'englishname',
        }

    p = make_parser()
    p.setErrorHandler(saxutils.ErrorPrinter())

    dh = XMLHandler('iso_639_entry', fields, cnx,
        lambda x, y: insert_language(x, y, plural_forms), two_or_three_letters)
    p.setContentHandler(dh)
    p.parse(files['language'])


spoken_re = re.compile('([a-z]*)_([A-Z]*).*')

def import_spoken(cnx, plural_forms):
    print
    print 'parsing spoken...'
    pairs = sets.Set()
    for line in file(files['spoken']).readlines():
        m = spoken_re.match(line)
        if not m:
            continue
        pairs.add((m.group(1), m.group(2)))

    cr = cnx.cursor()

    for pair in pairs:
        # We check if the language-country relation exists:
        cr.execute(
            """SELECT Language.id, Country.id, Language.englishname,
                      Country.name FROM Language, Country
                WHERE Language.code='%s' AND Country.iso3166code2='%s' AND
                      NOT EXISTS (SELECT * FROM Spokenin
                                    WHERE Spokenin.language=Language.id AND
                                          Spokenin.country=Country.id)""" %
                pair)
        if cr.rowcount > 0:
            # We don't have such relation yet.
            spoken_row = cr.fetchone()
            cr.execute("""INSERT INTO Spokenin VALUES(%d, %d)""" % (
                spoken_row[0], spoken_row[1]))

            # We add now the language_country Languages
            # FIXME: Could we assume that if we have already the spokenin
            # relation we already have that language into the Languages table?

            data = {
                'code': u'%s_%s' % pair,
                'englishname': unicode('%s from %s' % (
                    spoken_row[2],
                    spoken_row[3]), 'utf-8')}

            insert_language(cnx, data, plural_forms)

            cr.execute(
                """SELECT Language.id, Country.id
                    WHERE Language.code=%(language)s AND
                          Country.iso3166code2=%(country)s AND
                          NOT EXISTS (SELECT * FROM Spokenin
                                        WHERE Spokenin.language=Language.id
                                        AND Spokenin.country=Country.id)""",
                { 'language': '%s_%s' % pair,
                  'country': pair[1] })

            if cr.rowcount > 0:
                # We don't have such relation yet.
                spoken_row = cr.fetchone()
                cr.execute("""INSERT INTO Spokenin VALUES(%d, %d)""" % (
                    spoken_row[0], spoken_row[1]))

    cnx.commit()
    cr.close()

username = 'carlos'
dbname = 'launchpad_test'
plural_data_file = 'plural-form-data'

if __name__ == '__main__':
    (opts, trail)=getopt.getopt(sys.argv[1:], "u:d:f:",
                                ["username=", "dbname=", "plural-data="])
    for opt, arg in opts:
        if opt in ('-u', '--username'):
            username = arg
        elif opt in ('-d', '--dbname'):
            dbname = arg
        elif opt in ('-p', '--plural-data'):
            plural_data_file = arg

    locale.setlocale(locale.LC_ALL, 'C')
    cnx = psycopg.connect("user=%s dbname=%s" % (username, dbname))
    import_countries(cnx)
    plural_forms = get_plural_form_data(plural_data_file)
    import_languages(cnx, plural_forms)
    import_spoken(cnx, plural_forms)
