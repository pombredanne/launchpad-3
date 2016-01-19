# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import re


cveseq_regexp = r'(19|20)\d{2}\-\d{4,}'
CVEREF_PATTERN = re.compile(r'(CVE|CAN)-(%s)' % cveseq_regexp)


def valid_cve(name):
    """Validate CVE identification.

    Until 2014 CVE sequence had to be smaller 4 digits (<= 9999):

    >>> valid_cve('1999-1234')
    True
    >>> valid_cve('2014-9999')
    True

    And leading zeros were required for sequence in [1-999]:

    >>> valid_cve('2014-999')
    False
    >>> valid_cve('2014-0999')
    True

    From 2014 and on, sequence can be any sequence of digits greater or
    equal to 4 digits:

    >>> valid_cve('2014-19999')
    True
    >>> valid_cve('2014-99999999')
    True
    """
    pat = r"^%s" % cveseq_regexp
    if re.match(pat, name):
        return True
    return False
