# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This file is imported by parts/scripts/sitecustomize.py, as set up in our
# buildout.cfg (see the "initialization" key in the "[scripts]" section).

import os
from lp.services.mime import customizeMimetypes

def main():
    os.environ['STORM_CEXTENSIONS'] = '1'
    # This next line is done, via buildout, in parts/scripts/sitecustomize.py
    # (because the instance name, ${configuration:instance_name}, is dynamic).
    # os.environ.setdefault('LPCONFIG', '${configuration:instance_name}')
    customizeMimetypes()

main()
