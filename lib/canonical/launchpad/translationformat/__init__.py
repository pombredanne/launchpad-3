# Copyright 2006-2007 Canonical Ltd.  All rights reserved.
"""
Unified support for different translation import and export formats.
"""
__metaclass__ = type

from canonical.launchpad.translationformat.translation_import import *

# XXX CarlosPerelloMarin 20070609: POHeader still needs to be used outside the
# abstraction layer until we get rid of IPOFile.header which is .po specific.
# See bug #120192 for more information.
from canonical.launchpad.translationformat.gettext_po_parser import POHeader
