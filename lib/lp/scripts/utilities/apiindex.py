# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A script to build reference html from wadl.

Uses an xsl from the launchpadlib package."""

__metaclass__ = type
__all__ = ['main']


import pkg_resources
import subprocess
import sys

def main():
    source = sys.argv[1]
    stylesheet = pkg_resources.resource_filename(
        'launchpadlib', 'wadl-to-refhtml.xsl')
    subprocess.call(['xsltproc', stylesheet, source])
    pkg_resources.cleanup_resources()
