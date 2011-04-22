#! /usr/bin/python -S

# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Check that everything is alright in security.cfg

Usage hint:

% utilities/audit-security.py
"""
__metatype__ = type

import os
import sys
import re

from collections import defaultdict

TEST_DATA = """
[good]
public.foo = SELECT
public.bar = SELECT, INSERT
public.baz = SELECT

[bad]
public.foo = SELECT
public.bar = SELECT, INSERT
public.bar = SELECT
public.baz = SELECT
"""

BRANCH_ROOT = os.path.split(
    os.path.dirname(os.path.abspath(__file__)))[0]
SECURITY_PATH = os.path.join(
    BRANCH_ROOT, 'database', 'schema', 'security.cfg')


def strip(data):
    data = [d.strip() for d in data]
    return [d for d in data if not (d.startswith('#') or d == '')]


class SettingsAuditor:
    """Reads the security.cfg file and collects errors.

    We can't just use ConfigParser for this case, as we're doing our own
    specialized parsing--not interpreting the settings, but verifying."""

    section_regex = re.compile(r'\[.*\]')

    def __init__(self):
        self.errors = {}
        self.current_section = ''
        self.observed_settings = defaultdict(lambda: 0)

    def _get_section_name(self, line):
        if line.strip().startswith('['):
            return self.section_regex.match(line).group()
        else:
            return None

    def _get_setting(self, line):
        return line.split()[0]

    def start_new_section(self, new_section):
        for k in self.observed_settings.keys():
            if self.observed_settings[k] == 1:
                self.observed_settings.pop(k)
        duplicated_settings = self.observed_settings.keys()
        if len(duplicated_settings) > 0:
            self.errors[self.current_section] = self.observed_settings.keys()
        self.observed_settings = defaultdict(lambda: 0)
        self.current_section = new_section

    def readline(self, line):
        new_section = self._get_section_name(line)
        if new_section is not None:
            self.start_new_section(new_section)
        else:
            setting = self._get_setting(line)
            self.observed_settings[setting] += 1

    def print_error_data(self):
        print "The following errors were found in security.cfg"
        print "-----------------------------------------------"
        for section in self.errors.keys():
            print "In section: %s" % section
            for setting in self.errors[section]:
                print '\tDuplicate setting found: %s' % setting


def main(test=False):
    # This is a cheap hack to allow testing in the testrunner.
    if test:
        data = TEST_DATA.split('\n')
    else:
        data = file(SECURITY_PATH).readlines()
    data = strip(data)
    auditor = SettingsAuditor()
    for line in data:
        auditor.readline(line)
    auditor.start_new_section('')
    auditor.print_error_data()

if __name__ == '__main__':
    # smoketest check is a cheap hack to test the utility in the testrunner.
    try:
        test = sys.argv[1] == 'smoketest'
    except IndexError:
        test = False
    main(test=test)
