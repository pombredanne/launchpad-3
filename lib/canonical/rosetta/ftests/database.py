#!/usr/bin/python
#
# Copyright 2004 Canonical Ltd.  All rights reserverd.
#
# arch-tag: 9b977252-b19c-4482-89a0-862c501d2284

import sys, psycopg, pytranslations

from pytranslations.pofile import POParser, POTranslation

class PODBBridge:

    def __init__(self):
        self.cnx = psycopg.connect("user=carlos dbname=launchpad")

    def parse(self, input_file):
        self.parser = POParser()
        while True:
            batch = input_file.read(1024)
            if not batch:
                break
            self.parser.write(batch)
        self.parser.finish()

    def import_po(self, pot_name, lang_code):
        cr = self.cnx.cursor()
#       print self.parser.headers['Last-Translator'];
        # FIXME: Implement a Last-Translator parser.
        # FIXME: Implement comments

        #Insert the .po header
        header = {
            'pot_name': pot_name,
            'lang_code': lang_code,
            'topcomment': self.parser.header.commentText.encode("utf-8"),
            'header': self.parser.header.msgstr.encode("utf-8")
            }
        cr.execute(
            """SELECT pofile FROM POFile WHERE
                potfile = (SELECT potfile FROM POTFile
                            WHERE name=%(pot_name)s) AND
                language = (SELECT language FROM Language
                            WHERE code=%(lang_code)s)""", header)
        if cr.rowcount < 1:
            cr.execute(
                """INSERT INTO POFile (potfile, language, topcomment, header,
                                       lasttranslator)
                   VALUES (
                    (SELECT potfile FROM POTFile WHERE name=%(pot_name)s),
                    (SELECT language FROM Language WHERE code=%(lang_code)s),
                    %(topcomment)s,
                    %(header)s,
                    (SELECT person FROM Person
                        WHERE presentationname = 'Joe Example'));""", header)
            cr.execute(
                """SELECT pofile FROM POFile WHERE
                    potfile = (SELECT potfile FROM POTFile
                                WHERE name=%(pot_name)s) AND
                    language = (SELECT language FROM Language
                                WHERE code=%(lang_code)s)""", header)
        pofile = cr.fetchone()
        cr.execute(
            """UPDATE POTranslationSighting SET iscurrent = false
                WHERE pofile = %d""" % pofile)

        for message in self.parser.messages:
            if 'fuzzy' in message.flags:
                fuzzy = 'TRUE'
            else:
                fuzzy = 'FALSE'
            cr.execute(
                "SELECT pomsgid FROM POMsgID WHERE msgid = %(msgid)s",
                { 'msgid': message.msgid.encode("utf-8") })
            if cr.rowcount < 1:
                cr.execute(
                "INSERT INTO POMsgID (msgid) VALUES (%(msgid)s)",
                { 'msgid': message.msgid.encode("utf-8") })
                cr.execute(
                    "SELECT pomsgid FROM POMsgID WHERE msgid = %(msgid)s",
                    { 'msgid': message.msgid.encode("utf-8") })
            pomsgid = cr.fetchone()

            cr.execute(
                "SELECT potranslation FROM POTranslation WHERE text = %(text)s",
                { 'text': message.msgstr.encode("utf-8") })
            if cr.rowcount < 1:
                cr.execute(
                "INSERT INTO POTranslation (text) VALUES (%(text)s)",
                { 'text': message.msgstr.encode("utf-8") })
                cr.execute(
                    """SELECT potranslation FROM POTranslation
                        WHERE text = %(text)s""",
                    { 'text': message.msgstr.encode("utf-8") })
            potranslation = cr.fetchone()

            cr.execute(
                """SELECT potranslationsighting FROM POTranslationSighting
                    WHERE pomsgid = %(pomsgid)d AND
                          potranslation = %(potranslation)d""",
                { 'pomsgid': pomsgid[0], 'potranslation': potranslation[0] })

            if cr.rowcount < 1:
                cr.execute(
                    """INSERT INTO POTranslationSighting (pofile, pomsgid,
                           potranslation, license, fuzzy, rosettaprovided,
                           firstseen, lastseen, iscurrent)
                        VALUES(%(pofile)d, %(pomsgid)d, %(potranslation)d,
                            (SELECT license FROM License WHERE legalese = 'GPL-2'),
                        %(fuzzy)s, FALSE, now(), now(), TRUE)""",
                        { 'pofile': pofile[0], 'pomsgid': pomsgid[0],
                          'potranslation': potranslation[0],
                          'fuzzy': fuzzy })
            else:
                potranslationsighting = cr.fetchone()
                cr.execute(
                    """UPDATE POTranslationSighting SET
                        fuzzy = %(fuzzy)s, lastseen = now(), iscurrent = true
                        WHERE
                            potranslationsighting=%(potranslationsighting)d""",
                    { 'fuzzy': fuzzy,
                      'potranslationsighting': potranslationsighting[0] })
        self.cnx.commit()
        cr.close()

    def import_pot(self, pot_name):
        cr = self.cnx.cursor()

        # Do we have the .pot file already in the database?
        cr.execute(
            "SELECT potfile FROM POTFile WHERE name = %(name)s",
            { 'name': pot_name })
        if cr.rowcount > 0:
            potfile = cr.fetchone()
            cr.execute(
                """UPDATE POTMsgIDSighting SET iscurrent = false
                    WHERE potfile = %d""" % potfile)
            for message in self.parser.messages:
                cr.execute(
                    "SELECT pomsgid FROM POMsgID WHERE msgid = %(msgid)s",
                    { 'msgid': message.msgid.encode("utf-8") })
                if cr.rowcount < 1:
                    cr.execute(
                    "INSERT INTO POMsgID (msgid) VALUES (%(msgid)s)",
                    { 'msgid': message.msgid.encode("utf-8") })
                    cr.execute(
                    "SELECT pomsgid FROM POMsgID WHERE msgid = %(msgid)s",
                    { 'msgid': message.msgid.encode("utf-8") })
                pomsgid = cr.fetchone()
                sight_fields = {
                    'potfile': potfile[0],
                    'pomsgid': pomsgid[0],
                    'commenttext': message.commentText.encode("utf-8")}
                cr.execute(
                    """SELECT pomsgid FROM POTMsgIDSighting
                        WHERE potfile = %(potfile)d AND
                              pomsgid = %(pomsgid)d""", sight_fields)
                if cr.rowcount > 0:
                    cr.execute(
                        """UPDATE POTMsgIDSighting
                            SET iscurrent = true, lastseen = now(),
                            commenttext = %(commenttext)s
                            WHERE potfile = %(potfile)d AND
                                  pomsgid = %(pomsgid)d""", sight_fields)
                else:
                    cr.execute(
                        """INSERT INTO POTMsgIDSighting (potfile, pomsgid,
                            firstseen, lastseen, iscurrent, commenttext)
                            VALUES (%(potfile)d, %(pomsgid)d, now(), now(),
                            true, %(commenttext)s)""", sight_fields)
            self.cnx.commit()
        else:
            # FIXME: Missing POT file
            print "Please, create the POT file into the database"
        cr.close()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print "Usage: "
        print "\t" + sys.argv[0] + " pot_file pot_name"
        print "\t" + sys.argv[0] + " po_file pot_name language"
    else:
        bridge = PODBBridge()
        in_f = file(sys.argv[1], 'rU')
        bridge.parse(in_f)
        if len(sys.argv) == 4:
            print "Importing .po file..."
            bridge.import_po(sys.argv[2], sys.argv[3])
        else:
            print "Importing .pot file..."
            bridge.import_pot(sys.argv[2])

