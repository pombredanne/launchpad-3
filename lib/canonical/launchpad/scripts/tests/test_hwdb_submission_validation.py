# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Tests of the HWDB submissions parser."""

from datetime import datetime
import logging
import os
from unittest import TestCase, TestLoader

from zope.testing.loghandler import Handler
from canonical.config import config
from canonical.launchpad.scripts.hwdbsubmissions import SubmissionParser
from canonical.testing import BaseLayer


class TestHWDBSubmissionRelaxNGValidation(TestCase):
    """Tests of the Relax NG validation of the HWDB submission parser."""

    layer = BaseLayer

    submission_count = 0

    def assertEqual(self, x1, x2, msg):
        TestCase.assertEqual(self, x1, x2, msg)

    def assertNotEqual(self, x1, x2, msg):
        TestCase.assertNotEqual(self, x1, x2, msg)

    def setUp(self):
        """Setup the test environment."""
        self.log = logging.getLogger('test_hwdb_submission_parser')
        self.log.setLevel(logging.INFO)
        self.handler = Handler(self)
        self.handler.add(self.log.name)

        sample_data_path = os.path.join(
            config.root, 'lib', 'canonical', 'launchpad', 'scripts',
            'tests', 'hardwaretest.xml')
        self.sample_data = open(sample_data_path).read()

    def runValidator(self, sample_data):
        """Run the Relax NG validator.

        Create a unique submission ID to ensure that an error message
        expected in a test is indeed created by this test.
        """
        self.submission_count += 1
        submission_id = 'submission_%i' % self.submission_count
        result = SubmissionParser(self.log)._getValidatedEtree(sample_data,
                                                               submission_id)
        return result, submission_id

    def insertSampledata(self, data, insert_text, where):
        """Insert text into the sample data `data`.

        Insert the text `insert_text` before the first occurrence of
        `where` in `data`.
        """
        insert_position = data.find(where)
        return data[:insert_position] + insert_text + data[insert_position:]

    def replaceSampledata(self, data, replace_text, from_text, to_text):
        """Replace text in the sample data `data`.

        Search for the first occurrence of `from_text` in data, and for the
        first occurrence of `to_text` (after `from_text`) in `data`.
        Replace the text between `from_text` and `to_text` by `replace_text`.
        The strings `from_text` are `to_text` are part of the text which is
        replaced.
        """
        start_replace = data.find(from_text)
        end_replace = data.find(to_text, start_replace) + len(to_text)
        return data[:start_replace] + replace_text + data[end_replace:]

    def testNoXMLData(self):
        """The raw submission data must be XML."""
        sample_data = 'No XML'
        result, submission_id = self.runValidator(sample_data)
        self.handler.assertLogsMessage(
            "Parsing submission %s: line 1: "
                "Start tag expected, '<' not found" % submission_id,
            logging.ERROR)
        self.assertEqual(result, None, 'Expected detection of non-XML data')

    def testInvalidRootNode(self):
        """The root node must be <system>."""
        sample_data = '<?xml version="1.0" ?><nosystem/>'
        result, submission_id = self.runValidator(sample_data)
        self.handler.assertLogsMessage(
            "Parsing submission %s: root node is not '<system>'"
                % submission_id,
            logging.ERROR)
        self.assertEqual(result, None,
                         'Invalid root node not detected')

    def testInvalidFormatVersion(self):
        """The attribute `format` of the root node must be `1.0`."""
        sample_data = '<?xml version="1.0" ?><system version="nonsense"/>'
        result, submission_id = self.runValidator(sample_data)
        self.handler.assertLogsMessage(
            "Parsing submission %s: invalid submission format version: "
                "'nonsense'" % submission_id,
            logging.ERROR)
        self.assertEqual(result, None,
                         'Unknown submission format version not detected')

    def testMissingFormatVersion(self):
        """The root node must have the attribute `version`."""
        sample_data = '<?xml version="1.0" ?><system/>'
        result, submission_id = self.runValidator(sample_data)
        self.handler.assertLogsMessage(
            "Parsing submission %s: invalid submission format version: None"
                % submission_id,
            logging.ERROR)
        self.assertEqual(result, None,
                         'Missing submission format attribute not detected')

    def _setEncoding(self, encoding):
        """Set the encoding in the sample data to `encoding`."""
        return self.replaceSampledata(
            data=self.sample_data,
            replace_text='<?xml version="1.0" encoding="%s"?>' % encoding,
            from_text='<?xml',
            to_text='?>')

    def testAsciiEncoding(self):
        """Validation of ASCII encoded XML data.

        Bytes with bit 7 set must be detected as invalid.
        """
        sample_data_ascii_encoded = self._setEncoding('ascii')
        result, submission_id = self.runValidator(sample_data_ascii_encoded)
        self.assertNotEqual(result, None,
                            'Valid submission with ASCII encoding rejected')

        tag_with_umlaut = u'<architecture value="\xc4"/>'
        tag_with_umlaut = tag_with_umlaut.encode('iso-8859-1')
        sample_data = self.replaceSampledata(
            data=sample_data_ascii_encoded,
            replace_text=tag_with_umlaut,
            from_text='<architecture',
            to_text='/>')
        result, submission_id = self.runValidator(sample_data)
        self.assertEqual(result, None,
                         'Invalid submission with ASCII encoding accepted')
        self.handler.assertLogsMessage(
            "Parsing submission %s: line 28: Premature end of data in tag "
                "system line 2" % submission_id,
            logging.ERROR)

    def testISO8859_1_Encoding(self):
        """XML data with ISO-8859-1 may have bytes with bit 7 set."""
        sample_data_iso_8859_1_encoded = self._setEncoding('ISO-8859-1')
        tag_with_umlaut = '<architecture value="\xc4"/>'
        sample_data = self.replaceSampledata(
            data=sample_data_iso_8859_1_encoded,
            replace_text=tag_with_umlaut,
            from_text='<architecture',
            to_text='/>')
        result, submission_id = self.runValidator(sample_data)
        self.assertNotEqual(result, None,
                            'Valid submission with ISO-8859-1 encoding '
                                'rejected')

    def testUTF8Encoding(self):
        """UTF-8 encoded data is properly detected and parsed."""
        sample_data_utf8_encoded = self._setEncoding('UTF-8')
        umlaut = u'\xc4'.encode('utf8')
        tag = '<architecture value="%s"/>'
        tag_with_valid_utf8 = tag % umlaut
        sample_data = self.replaceSampledata(
            data=sample_data_utf8_encoded,
            replace_text=tag_with_valid_utf8,
            from_text='<architecture',
            to_text='/>')
        result, submission_id = self.runValidator(sample_data)
        self.assertNotEqual(result, None,
                            'Valid submission with UTF-8 encoding rejected')

        # Broken UTF8 encoding is detected.
        tag_with_broken_utf8 = tag % umlaut[0]
        sample_data = self.replaceSampledata(
            data=tag_with_broken_utf8,
            replace_text=tag_with_broken_utf8,
            from_text='<architecture',
            to_text='/>')
        result, submission_id = self.runValidator(sample_data)
        self.assertEqual(result, None,
                         'Invalid submissison with UTF-8 encoding accepted')
        self.handler.assertLogsMessage(
            "Parsing submission %s: "
                "line 1: Input is not proper UTF-8, indicate encoding !\n"
                "Bytes: 0xC3 0x22 0x2F 0x3E" % submission_id,
            logging.ERROR)

    # Using self.log.assertLogsMessage, the usual way to assert the
    # existence of an error or warning in the log data, leads to
    # quite unreadable code for many tests in this module:
    #
    # The error messages produced by the Relax NG validator and logged
    # in self.log are often several lines long, and contain "context
    # information" which is not of much interest for a functional test.
    # Moreover, many lines of the messages are more than 80 characters
    # long.

    def assertErrorMessage(self, submission, result, message, test):
        """Search for `message` in the log entry for `submission`."""
        self.assertEqual(result, None, 'test %s failed' % test)
        last_log_messages = []
        for r in self.handler.records:
            if r.levelno != logging.ERROR:
                continue
            candidate = r.getMessage()
            if candidate.startswith('Parsing submission %s:' % submission):
                if candidate.find(message) > 0:
                    return
                else:
                    last_log_messages.append(candidate)
        failmsg = (
            "No error log message for submission %s (testing %s) contained %s")
        failmsg = failmsg % (submission, test, message)
        if last_log_messages:
            failmsg = failmsg + '\nLog messages for the submission:\n'
            failmsg = failmsg + '\n'.join(last_log_messages)
        else:
            failmsg = failmsg + '\nNo messages logged for this submission'

        self.fail(failmsg)

    def testSubtagsOfSystem(self):
        """The root node <system> requires a fixed set of sub-tags."""
        # The omission of any of these tags leads to an error during
        # the Relax NG validation.
        sub_tags = ('summary', 'hardware', 'software', 'questions')
        for tag in sub_tags:
            sample_data = self.replaceSampledata(
                data=self.sample_data,
                replace_text='',
                from_text='<%s>' % tag,
                to_text='</%s>' % tag)
            result, submission_id = self.runValidator(sample_data)
            self.assertErrorMessage(
                submission_id, result,
                'ERROR:RELAXNGV:ERR_ENTITYREF_NO_NAME: '
                    'Expecting an element %s, got nothing' % tag,
                'missing sub-tag <%s> of <system>' % tag)

        # Adding any other tag as a subnode of <system> makes the
        # submission data invalid.
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text='<nonsense/>',
            where = '</system>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'RELAXNGV:ERR_UNDECLARED_ENTITY: '
                'Element system has extra content: nonsense',
            'invalid sub-tag of <system>')

        # Repeating one of the allowed sub-tags of <system> makes the
        # submission data invalid.
        for tag in sub_tags:
            sample_data = self.insertSampledata(
                data=self.sample_data,
                insert_text='<%s/>' % tag,
                where='</system>')
            result, submission_id = self.runValidator(sample_data)
            self.assertErrorMessage(
                submission_id, result,
                ':ERROR:RELAXNGV:ERR_CHARREF_IN_EPILOG: '
                    'Extra element %s in interleave' % tag,
                'duplicate sub-tag <%s> of <system>' % tag)

    def testSummaryRequiredTags(self):
        """The <summary> section requires a fixed set of sub-tags.

        If any of these tags is omitted, the submission data becomes invalid.
        """
        for tag in ('live_cd', 'system_id', 'distribution', 'distroseries',
                    'architecture', 'private', 'contactable', 'date_created'):
            sample_data = self.replaceSampledata(
                data=self.sample_data,
                replace_text='',
                from_text='<%s' % tag,
                to_text='/>')
            result, submission_id = self.runValidator(sample_data)
            self.assertErrorMessage(
                submission_id, result,
                'ERROR:RELAXNGV:ERR_ENTITYREF_NO_NAME: '
                    'Expecting an element %s, got nothing' % tag,
                'missing sub-tag <%s> of <summary>' % tag)

        sample_data = self.replaceSampledata(
            data=self.sample_data,
            replace_text='',
            from_text='<client',
            to_text='</client>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_ENTITYREF_NO_NAME: '
                'Expecting an element client, got nothing',
            'missing sub-tag <client> of <summary>')

    def testAdditionalSummaryTags(self):
        """Arbitrary tags are forbidden as sub-tags of <summary>.

        The only allowed tags are specified by the Relax NG schema:
        live_cd, system_id, distribution, distroseries, architecture,
        private, contactable, date_created.
        """
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text='<nonsense/>',
            where='</summary>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_UNDECLARED_ENTITY: '
                'Element summary has extra content: nonsense',
            'invalid sub-tag <nonsense/> of <summary>')

    def testSummaryValidationOfBooleanSubtags(self):
        """Validation of boolean tags in the <summary> section.

        These tags may only have the attribute 'value', and the
        value of this attribute must be 'True' or 'False'.
        """
        # The only allowed values for the "boolean" tags (live_cd, private,
        # contactable) are 'True' and 'False'. In self.sample_data, 'False'
        # is set for all three tags. In all three tags, the value may also
        # be 'True'.
        for tag in ('live_cd', 'private', 'contactable'):
            replace_text = '<%s value="False"/>' % tag
            sample_data = self.sample_data.replace(
                '<%s value="False"/>' % tag,
                '<%s value="True"/>' % tag)
            result, submission_id = self.runValidator(sample_data)
            self.assertNotEqual(result, None,
                                'Valid boolean sub-tag <%s value="False"> '
                                    'of <summary> rejected')

            # Other values than 'True' and 'False' are rejected by the
            # Relax NG validation.
            sample_data = self.sample_data.replace(
                '<%s value="False"/>' % tag,
                '<%s value="nonsense"/>' % tag)
            result, submission_id = self.runValidator(sample_data)
            self.assertErrorMessage(
                submission_id, result,
                ':ERROR:RELAXNGV:ERR_PEREF_NO_NAME: '
                    'Element %s failed to validate attributes' % tag,
                'boolean sub-tags of <summary>: invalid attribute '
                    'value of <%s>' % tag)

    def testDateCreatedParsing(self):
        """Parsing of the date_created value.

        The parser expects a valid datetime value (ISO format) in the
        date_created tag, like

        "2007-01-01T01:02:03.400000"
        "2007-01-01T01:02:03Z"
        "2007-01-01T01:02:03:600+01:00"

        The fractional part of the seconds is optional as well as the
        time zone information ('Z' for UTC or an offset in hh:mm).
        """
        self.assertValidDateTime('2007-09-28T16:09:20.126842',
                                  datetime(2007, 9, 28, 16, 9, 20, 126842))

        # The Relax NG validator detects missing digits in the numbers for
        # year, month, day, hour, minute, second.
        missing_digits = (
            '200-09-28T16:09:20.126842',
            '2007-9-28T16:09:20.126842',
            '2007-09-8T16:09:20.126842',
            '2007-09-28T6:09:20.126842',
            '2007-09-28T16:9:20.126842',
            '2007-09-28T16:09:2.126842')
        for invalid_datetime in missing_digits:
            self.assertDateErrorIsDetected(invalid_datetime)

        # Only digits are allowed in date and time numbers.
        no_digits = (
            'x007-09-28T16:09:20.126842',
            '2007-x9-28T16:09:20.126842',
            '2007-09-x8T16:09:20.126842',
            '2007-09-28Tx6:09:20.126842',
            '2007-09-28T16:x9:20.126842',
            '2007-09-28T16:09:x0.126842',
            '2007-09-28T16:09:20.x26842')
        for invalid_datetime in no_digits:
            self.assertDateErrorIsDetected(invalid_datetime)

        # The "separator symbol" between year, month, day must be a '-'
        self.assertDateErrorIsDetected('2007 09-28T16:09:20.126842')
        self.assertDateErrorIsDetected('2007-09 28T16:09:20.126842')

        # The "separator symbol" between hour, minute, second must be a ':'
        self.assertDateErrorIsDetected('2007-09-28T16 09:20.126842')
        self.assertDateErrorIsDetected('2007-09-28T16:09 20.126842')

        # The fractional part may be shorter than 6 digits...
        self.assertValidDateTime('2007-09-28T16:09:20.1',
                                 datetime(2007, 9, 28, 16, 9, 20, 100000))

        # ...or it may be omitted...
        self.assertValidDateTime('2007-09-28T16:09:20',
                                 datetime(2007, 9, 28, 16, 9, 20))

        # ...but it may not have more than 6 digits.
        self.assertDateErrorIsDetected('2007-09-28T16:09 20.1234567')

        # A timezone may be specified. 'Z' means UTC
        self.assertValidDateTime('2007-09-28T16:09:20.123456Z',
                                 datetime(2007, 9, 28, 16, 9, 20, 123456))
        self.assertValidDateTime('2007-09-28T16:09:20.123456+02:00',
                                 datetime(2007, 9, 28, 14, 9, 20, 123456))
        self.assertValidDateTime('2007-09-28T16:09:20.123456-01:00',
                                 datetime(2007, 9, 28, 17, 9, 20, 123456))

        # Other values than 'Z', '+hh:mm' or '-hh:mm' in the timezone part
        # are detected as errors.
        self.assertDateErrorIsDetected('2007-09-28T16:09 20.1234567x')

        # The values for month, day, hour, minute, timzone must be in their
        # respective valid range.
        wrong_range = (
            '2007-00-28T16:09:20.126842',
            '2007-13-28T16:09:20.126842',
            '2007-09-00T16:09:20.126842',
            '2007-02-29T16:09:20.126842',
            '2007-09-28T24:09:20.126842',
            '2007-09-28T16:60:20.126842',
            '2007-09-28T16:09:60',
            '2007-09-28T16:09:20.126842+24:00',
            '2007-09-28T16:09:20.126842-24:00')
        for invalid_datetime in wrong_range:
            self.assertDateErrorIsDetected(invalid_datetime)

        # Leap seconds (a second appended to a day) pass the Relax NG
        # validation properly...
        sample_data = self.sample_data.replace(
            '<date_created value="2007-09-28T16:09:20.126842"/>',
            '<date_created value="2007-09-28T23:59:60.999"/>')
        result, submission_id = self.runValidator(sample_data)

        # ...but the datetime function rejects them.
        self.assertRaises(ValueError, datetime, 2007, 12, 31, 23, 59, 60, 999)

        # Two leap seconds are rejected by the Relax NG validator.
        self.assertDateErrorIsDetected('2007-09-28T23:59:61')

    def assertDateErrorIsDetected(self, invalid_datetime):
        """Run a single test for an invalid datetime."""
        sample_data = self.sample_data.replace(
            '<date_created value="2007-09-28T16:09:20.126842"/>',
            '<date_created value="%s"/>' % invalid_datetime)
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            "ERROR:RELAXNGV:ERR_DOCUMENT_START: "
                "Type dateTime doesn't allow value '%s'" % invalid_datetime,
            'invalid datetime %s' % invalid_datetime)

    def assertValidDateTime(self, datetime_as_string, datetime_expected):
        """Run a single test for a valid datetime."""
        sample_data = self.sample_data.replace(
            '<date_created value="2007-09-28T16:09:20.126842"/>',
            '<date_created value="%s"/>' % datetime_as_string)
        result, submission_id = self.runValidator(sample_data)
        self.assertNotEqual(result, None,
                            'valid datetime %s rejected' % datetime_as_string)

    def testClientTagAttributes(self):
        """Validation of <client> tag attributes.

        The <client> tag requires the attributes 'name' and 'version';
        other attributes are not allowed.
        """
        # The omission of either of the required attributes is detected by
        # the Relax NG validation
        for only_attribute in ('name', 'version'):
            sample_data = self.sample_data.replace(
                '<client name="hwtest" version="0.9">',
                '<client %s="some_value">' % only_attribute)
            result, submission_id = self.runValidator(sample_data)
            self.assertErrorMessage(
                submission_id, result,
                'ERROR:RELAXNGV:ERR_PEREF_NO_NAME: '
                    'Element client failed to validate attributes',
                'missing required attribute in <client>')

        # Other attributes are rejected by the Relax NG validation.
        sample_data = self.sample_data.replace(
            '<client name="hwtest" version="0.9">',
            '<client name="hwtest" version="0.9" foo="bar">')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:WAR_UNDECLARED_ENTITY: '
                'Invalid attribute foo for element client',
            'testing invalid attribute in <client>')

    def testSubTagsOfClient(self):
        """The only allowed sub-tag of <client> is <plugin>."""
        sample_data = self.sample_data.replace(
            '<client name="hwtest" version="0.9">',
            '<client name="hwtest" version="0.9"><nonsense/>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_UNDECLARED_ENTITY: '
                'Element client has extra content: nonsense',
            'invalid sub-tag of <client>')

    def testClientPluginAttributes(self):
        """Validation of <plugin> tag attributes.

        The <plugin> tag requires the attributes 'name' and 'version';
        other attributes are not allowed.
        """
        # The omission of either of the required attributes is detected by
        # by the Relax NG validation
        for only_attribute in ('name', 'version'):
            tag =  '<plugin %s="some_value"/>' % only_attribute
            sample_data = self.sample_data.replace(
                '<plugin name="architecture_info" version="1.1"/>', tag)
            result, submission_id = self.runValidator(sample_data)
            self.assertErrorMessage(
                submission_id, result,
                'ERROR:RELAXNGV:ERR_PEREF_NO_NAME: '
                    'Element plugin failed to validate attributes',
                'missing client plugin attributes: %s' % tag)

        # Other attributes are rejected by the Relax NG validation.
        sample_data = self.sample_data.replace(
            '<plugin name="architecture_info" version="1.1"/>',
            '<plugin name="architecture_info" version="1.1" foo="bar"/>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:WAR_UNDECLARED_ENTITY: '
                'Invalid attribute foo for element plugin',
            'invalid attribute in client plugin')

    def testHardwareSubTags(self):
        """The <hardware> tag has a fixed set of allowed sub-tags.

        Valid sub-tags are <hal>, <processors>, <aliases>.
        <aliases> is optional; <hal> and <processors> are required.
        """
        # Omitting either of the required tags leads on an error.
        for tag in ('hal', 'processors'):
            sample_data = self.replaceSampledata(
                data=self.sample_data,
                replace_text='',
                from_text='<%s' % tag,
                to_text='</%s>' % tag)
            result, submission_id = self.runValidator(sample_data)
            self.assertErrorMessage(
                submission_id, result,
                'ERROR:RELAXNGV:ERR_ENTITYREF_NO_NAME: '
                    'Expecting an element %s, got nothing' % tag,
                'missing tag <%s> in <hardware>' % tag)

        # The <aliases> tag may be omitted.
        sample_data = self.replaceSampledata(
            data=self.sample_data,
            replace_text='',
            from_text='<aliases>',
            to_text='</aliases>')
        result, submission_id = self.runValidator(sample_data)
        self.assertNotEqual(result, None,
                            'submission without <aliases> rejected')

        # Other subtags are not allowed in <hardware>.
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text='<nonsense/>',
            where='</hardware>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_UNDECLARED_ENTITY: '
                'Element hardware has extra content: nonsense',
            'invalid subtag of <hardware>')

    def testHalAttributes(self):
        """Validation of <hal> tag attributes.

        The <hal> tag must have the 'version' attribute; other attributes are
        not allowed.
        """
        sample_data = self.sample_data.replace(
            '<hal version="0.5.8.1">', '<hal>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'RELAXNGV:ERR_PEREF_NO_NAME: '
                'Element hal failed to validate attributes',
            'missing version attribute of <hal>')

        sample_data = self.sample_data.replace(
            '<hal version="0.5.8.1">',
            '<hal version="0.5.8.1" foo="bar">')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'RELAXNGV:WAR_UNDECLARED_ENTITY: '
                'Invalid attribute foo for element hal',
            'invalid attribute in <hal>')

    def testHalSubtags(self):
        """Validation of sub-tags of <hal>.

        <hal> must contain at least one <device> sub-tag. All other sub-tags
        are invalid.
        """
        # If the two <device> sub-tag of the sample data are removed, the
        # submission becomes invalid.
        sample_data = self.sample_data
        for count in range(2):
            sample_data = self.replaceSampledata(
                data=sample_data,
                replace_text='',
                from_text='<device',
                to_text='</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_ENTITYREF_NO_NAME: '
                'Expecting an element device, got nothing',
            'missing <device> sub-tag in <hal>')

        # Any other tag than <device> within <hal> is not allowed.
        sample_data = self.sample_data
        insert_position = sample_data.find('<device')
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text='<nonsense/>',
            where='</hal>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_CHARREF_IN_DTD: '
                'Expecting element device, got nonsense',
            'invalid sub-tag in <hal>')

    def testDeviceAttributes(self):
        """Validation of the attributes of the <device> tag.

        <device> must have the attributes 'id' and 'udi'; the attribute
        'parent' is optional. The latter is already shown by

            <device id="130" udi="/org/freedesktop/Hal/devices/computer">

        in the standard sample data.

        The values of 'id' and 'parent' must be integers.
        """
        for only_attribute in ('id', 'udi'):
            sample_data = self.replaceSampledata(
                data=self.sample_data,
                replace_text='<device %s="2">' % only_attribute,
                from_text='<device',
                to_text='>')
            result, submission_id = self.runValidator(sample_data)
            self.assertErrorMessage(
                submission_id, result,
                'ERROR:RELAXNGV:ERR_PEREF_NO_NAME: '
                    'Element device failed to validate attributes',
                'missing attribute in <device>')

        sample_data = self.replaceSampledata(
            data=self.sample_data,
            replace_text='<device id="NoInteger" udi="foo">',
            from_text='<device',
            to_text='>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            "ERROR:RELAXNGV:ERR_DOCUMENT_START: "
                "Type integer doesn't allow value 'NoInteger'",
            "invalid content of the 'id' attribute of <device>")

        sample_data = self.replaceSampledata(
            data=self.sample_data,
            replace_text='<device id="1" parent="NoInteger" udi="foo">',
            from_text='<device',
            to_text='>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:WAR_UNDECLARED_ENTITY: '
                'Invalid attribute parent for element device',
            "invalid content of the 'parent' attribute of <device>")

    def testDeviceContent(self):
        """<device> tags may only contain <property> tags."""
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text="<nonsense/>",
            where="</device>")
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'RELAXNGV:ERR_CHARREF_IN_DTD: '
                'Expecting element property, got nonsense',
            'invalid subtag of <device>')

    # Tests for the <property> and the <value> tag.
    #
    # Both tags are very similar: They they have an attribute 'type'
    # and they have a "value", where "value" is, depending on the type
    # attribute, either represented by CDATA content or by a <value>
    # sub-tag.
    #
    # The main difference between the <value> and <property> tags is
    # their location: The <property> tag is a sub-tag of tags like <device>,
    # <processor> or <software>, while <value> is a sub-tag of <property>,
    # when the <property> has one of the types 'list', 'dbus.Array', 'dict',
    # or 'dbus.Dictionary'.
    #
    # If <value> is a sub-tag of a list-like <property> or <value>, it
    # has a 'type' attribute and a value as described above; if <value>
    # is a sub-tag of a dict-like <property> or <value>, it has a 'type'
    # and a 'name' attribute and a value as described above.
    #
    # Allowed types are: 'dbus.Boolean', 'bool', 'dbus.String',
    # 'dbus.UTF8String', 'str', 'dbus.Byte', 'dbus.Int16', 'dbus.Int32',
    # 'dbus.Int64', 'dbus.UInt16', 'dbus.UInt32', 'dbus.UInt64', 'int',
    # 'long', 'dbus.Double', 'float', 'dbus.Array', 'list',
    # 'dbus.Dictionary', 'dict'.

    def _testPropertyMissingNameAttribute(self, property):
        """The name attribute is required for all property variants."""
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text=property,
            where='</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_UNDECLARED_ENTITY: '
                'Element device has extra content: property',
            'testing missing name attribute in %s' % property)

    def _testBooleanProperty(self, content_type):
        """Validation of a boolean type property or value."""
        for value in ('True', 'False'):
            tag = ('<property name="foo" type="%s">%s</property>'
                   % (content_type, value))
            sample_data = self.insertSampledata(
                data=self.sample_data,
                insert_text=tag,
                where='</device>')
            result, submission_id = self.runValidator(sample_data)
            self.assertNotEqual(
                result, None, 'Valid boolean property tag %s rejected' % tag)

        # Other content than 'True' and 'False' is rejected by the Relax NG
        # validation.
        tag = '<property name="foo" type="%s">0</property>' % content_type
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text=tag,
            where='</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_PEREF_SEMICOL_MISSING: '
                'Element property failed to validate content',
            'invalid boolean property: %s' % tag)

        tag = '<property type="%s">False</property>' % content_type
        self._testPropertyMissingNameAttribute(tag)

        # Sub-tags are not allowed.
        tag = '<property name="foo" type="%s">False<nonsense/></property>'
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text=tag,
            where='</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            ':ERROR:RELAXNGV:ERR_PEREF_SEMICOL_MISSING: '
                'Element property failed to validate content',
            'sub-tag in boolean property: %s' % tag)

    def testBooleanProperties(self):
        for content_type in ('dbus.Boolean', 'bool'):
            self._testBooleanProperty(content_type)

    def _testStringProperty(self, property_type):
        """Validation of a string property."""
        self._testPropertyMissingNameAttribute(
            '<property type="%s">blah</property>' % property_type)

        # Sub-tags are not allowed.
        tag = '<property name="foo" type="%s">False<nonsense/></property>'
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text=tag,
            where='</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_PEREF_SEMICOL_MISSING: '
                'Element property failed to validate content',
            'sub-tags of string-like <property type="%s">' % property_type)

    def testStringProperties(self):
        """Validation of string properties."""
        for property_type in ('dbus.String', 'dbus.UTF8String', 'str'):
            self._testStringProperty(property_type)

    def _testEmptyIntegerContent(self, property_type, relax_ng_type):
        """Detection of an empty property with integer content."""
        tag = '<property name="foo" type="%s"/>' % property_type
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text=tag,
            where='</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_UNKNOWN_ENCODING: '
                'Error validating datatype %s\n'
                % relax_ng_type,
            'empty content of <property type="%s">' % relax_ng_type)

    def _testInvalidIntegerContent(self,  property_type, relax_ng_type):
        """Detection of invalid content of a property with integer content."""
        tag = '<property name="foo" type="%s">X</property>' % property_type
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text=tag,
            where='</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            "ERROR:RELAXNGV:ERR_DOCUMENT_START: "
                "Type %s doesn't allow value 'X'"
                % relax_ng_type,
            'invalid content of <property type="%s">' % relax_ng_type)

    def _testMinMaxIntegerValue(self, property_type, relax_ng_type,
                                valid_value, invalid_value):
        """Detection of integer values outside of the allowed range."""
        tag_template = '<property name="foo" type="%s">%i</property>'
        tag = tag_template % (property_type, valid_value)
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text=tag,
            where='</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertNotEqual(result, None,
                            'Valid integer value in %s rejected' % tag)

        tag = tag_template % (property_type, invalid_value)
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text=tag,
            where='</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            "ERROR:RELAXNGV:ERR_DOCUMENT_START: "
                "Type %s doesn't allow value '%i'\n"
                % (relax_ng_type, invalid_value),
            'min or max values of <property type="%s"> (%s, %s)'
                % (relax_ng_type, valid_value, invalid_value))

    def _testIntegerProperty(self, property_type, relax_ng_type, min_value,
                             max_value):
        """Validation of an integer property."""
        self._testPropertyMissingNameAttribute(
            '<property type="%s">1</property>' % property_type)

        # Empty content is detected as invalid.
        self._testEmptyIntegerContent(property_type, relax_ng_type)

        # Non-digit content is detected as invalid.
        self._testInvalidIntegerContent(property_type, relax_ng_type)

        # A value smaller than the minimum allowed value is detected as
        # invalid.
        if min_value is not None:
            self._testMinMaxIntegerValue(
                property_type, relax_ng_type, min_value, min_value-1)

        # A value larger than the maximum allowed value is detected as
        # invalid.
        if max_value is not None:
            self._testMinMaxIntegerValue(
                property_type, relax_ng_type, max_value, max_value+1)

    def testIntegerProperties(self):
        """Validation of integer properties."""
        type_info = (('dbus.Byte', 'unsignedByte', 0, 255),
                     ('dbus.Int16', 'short',  -2**15, 2**15-1),
                     ('dbus.Int32', 'int',  -2**31, 2**31-1),
                     ('dbus.Int64', 'long', -2**63, 2**63-1),
                     ('dbus.UInt16', 'unsignedShort', 0, 2**16-1),
                     ('dbus.UInt32', 'unsignedInt', 0, 2**32-1),
                     ('dbus.UInt64', 'unsignedLong', 0, 2**64-1),
                     ('long', 'integer', None, None),
                     ('int', 'int', -2**31, 2**31-1))
        for property_type, relax_ng_type, min_value, max_value in type_info:
            self._testIntegerProperty(
                property_type, relax_ng_type, min_value, max_value)

    def _testEmptyDecimalContent(self, property_type):
        """Detection of an empty property with number content."""
        tag = '<property name="foo" type="%s"/>' % property_type
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text=tag,
            where='</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            "ERROR:RELAXNGV:ERR_DOCUMENT_START: "
                "Type decimal doesn't allow value ''\n",
            'empty decimal type property %s' % property_type)

    def _testInvalidDecimalContent(self,  property_type):
        """Detection of invalid content of a property with number content."""
        tag = '<property name="foo" type="%s">X</property>' % property_type
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text=tag,
            where='</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            "ERROR:RELAXNGV:ERR_DOCUMENT_START: "
                "Type decimal doesn't allow value 'X'",
            'invalid content in decimal type prperty %s' % property_type)

    def _testDecimalProperty(self, property_type):
        """Validation of an integer property."""
        self._testPropertyMissingNameAttribute(
            '<property type="%s">1</property>' % property_type)

        # Empty content is detected as invalid.
        self._testEmptyDecimalContent(property_type)

        # Non-digit content is detected as invalid.
        self._testInvalidDecimalContent(property_type)

    def testDecimalProperties(self):
        """Validation of dbus.Double and float properties."""
        for property_type in ('dbus.Double', 'float'):
            self._testDecimalProperty(property_type)

    def _testListAndDictPropertyCDataContent(self, property_type):
        """List and dict properties may not have CDATA content."""
        tag = '<property name="foo" type="%s">X</property>' % property_type
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text=tag,
            where='</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_UNDECLARED_ENTITY: '
                'Element property has extra content: text',
            'testing CDATA content of <property type="%s">' % property_type)

    def _testEmptyListAndDictProperty(self, property_type):
        """Validation of empty list properties."""
        tag = '<property name="foo" type="%s"></property>' % property_type
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text=tag,
            where='</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertNotEqual(
            result, None,
            'Valid submission with empty <property type="%s"> rejected'
                % property_type)

    def _testInvalidSubtagOfListAndDictProperty(self, property_type):
        """Other sub-tags than <value> are not allowed in lists and dicts."""
        tag = '<property name="foo" type="%s"><nonsense/></property>'
        tag = tag % property_type
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text=tag,
            where='</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_CHARREF_IN_DTD: '
                'Expecting element value, got nonsense\n',
            'invalid subtag of <property type="%s">' % property_type)

    def _wrapValue(self, value_tag, property_type):
        """Wrap a <value> tag into a <property> tag."""
        return ('<property name="bar" type="%s">%s</property>'
                % (property_type, value_tag))

    def _testBooleanValueTagValues(self, property_type, tag_template):
        """Validation of the CDATA values of a <value> tag."""
        # The only allowed values are True and False.
        for cdata_value in ('True', 'False'):
            tag = tag_template % cdata_value
            tag = self._wrapValue(tag, property_type)
            sample_data = self.insertSampledata(
                data=self.sample_data,
                insert_text=tag,
                where='</device>')
            result, submission_id = self.runValidator(sample_data)
            self.assertNotEqual(result, None)
        # Any other text in the <value> tag is invalid.
        tag = tag_template % 'nonsense'
        tag = self._wrapValue(tag, property_type)
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text=tag,
            where='</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertEqual(result, None)
        self.assertErrorMessage(
            submission_id,
            'Error validating value ')
        # An empty <value> tag is invalid.
        tag = tag_template % ''
        tag = self._wrapValue(tag, property_type)
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text=tag,
            where='</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertEqual(result, None)
        self.assertErrorMessage(
            submission_id,
            'ERROR:RELAXNGV:ERR_UNSUPPORTED_ENCODING: '
                'Error validating value ')

    def _setupValueTagTemplates(self, value_type):
        """Return templates for value tags with/without a name attribute."""
        tag_with_name = '<value name="foo" type="%s">' % value_type
        tag_with_name = tag_with_name + '%s</value>'
        tag_without_name = '<value type="%s">' % value_type
        tag_without_name = tag_without_name + '%s</value>'
        return tag_with_name, tag_without_name

    def _testValueTagWithCData(self, value_type, needs_name_attribute,
                               valid_content, invalid_content,
                               property_template):
        """Validation of tags with CData values"""
        tag_with_name, tag_without_name = self._setupValueTagTemplates(
            value_type)
        if needs_name_attribute:
            tag = tag_without_name % valid_content[0]
            tag = property_template % tag
            sample_data = self.insertSampledata(
                data=self.sample_data,
                insert_text=tag,
                where='</device>')
            result, submission_id = self.runValidator(sample_data)
            self.assertErrorMessage(
                submission_id, result,
                'ERROR:RELAXNGV:ERR_UNDECLARED_ENTITY: '
                    'Element device has extra content: property',
                'missing name attribute in value tag %s' % tag)
        else:
            tag = tag_with_name % valid_content[0]
            tag = property_template % tag
            sample_data = self.insertSampledata(
                data=self.sample_data,
                insert_text=tag,
                where='</device>')
            result, submission_id = self.runValidator(sample_data)
            self.assertErrorMessage(
                submission_id, result,
                'ERROR:RELAXNGV:ERR_UNDECLARED_ENTITY: '
                    'Element device has extra content: property',
                'invalid name attribute in value tag %s' % tag)

        if needs_name_attribute:
            template = tag_with_name
        else:
            template = tag_without_name
        template = property_template % template
        for value in valid_content:
            tag = template % value
            sample_data = self.insertSampledata(
                data=self.sample_data,
                insert_text=tag,
                where='</device>')
            result, submission_id = self.runValidator(sample_data)
            self.assertNotEqual(
                result, None,
                'Valid submission with tag %s rejected' % tag)
        for value, expected_error in invalid_content:
            tag = template % value
            sample_data = self.insertSampledata(
                data=self.sample_data,
                insert_text=tag,
                where='</device>')
            result, submission_id = self.runValidator(sample_data)
            self.assertErrorMessage(
                submission_id, result, expected_error,
                'invalid content of value tag %s' % tag)

    def _setupContainerTag(self, tag, name, container_type):
        """Setup a template for a property or value tag with sub-tags.

        tag must be either 'property' or 'value'

        name is the value of the name attribute of the template, or
        None, if the template shall not have the attribute name.

        container_type must be one of 'list', 'dbus.List', 'dict',
        'dbus.Dictionary'.

        Return: A tag template for this property/value type and a flag,
        if value tags within this tag need a name attribute.
        """
        if name is not None:
            container_template = (
                '<%s name="%s" type="%s">' % (tag, name, container_type))
        else:
            container_template = '<%s type="%s">' % (tag, container_type)
        container_template = container_template + '%s' + '</%s>' % tag
        if container_type in ('dbus.Dictionary', 'dict'):
            needs_name_attribute = True
        elif container_type in ('dbus.Array', 'list'):
            needs_name_attribute = False
        else:
            raise AssertionError(
                '_setupPropertyTag called for invalid property type:'
                % container_type)
        return container_template, needs_name_attribute

    def _testBooleanValueTags(self, property_type):
        """Validation of boolean-like <value> tags."""
        property_template, needs_name_attribute = (
            self._setupContainerTag('property', 'foor', property_type))
        valid_content = ('True', 'False')
        invalid_content = (
            ('nonsense', 'ERROR:RELAXNGV:ERR_UNDECLARED_ENTITY: '
                         'Element property has extra content: value'),
            ('', 'ERROR:RELAXNGV:ERR_UNDECLARED_ENTITY: '
                 'Element property has extra content: value'),
            ('<nonsense/>', 'ERROR:RELAXNGV:ERR_ENTITY_IS_EXTERNAL: '
                            'Value element value has child elements'))
        for value_type in ('dbus.Boolean', 'bool'):
            self._testValueTagWithCData(value_type, needs_name_attribute,
                                        valid_content, invalid_content,
                                        property_template)

    def _testStringValueTags(self, property_type):
        """Validation of string-like <value> tags."""
        property_template, needs_name_attribute = (
            self._setupContainerTag('property', 'foo', property_type))
        valid_content = ('any text', '')
        invalid_content = (
            ('<nonsense/>', 'ERROR:RELAXNGV:ERR_UNDECLARED_ENTITY: '
                            'Element value has extra content: nonsense'),)
        for value_type in ('dbus.String', 'str'):
            self._testValueTagWithCData(value_type, needs_name_attribute,
                                        valid_content, invalid_content,
                                        property_template)

    def _makeSampleDataForValueTag(self, property_type, value_type, value):
        property_template, needs_name_attribute = (
            self._setupContainerTag('property', 'foo', property_type))
        value_template_with_name, value_template_without_name = (
            self._setupValueTagTemplates(value_type))
        if needs_name_attribute:
            value_tag = value_template_with_name % value
        else:
            value_tag = value_template_without_name % value
        property_tag = property_template % value_tag
        return self.insertSampledata(
            data=self.sample_data,
            insert_text=property_tag,
            where='</device>')

    def _testIntegerLimit(self, property_type, value_type, relax_ng_type,
                          allowed, disallowed):
        """Validation of the smallest or largest value of an int type."""
        sample_data = self._makeSampleDataForValueTag(
            property_type, value_type, allowed)
        result, submission_id = self.runValidator(sample_data)
        self.assertNotEqual(
            result, None,
            'Testing integer limits: Valid submission for property type %s '
                'value type %s, value %s rejected'
                % (property_type, value_type, allowed))

        sample_data = self._makeSampleDataForValueTag(
            property_type, value_type, disallowed)
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            "ERROR:RELAXNGV:ERR_DOCUMENT_START: "
                "Type %s doesn't allow value '%s'" % (relax_ng_type,
                                                      disallowed),
            'invalid value %s of value type %s in property type %s'
                % (disallowed, value_type, property_type))

    def _testIntegerValueTag(self, property_type, value_type, relax_ng_type,
                             min_allowed, max_allowed):
        """Valudation of a <value> tag wwith integral content."""
        property_template, needs_name_attribute = (
            self._setupContainerTag('property', 'foo', property_type))
        valid_content = ('0', '1')
        invalid_content = (('', 'ERROR:RELAXNGV:ERR_UNKNOWN_ENCODING: '
                                    'Error validating datatype %s'
                                    % relax_ng_type),
                           ('1.1', "ERROR:RELAXNGV:ERR_DOCUMENT_START: "
                                       "Type %s doesn't allow "
                                       "value '1.1'"
                                       % relax_ng_type),
                           ('nonsense', "ERROR:RELAXNGV:ERR_DOCUMENT_START: "
                                            "Type %s doesn't allow "
                                            "value 'nonsense'"
                                            % relax_ng_type),
                           ('<nonsense/>',
                            'ERROR:RELAXNGV:ERR_UNPARSED_ENTITY: '
                            'Datatype element value has child elements'))
        self._testValueTagWithCData(value_type, needs_name_attribute,
                                    valid_content, invalid_content,
                                    property_template)
        if min_allowed is not None:
            self._testIntegerLimit(property_type, value_type, relax_ng_type,
                                   min_allowed, min_allowed - 1)
        if max_allowed is not None:
            self._testIntegerLimit(property_type, value_type, relax_ng_type,
                                   max_allowed, max_allowed + 1)

    def _testIntegerValueTags(self, property_type):
        """Validation of <value> tags with integral content."""
        int_types = (
            ('dbus.Byte', 'unsignedByte', 0, 255),
            ('dbus.Int16', 'short', -32768, 32767),
            ('dbus.Int32', 'int', -2**31, 2**31-1),
            ('dbus.Int64', 'long', -2**63, 2**63-1),
            ('dbus.UInt16', 'unsignedShort', 0, 2**16-1),
            ('dbus.UInt32', 'unsignedInt', 0, 2**32-1),
            ('dbus.UInt64', 'unsignedLong', 0, 2**64-1),
            ('int', 'int', -2**31, 2**31-1),
            ('long', 'integer', None, None))
        for value_type, relax_ng_type, min_allowd, max_allowed in int_types:
            self._testIntegerValueTag(property_type, value_type, relax_ng_type,
                                      min_allowd, max_allowed)

    def _testFloatValueTag(self, property_type, value_type):
        """Validation of a <value> tag with float-number content."""
        property_template, needs_name_attribute = (
            self._setupContainerTag('property', 'foo', property_type))
        valid_content = ('0', '1', '1.1', '-2.34')
        invalid_content = (('', "ERROR:RELAXNGV:ERR_DOCUMENT_START: "
                                    "Type decimal doesn't allow value ''"),
                           ('nonsense', "ERROR:RELAXNGV:ERR_DOCUMENT_START: "
                                            "Type decimal doesn't allow "
                                            "value 'nonsense'"),
                           ('<nonsense/>',
                            'ERROR:RELAXNGV:ERR_UNPARSED_ENTITY: '
                                'Datatype element value has child elements'))
        self._testValueTagWithCData(value_type, needs_name_attribute,
                                    valid_content, invalid_content,
                                    property_template)

    def _testFloatValueTags(self, property_type):
        """Validation of <value> tags with float-number content."""
        float_types = ('dbus.Double', 'float')
        for value_type in float_types:
            self._testFloatValueTag(property_type, value_type)

    def _testListOrDictValueTag(self, property_type, value_type):
        """Validation of a list or dict-like value tag."""
        property_template, needs_name_attribute = self._setupContainerTag(
            'property', 'foo', property_type)
        if needs_name_attribute:
            value_template, needs_name_attribute = self._setupContainerTag(
                'value', 'bar', value_type)
        else:
            value_template, needs_name_attribute = self._setupContainerTag(
                'value', None, value_type)
        template = property_template % value_template

        # CDATA content is not allowed.
        tag = template % 'nonsense'
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text = tag,
            where = '</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_UNDECLARED_ENTITY: '
                'Element value has extra content: text',
            'CDATA in <value type="%s">' % value_type)

        # Lists and dicts may be empty.
        tag = template % ''
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text = tag,
            where = '</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertNotEqual(
            result, None, 'empty tag <value type="%s">' % value_type)

        # Other sub-tags than <value> are invalid.
        tag = template % '<nonsense/>'
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text = tag,
            where = '</device>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_UNDECLARED_ENTITY: '
                'Element value has extra content: nonsense',
            'CDATA in <value type="%s">' % value_type)

        if needs_name_attribute:
            # Dict-like <value> tags need nested <value> tags with the
            # attribute name.
            tag = template % '<value type="int" name="baz">1</value>'
            sample_data = self.insertSampledata(
                data=self.sample_data,
                insert_text = tag,
                where = '</device>')
            result, submission_id = self.runValidator(sample_data)
            self.assertNotEqual(
                result, None,
                'valid <value> tag inside <value type="%s">' % value_type)

            tag = template % '<value type="int">1</value>'
            sample_data = self.insertSampledata(
                data=self.sample_data,
                insert_text = tag,
                where = '</device>')
            result, submission_id = self.runValidator(sample_data)
            self.assertErrorMessage(
                submission_id, result,
                'ERROR:RELAXNGV:ERR_UNDECLARED_ENTITY: '
                    'Element value has extra content: value',
                'invalid <value> tag inside <value type="%s">' % value_type)
        else:
            # List-like <value> tags need nested <value> tags without the
            # attribute name.
            tag = template % '<value type="int">1</value>'
            sample_data = self.insertSampledata(
                data=self.sample_data,
                insert_text = tag,
                where = '</device>')
            result, submission_id = self.runValidator(sample_data)
            self.assertNotEqual(
                result, None,
                'valid <value> tag inside <value type="%s">' % value_type)

            tag = template % '<value type="int" nam="baz">1</value>'
            sample_data = self.insertSampledata(
                data=self.sample_data,
                insert_text = tag,
                where = '</device>')
            result, submission_id = self.runValidator(sample_data)
            self.assertErrorMessage(
                submission_id, result,
                'ERROR:RELAXNGV:ERR_UNDECLARED_ENTITY: '
                    'Element value has extra content: value',
                'invalid <value> tag inside <value type="%s">' % value_type)

    def _testListAndDictValueTags(self, property_type):
        """Validation of list and dict-like values."""
        for value_type in ('list', 'dbus.Array', 'dict', 'dbus.Dictionary'):
            self._testListOrDictValueTag(property_type, value_type)

    def _testValueTags(self, property_type):
        """Tests of <value> sub-tags of <property type="property_type">."""
        self._testBooleanValueTags(property_type)
        self._testStringValueTags(property_type)
        self._testIntegerValueTags(property_type)
        self._testFloatValueTags(property_type)
        self._testListAndDictValueTags(property_type)

    def _testListOrDictProperty(self, property_type):
        """Validation of a list property."""
        self._testListAndDictPropertyCDataContent(property_type)
        self._testEmptyListAndDictProperty(property_type)
        self._testInvalidSubtagOfListAndDictProperty(property_type)
        self._testValueTags(property_type)

    def testListAndDictProperties(self):
        """Validation of dbus.Array and list properties."""
        for property_type in ('dbus.Array', 'list', 'dbus.Dictionary', 'dict'):
            self._testListOrDictProperty(property_type)

    def testProcessorsTag(self):
        """Validation of the <processors> tag.

        This tag has no attributes. The only allowed sub-tag is <processor>.
        At least one <processor> tag must be present.
        """
        sample_data = self.sample_data.replace(
            '<processors>', '<processors foo="bar">')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:WAR_UNDECLARED_ENTITY: '
                'Invalid attribute foo for element processors',
            'invalid attribute of <processors>')

        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text='<nonsense/>',
            where = '</processors>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_CHARREF_IN_DTD: '
                'Expecting element processor, got nonsense',
            'invalid sub-tag of <processors>')

        sample_data = self.replaceSampledata(
            data=self.sample_data,
            replace_text='',
            from_text='<processor id',
            to_text='</processor>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_ENTITYREF_NO_NAME: '
                'Expecting an element processor, got nothing',
            'missing sub-tags of <processors>')

    def testProcessorTag(self):
        """Validation of the <processors> tag."""
        # The attributes "id" and "name" are required.
        sample_data = self.sample_data.replace(
            '<processor id="123" name="0">', '<processor id="123">')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_PEREF_NO_NAME: '
                'Element processor failed to validate attributes',
            'missing attribute "name" of <processors>')

        sample_data = self.sample_data.replace(
            '<processor id="123" name="0">', '<processor name="0">')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_PEREF_NO_NAME: '
                'Element processor failed to validate attributes',
            'missing attribute "id" attribute of <processors>')

        # other attributes are invalid.
        sample_data = self.sample_data.replace(
            '<processor id="123" name="0">',
            '<processor id="123" name="0" foo="bar">')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:WAR_UNDECLARED_ENTITY: '
                'Invalid attribute foo for element processor',
            'missing attribute "id" attribute of <processors>')

        # Other sub-tags than <property> are invalid.
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text='<nonsense/>',
            where = '</processor>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_CHARREF_IN_DTD: '
                'Expecting element property, got nonsense',
            'invalid sub-tag of <processor>')

        # At least one <property> tag must be present
        sample_data = self.replaceSampledata(
            data=self.sample_data,
            replace_text='<processor id="123" name="0"/>',
            from_text='<processor id="123" name="0">',
            to_text='</processor>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_ENTITYREF_NO_NAME: '
                'Expecting an element property, got nothing',
            'missing sub-tags of <processor>')

    def testAliasesTag(self):
        """Validation of the <aliases> tag."""
        # The <aliases> tag has no attributes.
        sample_data = self.sample_data.replace(
            '<aliases>', '<aliases foo="bar">')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_CHARREF_IN_EPILOG: '
                'Extra element aliases in interleave',
            'invalid attribute of <aliases>')

        # The <aliases> tag may be omittied.
        sample_data = self.replaceSampledata(
            data=self.sample_data,
            replace_text='',
            from_text='<aliases>',
            to_text='</aliases>')
        result, submission_id = self.runValidator(sample_data)
        self.assertNotEqual(result, None, 'omitted tag <aliases>')

        # The <aliases> may be empty.
        sample_data = self.replaceSampledata(
            data=self.sample_data,
            replace_text='<aliases/>',
            from_text='<aliases>',
            to_text='</aliases>')
        result, submission_id = self.runValidator(sample_data)
        self.assertNotEqual(result, None, 'empty tag <aliases>')

        # Other sub-tags than <alias> are invalid.
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text='<nonsense/>',
            where='</aliases>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_CHARREF_IN_EPILOG: '
                'Extra element aliases in interleave',
            'invalid sub-tag of <aliases>')

    def testAliasTag(self):
        """Validation of the <alias> tag."""
        # The attribute target is required.
        # Note that the expected error message from the validator
        # is identical to the last error message expected in
        # testAliasesTag: lxml's Relax NG validator is sometimes
        # not as informative as one might wish.
        sample_data = self.sample_data.replace(
            '<alias target="65">', '<alias>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_CHARREF_IN_EPILOG: '
                'Extra element aliases in interleave',
            'missing attribute of <alias>')

        # Other attributes are not allowed. We get again the same
        # quite unspecific error message as above.
        sample_data = self.sample_data.replace(
            '<alias target="65">', '<alias target="65" foo="bar">')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_CHARREF_IN_EPILOG: '
                'Extra element aliases in interleave',
            'invalid attribute of <alias>')

        # The <alias> tag requires exactly two sub-tags: <vendor> and
        # <model>. Omitting either of them is forbidden. Again, we get
        # same error message from the validator.
        sample_data = self.replaceSampledata(
            data=self.sample_data,
            replace_text='',
            from_text='<vendor>',
            to_text='</vendor>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_CHARREF_IN_EPILOG: '
                'Extra element aliases in interleave',
            'missing sub-tag <vendor> of <alias>')
        sample_data = self.replaceSampledata(
            data=self.sample_data,
            replace_text='',
            from_text='<model>',
            to_text='</model>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_CHARREF_IN_EPILOG: '
                'Extra element aliases in interleave',
            'missing sub-tag <model> of <alias>')

        # Other sub-tags are not allowed.
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text='<nonsense/>',
            where='</alias>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_CHARREF_IN_EPILOG: '
                'Extra element aliases in interleave',
            'invalid sub-tag of <alias>')

    def testAliasVendorTag(self):
        """Validation of the <vendor> tag in <alias>."""
        # The tag may not have any attributes. As for the <alias> tag,
        # we don't get very specific error messages.
        sample_data = self.sample_data.replace(
            '<vendor>', '<vendor foo="bar">')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_CHARREF_IN_EPILOG: '
                'Extra element aliases in interleave',
            'invalid attribute of <vendor>')

        # <vendor> may not have any sub-tags.
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text='<nonsense/>',
            where='</vendor>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_CHARREF_IN_EPILOG: '
                'Extra element aliases in interleave',
            'invalid sub-tag of <alias>')

    def testAliasModelTag(self):
        """Validation of the <model> tag in <alias>."""
        # The tag may not have any attributes. As for the <alias> tag,
        # we don't get very specific error messages.
        sample_data = self.sample_data.replace(
            '<model>', '<model foo="bar">')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_CHARREF_IN_EPILOG: '
                'Extra element aliases in interleave',
            'invalid attribute of <model>')

        # <model> may not have any sub-tags.
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text='<nonsense/>',
            where='</model>')
        result, submission_id = self.runValidator(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            'ERROR:RELAXNGV:ERR_CHARREF_IN_EPILOG: '
                'Extra element aliases in interleave',
            'invalid sub-tag of <alias>')


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
