# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from canonical.rosetta import pofile
import unittest, doctest
import warnings

class POBasicTestCase(unittest.TestCase):

    def setUp(self):
        self.parser = pofile.POParser()
        warnings.filterwarnings('ignore', category=pofile.POSyntaxWarning)

    def testSingular(self):
        self.parser.write('''msgid "foo"\nmsgstr "bar"\n''')
        self.parser.finish()
        messages = self.parser.messages
        self.assertEqual(len(messages), 1, "incorrect number of messages")
        self.assertEqual(messages[0].msgid, "foo", "incorrect msgid")
        self.assertEqual(messages[0].msgstr, "bar", "incorrect msgstr")
        assert 'fuzzy' not in messages[0].flags, "incorrect fuzziness"

    def testNoNewLine(self):
        # note, no trailing newline; this raises a warning
        self.parser.write('''msgid "foo"\nmsgstr "bar"''')
        self.parser.finish()
        messages = self.parser.messages
        self.assertEqual(messages[0].msgid, "foo", "incorrect msgid")
        self.assertEqual(messages[0].msgstr, "bar", "incorrect msgstr")

    def testMissingQuote(self):
        self.parser.write('''msgid "foo"\nmsgstr "bar''')

        try:
            self.parser.finish()
        except pofile.POSyntaxError:
            pass
        else:
            self.fail("uncaught syntax error (missing quote)")

    def testBadNewline(self):
        try:
            self.parser.write('''msgid "foo\n"\nmsgstr "bar"\n''')
            self.parser.finish()
        except pofile.POSyntaxError:
            pass
        else:
            self.fail("uncaught syntax error (misplaced newline)")

    def testBadBackslash(self):
        try:
            self.parser.write('''msgid "foo\\"\nmsgstr "bar"\n''')
            self.parser.finish()
        except pofile.POSyntaxError:
            pass
        else:
            self.fail("uncaught syntax error (misplaced backslash)")

    def testMissingMsgstr(self):
        self.parser.write('''msgid "foo"\n''')

        try:
            self.parser.finish()
        except pofile.POSyntaxError:
            pass
        else:
            self.fail("uncaught syntax error (missing msgstr)")

    def testMissingMsgid1(self):
        try:
            self.parser.write('''msgid_plural "foos"\n''')
            self.parser.finish()
        except pofile.POSyntaxError:
            pass
        else:
            self.fail("uncaught syntax error (missing msgid before "
                "msgid_plural)")

    def testMissingMsgid2(self):
        self.parser.write("# blah blah blah\n")

        try:
            self.parser.finish()
        except pofile.POSyntaxError:
            pass
        else:
            self.fail("uncaught syntax error (missing msgid after comment)")

    def testFuzzy(self):
        self.parser.write("""#, fuzzy\nmsgid "foo"\nmsgstr "bar"\n""")
        self.parser.finish()
        messages = self.parser.messages
        assert 'fuzzy' in messages[0].flags, "missing fuzziness"

    def testComment(self):
        self.parser.write(
            '#. foo/bar.baz\n'
            '# cake not drugs\n'
            'msgid "a"\n'
            'msgstr "b"\n')
        self.parser.finish()
        messages = self.parser.messages
        self.assertEqual(messages[0].sourceComment, "foo/bar.baz\n",
                "incorrect source comment")
        self.assertEqual(messages[0].commentText, " cake not drugs\n",
                "incorrect comment text")
        assert 'fuzzy' not in messages[0].flags, "incorrect fuzziness"

    def testEscape(self):
        self.parser.write('''msgid "foo\\"bar\\nbaz\\\\xyzzy"\nmsgstr"z"\n''')
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
        self.parser.write('''msgid "foo"\nmsgid_plural "foos"\n'''
            '''msgstr[0] "bar"\nmsgstr[1] "bars"\n''')
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
        self.parser.write('''#, fuzzy\n#~ msgid "foo"\n#~ msgstr "bar"\n''')
        self.parser.finish()
        messages = self.parser.messages
        self.assertEqual(messages[0].msgid, "foo", "incorrect msgid")
        self.assertEqual(messages[0].msgstr, "bar", "incorrect msgstr")
        assert messages[0].is_obsolete(), "incorrect obsolescence"
        assert 'fuzzy' in messages[0].flags, "incorrect fuzziness"

    def testMultiLineObsolete(self):
        self.parser.write('''#~ msgid "foo"\n#~ msgstr ""\n#~ "bar"\n''')
        self.parser.finish()
        messages = self.parser.messages
        self.assertEqual(messages[0].msgid, "foo")
        self.assertEqual(messages[0].msgstr, "bar")

    def testMisorderedHeader(self):
        warnings.filterwarnings('error', category=pofile.POSyntaxWarning)
        try:
            self.parser.write(
                'msgid "a"\n'
                'msgstr "b"\n\n'
                'msgid ""\n'
                'msgstr "z: y"\n'
                'msgid "c"\n'
                'msgstr "d"\n')
            self.parser.finish()
        except pofile.POSyntaxWarning:
            pass
        else:
            self.fail("no warning when misordered header encountered")

    def testVeryMisorderedHeader(self):
        warnings.filterwarnings('error', category=pofile.POSyntaxWarning)
        try:
            self.parser.write(
                '''msgid "a"\nmsgstr "b"\n\nmsgid ""\nmsgstr "z: y"\n''')
            self.parser.finish()
        except pofile.POSyntaxWarning:
            pass
        else:
            self.fail("no warning when misordered header encountered")

    def testDuplicateMsgid(self):
        try:
            self.parser.write('''msgid "foo"\nmsgstr "bar1"\n\n'''
                '''msgid "foo"\nmsgstr "bar2"\n''')
            self.parser.finish()
        except pofile.POInvalidInputError:
            pass
        else:
            self.fail("no error when duplicate msgid encountered")


def test_suite():
    dt_suite = doctest.DocTestSuite(pofile)
    loader = unittest.TestLoader()
    ut_suite = loader.loadTestsFromTestCase(POBasicTestCase)
    return unittest.TestSuite((ut_suite, dt_suite))

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(test_suite())
