import pkg_resources
import subprocess
import sys

def main():
    source = sys.argv[1]
    stylesheet = pkg_resources.resource_filename(
        'launchpadlib', 'wadl-to-refhtml.xsl')
    subprocess.call(['xsltproc', stylesheet, source])
    pkg_resources.cleanup_resources()