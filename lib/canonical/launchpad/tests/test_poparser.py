# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

import unittest
import doctest
import textwrap
from canonical.launchpad.components import poparser as pofile

DEFAULT_HEADER = '''
msgid ""
msgstr ""
"Content-Type: text/plain; charset=ASCII\\n"
'''

class POBasicTestCase(unittest.TestCase):

    def setUp(self):
        self.parser = pofile.POParser()

    def testSingular(self):
        self.parser.write('''%smsgid "foo"\nmsgstr "bar"\n''' % DEFAULT_HEADER)
        self.parser.finish()
        messages = self.parser.messages
        self.assertEqual(len(messages), 1, "incorrect number of messages")
        self.assertEqual(messages[0].msgid, "foo", "incorrect msgid")
        self.assertEqual(messages[0].msgstr, "bar", "incorrect msgstr")
        assert 'fuzzy' not in messages[0].flags, "incorrect fuzziness"

    def testNoNewLine(self):
        # note, no trailing newline; this raises a warning
        self.parser.write('''%smsgid "foo"\nmsgstr "bar"''' % DEFAULT_HEADER)
        self.parser.finish()
        messages = self.parser.messages
        self.assertEqual(messages[0].msgid, "foo", "incorrect msgid")
        self.assertEqual(messages[0].msgstr, "bar", "incorrect msgstr")

    def testMissingQuote(self):
        self.parser.write('''%smsgid "foo"\nmsgstr "bar''' % DEFAULT_HEADER)

        try:
            self.parser.finish()
        except pofile.POSyntaxError:
            pass
        else:
            self.fail("uncaught syntax error (missing quote)")

    def testBadNewline(self):
        try:
            self.parser.write(
                '''%smsgid "foo\n"\nmsgstr "bar"\n''' % DEFAULT_HEADER)
            self.parser.finish()
        except pofile.POSyntaxError:
            pass
        else:
            self.fail("uncaught syntax error (misplaced newline)")

    def testBadBackslash(self):
        try:
            self.parser.write(
                '''%smsgid "foo\\"\nmsgstr "bar"\n''' % DEFAULT_HEADER)
            self.parser.finish()
        except pofile.POSyntaxError:
            pass
        else:
            self.fail("uncaught syntax error (misplaced backslash)")

    def testMissingMsgstr(self):
        self.parser.write('''%smsgid "foo"\n''' % DEFAULT_HEADER)

        try:
            self.parser.finish()
        except pofile.POSyntaxError:
            pass
        else:
            self.fail("uncaught syntax error (missing msgstr)")

    def testMissingMsgid1(self):
        try:
            self.parser.write('''%smsgid_plural "foos"\n''' % DEFAULT_HEADER)
            self.parser.finish()
        except pofile.POSyntaxError:
            pass
        else:
            self.fail("uncaught syntax error (missing msgid before "
                "msgid_plural)")

    def testMissingMsgid2(self):
        self.parser.write("%s# blah blah blah\n" % DEFAULT_HEADER)

        try:
            self.parser.finish()
        except pofile.POSyntaxError:
            pass
        else:
            self.fail("uncaught syntax error (missing msgid after comment)")

    def testFuzzy(self):
        self.parser.write(
            """%s#, fuzzy\nmsgid "foo"\nmsgstr "bar"\n""" % DEFAULT_HEADER)
        self.parser.finish()
        messages = self.parser.messages
        assert 'fuzzy' in messages[0].flags, "missing fuzziness"

    def testComment(self):
        self.parser.write(textwrap.dedent("""
            %s
            #. foo/bar.baz\n
            # cake not drugs\n
            msgid "a"\n
            msgstr "b"\n""" % DEFAULT_HEADER))
        self.parser.finish()
        messages = self.parser.messages
        self.assertEqual(messages[0].sourceComment, "foo/bar.baz\n",
                "incorrect source comment")
        self.assertEqual(messages[0].commentText, " cake not drugs\n",
                "incorrect comment text")
        assert 'fuzzy' not in messages[0].flags, "incorrect fuzziness"

    def testEscape(self):
        self.parser.write(
            '''%smsgid "foo\\"bar\\nbaz\\\\xyzzy"\nmsgstr"z"\n''' %
                DEFAULT_HEADER)
        self.parser.finish()
        messages = self.parser.messages
        self.assertEqual(messages[0].msgid, 'foo"bar\nbaz\\xyzzy')

    # Lalo doesn't agree with this test
    # def badEscapeTest(self):
    #     self.parser.write('''msgid "foo\."\nmsgstr "bar"\n''')
    #
    #     try:
    #         self.parser.finish()
    #     except pofile.POSyntaxError:
    #         pass
    #     else:
    #         self.fail("no exception on bad escape sequence")

    def testPlural(self):
        self.parser.header = pofile.POHeader()
        self.parser.header.nplurals = 2
        self.parser.write(textwrap.dedent('''
            %s
            msgid "foo"
            msgid_plural "foos"
            msgstr[0] "bar"
            msgstr[1] "bars"''' % DEFAULT_HEADER))
        self.parser.finish()
        messages = self.parser.messages
        self.assertEqual(messages[0].msgid, "foo", "incorrect msgid")
        assert not messages[0].msgstr, "msgstr should be absent"
        self.assertEqual(messages[0].msgidPlural, "foos",
            "incorrect msgid_plural")
        assert messages[0].msgstrPlurals, "missing msgstr_plurals"
        self.assertEqual(len(messages[0].msgstrPlurals), 2,
            "incorrect number of msgstr_plurals")
        self.assertEqual(messages[0].msgstrPlurals[0], "bar",
            "incorrect msgstr_plural")
        self.assertEqual(messages[0].msgstrPlurals[1], "bars",
            "incorrect msgstr_plural")
        assert 'fuzzy' not in messages[0].flags, "incorrect fuzziness"

    def testObsolete(self):
        self.parser.write(
            '%s#, fuzzy\n#~ msgid "foo"\n#~ msgstr "bar"\n' % DEFAULT_HEADER)
        self.parser.finish()
        messages = self.parser.messages
        self.assertEqual(messages[0].msgid, "foo", "incorrect msgid")
        self.assertEqual(messages[0].msgstr, "bar", "incorrect msgstr")
        assert messages[0].is_obsolete(), "incorrect obsolescence"
        assert 'fuzzy' in messages[0].flags, "incorrect fuzziness"

    def testMultiLineObsolete(self):
        self.parser.write(
            '%s#~ msgid "foo"\n#~ msgstr ""\n#~ "bar"\n' % DEFAULT_HEADER)
        self.parser.finish()
        messages = self.parser.messages
        self.assertEqual(messages[0].msgid, "foo")
        self.assertEqual(messages[0].msgstr, "bar")

    def testDuplicateMsgid(self):
        try:
            self.parser.write(textwrap.dedent('''
                %s
                msgid "foo"
                msgstr "bar1"

                msgid "foo"
                msgstr "bar2"''' % DEFAULT_HEADER))
            self.parser.finish()
        except pofile.POInvalidInputError:
            pass
        else:
            self.fail("no error when duplicate msgid encountered")

    def testSquareBracketAndPlural(self):
        try:
            self.parser.write(textwrap.dedent('''
                %s
                msgid "foo %%d"
                msgid_plural "foos %%d"
                msgstr[0] "foo translated[%%d]"
                msgstr[1] "foos translated[%%d]"
                ''' % DEFAULT_HEADER))
        except ValueError:
            self.fail("The SquareBracketAndPlural test failed")

    def testUpdateHeader(self):
        self.parser.write('msgid ""\nmsgstr "foo: bar\\n"\n')
        self.parser.finish()
        self.parser.header['plural-forms'] = 'nplurals=2; plural=random()'
        self.assertEqual(unicode(self.parser.header),
            u'msgid ""\n'
            u'msgstr ""\n'
            u'"foo: bar\\n"\n'
            u'"Content-Type: text/plain; charset=ASCII\\n"\n'
            u'"plural-forms: nplurals=2; plural=random()\\n"')

    def testMultipartString(self):
        foos = 9
        self.parser.write('''
            %s
            msgid "foo1"
            msgstr ""
            "bar"

            msgid "foo2"
            msgstr "b"
            "ar"

            msgid "foo3"
            msgstr "b""ar"

            msgid "foo4"
            msgstr "ba" "r"

            msgid "foo5"
            msgstr "b""a""r"

            msgid "foo6"
            msgstr "bar"""

            msgid "foo7"
            msgstr """bar"

            msgid "foo8"
            msgstr "" "bar" ""

            msgid "foo9"
            msgstr "" "" "bar" """"
            ''' % DEFAULT_HEADER)
        self.parser.finish()
        messages = self.parser.messages
        self.assertEqual(len(messages), foos, "incorrect number of messages")
        for n in range(1,foos):
            msgidn = "foo"+str(n)
            self.assertEqual(messages[n-1].msgid, msgidn, "incorrect msgid")
            self.assertEqual(messages[n-1].msgstr, "bar", "incorrect msgstr")


def test_suite():
    dt_suite = doctest.DocTestSuite(pofile)
    loader = unittest.TestLoader()
    ut_suite = loader.loadTestsFromTestCase(POBasicTestCase)
    return unittest.TestSuite((ut_suite, dt_suite))

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(test_suite())
