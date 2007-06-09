#!/usr/bin/python2.4
"""
Create static files such as +style-slimmer.css
"""

import os
import contrib.slimmer

inputfile = os.path.join(os.path.abspath(''), 
    'lib/canonical/launchpad/icing/style.css')
outputfile = os.path.join(os.path.abspath(''), 
    'lib/canonical/launchpad/icing/+style-slimmer.css')

cssdata = open(inputfile, 'rb').read()
slimmed = contrib.slimmer.slimmer(cssdata, 'css')
open(outputfile, 'w').write(slimmed)
