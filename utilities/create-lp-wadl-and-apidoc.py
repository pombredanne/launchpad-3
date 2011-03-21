#! /usr/bin/python -S
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Create a static WADL file describing the current webservice.

Example:

    % LPCONFIG=development bin/py utilities/create-lp-wadl-and-apidoc.py \\
      "lib/canonical/launchpad/apidoc/wadl-development-%(version)s.xml"
"""
import _pythonpath # Not lint, actually needed.

from multiprocessing import Process
import optparse
import os
import sys

from zope.component import getUtility
from zope.pagetemplate.pagetemplatefile import PageTemplateFile

from canonical.launchpad.rest.wadl import generate_wadl, generate_html
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.systemhomes import WebServiceApplication
from lazr.restful.interfaces import IWebServiceConfiguration


def write(filename, content):
    """Replace the named file with the given string."""
    f = open(filename, 'w')
    f.write(content)
    f.close()


def make_files(path_template, directory, version, force):
    wadl_filename = path_template % {'version': version}
    # If the WADL file doesn't exist or we're being forced to regenerate
    # it...
    if (not os.path.exists(wadl_filename) or force):
        print "Writing WADL for version %s to %s." % (
            version, wadl_filename)
        write(wadl_filename, generate_wadl(version))
    else:
        print "Skipping already present WADL file:", wadl_filename

    # Now, convert the WADL into an human-readable description and
    # put the HTML in the same directory as the WADL.
    html_filename = os.path.join(directory, version + ".html")
    # If the HTML file doesn't exist or we're being forced to regenerate
    # it...
    if (not os.path.exists(html_filename) or force):
        print "Writing apidoc for version %s to %s" % (
            version, html_filename)
        write(html_filename, generate_html(wadl_filename,
            suppress_stderr=False))
    else:
        print "Skipping already present HTML file:", html_filename


def main(path_template, force=False):
    WebServiceApplication.cached_wadl = None # do not use cached file version
    execute_zcml_for_scripts()
    config = getUtility(IWebServiceConfiguration)
    directory = os.path.dirname(path_template)

    # First, create an index.html with links to all the HTML
    # documentation files we're about to generate.
    template_file = 'apidoc-index.pt'
    template = PageTemplateFile(template_file)
    index_filename = os.path.join(directory, "index.html")
    print "Writing index:", index_filename
    f = open(index_filename, 'w')
    f.write(template(config=config))

    # Start a process to build each set of WADL and HTML files.
    processes = []
    for version in config.active_versions:
        p = Process(target=make_files,
            args=(path_template, directory, version, force))
        p.start()
        processes.append(p)

    # Wait for all the subprocesses to finish.
    for p in processes:
        p.join()

    return 0


def parse_args(args):
    usage = "usage: %prog [options] PATH_TEMPLATE"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option(
        "--force", action="store_true",
        help="Replace any already-existing files.")
    parser.set_defaults(force=False)
    options, args = parser.parse_args(args)
    if len(args) != 2:
        parser.error("A path template is required.")

    return options, args


if __name__ == '__main__':
    options, args = parse_args(sys.argv)
    sys.exit(main(args[1], options.force))
