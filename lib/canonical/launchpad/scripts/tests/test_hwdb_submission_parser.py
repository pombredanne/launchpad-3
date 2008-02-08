# Copyright 2008 Canonical Ltd.  All rights reserved.
"""Tests of the HWDB submissions parser."""

from datetime import datetime
import logging
from lxml import etree
import os
import pytz
from unittest import TestCase, TestLoader

from zope.testing.loghandler import Handler
from canonical.config import config
from canonical.launchpad.scripts.hwdbsubmissions import SubmissionParser
from canonical.testing import BaseLayer


class TestHWDBSubmissionParser(TestCase):
    """Tests of the HWDB submission parser."""

    layer = BaseLayer

    submission_count = 0

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

    def assertErrorMessage(self, submission_key, result, message, test):
        """Search for message in the log entries for submission_key.

        assertErrorMessage requires that
        (a) a log message starts with "Parsing submisson <submission_key>:"
        (b) the error message passed as the parameter message appears
            in a log string that matches (a)
        (c) result, which is supposed to contain an object representing
            the result of parsing a submission, is None.

        If all three criteria match, assertErrormessage does not raise any
        exception.
        """
        self.assertEqual(
            result, None,
            'The test %s failed: The parsing result is not None.' % test)
        last_log_messages = []
        for r in self.handler.records:
            if r.levelno != logging.ERROR:
                continue
            candidate = r.getMessage()
            if candidate.startswith('Parsing submission %s:'
                                    % submission_key):
                if candidate.find(message) > 0:
                    return
                else:
                    last_log_messages.append(candidate)
        failmsg = [
            "No error log message for submission %s (testing %s) contained %s"
                % (submission_key, test, message)]
        if last_log_messages:
            failmsg.append('Log messages for the submission:')
            failmsg.extend(last_log_messages)
        else:
            failmsg.append('No messages logged for this submission')

        self.fail('\n'.join(failmsg))

    def runParser(self, sample_data):
        """Run the HWDB submission parser."""
        self.submission_count += 1
        submission_id = 'submission_%i' % self.submission_count
        result = SubmissionParser(self.log).parseSubmission(sample_data,
                                                            submission_id)
        return result, submission_id

    def insertSampledata(self, data, insert_text, where):
        """Insert text into the sample data `data`.

        Insert the text `insert_text` before the first occurrence of
        `where` in `data`.
        """
        insert_position = data.find(where)
        return data[:insert_position] + insert_text + data[insert_position:]

    def getTimestampETreeNode(self, time_string):
        """Return an Elementtree node for an XML tag with a timestamp."""
        return etree.Element('date_created', value=time_string)

    def testTimeConversion(self):
        """Test of the conversion of a "time string" into datetime object."""
        # Year, month, day, hour, minute, second are required.
        # We assume that such a value without timezone information is UTC.
        parser = SubmissionParser(self.log)
        utc_tz = pytz.timezone('UTC')

        time_node = self.getTimestampETreeNode('2008-01-02T03:04:05')
        self.assertEqual(parser._getValueAttributeAsDateTime(time_node),
                         datetime(2008, 1, 2, 3, 4, 5, tzinfo=utc_tz))

        # The timezone value 'Z' means UTC
        time_node = self.getTimestampETreeNode('2008-01-02T03:04:05Z')
        self.assertEqual(parser._getValueAttributeAsDateTime(time_node),
                         datetime(2008, 1, 2, 3, 4, 5, tzinfo=utc_tz))

        # A time zone offset is added to the given time, so that the resulting
        # time stamp is in UTC.
        time_node = self.getTimestampETreeNode('2008-01-02T03:04:05+01:00')
        self.assertEqual(parser._getValueAttributeAsDateTime(time_node),
                         datetime(2008, 1, 2, 2, 4, 5, tzinfo=utc_tz))

        time_node = self.getTimestampETreeNode('2008-01-02T03:04:05-01:00')
        self.assertEqual(parser._getValueAttributeAsDateTime(time_node),
                         datetime(2008, 1, 2, 4, 4, 5, tzinfo=utc_tz))

        # The time zone offset may be given with "minute resolution".
        time_node = self.getTimestampETreeNode('2008-01-02T03:04:05+00:01')
        self.assertEqual(parser._getValueAttributeAsDateTime(time_node),
                         datetime(2008, 1, 2, 3, 3, 5, tzinfo=utc_tz))

        time_node = self.getTimestampETreeNode('2008-01-02T03:04:05-00:01')
        self.assertEqual(parser._getValueAttributeAsDateTime(time_node),
                         datetime(2008, 1, 2, 3, 5, 5, tzinfo=utc_tz))

        # Leap seconds are rounded down to 59.999999 seconds.
        time_node = self.getTimestampETreeNode('2008-01-02T23:59:60.999')
        self.assertEqual(parser._getValueAttributeAsDateTime(time_node),
                         datetime(2008, 1, 2, 23, 59, 59, 999999,
                                  tzinfo=utc_tz))
        

    def testBooleanValuesInSummary(self):
        """Test boolean values in the <summary> section.
        """
        # The parser returns either True or False for the nodes
        # <live_cd>, <private>, <contactable>.
        boolean_nodes = ('live_cd', 'private', 'contactable')
        result, submission_id = self.runParser(self.sample_data)
        summary = result['summary']
        for node in boolean_nodes:
            self.assertEqual(
                summary[node], False,
                'Testing parsing result of <%s> in <summary>: Got %s, '
                    'expected False' % (node, summary[node]))
        for node in boolean_nodes:
            sample_data = self.sample_data.replace(
                '<%s value="False"/>' % node, '<%s value="True"/>' % node)
            result, submission_id = self.runParser(sample_data)
            summary = result['summary']
            self.assertEqual(
                summary[node], True,
                'Testing parsing result of <%s> in <summary>: Got %s, '
                    'expected True' % (node, summary[node]))

    def testSummaryParser(self):
        """Test of the parser for the XML submission data."""
        result, submission_id = self.runParser(self.sample_data)
        self.assertNotEqual(result, None, 
                            'Submission parser returned an error '
                            'for valid data.')

        # The <summary> section is returned as a simple dictionary.
        # Possibly missing tags are already catched by the Relax NG
        # validation, as is invalid content of tags with boolean
        # or datetime content, hence there is no need to check for
        # this type of "bad data" here.
        summary = result['summary']
        client_expected = {'name': 'hwtest',
                           'version': '0.9',
                           'plugins': [{'name': 'architecture_info',
                                        'version': '1.1'},
                                       {'name': 'find_network_controllers',
                                        'version': '2.34'},
                                       {'name': 'internet_ping',
                                        'version': '1.1'},
                                       {'name': 'harddisk_speed',
                                        'version': '0.7'}
                                      ]}
        utc_tz = pytz.timezone('UTC')
        summary_expected = {'live_cd': False,
                            'system_id': 'f982bb1ab536469cebfd6eaadcea0ffc',
                            'distribution': 'Ubuntu',
                            'distroseries': '7.04',
                            'architecture': 'amd64',
                            'private': False,
                            'contactable': False,
                            'date_created': datetime(2007, 9, 28, 16, 9, 20,
                                                     126842, tzinfo=utc_tz),
                            'client': client_expected}
        self.assertEqual(summary, summary_expected,
                         'Submission parser: Invalid <summary> result')

    def _runPropertyTest(self, properties):
        """Insert the string properties into the test data and run the parser.

        :return: the parsed properties represented as a Python list.

        The string properties is wrapped into <device>...</device> and
        appended to the end of the <hal> section of the sample sumission
        data.
        """
        insert_text = ('<device id="555" '
                       'udi="/org/freedesktop/Hal/devices/bogus">%s</device>')
        insert_text = insert_text % properties
        sample_data = self.insertSampledata(
            data=self.sample_data,
            insert_text=insert_text,
            where='</hal>')

        result, submission_id = self.runParser(sample_data)
        
        devices = result['hardware']['hal']['devices']
        devices = [device for device in devices if device['id'] == 555]
        return devices[0]['properties']

    def testBooleanProperties(self):
        """Bool properties are converted into {'name': (value, type_string)}

        type(value) is bool.
        """
        property_xml = '<property name="booltest" type="bool">True</property>'
        properties = self._runPropertyTest(property_xml)
        self.assertEqual(properties,
                         {'booltest': (True, 'bool')},
                         'Invalid parsing result for boolean property %s'
                             % property_xml)

        property_xml = '<property name="booltest" type="bool">False</property>'
        properties = self._runPropertyTest(property_xml)
        self.assertEqual(properties,
                         {'booltest': (False, 'bool')},
                         'Invalid parsing result for boolean property %s'
                             % property_xml)

        property_xml = ('<property name="booltest" type="dbus.Boolean">'
                        'False</property>')
        properties = self._runPropertyTest(property_xml)
        self.assertEqual(properties,
                         {'booltest': (False, 'dbus.Boolean')},
                         'Invalid parsing result for boolean property %s'
                             % property_xml)

        property_xml = ('<property name="booltest" type="dbus.Boolean">'
                        'True</property>')
        properties = self._runPropertyTest(property_xml)
        self.assertEqual(properties,
                         {'booltest': (True, 'dbus.Boolean')},
                         'Invalid parsing result for boolean property %s'
                             % property_xml)

    def testStringProperties(self):
        """String properties are converted into {'name': (value, type_string)}.

        type(value) is string.
        """
        property_xml = '<property name="strtest" type="str">abcd</property>'
        properties = self._runPropertyTest(property_xml)
        self.assertEqual(properties,
                         {'strtest': ('abcd', 'str')},
                         'Invalid parsing result for string property %s'
                         % property_xml)

        property_xml = ('<property name="strtest" type="dbus.String">abcd'
                        '</property>')
        properties = self._runPropertyTest(property_xml)
        self.assertEqual(properties,
                         {'strtest': ('abcd', 'dbus.String')},
                         'Invalid parsing result for string property %s'
                         % property_xml)

        property_xml = ('<property name="strtest" type="dbus.UTF8String">'
                       'abcd</property>')
        properties = self._runPropertyTest(property_xml)
        self.assertEqual(properties,
                         {'strtest': ('abcd', 'dbus.UTF8String')},
                         'Invalid parsing result for string property %s'
                         % property_xml)

    def testIntegerProperties(self):
        """Int properties are converted into {'name': (value, type_string)}.

        type(value) is int or long, depending on the value.
        """
        property_template = '<property name="inttest" type="%s">123</property>'
        for property_type in ('dbus.Byte', 'dbus.Int16', 'dbus.Int32',
                              'dbus.Int64', 'dbus.UInt16', 'dbus.UInt32',
                              'dbus.UInt64', 'int', 'long'):
            property_xml = property_template % property_type
            properties = self._runPropertyTest(property_xml)
            self.assertEqual(properties,
                             {'inttest': (123, property_type)},
                             'Invalid parsing result for integer property: '
                             '%s' % property_xml)
        # If the value is too large for an int, a Python long is returned.
        property_xml = """
            <property name="inttest" type="long">
                12345678901234567890
            </property>"""
        properties = self._runPropertyTest(property_xml)
        self.assertEqual(properties,
                         {'inttest': (12345678901234567890L,'long')},
                         'Invalid parsing result for integer property: '
                         '%s' % property_xml)

    def testFloatProperties(self):
        """Float properties are converted into {'name': (value, type_string)}.

        type(value) is float.
        """
        property_template = ('<property name="floattest" type="%s">'
                            '1.25</property>')
        for property_type in ('dbus.Double', 'float'):
            property_xml = property_template % property_type
            properties = self._runPropertyTest(property_xml)
            self.assertEqual(properties,
                             {'floattest': (1.25, property_type)},
                             'Invalid parsing result for float property: '
                             '%s' % property_xml)

    def testListProperties(self):
        """List properties are converted into {'name': a_list}.

        a_list is a Python list, where the list elements represent the
        values of the <value> sub-nodes of the <property>.
        """
        property_template = """
            <property name="listtest" type="%s">
                <value type="int">1</value>
                <value type="int">2</value>
                <value type="str">a</value>
            </property>
            """
        for property_type in ('dbus.Array', 'list'):
            property_xml = property_template % property_type
            properties = self._runPropertyTest(property_xml)
            self.assertEqual(properties,
                             {'listtest': ([(1, 'int'),
                                            (2, 'int'),
                                            ('a', 'str')], property_type)},
                             'Invalid Parsing result for list property: '
                             '%s' % property_xml)

    def testDictProperties(self):
        """List properties are converted into {'name': a_dict}.

        a_dict is a Python dictionary, where the items represent the
        values of the <value> sub-nodes of the <property>.
        """
        property_template = """
            <property name="dicttest" type="%s">
                <value name="one" type="int">1</value>
                <value name="two" type="int">2</value>
                <value name="three" type="str">a</value>
            </property>
            """
        for property_type in ('dbus.Dictionary', 'dict'):
            property_xml = property_template % property_type
            properties = self._runPropertyTest(property_xml)
            self.assertEqual(properties,
                             {'dicttest': ({'one': (1, 'int'),
                                            'two': (2, 'int'),
                                            'three': ('a', 'str')},
                                           property_type)},
                             'Invalid Parsing result for dict property: '
                             '%s' % property_xml)

    def testDuplicateProperty(self):
        """Two properties with the same name in one set are invalid."""
        sample_data = self.sample_data
        duplicate_property = (
            '<property name="info.parent" type="dbus.String">xxx</property>')
        insert_at = 'udi="/org/freedesktop/Hal/devices/platform_bluetooth">'
        sample_data = sample_data.replace(
            insert_at, insert_at + duplicate_property)

        result, submission_id = self.runParser(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            '<property name="info.parent"> found more than once in <device>',
            'Detection of duplicate properties')
        
    def testHalData(self):
        """The <hal> node is converted into a Python dict."""
        result, submission_id = self.runParser(self.sample_data)
        hal_data = result['hardware']['hal']
        expected_device_1 = {
            'udi': '/org/freedesktop/Hal/devices/platform_bluetooth',
            'id': 0,
            'parent': '130',
            'properties': {
                'storage.size': (0, 'dbus.UInt64'),
                'info.parent': ('/org/freedesktop/Hal/devices/computer',
                                'dbus.String'),
                'info.bus': ('platform', 'dbus.String'),
                'test.only': ({'blah': (1234, 'dbus.Int32'),
                               'foo': ('bar', 'dbus.String')},
                              'dbus.Dictionary'),
                'info.capabilities': ([('button', 'dbus.String')],
                                      'dbus.Array'),
                'linux.acpi_type': (11, 'dbus.Int32'),
                'button.has_state': (False, 'dbus.Boolean')}}
        expected_device_2 = {
            'udi': '/org/freedesktop/Hal/devices/computer',
            'id': 130,
            'parent': None,
            'properties': {'info.bus': ('unknown', 'dbus.String')}}

        self.assertEqual(
            hal_data,
            {'version': '0.5.8.1',
             'devices': [expected_device_1, expected_device_2]},
            'Unexpected parsing result for <hal> data')

    def testProcessorsData(self):
        """The <processors> node is converted into a Python list.

        The list elements represent the <processor> nodes.
        """
        result, submission_id = self.runParser(self.sample_data)
        processors_data = result['hardware']['processors']
        expected_data = [
            {'id': 123,
             'name': '0',
             'properties': {'cpu_mhz': (1000.0, 'float'),
                            'flags': ([('fpu', 'str'),
                                       ('vme', 'str'),
                                       ('de', 'str')],
                                      'list'),
                            'wp': (True, 'bool')}}]
        self.assertEqual(processors_data, expected_data,
                         'Unexpected parsing result for <processors> data')
        
    def testAliasesData(self):
        """The <aliases> node is converted into a Python list.

        The list elements represent the <alias> nodes.
        """
        result, submission_id = self.runParser(self.sample_data)
        aliases_data = result['hardware']['aliases']
        expected_data = [
            {'target': 65,
             'model': 'QuickPrint 9876',
             'vendor': 'Medion'}]
        self.assertEqual(aliases_data, expected_data,
                         'Unexpected parsing result for <aliases> data')

    def testLsbReleaseData(self):
        """The <lsbrelease> node is converted into a Python dictionary.

        Each dict item represents a <property> sub-node.
        """
        result, submission_id = self.runParser(self.sample_data)
        lsbrelease_data = result['software']['lsbrelease']
        expected_data = {
            'release': ('7.04', 'str'),
            'codename': ('feisty', 'str'),
            'dict_example': (
                {'a': ('value for key a', 'str'),
                 'b': (1234, 'int')},
                'dict'),
            'distributor-id': ('Ubuntu', 'str'),
            'description': ('Ubuntu 7.04', 'str')}

        self.assertEqual(lsbrelease_data, expected_data,
                         'Unexpected parsing result for <lsbrelease> data')

    def testPackagesData(self):
        """The <packages> node is converted into a Python dictionary.

        Each dict item represents a <package> sub-node as
        (package_name, package_data), where package_data
        is a dictionary representing the <property> sub-nodes of a
        <package> node.
        """
        result, submission_id = self.runParser(self.sample_data)
        packages_data = result['software']['packages']
        expected_data = {
            'metacity': {
                'installed_size': (868352, 'int'),
                'section': ('x11', 'str'),
                'summary': ('A lightweight GTK2 based Window Manager', 'str'),
                'priority': ('optional', 'str'),
                'source': ('metacity', 'str'),
                'version': ('1:2.18.2-0ubuntu1.1', 'str'),
                'size': (429128, 'int')}}

        self.assertEqual(packages_data, expected_data,
                         'Unexpected parsing result for <packages> data')

    def testDuplicatePackage(self):
        """Two <package> nodes with the same name are rejected."""
        sample_data = self.sample_data
        duplicate_package = """
            <package name="metacity">
                <property name="whatever" type="int">1</property>
            </package>"""
        insert_at ='<packages>'
        sample_data = sample_data.replace(
            insert_at, insert_at + duplicate_package)

        result, submission_id = self.runParser(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            '<package name="metacity"> appears more than once in <packages>',
            'Detection of duplicate <package> nodes in <packages>')

    def testXorgData(self):
        """The <xorg> node is converted into a Python dictionary."""
        result, submission_id = self.runParser(self.sample_data)
        xorg_data = result['software']['xorg']
        expected_data = {
            'version': '1.3.0',
            'drivers': {
                'fglrx': {'device': 12,
                          'version': '1.23',
                          'name': 'fglrx',
                          'class': 'X.Org Video Driver'}}}

        self.assertEqual(xorg_data, expected_data,
                         'Unexpected parsing result for <xorg> data')

    def testDuplicateXorgDriver(self):
        """Two <driver> nodes in <xorg> with the same name are rejected."""
        sample_data = self.sample_data
        duplicate_driver = (
            '<driver name="fglrx" class="X.Org Video Driver"/>')
        insert_at ='<xorg version="1.3.0">'
        sample_data = sample_data.replace(
            insert_at, insert_at + duplicate_driver)

        result, submission_id = self.runParser(sample_data)
        self.assertErrorMessage(
            submission_id, result,
            '<driver name="fglrx"> appears more than once in <xorg>',
            'Detection of duplicate <driver> node in <xorg>')

    def testQuestionsData(self):
        """The <questions> node is converted into a Python dictionaryxxxxx."""
        result, submission_id = self.runParser(self.sample_data)
        questions_data = result['questions']

        expected_question_1 = {
            'name': 'detected_network_controllers',
            'plugin': 'find_network_controllers',
            'targets': [{'id': 42,
                         'drivers': ['ipw3945']},
                        {'id': 43,
                         'drivers': []}],
            'answer': {'type': 'multiple_choice',
                       'value': 'pass'},
            'answer_choices': [('fail', 'str'),
                               ('pass', 'str'),
                               ('skip', 'str')],
            'comment': 'The WLAN adapter drops the connection very '
                       'frequently.'}
        expected_question_2 = {
            'name': 'internet_ping',
            'plugin': 'internet_ping',
            'targets': [
                {'drivers': [],
                 'id': 23}],
            'answer': {
                'type': 'multiple_choice',
                'value': 'pass'},
            'answer_choices': [
                ('fail', 'str'),
                ('pass', 'str'),
                ('skip', 'str')]}
        expected_question_3 = {
            'name': 'harddisk_speed',
            'plugin': 'harddisk_speed',
            'answer': {
                'type': 'measurement',
                'value': '38.4',
                'unit': 'MB/sec'},
            'targets': [
                {'drivers': [],
                 'id': 87}],
                        'command': 'hdparm -t /dev/sda'}


        expected_data = [
            expected_question_1, expected_question_2, expected_question_3]

        self.assertEqual(questions_data, expected_data,
                         'Unexpected parsing result for <questions> data')

        


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
