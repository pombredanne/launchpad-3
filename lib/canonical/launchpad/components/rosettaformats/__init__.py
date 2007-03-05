# Copyright 2006 Canonical Ltd.  All rights reserved.

"""
Unified support for different Rosetta import and export formats.
"""
__metaclass__ = type

__all__ = [
    'PoSupport',
    'MozillaSupport'
    ]

from canonical.launchpad.components.rosettaformats.gettext_po import PoSupport
from canonical.launchpad.components.rosettaformats.mozilla_xpi import  (
    MozillaSupport )
