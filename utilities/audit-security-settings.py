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

from lp.scripts.utilities import SettingsAuditor


BRANCH_ROOT = os.path.split(
    os.path.dirname(os.path.abspath(__file__)))[0]
SECURITY_PATH = os.path.join(
    BRANCH_ROOT, 'database', 'schema', 'security.cfg')

def main(test=False):
    # This is a cheap hack to allow testing in the testrunner.
    data = file(SECURITY_PATH).readlines()
    data = strip(data)
    auditor = SettingsAuditor()
    auditor.audit(data)
    print auditor.error_data

if __name__ == '__main__':
    # smoketest check is a cheap hack to test the utility in the testrunner.
    main()
