#!/usr/bin/python2.4
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Create static files such as +style-slimmer.css
"""

import _pythonpath
from canonical.launchpad.scripts.runlaunchpad import make_css_slimmer

if __name__=="__main__":
    make_css_slimmer()
    
