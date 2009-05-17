# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, 'lib'
    ))

# Enable Storm's C extensions
os.environ['STORM_CEXTENSIONS'] = '1'
