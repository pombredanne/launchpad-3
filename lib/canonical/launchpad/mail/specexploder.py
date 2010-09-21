# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Functions dealing with extracting information from spec notifications."""

__metaclass__ = type

import re


_moin_url_re = re.compile(r'(https?://[^ \r\n]+)')

def get_spec_url_from_moin_mail(moin_text):
     """Extract a specification URL from Moin change notification."""
     match = _moin_url_re.search(moin_text)
     if match:
          return match.group(1)
     else:
          return None
