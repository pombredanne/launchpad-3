# Copyright (C) 2005-2007  Canonical Ltd.

"""Tests for debversion."""

__metaclass__ = type

# These tests came from sourcerer.

import unittest

class Version(unittest.TestCase):
    # Known values that should work
    VALUES = (
        "1",
        "1.0",
        "1:1.0",
        "1.0-1",
        "1:1.0-1",
        "3.4-2.1",
        "1.5.4-1.woody.0",
        "1.6-0+1.5a-4",
        "1.3~rc1-4",
        )

    # Known less-than comparisons
    COMPARISONS = (
        ( "1.0", "1.1" ),
        ( "1.1", "2.0" ),
        ( "2.1", "2.10" ),
        ( "2.2", "2.10" ),
        ( "1.0", "1:1.0" ),
        ( "1:9.0", "2:1.0" ),
        ( "1.0-1", "1.0-2" ),
        ( "1.0", "1.0-1" ),
        ( "1a", "1b" ),
        ( "1a", "2" ),
        ( "1a", "1." ),
        ( "1a", "1+" ),
        ( "1:1a", "1:1:" ),
        ( "1a-1", "1--1" ) ,
        ( "1+-1", "1--1" ),
        ( "1--1", "1.-1" ),
        ( "1:1.", "1:1:" ),
        ( "1A", "1a" ),
        ( "1~", "1" ),
        ( "1~", "1~a" ),
        ( "1~a", "1~b" ),
        )

    def testAcceptsString(self):
        """Version should accept a string input."""
        from canonical.archivepublisher.debversion import Version
        Version("1.0")

    def testReturnString(self):
        """Version should convert to a string."""
        from canonical.archivepublisher.debversion import Version
        self.assertEquals(str(Version("1.0")), "1.0")

    def testAcceptsInteger(self):
        """Version should accept an integer."""
        from canonical.archivepublisher.debversion import Version
        self.assertEquals(str(Version(1)), "1")

    def testAcceptsNumber(self):
        """Version should accept a number."""
        from canonical.archivepublisher.debversion import Version
        self.assertEquals(str(Version(1.2)), "1.2")

    def testOmitZeroEpoch(self):
        """Version should omit epoch when zero."""
        from canonical.archivepublisher.debversion import Version
        self.assertEquals(str(Version("0:1.0")), "1.0")

    def testOmitZeroRevision(self):
        """Version should not omit zero revision."""
        from canonical.archivepublisher.debversion import Version
        self.assertEquals(str(Version("1.0-0")), "1.0-0")

    def testNotEmpty(self):
        """Version should fail with empty input."""
        from canonical.archivepublisher.debversion import Version, BadInputError
        self.assertRaises(BadInputError, Version, "")

    def testEpochNotEmpty(self):
        """Version should fail with empty epoch."""
        from canonical.archivepublisher.debversion import Version, BadEpochError
        self.assertRaises(BadEpochError, Version, ":1")

    def testEpochNonNumeric(self):
        """Version should fail with non-numeric epoch."""
        from canonical.archivepublisher.debversion import Version, BadEpochError
        self.assertRaises(BadEpochError, Version, "a:1")

    def testEpochNonInteger(self):
        """Version should fail with non-integral epoch."""
        from canonical.archivepublisher.debversion import Version, BadEpochError
        self.assertRaises(BadEpochError, Version, "1.0:1")

    def testEpochNonNegative(self):
        """Version should fail with a negative epoch."""
        from canonical.archivepublisher.debversion import Version, BadEpochError
        self.assertRaises(BadEpochError, Version, "-1:1")

    def testUpstreamNotEmpty(self):
        """Version should fail with empty upstream."""
        from canonical.archivepublisher.debversion import Version, BadUpstreamError
        self.assertRaises(BadUpstreamError, Version, "1:-1")

    def testUpstreamNonDigitStart(self):
        """Version should fail when upstream doesn't start with a digit."""
        from canonical.archivepublisher.debversion import Version, BadUpstreamError
        self.assertRaises(BadUpstreamError, Version, "a1")

    def testUpstreamInvalid(self):
        """Version should fail when upstream contains a bad character."""
        from canonical.archivepublisher.debversion import Version, BadUpstreamError
        self.assertRaises(BadUpstreamError, Version, "1!0")

    def testRevisionNotEmpty(self):
        """Version should fail with empty revision."""
        from canonical.archivepublisher.debversion import Version, BadRevisionError
        self.assertRaises(BadRevisionError, Version, "1-")

    def testRevisionInvalid(self):
        """Version should fail when revision contains a bad character."""
        from canonical.archivepublisher.debversion import Version, BadRevisionError
        self.assertRaises(BadRevisionError, Version, "1-!")

    def testValues(self):
        """Version should give same input as output."""
        from canonical.archivepublisher.debversion import Version
        for value in self.VALUES:
            result = str(Version(value))
            self.assertEquals(value, result)

    def testComparisons(self):
        """Sample Version comparisons should pass."""
        from canonical.archivepublisher.debversion import Version
        for x, y in self.COMPARISONS:
            self.failUnless(Version(x) < Version(y))

    def testNullEpochIsZero(self):
        """Version should treat an omitted epoch as a zero one."""
        from canonical.archivepublisher.debversion import Version
        self.failUnless(Version("1.0") == Version("0:1.0"))

    def testNullRevisionIsZero(self):
        """Version should treat an omitted revision as a zero one.

        NOTE: This isn't what Policy says!  Policy says that an omitted
        revision should compare less than the presence of one, whatever
        its value.

        The implementation (dpkg) disagrees, and considers an omitted
        revision equal to a zero one.  I'm obviously biased as to which
        this module obeys.
        """
        from canonical.archivepublisher.debversion import Version
        self.failUnless(Version("1.0") == Version("1.0-0"))

    def testWithoutEpoch(self):
        """Version.without_epoch returns version without epoch."""
        from canonical.archivepublisher.debversion import Version
        self.assertEquals(Version("1:2.0").without_epoch, "2.0")


