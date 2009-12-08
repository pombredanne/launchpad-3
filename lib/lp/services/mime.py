# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Provide the mimetypes functionality with extensions."""

__metaclass__ = type
__all__ = [
    'mimetypes'
    ]

import mimetypes

mimetypes.init()

# Add support for bz2 encodings, which is not present in python2.5.
mimetypes.encodings_map.setdefault('.bz2', 'bzip2')
mimetypes.suffix_map.setdefault('.tbz2', '.tar.bz2')
