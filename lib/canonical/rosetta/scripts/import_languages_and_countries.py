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
import sys, os, getopt, urllib2, locale, time, re, sets, psycopg

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

#        print 'got: %r' % data


        self.dbhook(self.cnx, data)

#        print 'got: %r' % data

locale.setlocale(locale.LC_ALL, 'C')

## try:
##     (opts,trail)=getopt.getopt(sys.argv[1:],"f:c:v:",
##                                ["fields=", "comments=", "is-version="])
##     assert trail, "No argument provided"
## except Exception,e:
##     print "ERROR: %s" % e
##     print
##     print "Usage: iso2pot filename [outfilename]"
##     print " filename: xml data file from iso-codes package"
##     print " outfilename: Write to this file"
##     sys.exit(1)

## for opt, arg in opts:
##     if opt in ('-v', '--is-version'):
##         version = arg
##     elif opt in ('-f', '--fields'):
##      fields = arg.split(',')
##     elif opt in ('-c','--comments'):
##         comment = arg

## if len(trail)==2:
##     ofile = open(trail[1], 'w')
## else:
##     ofile = sys.stdout

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

def insert_language(cnx, data):
    cr = cnx.cursor()

    # We check first if the entry already exists.
    # We assume that all countries have an iso3166code2 code
    cr.execute(
        """SELECT englishname FROM Language WHERE code='%s'""" % (
        data['code'].encode('utf-8')))
        
    # If it does not exists, it's inserted
    if cr.rowcount < 1:
        cr.execute(
            """INSERT INTO Language (%s) VALUES (%s)""" % (
                ','.join(data.keys()),
                ','.join([str(psycopg.QuotedString(value.encode('utf-8').strip())) for value in data.values()])))
    else:
        # It already exists, we should check if it needs any update
        # That's if the englishname != from data['englishname']
        country_row = cr.fetchone()
        if country_row[0] != data['englishname'].encode('utf-8'):
            # We need to update the name
            cr.execute(
                """UPDATE Language SET englishname='%s' WHERE code='%s'""" %(
                data['englishname'].encode('utf-8'),
                data['code'].encode('utf-8')))
            print ("%r has been updated" % data)

    cnx.commit()
    cr.close()

def import_languages(cnx):
    print
    print 'importing languages...'
    fields = {
        'iso_639_1_code': 'code',
        'iso_639_2T_code': 'code2',
        'name': 'englishname',
        }

    p = make_parser()
    p.setErrorHandler(saxutils.ErrorPrinter())

    dh = XMLHandler('iso_639_entry', fields, cnx, insert_language, two_or_three_letters)
    p.setContentHandler(dh)
    p.parse(files['language'])


spoken_re = re.compile('([a-z]*)_([A-Z]*).*')

def import_spoken(cnx):
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

            insert_language(cnx, data)

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


if __name__ == '__main__':
    cnx = psycopg.connect("user=carlos dbname=launchpad")
    import_countries(cnx)
    import_languages(cnx)
    import_spoken(cnx)