class Strcut(unittest.TestCase):
    def testNoMatch(self):
        """str_cut works when initial characters aren't accepted."""
        from canonical.archivepublisher.debversion import strcut
        self.assertEquals(strcut("foo", 0, "gh"), ( "", 0 ))

    def testSingleMatch(self):
        """str_cut matches single initial character."""
        from canonical.archivepublisher.debversion import strcut
        self.assertEquals(strcut("foo", 0, "fgh"), ( "f", 1 ))

    def testMultipleMatch(self):
        """str_cut matches multiple initial characters."""
        from canonical.archivepublisher.debversion import strcut
        self.assertEquals(strcut("foobar", 0, "fo"), ( "foo", 3 ))

    def testCompleteMatch(self):
        """str_cut works when all characters match."""
        from canonical.archivepublisher.debversion import strcut
        self.assertEquals(strcut("foo", 0, "fo"), ( "foo", 3 ))

    def testNonMiddleMatch(self):
        """str_cut doesn't match characters that aren't at the start."""
        from canonical.archivepublisher.debversion import strcut
        self.assertEquals(strcut("barfooquux", 0, "fo"), ( "", 0 ))

    def testIndexMatch(self):
        """str_cut matches characters from middle when index given."""
        from canonical.archivepublisher.debversion import strcut
        self.assertEquals(strcut("barfooquux", 3, "fo"), ( "foo", 6 ))


class DebOrder(unittest.TestCase):
    # Non-tilde characters in order
    CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-.:"

    def testTilde(self):
        """deb_order returns -1 for a tilde."""
        from canonical.archivepublisher.debversion import deb_order
        self.assertEquals(deb_order("~", 0), -1)

    def testCharacters(self):
        """deb_order returns positive for other characters."""
        from canonical.archivepublisher.debversion import deb_order
        for char in self.CHARS:
            self.failUnless(deb_order(char, 0) > 0)

    def testCharacterOrder(self):
        """deb_order returns characters in correct order."""
        from canonical.archivepublisher.debversion import deb_order
        last = None
        for char in self.CHARS:
            if last is not None:
                self.failUnless(deb_order(char, 0) > deb_order(last, 0))
            last = char

    def testOvershoot(self):
        """deb_order returns zero if idx is longer than the string."""
        from canonical.archivepublisher.debversion import deb_order
        self.assertEquals(deb_order("foo", 10), 0)

    def testEmptyString(self):
        """deb_order returns zero if given empty string."""
        from canonical.archivepublisher.debversion import deb_order
        self.assertEquals(deb_order("", 0), 0)


