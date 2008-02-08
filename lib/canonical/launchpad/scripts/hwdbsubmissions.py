# Copyright 2007, 2008 Canonical Ltd.  All rights reserved.

"""Parse Hardware Database submissions.

Base classes, intended to be used both for the commercial certification
data and for the community test submissions.
"""


__all__ = ['SubmissionParser']


from cStringIO import StringIO
from datetime import datetime, timedelta
from logging import getLogger
from lxml import etree
import os, pytz, re

from canonical.config import config


_relax_ng_files = {
    '1.0': 'hardware-1_0.rng', }

_time_regex = re.compile(
    r'^(\d\d\d\d)-(\d\d)-(\d\d)'
     'T(\d\d):(\d\d):(\d\d)(\.(\d{0,6}))?'
     '((([-+])(\d\d):(\d\d))|Z)?$')


class SubmissionParser:
    """A Parser for the submissions to the hardware database."""

    def __init__(self, logger=None):
        if logger is None:
            logger = getLogger()
        self.logger = logger
        self.doc_parser = etree.XMLParser(remove_comments=True)

        self.validator = {}
        directory = os.path.join(config.root, 'lib', 'canonical',
                                 'launchpad', 'scripts')
        for version, relax_ng_filename in _relax_ng_files.items():
            path = os.path.join(directory, relax_ng_filename)
            relax_ng_doc = etree.parse(path)
            self.validator[version] = etree.RelaxNG(relax_ng_doc)

    def _logError(self, message, submission_key):
        self.logger.error(
            'Parsing submission %s: %s' % (submission_key, message))

    def _getValidatedEtree(self, submission, submission_key):
        """Create an etree doc from the XML string submission and validate it.

        :return: an `lxml.etree` instance representation of a valid
            submission or None for invalid submissions.
        """
        try:
            tree = etree.parse(StringIO(submission), parser=self.doc_parser)
        except etree.XMLSyntaxError, error_value:
            self._logError(error_value, submission_key)
            return None
        self.docinfo = tree.docinfo

        submission_doc = tree.getroot()
        if submission_doc.tag != 'system':
            self._logError("root node is not '<system>'", submission_key)
            return None
        version = submission_doc.attrib.get('version', None)
        if not version in self.validator.keys():
            self._logError(
                'invalid submission format version: %s' % repr(version),
                submission_key)
            return None
        self.submission_format_version = version

        validator = self.validator[version]
        if not validator(tree):
            self._logError(
                'Relax NG validation failed.\n%s' % validator.error_log,
                submission_key)
            return None
        return submission_doc

    def _getValueAttributeAsBoolean(self, node):
        """Return the value of the attribute "value" as a boolean."""
        value = node.attrib['value']
        # Paranoia check: The Relax NG validation already ensures that the
        # attribute value is either 'True' or 'False'.
        assert value in ('True', 'False'), (
            'Parsing submission %s: Boolean value for attribute "value" '
            'expected in tag <%s>' % (self.submission_key, node.tag))
        return value == 'True'

    def _getValueAttributeAsString(self, node):
        """Return the value of the attribute "value".

        """
        # The Relax NG validation ensures that the attribute exists.
        return node.attrib['value']

    def _getValueAttributeAsDateTime(self, time_node):
        """Convert a "value" attribute into a datetime object.

        The Relax NG validation must ensure that text contains a valid
        date and time value in the form yyyy-mm-ddThh:mm:ss.ffffff,
        optionally followed by timezone data in the form 'Z' (meaning UTC)
        or +hh:mm or -hh:mm.
        """
        time_text = time_node.get('value')

        # we cannot use time.strptime: this function accepts neither fractions
        # of a second nor a time zone given e.g. as '+02:30'.
        mo = _time_regex.search(time_text)

        # Paranoia check: _time_regex should match for all datetime strings
        # that passed the Relax NG validation.
        assert mo is not None, (
            'Parsing submission %s: Invald datetime string: %s'
            % (self.submission_key, time_text))

        (year, month, day, hour, minute, second, dot_second_fraction,
         second_fraction, tz1, tz2, tz_sign, tz_hour, tz_minute) = mo.groups()

        year = int(year)
        month = int(month)
        day = int(day)
        hour = int(hour)
        minute = int(minute)
        second = int(second)
        if second_fraction is not None:
            second_fraction = int(second_fraction)
        else:
            second_fraction = 0

        # The Relax NG validator accepts leap seconds, but the datetime
        # constructor rejects them. The time values submitted by the HWDB
        # client are not necessarily very precise, hence we can round down
        # to 59.999999 seconds without losing any real precision.
        if second > 59:
            second = 59
            second_fraction = 999999

        timestamp = datetime(year, month, day, hour, minute, second,
                             second_fraction, tzinfo=pytz.timezone('utc'))
        if tz_sign in ('-', '+'):
            delta = timedelta(hours=int(tz_hour), minutes=int(tz_minute))
            if tz_sign == '-':
                timestamp = timestamp + delta
            else:
                timestamp = timestamp - delta
        return timestamp

    def _getClientData(self, client_node):
        """Parse the <client> node in the <summary> section.

        :return: A dictionary with keys 'name', 'version', 'plugins'.
                 Name and version describe the the client program that
                 produced the submission. Pugins is a list with one
                 entry per client plugin; each entry is dictionary with
                 the keys 'name' and 'version'.
        """
        result = {'name': client_node.get('name'),
                  'version': client_node.get('version')}
        plugins = result['plugins'] = []
        for node in client_node.getchildren():
            # Ensured by the Relax NG validation: The only allowed sub-tag
            # of <client> is <plugin>, which has the attributes 'name' and
            # 'version'.
            plugins.append({'name': node.get('name'),
                            'version': node.get('version')})
        return result

    _parse_summary_section = {
        'live_cd': _getValueAttributeAsBoolean,
        'system_id': _getValueAttributeAsString,
        'distribution': _getValueAttributeAsString,
        'distroseries': _getValueAttributeAsString,
        'architecture': _getValueAttributeAsString,
        'private': _getValueAttributeAsBoolean,
        'contactable': _getValueAttributeAsBoolean,
        'date_created': _getValueAttributeAsDateTime,
        'client': _getClientData,
        }

    def _parseSummary(self, summary_node):
        """Parse the <summary> part of a submission.

        :return: A dictionary with the keys 'live_cd', 'system_id',
                 'distribution', 'distroseries', 'architecture',
                 'private', 'contactable', 'date_created', 'client'.
                 See the sample XML file tests/hardwaretest.xml for
                 detailed description of the values.
        """
        summary = {}
        # The Relax NG validation ensures that we have exactly those
        # sub-nodes that are listed in _parse_summary_section.
        for node in summary_node.getchildren():
            parser = self._parse_summary_section[node.tag]
            summary[node.tag] = parser(self, node)
        return summary

    def _getValueAndType(self, node):
        """Return (value, type) of a <property> or <value> node."""
        type_ = node.get('type')
        if type_ in ('dbus.Boolean', 'bool'):
            value = node.text.strip()
            # Pure paranoia: The Relax NG validation ensures that <property>
            # and <value> tags have only the allowed values.
            assert value in ('True', 'False'), (
                'Parsing submission %s: Invalid bool value for <property> or '
                    '<value>: %s' % (self.submission_key, repr(value)))
            return (value == 'True', type_)
        elif type_ in ('str', 'dbus.String', 'dbus.UTF8String'):
            encoding = self.docinfo.encoding
            if encoding is None:
                encoding = 'ascii'
            return (node.text.strip().decode(encoding), type_)
        elif type_ in ('dbus.Byte', 'dbus.Int16', 'dbus.Int32', 'dbus.Int64',
                       'dbus.UInt16', 'dbus.UInt32', 'dbus.UInt64', 'int',
                       'long'):
            value = node.text.strip()
            return (int(value), type_)
        elif type_ in ('dbus.Double', 'float'):
            value = node.text.strip()
            return (float(value), type_)
        elif type_ in ('dbus.Array', 'list'):
            value = []
            for sub_node in node.getchildren():
                value.append(self._getValueAndType(sub_node))
            return (value, type_)
        elif type_ in ('dbus.Dictionary', 'dict'):
            value = {}
            for sub_node in node.getchildren():
                value[sub_node.get('name')] = self._getValueAndType(sub_node)
            return (value, type_)
        else:
            # This should not happen: The Relax NG validation ensures
            # that we have only those values for type_ that appear in
            # the if/elif expressions above.
            raise AssertionError(
                'Parsing submission %s: Unexpected <property> or <value> '
                    'type: %s' % type_)

    def _parseProperty(self, property_node):
        """Parse a <property> node.

        :return: (name, (value, type)) of a property.
        """
        property_name = property_node.get('name')
        return (property_node.get('name'),
                self._getValueAndType(property_node))

    def _parseProperties(self, properties_node):
        """Parse <property> sub-nodes of properties_node.

        :return: A dictionary, where each key is the name of a property;
                 the values are the tuples (value, type) of a property.
        """
        properties = {}
        for property_node in properties_node.getchildren():
            # Paranoia check: The Relax NG schema ensures that a node
            # with <property> sub-nodes has no other sub-nodes
            assert property_node.tag == 'property', (
            'Parsing submission %s: Found <%s> node, expected <property>'
                % (self.submission_key, property_node.tag))
            property_name, property_value = self._parseProperty(property_node)
            if property_name in properties.keys():
                raise ValueError(
                    '<property name="%s"> found more than once in <%s>'
                    % (property_name, properties_node.tag))
            properties[property_name] = property_value
        return properties

    def _parseDevice(self, device_node):
        """Parse a HAL <device> node.

        :return: A dictionary d with the keys 'id', 'udi', 'parent',
                 'properties'. d['id'] is an ID of the device d['udi']
                 is the HAL UDI of the device; d['properties'] is a
                 dictionary with the properties of the device (see
                 _parseProperties for details).
        """
        device_data = {'id': int(device_node.get('id')),
                       'udi': device_node.get('udi'),
                       'parent': device_node.get('parent', None)}
        device_data['properties'] = self._parseProperties(device_node)
        return device_data
    
    def _parseHAL(self, hal_node):
        """Parse the <hal> section of a submission.

        :return: A list, where each entry is the result of a _parseDevice
                 call.
        """
        # The Relax NG validation ensures that <hal> has the attribute
        # "version"
        hal_data = {'version': hal_node.get('version')}
        hal_data['devices'] = devices = []
        for device_node in hal_node.getchildren():
            # Pure paranoia: The Relax NG validation ensures already
            # that we have only <device> tags within <hal>
            assert device_node.tag == 'device', (
                'Parsing submission %s: Unexpected tag <%s> in <hal>'
                % (self.submission_key, device_node.tag))
            devices.append(self._parseDevice(device_node))
        return hal_data

    def _parseProcessors(self, processors_node):
        """Parse the <processors> node.

        :return: A list of dictionaries, where each dictionary d contains
                 the data of a <processor> node. The dictionary keys are
                 'id', 'name', 'properties'. d['id'] is an ID of a
                 <processor> node, d['name'] its name, and d['properties']
                 contains the properties of a processor (see
                 _parseProperties for details).
        """
        result = []
        for processor_node in processors_node.getchildren():
            # Pure paranoia: The Relax NG valiation ensures already
            # the we have only <processor> as sub-tags of <processors>.
            assert processor_node.tag == 'processor', (
                'Parsing submission %s: Unexpected tag <%s> in <processors>'
                   % (self.submission_key, processors_node.tag))
            processor = {}
            processor['id'] = int(processor_node.get('id'))
            processor['name'] = processor_node.get('name')
            processor['properties'] = self._parseProperties(processor_node)
            result.append(processor)
        return result

    def _parseAliases(self, aliases_node):
        """Parse the <aliases> node.

        :return: A list of dictionaries, where each dictionary d has the
                 keys 'id', 'vendor', 'model'. d['id'] is the ID of a
                 HAL device; d['vendor'] is an alternative vendor name of
                 the device; d['model'] is an alternative model name.

                 See tests/hardwaretest.xml more more details.
        """
        aliases = []
        for alias_node in aliases_node.getchildren():
            # Pure paranoia: The Relax NG valiation ensures already
            # the we have only <alias> tags within <aliases>
            assert alias_node.tag == 'alias', (
                'Parsing submission %s: Unexpected tag <%s> in <aliases>'
                    % (self.submission_key, alias_node.tag))
            alias = {'target': int(alias_node.get('target'))}
            for sub_node in alias_node.getchildren():
                # The Relax NG svalidation ensures that we have exactly
                # two subnodes: <vendor> and <model>
                alias[sub_node.tag] = sub_node.text.strip()
            aliases.append(alias)
        return aliases

    _parse_hardware_section = {
        'hal': _parseHAL,
        'processors': _parseProcessors,
        'aliases': _parseAliases}

    def _parseHardware(self, hardware_node):
        """Parse the <hardware> part of a submission.

        :return: A dictionary with the keys 'hal', 'processors', 'aliases',
                 where the values are the parsing results of _parseHAL,
                 _parseProcessors, _parseAliases.
        """
        hardware_data = {}
        for node in hardware_node.getchildren():
            parser = self._parse_hardware_section[node.tag]
            result = parser(self, node)
            hardware_data[node.tag] = result
        return hardware_data

    def _parseLSBRelease(self, lsb_node):
        """Parse the <lsb_release> part of a submission.

        :return: A dictionary with the content of the <properta> nodes
                 within the <lsb> node. See tests/hardwaretest.xml for
                 details.
        """
        return self._parseProperties(lsb_node)

    def _parsePackages(self, packages_node):
        """Parse the <packages> part of a submission.

        :return: A dictionary with one entry per <package> sub-node.
                 The key is the package name, the value a dictionary
                 containing the content of the <property> nodes within
                 <package>. See tests/hardwaretest.xml for more details.
        """
        packages = {}
        for package_node in packages_node.getchildren():
            # Pure paranoia: The Relax NG validation ensures already
            # that we have only <package> tags within <packages>.
            assert package_node.tag == 'package', (
                'Parsing submission %s: Unexpected tag <%s> in <packages>'
                % (self.submission_key, package_node.tag))
            package_name = package_node.get('name')
            if package_name in packages.keys():
                raise ValueError(
                    '<package name="%s"> appears more than once in <packages>'
                    % package_name)
            packages[package_name] = self._parseProperties(package_node)
        return packages

    def _parseXOrg(self, xorg_node):
        """Parse the <xorg> part of a submission.

        :return: A dictionary with the keys 'version' and 'drivers'.
                 d['version'] is the xorg version; d['drivers'] is
                 a dictionary with one entry for each <driver> sub-node,
                 where the key is the driver name, the value is a dictionary
                 containing the attributes of the <driver> node. See
                 tests/hardwaretest.xml for more details.
        """
        xorg_data = {'version': xorg_node.get('version')}
        xorg_data['drivers'] = xorg_drivers = {}
        for driver_node in xorg_node.getchildren():
            # Pure paranoia: The Relax NG validation ensures already
            # that we have only <driver> tags within <xorg>.
            assert driver_node.tag == 'driver', (
                'Parsing submission %s: Unexpected tag <%s> in <xorg>'
                    % (self.submission_key, driver_node.tag))
            driver_info = dict(driver_node.attrib)
            if driver_info.has_key('device'):
                # The Relax NG validation ensures that driver_info['device']
                # consists of only digits, if present.
                driver_info['device'] = int(driver_info['device'])
            driver_name = driver_info['name']
            if driver_name in xorg_drivers.keys():
                raise ValueError(
                    '<driver name="%s"> appears more than once in <xorg>'
                    % driver_name)
            xorg_drivers[driver_name] = driver_info
        return xorg_data

    _parse_software_section = {
        'lsbrelease': _parseLSBRelease,
        'packages': _parsePackages,
        'xorg': _parseXOrg}

    def _parseSoftware(self, software_node):
        """Parse the <software> section of a submission.

        :return: A dictionary with the keys 'lsbrelease', 'packages',
                 'xorg', containing the parsing results of the respective
                 sub-nodes. The key 'lsbrelease' exists always; 'xorg'
                 and 'packages' are optional. See _parseLSBRelease,
                 _parsePackages, _parseXOrg for more details.
        """
        software_data = {}
        for node in software_node.getchildren():
            parser = self._parse_software_section[node.tag]
            result = parser(self, node)
            software_data[node.tag] = result
        return software_data

    def _parseQuestions(self, questions_node):
        """Parse the <questions> part of a submission.

        :return: A list, where each entry is a dictionary containing
                 the parsing result of the <question> sub-nodes.

                 Content of a list entry d (see tests/hardwaretest.xml
                 for a more detailed description):
                 d['name']:
                        The name of a question. (Always present)
                 d['plugin']:
                        The name of the client plugin which is
                        "responsible" for the question. (Optional)
                 d['targets']:
                        A list, where each entry is a dicitionary
                        describing a target device for this question.
                        This list is always present, but may be empty.

                        The contents of each list entry t is:

                        t['id']:
                                The ID of a HAL <device> node of a
                                target device.
                        t['drivers']:
                                A list of driver names, possibly empty.
                 d['answer']:
                        The answer to this question. The value is a
                        dictionary a:
                        a['value']:
                                The value of the answer. (Always present)

                                For questions of type muliple_choice,
                                the value should match one of the
                                entries of the answer_choices list,

                                For questions of type measurement, the
                                value is a numerical value.
                        a['type']:
                                This is either 'multiple_choice' or
                                'measurement'. (Always present)
                        a['unit']:
                                The unit of a measurement value.
                                (Optional)
                 d['answer_choices']:
                        A list of choices from which the user can select
                        an answer. This list is always present, but should
                        be empty for questions of type measurement.
                 d['command']:
                        The command line of a test script which was
                        run for this question. (Optional)
                 d['comment']:
                        A comment the user has typed when running the
                        client. (Optional)

                 A consistency check of the content of d is done in
                 method _checkSubmissionConsistency.
        """
        questions = []
        for question_node in questions_node.getchildren():
            # Pure paranoia: The Relax NG validation ensures already
            # that we have only <driver> tags within <xorg>
            assert question_node.tag == 'question', (
                'Parsing submission %s: Unexpected tag <%s> in <questions>'
                % (self.submission_key, question_node.tag))
            question = {'name': question_node.get('name')}
            plugin = question_node.get('plugin', None)
            if plugin is not None:
                question['plugin'] = plugin
            question['targets'] = targets = []
            answer_choices = []

            for sub_node in question_node.getchildren():
                sub_tag = sub_node.tag
                if sub_tag == 'answer':
                    question['answer'] = answer = {}
                    answer['type'] = sub_node.get('type')
                    if answer['type'] == 'multiple_choice':
                        question['answer_choices'] = answer_choices
                    unit = sub_node.get('unit', None)
                    if unit is not None:
                        answer['unit'] = unit
                    answer['value'] = sub_node.text.strip()
                elif sub_tag == 'answer_choices':
                    for value_node in sub_node.getchildren():
                        answer_choices.append(
                            self._getValueAndType(value_node))
                elif sub_tag == 'target':
                    # The Relax NG schema ensures that the attribute
                    # id exists and that it is an integer
                    target = {'id': int(sub_node.get('id'))}
                    target['drivers'] = drivers = []
                    for driver_node in sub_node.getchildren():
                        drivers.append(driver_node.text.strip())
                    targets.append(target)
                elif sub_tag in('comment', 'command'):
                    data = sub_node.text
                    if data is not None:
                        question[sub_tag] = data.strip()
                else:
                    # This should not happen: The Relax NG validation
                    # ensures that we have only those tags which appear
                    # in the if/elif expressions.
                    raise AssertionError(
                        'Parsing submission %s: Unexpected node <%s> in '
                        '<question>' % (self.submission_key, sub_tag))
            questions.append(question)
        return questions

    _parse_system = {
        'summary': _parseSummary,
        'hardware': _parseHardware,
        'software': _parseSoftware,
        'questions': _parseQuestions}

    def parseSubmission(self, submission, submission_key):
        """Parse the data of a HWDB submission.

        :return: A dictionary with the keys 'summary', 'hardware',
                 'software', 'questions'. See _parseSummary,
                 _parseHardware, _parseSoftware, _parseQuestions for
                 the content.
        """
        self.submission_key = submission_key
        submission_doc  = self._getValidatedEtree(submission, submission_key)
        if submission_doc is None:
            return None
        submission_data = {}

        # The RelaxNG validation ensures that submission_doc has exactly
        # four sub-nodes and that the names of the sub-nodes appear in the
        # keys of self._parser_system_tags.
        try:
            for node in submission_doc.getchildren():
                parser = self._parse_system[node.tag]
                submission_data[node.tag] = parser(self, node)
        except ValueError, value:
            self._logError(value, submission_key)
            return None
        return submission_data
