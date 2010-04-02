#!/usr/bin/python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os

archtag = os.popen("dpkg --print-architecture").read().strip()

from optparse import OptionParser

parser = OptionParser()
parser.add_option("-n", "--name", dest="NAME",
                  help="the name for this buildd",
                  metavar="NAME",
                  default="default")

parser.add_option("-H", "--host", dest="BINDHOST",
                  help="the IP/host this buildd binds to",
                  metavar="HOSTNAME",
                  default="localhost")

parser.add_option("-p", "--port", dest="BINDPORT",
                  help="the port this buildd binds to",
                  metavar="PORT",
                  default="8221")

parser.add_option("-a", "--arch", dest="ARCHTAG",
                  help="the arch tag this buildd claims",
                  metavar="ARCHTAG",
                  default=archtag)

parser.add_option("-t", "--template", dest="TEMPLATE",
                  help="the template file to use",
                  metavar="FILE",
                  default="/usr/share/launchpad-buildd/template-buildd-slave.conf")

(options, args) = parser.parse_args()

template = open(options.TEMPLATE, "r").read()

replacements = {
    "@NAME@": options.NAME,
    "@BINDHOST@": options.BINDHOST,
    "@ARCHTAG@": options.ARCHTAG,
    "@BINDPORT@": options.BINDPORT,
    }

for replacement_key in replacements:
    template = template.replace(replacement_key,
                                replacements[replacement_key])

print template