class DebCmpStr(unittest.TestCase):
    # Sample strings
    VALUES = (
        "foo",
        "FOO",
        "Foo",
        "foo+bar",
        "foo-bar",
        "foo.bar",
        "foo:bar"
        )

    # Non-letter characters in order
    CHARS = "+-.:"

    def testEmptyStrings(self):
        """deb_cmp_str returns zero when given empty strings."""
        from canonical.archivepublisher.debversion import deb_cmp_str
        self.assertEquals(deb_cmp_str("", ""), 0)

    def testFirstEmptyString(self):
        """deb_cmp_str returns -1 when first string is empty."""
        from canonical.archivepublisher.debversion import deb_cmp_str
        self.assertEquals(deb_cmp_str("", "foo"), -1)

    def testSecondEmptyString(self):
        """deb_cmp_str returns 1 when second string is empty."""
        from canonical.archivepublisher.debversion import deb_cmp_str
        self.assertEquals(deb_cmp_str("foo", ""), 1)

    def testTildeEmptyString(self):
        """deb_cmp_str returns -1 when tilde compared to empty string."""
        from canonical.archivepublisher.debversion import deb_cmp_str
        self.assertEquals(deb_cmp_str("~", ""), -1)

    def testLongerFirstString(self):
        """deb_cmp_str returns 1 when first string is longer."""
        from canonical.archivepublisher.debversion import deb_cmp_str
        self.assertEquals(deb_cmp_str("foobar", "foo"), 1)

    def testLongerSecondString(self):
        """deb_cmp_str returns -1 when second string is longer."""
        from canonical.archivepublisher.debversion import deb_cmp_str
        self.assertEquals(deb_cmp_str("foo", "foobar"), -1)

    def testTildeEmptyString(self):
        """deb_cmp_str returns -1 when first string is longer by a tilde."""
        from canonical.archivepublisher.debversion import deb_cmp_str
        self.assertEquals(deb_cmp_str("foo~", "foo"), -1)

    def testIdenticalString(self):
        """deb_cmp_str returns 0 when given identical strings."""
        from canonical.archivepublisher.debversion import deb_cmp_str
        for value in self.VALUES:
            self.assertEquals(deb_cmp_str(value, value), 0)

    def testNonIdenticalString(self):
        """deb_cmp_str returns non-zero when given non-identical strings."""
        from canonical.archivepublisher.debversion import deb_cmp_str
        last = self.VALUES[-1]
        for value in self.VALUES:
            self.assertNotEqual(deb_cmp_str(last, value), 0)
            last = value

    def testIdenticalTilde(self):
        """deb_cmp_str returns 0 when given identical tilded strings."""
        from canonical.archivepublisher.debversion import deb_cmp_str
        self.assertEquals(deb_cmp_str("foo~", "foo~"), 0)

    def testUppercaseLetters(self):
        """deb_cmp_str orders upper case letters in alphabetical order."""
        from canonical.archivepublisher.debversion import deb_cmp_str
        last = "A"
        for value in range(ord("B"), ord("Z")):
            self.assertEquals(deb_cmp_str(last, chr(value)), -1)
            last = chr(value)

    def testLowercaseLetters(self):
        """deb_cmp_str orders lower case letters in alphabetical order."""
        from canonical.archivepublisher.debversion import deb_cmp_str
        last = "a"
        for value in range(ord("b"), ord("z")):
            self.assertEquals(deb_cmp_str(last, chr(value)), -1)
            last = chr(value)

    def testLowerGreaterThanUpper(self):
        """deb_cmp_str orders lower case letters after upper case."""
        from canonical.archivepublisher.debversion import deb_cmp_str
        self.assertEquals(deb_cmp_str("a", "Z"), 1)

    def testCharacters(self):
        """deb_cmp_str orders characters in prescribed order."""
        from canonical.archivepublisher.debversion import deb_cmp_str
        chars = list(self.CHARS)
        last = chars.pop(0)
        for char in chars:
            self.assertEquals(deb_cmp_str(last, char), -1)
            last = char

    def testCharactersGreaterThanLetters(self):
        """deb_cmp_str orders characters above letters."""
        from canonical.archivepublisher.debversion import deb_cmp_str
        self.assertEquals(deb_cmp_str(self.CHARS[0], "z"), 1)


class DebCmp(unittest.TestCase):
    def testEmptyString(self):
        """deb_cmp returns 0 for the empty string."""
        from canonical.archivepublisher.debversion import deb_cmp
        self.assertEquals(deb_cmp("", ""), 0)

    def testStringCompare(self):
        """deb_cmp compares initial string portions correctly."""
        from canonical.archivepublisher.debversion import deb_cmp
        self.assertEquals(deb_cmp("a", "b"), -1)
        self.assertEquals(deb_cmp("b", "a"), 1)

    def testNumericCompare(self):
        """deb_cmp compares numeric portions correctly."""
        from canonical.archivepublisher.debversion import deb_cmp
        self.assertEquals(deb_cmp("foo1", "foo2"), -1)
        self.assertEquals(deb_cmp("foo2", "foo1"), 1)
        self.assertEquals(deb_cmp("foo200", "foo5"), 1)

    def testMissingNumeric(self):
        """deb_cmp treats missing numeric as zero."""
        from canonical.archivepublisher.debversion import deb_cmp
        self.assertEquals(deb_cmp("foo", "foo0"), 0)
        self.assertEquals(deb_cmp("foo", "foo1"), -1)
        self.assertEquals(deb_cmp("foo1", "foo"), 1)

    def testEmptyString(self):
        """deb_cmp works when string potion is empty."""
        from canonical.archivepublisher.debversion import deb_cmp
        self.assertEquals(deb_cmp("100", "foo100"), -1)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
