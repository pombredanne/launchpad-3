# Copyright 2008 Canonical Ltd.  All rights reserved.
"""Tests of the HWDB submissions parser."""

from cStringIO import StringIO
from datetime import datetime
import logging
import os
from unittest import TestCase, TestLoader

from lxml import etree

import pytz

from zope.testing.loghandler import Handler

from canonical.config import config
from canonical.launchpad.scripts.hwdbsubmissions import SubmissionParser
from canonical.testing import BaseLayer


class TestHWDBSubmissionParser(TestCase):
    """Tests of the HWDB submission parser."""

    layer = BaseLayer

    def setUp(self):
        """Setup the test environment."""
        self.log = logging.getLogger('test_hwdb_submission_parser')
        self.log.setLevel(logging.INFO)
        self.handler = Handler(self)
        self.handler.add(self.log.name)

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

        # time values may be given with microsecond resolution.
        time_node = self.getTimestampETreeNode('2008-01-02T03:04:05.123')
        self.assertEqual(parser._getValueAttributeAsDateTime(time_node),
                         datetime(2008, 1, 2, 3, 4, 5, 123000, tzinfo=utc_tz))

        time_node = self.getTimestampETreeNode('2008-01-02T03:04:05.123456')
        self.assertEqual(parser._getValueAttributeAsDateTime(time_node),
                         datetime(2008, 1, 2, 3, 4, 5, 123456, tzinfo=utc_tz))

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

        # "Negative" time values raise a ValueError.
        time_node = self.getTimestampETreeNode('-1000-01-02/03:04:05')
        parser.submission_key = 'testing negative time stamps'
        self.assertRaises(
            ValueError, parser._getValueAttributeAsDateTime, time_node)

        # Time values with years values with five or more digits raise
        # a ValueError.
        time_node = self.getTimestampETreeNode('12345-01-02/03:04:05')
        parser.submission_key = 'testing negative time stamps'
        self.assertRaises(
            ValueError, parser._getValueAttributeAsDateTime, time_node)

    def testSummary(self):
        node = etree.fromstring("""
            <summary>
                <live_cd value="False"/>
                <system_id value="f982bb1ab536469cebfd6eaadcea0ffc"/>
                <distribution value="Ubuntu"/>
                <distroseries value="7.04"/>
                <architecture value="amd64"/>
                <private value="False"/>
                <contactable value="False"/>
                <date_created value="2007-09-28T16:09:20.126842"/>
                <client name="hwtest" version="0.9">
                    <plugin name="architecture_info" version="1.1"/>
                    <plugin name="find_network_controllers" version="2.34"/>
                </client>
            </summary>
            """)
        parser = SubmissionParser(self.log)
        summary = parser._parseSummary(node)
        utc_tz = pytz.timezone('UTC')
        expected_data = {
            'live_cd': False,
            'system_id': 'f982bb1ab536469cebfd6eaadcea0ffc',
            'distribution': 'Ubuntu',
            'distroseries': '7.04',
            'architecture': 'amd64',
            'private': False,
            'contactable': False,
            'date_created': datetime(2007, 9, 28, 16, 9, 20, 126842,
                                     tzinfo=utc_tz),
            'client': {
                'name': 'hwtest',
                'version': '0.9',
                'plugins': [
                    {'name': 'architecture_info',
                     'version': '1.1'},
                    {'name': 'find_network_controllers',
                     'version': '2.34'}]}
            }
        self.assertEqual(
            summary, expected_data,
            'SubmissionParser.parseSummary returned an unexpected result')
        

    def _runPropertyTest(self, xml):
        parser = SubmissionParser(self.log)
        node = etree.fromstring(xml)
        return parser._parseProperty(node)

    def testBooleanPropertyTypes(self):
        """Test the parsing result for a boolean property."""
        for property_type in ('bool', 'dbus.Boolean'):
            for value in (True, False):
                xml = ('<property type="%s" name="foo">%s</property>'
                       % (property_type, value))
                result = self._runPropertyTest(xml)
                self.assertEqual(
                    result, ('foo', (value, property_type)),
                    'Invalid parsing result for boolean property type %s, '
                        'expected %s, got %s'
                    % (property_type, value, result))

    def testStringPropertyTypes(self):
        """String properties are converted into (name, (value, type))."""
        xml_template = '<property type="%s" name="foo">some text</property>'
        for property_type in ('str', 'dbus.String', 'dbus.UTF8String'):
            xml = xml_template % property_type
            result = self._runPropertyTest(xml)
            self.assertEqual(
                result, ('foo', ('some text', property_type)),
                'Invalid parsing result for string property type %s, '
                'expected "some text", got "%s"'
                    % (property_type, result))

    def testStringPropertyEncoding(self):
        """Different encodings are properly handled."""
        xml_template = '''<?xml version="1.0" encoding="%s"?>
                          <property type="str" name="foo">%s</property>'''
        euro_symbol = u'\u20ac'
        parser = SubmissionParser()
        for encoding in ('utf-8', 'iso8859-15'):
            xml = xml_template % (encoding, euro_symbol.encode(encoding))
            tree = etree.parse(StringIO(xml))
            parser.docinfo = tree.docinfo
            node = tree.getroot()
            result = parser._parseProperty(node)
            self.assertEqual(result, ('foo', (euro_symbol, 'str')),
                'Invalid parsing result for string encoding %s, '
                'expected the Euro symbol (0x20AC), got %s'
                    % (encoding, repr(result)))

    def testIntegerPropertyTypes(self):
        """Int properties are converted into (name, (value, type_string)).

        type(value) is int or long, depending on the value.
        """
        xml_template = '<property name="inttest" type="%s">123</property>'
        for property_type in ('dbus.Byte', 'dbus.Int16', 'dbus.Int32',
                              'dbus.Int64', 'dbus.UInt16', 'dbus.UInt32',
                              'dbus.UInt64', 'int', 'long'):
            xml = xml_template % property_type
            result = self._runPropertyTest(xml)
            self.assertEqual(result, ('inttest', (123, property_type)),
                             'Invalid parsing result for integer property '
                             'type %s' % property_type)
        # If the value is too large for an int, a Python long is returned.
        xml = """
            <property name="inttest" type="long">
                12345678901234567890
            </property>"""
        properties = self._runPropertyTest(xml)
        self.assertEqual(properties,
                         ('inttest', (12345678901234567890L, 'long')),
                         'Invalid parsing result for integer property with '
                             'a large value')

    def testFloatPropertyTypes(self):
        """Float properties are converted into ('name', (value, type_string)).

        type(value) is float.
        """
        xml_template = ('<property name="floattest" type="%s">'
                            '1.25</property>')
        for property_type in ('dbus.Double', 'float'):
            xml = xml_template % property_type
            result = self._runPropertyTest(xml)
            self.assertEqual(result, ('floattest', (1.25, property_type)),
                             'Invalid parsing result for float property type: '
                             '%s' % property_type)

    def testListPropertyTypes(self):
        """List properties are converted into ('name', a_list).

        a_list is a Python list, where the list elements represent the
        values of the <value> sub-nodes of the <property>.
        """
        xml_template = """
            <property name="listtest" type="%s">
                <value type="int">1</value>
                <value type="str">a</value>
                <value type="list">
                    <value type="int">2</value>
                    <value type="float">3.4</value>
                </value>
                <value type="dict">
                    <value name="one" type="int">2</value>
                    <value name="two" type="str">b</value>
                </value>
            </property>
            """
        for property_type in ('dbus.Array', 'list'):
            xml = xml_template % property_type
            result = self._runPropertyTest(xml)
            self.assertEqual(result,
                             ('listtest', ([(1, 'int'),
                                            ('a', 'str'),
                                            ([(2, 'int'),
                                              (3.4, 'float')], 'list'),
                                            ({'one': (2, 'int'),
                                              'two': ('b', 'str')}, 'dict')],
                                           property_type)),
                             'Invalid parsing result for list property: '
                             '%s' % xml)

    def testDictPropertyTypes(self):
        """Dict properties are converted into ('name', a_dict).

        a_dict is a Python dictionary, where the items represent the
        values of the <value> sub-nodes of the <property>.
        """
        xml_template = """
            <property name="dicttest" type="%s">
                <value name="one" type="int">1</value>
                <value name="two" type="str">a</value>
                <value name="three" type="list">
                    <value type="int">2</value>
                    <value type="float">3.4</value>
                </value>
                <value name="four" type="dict">
                    <value name="five" type="int">2</value>
                    <value name="six" type="str">b</value>
                </value>
            </property>
            """
        for property_type in ('dbus.Dictionary', 'dict'):
            xml = xml_template % property_type
            result = self._runPropertyTest(xml)
            self.assertEqual(
                result,
                ('dicttest', ({'one': (1, 'int'),
                               'two': ('a', 'str'),
                               'three': ([(2, 'int'),
                                          (3.4, 'float')], 'list'),
                               'four': ({'five': (2, 'int'),
                                         'six': ('b', 'str')}, 'dict')},
                              property_type)),
                'Invalid parsing result for dict property: %s' % xml)

    def testProperties(self):
        """A set of properties is converted into a dictionary."""
        node = etree.fromstring("""
            <container>
                <property name="one" type="int">1</property>
                <property name="two" type="str">a</property>
            </container>
            """)
        parser = SubmissionParser(self.log)
        result = parser._parseProperties(node)
        self.assertEqual(result,
                         {'one': (1, 'int'),
                          'two': ('a', 'str')},
                         'Invalid parsing result for a property set')

        # Duplicate property names raise a ValueError
        node = etree.fromstring("""
            <container>
                <property name="one" type="int">1</property>
                <property name="one" type="str">a</property>
            </container>
            """)
        self.assertRaises(ValueError, parser._parseProperties, node)


    def testDevice(self):
        """A device node is converted into a dictionary."""
        test = self
        def _parseProperties(self, node):
            test.assertTrue(isinstance(self, SubmissionParser))
            test.assertEqual(node.tag, 'device')
            return 'parsed properties'
        parser = SubmissionParser(self.log)
        parser._parseProperties = lambda node: _parseProperties(parser, node)

        node = etree.fromstring("""
            <device id="2" udi="/org/freedesktop/Hal/devices/acpi_CPU0"
                    parent="1">
                <property name="info.product" type="str">
                    Intel(R) Core(TM)2 CPU
                </property>
            </device>
            """)
        result = parser._parseDevice(node)
        self.assertEqual(result,
                         {'id': 2,
                          'udi': '/org/freedesktop/Hal/devices/acpi_CPU0',
                          'parent': 1,
                          'properties': 'parsed properties'},
                         'Invalid parsing result for <device> (2)')

        # the attribute "parent" may be omitted.
        node = etree.fromstring("""
            <device id="1" udi="/org/freedesktop/Hal/devices/computer">
                <property name="info.product" type="str">Computer</property>
            </device>
            """)
        result = parser._parseDevice(node)
        self.assertEqual(result,
                         {'id': 1,
                          'udi': '/org/freedesktop/Hal/devices/computer',
                          'parent': None,
                          'properties': 'parsed properties'},
                         'Invalid parsing result for <device> (1)')

    def testHal(self):
        """The <hal> node is converted into a Python dict."""
        test = self
        def _parseDevice(self, node):
            test.assertTrue(isinstance(self, SubmissionParser))
            test.assertEqual(node.tag, 'device')
            return 'parsed device node'
        parser = SubmissionParser(self.log)
        parser._parseDevice = lambda node: _parseDevice(parser, node)

        node = etree.fromstring("""
            <hal version="0.5.9.1">
                <device/>
                <device/>
            </hal>
            """)
        result = parser._parseHAL(node)
        self.assertEqual(result,
                         {'version': '0.5.9.1',
                          'devices': ['parsed device node',
                                      'parsed device node']},
                         'Invalid parsing result for <hal>')

    def testProcessors(self):
        """The <processors> node is converted into a Python list.

        The list elements represent the <processor> nodes.
        """
        test = self
        def _parseProperties(self, node):
            test.assertTrue(isinstance(self, SubmissionParser))
            test.assertEqual(node.tag, 'processor')
            return 'parsed properties'
        parser = SubmissionParser(self.log)
        parser._parseProperties = lambda node: _parseProperties(parser, node)

        node = etree.fromstring("""
            <processors>
                <processor id="123" name="0">
                    <property/>
                </processor>
                <processor id="124" name="1">
                    <property/>
                </processor>
            </processors>
            """)
        result = parser._parseProcessors(node)
        self.assertEqual(result,
                         [{'id': 123,
                           'name': '0',
                           'properties': 'parsed properties'},
                          {'id': 124,
                           'name': '1',
                           'properties': 'parsed properties'}],
                         'Invalid parsing result for <processors>')

    def testAliases(self):
        """The <aliases> node is converted into a Python list.

        The list elements represent the <alias> nodes.
        """
        parser = SubmissionParser(self.log)
        node = etree.fromstring("""
            <aliases>
                <alias target="1">
                    <vendor>Artec</vendor>
                    <model>Ultima 2000</model>
                </alias>
                <alias target="2">
                    <vendor>Medion</vendor>
                    <model>MD 4394</model>
                </alias>
            </aliases>
            """)
        result = parser._parseAliases(node)
        self.assertEqual(result,
                         [{'target': 1,
                           'vendor': 'Artec',
                           'model': 'Ultima 2000'},
                          {'target': 2,
                           'vendor': 'Medion',
                           'model': 'MD 4394'}],
                         'Invalid parsing result for <aliases>')

    def testHardware(self):
        """The <hardware> tag is converted into a dictionary."""
        test = self

        def _parseHAL(self, node):
            test.assertTrue(isinstance(self, SubmissionParser))
            test.assertEqual(node.tag, 'hal')
            return 'parsed HAL data'

        def _parseProcessors(self, node):
            test.assertTrue(isinstance(self, SubmissionParser))
            test.assertEqual(node.tag, 'processors')
            return 'parsed processor data'

        def _parseAliases(self, node):
            test.assertTrue(isinstance(self, SubmissionParser))
            test.assertEqual(node.tag, 'aliases')
            return 'parsed alias data'

        parser = SubmissionParser(self.log)
        parser._parseHAL = lambda node: _parseHAL(parser, node)
        parser._parseProcessors = lambda node: _parseProcessors(parser, node)
        parser._parseAliases = lambda node: _parseAliases(parser, node)
        parser._setHardwareSectionParsers()

        node = etree.fromstring("""
            <hardware>
                <hal/>
                <processors/>
                <aliases/>
            </hardware>
            """)
        result = parser._parseHardware(node)
        self.assertEqual(result,
                         {'hal': 'parsed HAL data',
                          'processors': 'parsed processor data',
                          'aliases': 'parsed alias data'},
                         'Invalid parsing result for <hardware>')

    def testLsbRelease(self):
        """The <lsbrelease> node is converted into a Python dictionary.

        Each dict item represents a <property> sub-node.
        """
        node = etree.fromstring("""
            <lsbrelease>
                <property name="release" type="str">
                    7.04
                </property>
                <property name="codename" type="str">
                    feisty
                </property>
                <property name="distributor-id" type="str">
                    Ubuntu
                </property>
                <property name="description" type="str">
                    Ubuntu 7.04
                </property>
            </lsbrelease>
            """)
        parser = SubmissionParser(self.log)
        result = parser._parseLSBRelease(node)
        self.assertEqual(result,
                         {'distributor-id': ('Ubuntu', 'str'),
                          'release': ('7.04', 'str'),
                          'codename': ('feisty', 'str'),
                          'description': ('Ubuntu 7.04', 'str')},
                         'Invalid parsing result for <lsbrelease>')

    def testPackages(self):
        """The <packages> node is converted into a Python dictionary.

        Each dict item represents a <package> sub-node as
        (package_name, package_data), where package_data
        is a dictionary representing the <property> sub-nodes of a
        <package> node.
        """
        node = etree.fromstring("""
            <packages>
                <package name="metacity">
                    <property name="installed_size" type="int">
                        868352
                    </property>
                    <property name="section" type="str">
                        x11
                    </property>
                    <property name="summary" type="str">
                        A lightweight GTK2 based Window Manager
                    </property>
                    <property name="priority" type="str">
                        optional
                    </property>
                    <property name="source" type="str">
                        metacity
                    </property>
                    <property name="version" type="str">
                        1:2.18.2-0ubuntu1.1
                    </property>
                    <property name="size" type="int">
                        429128
                    </property>
                </package>
            </packages>
            """)
        parser = SubmissionParser(self.log)
        result = parser._parsePackages(node)
        self.assertEqual(result,
                         {'metacity':
                          {'installed_size': (868352, 'int'),
                           'priority': ('optional', 'str'),
                           'section': ('x11', 'str'),
                           'size': (429128, 'int'),
                           'source': ('metacity', 'str'),
                           'summary':
                               ('A lightweight GTK2 based Window Manager',
                                'str'),
                           'version': ('1:2.18.2-0ubuntu1.1', 'str')}},
                         'Invalid parsing result for <packages>')

    def testDuplicatePackage(self):
        """Two <package> nodes with the same name are rejected."""
        node = etree.fromstring("""
            <packages>
                <package name="foo">
                    <property name="size" type="int">10000</property>
                </package>
                <package name="foo">
                    <property name="size" type="int">10000</property>
                </package>
            </packages>
            """)
        self.assertRaises(ValueError, SubmissionParser()._parsePackages, node)

    def testXorg(self):
        """The <xorg> node is converted into a Python dictionary."""
        node = etree.fromstring("""
            <xorg version="1.1">
                <driver name="fglrx" version="1.23"
                        class="X.Org Video Driver" device="12"/>
                <driver name="kbd" version="1.2.1"
                        class="X.Org XInput driver" device="15"/>

            </xorg>
            """)
        parser = SubmissionParser(self.log)
        result = parser._parseXOrg(node)
        self.assertEqual(result,
                         {'version': '1.1',
                         'drivers': {'fglrx': {'name': 'fglrx',
                                               'version': '1.23',
                                               'class': 'X.Org Video Driver',
                                               'device': 12},
                                     'kbd': {'name': 'kbd',
                                             'version': '1.2.1',
                                             'class': 'X.Org XInput driver',
                                             'device': 15}}},
                         'Invalid parsing result for <xorg>')

    def testDuplicateXorgDriver(self):
        """Two <driver> nodes in <xorg> with the same name are rejected."""
        node = etree.fromstring("""
            <xorg>
                <driver name="mouse" class="X.Org XInput driver"/>
                <driver name="mouse" class="X.Org XInput driver"/>
            </xorg>
            """)
        self.assertRaises(ValueError, SubmissionParser()._parseXOrg, node)

    def testSoftwareSection(self):
        """Test SubissionParser._parseSoftware

        Ensure that all sub-parsers are properly called.
        """
        test = self
        def _parseLSBRelease(self, node):
            test.assertTrue(isinstance(self, SubmissionParser))
            test.assertEqual(node.tag, 'lsbrelease')
            return 'parsed lsb release'

        def _parsePackages(self, node):
            test.assertTrue(isinstance(self, SubmissionParser))
            test.assertEqual(node.tag, 'packages')
            return 'parsed packages'

        def _parseXOrg(self, node):
            test.assertTrue(isinstance(self, SubmissionParser))
            test.assertEqual(node.tag, 'xorg')
            return 'parsed xorg'

        parser = SubmissionParser()
        parser._parseLSBRelease = lambda node: _parseLSBRelease(parser, node)
        parser._parsePackages = lambda node: _parsePackages(parser, node)
        parser._parseXOrg = lambda node: _parseXOrg(parser, node)
        parser._setSoftwareSectionParsers()

        node = etree.fromstring("""
            <software>
                <lsbrelease/>
                <packages/>
                <xorg/>
            </software>
            """)
        result = parser._parseSoftware(node)
        self.assertEqual(result,
                         {'lsbrelease': 'parsed lsb release',
                          'packages': 'parsed packages',
                          'xorg': 'parsed xorg'},
                         'Invalid parsing result for <softwar>')

    def testMultipleChoiceQuestion(self):
        """The <questions> node is converted into a Python dictionary."""
        node = etree.fromstring("""
            <questions>
                <question name="detected_network_controllers"
                          plugin="find_network_controllers">
                    <target id="42">
                        <driver>ipw3945</driver>
                    </target>
                    <target id="43"/>
                    <command/>
                    <answer type="multiple_choice">pass</answer>
                    <answer_choices>
                        <value type="str">fail</value>
                        <value type="str">pass</value>
                        <value type="str">skip</value>
                    </answer_choices>
                    <comment>
                        The WLAN adapter drops the connection very frequently.
                    </comment>
                </question>
            </questions>
            """)
        parser = SubmissionParser()
        result = parser._parseQuestions(node)
        self.assertEqual(
            result,
            [{'name': 'detected_network_controllers',
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
                         'frequently.'}],
            'Invalid parsing result for multiple choice question')
                         

    def testMeasurementQuestion(self):
        """The <questions> node is converted into a Python dictionary."""
        node = etree.fromstring("""
            <questions>
                <question name="harddisk_speed"
                          plugin="harddisk_speed">
                    <target id="87"/>
                    <command>hdparm -t /dev/sda</command>
                    <answer type="measurement" unit="MB/sec">38.4</answer>
                </question>
            </questions>
            """)
        parser = SubmissionParser()
        result = parser._parseQuestions(node)
        self.assertEqual(
            result,
            [{
              'name': 'harddisk_speed',
              'plugin': 'harddisk_speed',
              'answer': {'type': 'measurement',
                         'value': '38.4',
                         'unit': 'MB/sec'},
              'targets': [{'drivers': [],
                           'id': 87}],
              'command': 'hdparm -t /dev/sda'}],
            'Invalid parsing result for measurement question')
                         
    def testMainParser(self):
        """Test SubmissionParser.parseMainSections

        Ensure that all sub-parsers are properly called.
        """
        test = self
        def _parseSummary(self, node):
            test.assertTrue(isinstance(self, SubmissionParser))
            test.assertEqual(node.tag, 'summary')
            return 'parsed summary'

        def _parseHardware(self, node):
            test.assertTrue(isinstance(self, SubmissionParser))
            test.assertEqual(node.tag, 'hardware')
            return 'parsed hardware'

        def _parseSoftware(self, node):
            test.assertTrue(isinstance(self, SubmissionParser))
            test.assertEqual(node.tag, 'software')
            return 'parsed software'

        def _parseQuestions(self, node):
            test.assertTrue(isinstance(self, SubmissionParser))
            test.assertEqual(node.tag, 'questions')
            return 'parsed questions'

        parser = SubmissionParser(self.log)
        parser._parseSummary = lambda node: _parseSummary(parser, node)
        parser._parseHardware = lambda node: _parseHardware(parser, node)
        parser._parseSoftware = lambda node: _parseSoftware(parser, node)
        parser._parseQuestions = lambda node: _parseQuestions(parser, node)
        parser._setMainSectionParsers()

        node = etree.fromstring("""
            <system>
                <summary/>
                <hardware/>
                <software/>
                <questions/>
            </system>
            """)

        expected_data = {
            'summary': 'parsed summary',
            'hardware': 'parsed hardware',
            'software': 'parsed software',
            'questions':  'parsed questions'}

        result = parser.parseMainSections(node)
        self.assertEqual(result, expected_data,
            'SubmissionParser.parseSubmission returned an unexpected result')

    def testSubmissionParser(self):
        """Test the entire parser."""
        sample_data_path = os.path.join(
            config.root, 'lib', 'canonical', 'launchpad', 'scripts',
            'tests', 'hardwaretest.xml')
        sample_data = open(sample_data_path).read()
        parser = SubmissionParser()
        result = parser.parseSubmission(sample_data, 'parser test 1')
        self.assertNotEqual(result, None,
                            'Valid submission data rejected by '
                            'SubmissionParser.parseSubmission')

        # parseSubmission returns None, if the submitted data is not
        # well-formed XML...
        result = parser.parseSubmission(
            sample_data.replace('<summary', '<inconsitent_opening_tag'),
            'parser test 2')
        self.assertEqual(result, None,
                         'Not-well-formed XML data accepted by '
                         'SubmissionParser.parseSubmission')
        
        # ...or if RelaxNG validation fails...
        result = parser.parseSubmission(
            sample_data.replace('<summary', '<summary foo="bar"'),
            'parser test 3')
        self.assertEqual(result, None,
                         'XML data that does pass the Relax NG validation '
                         'accepted by SubmissionParser.parseSubmission')

        # ...or if the parser detects an inconsistency, like a
        # property set containing two properties with the same name.
        result = parser.parseSubmission(
            sample_data.replace(
                '<property name="info.parent"',
                """<property name="info.parent" type="dbus.String">
                       foo
                   </property>
                   <property name="info.parent"
                """,
                1),
            'parser test 4')
        self.assertEqual(result, None,
                         'XML data that does pass the Relax NG validation '
                         'accepted by SubmissionParser.parseSubmission')
        
        

def test_suite():
    return TestLoader().loadTestsFromName(__name__)