#    print "Comment (" + str(len(parser.header.comment)) + "):"
#    print parser.header.comment
#    print "Generated comment (" + str(len(parser.header.generated_comment)) + "):"
#    print parser.header.generated_comment
#    if 'fuzzy' in parser.header.flags:
#        print "Fuzzy: YES"
#    if 'c-format' in parser.header.flags:
#        print "c-format: YES"
#    print "msgid (" + str(len(parser.header.msgid)) + "):"
#    print parser.header.msgid
#    print "msgid_plural (" + str(len(parser.header.msgidPlural)) + "):"
#    print parser.header.msgidPlural
#    print "msgstr (" + str(len(parser.header.msgstr)) + "):"
#    print parser.header.msgstr
#    for plural in parser.header.msgstrPlurals:
#        print "msgstr_plural (" + str(len(plural)) + "):"
#        print plural

#    for message in parser.messages:
#        print "Comment (" + str(len(message.comment)) + "):"
#        print message.comment
#        print "Generated comment (" + str(len(message.generated_comment)) + "):"
#        print message.generated_comment
#        if 'fuzzy' in message.flags:
#            print "Fuzzy: YES"
#        if 'c-format' in message.flags:
#            print "c-format: YES"
#        print "msgid (" + str(len(message.msgid)) + "):"
#        print message.msgid
       # print "msgid_plural (" + str(len(message.msgidPlural)) + "):"
#        print message.msgidPlural
#        print "msgstr (" + str(len(message.msgstr)) + "):"
#        print message.msgstr
#        for plural in message.msgstrPlurals:
#            print "msgstr_plural (" + str(len(plural)) + "):"
#            print plural
