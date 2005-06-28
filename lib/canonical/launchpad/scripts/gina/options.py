# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

"""Gina Options.

Handle the avaiable gina options.
"""

from optparse import OptionParser

parser = OptionParser()
parser.add_option("-r","--root", dest="package_root",
                  help="read archive from ROOT",
                  metavar="ROOT",
                  default="/srv/archive.ubuntu.com/ubuntu/")

parser.add_option("-k","--keyrings", dest="keyrings_root",
                  help="read keyrings from KEYRINGS",
                  metavar="KEYRINGS",
                  default="keyrings/")

parser.add_option("-D","--distro", dest="distro",
                  help="import into DISTRO",
                  metavar="DISTRO",
                  default="ubuntu")

parser.add_option("-d","--distrorelease", dest="distrorelease",
                  help="import into DISTRORELEASE",
                  metavar="DISTRORELEASE",
                  default="warty")

parser.add_option("-c","--components", dest="components",
                  help="import COMPONENTS components",
                  metavar="COMPONENTS",
                  default="main,restricted,universe")

parser.add_option("-a", "--arch", dest="archs",
                  help="import ARCHS architectures",
                  metavar="ARCHS",
                  default="i386,powerpc,amd64")

parser.add_option("-p", "--pocket", dest="pocket",
                  help="The pocket where the files should be published",
                  metavar="POCKET",
                  default="plain")

parser.add_option("-P", "--pocketrelease", dest="pocket_distrorelease",
                  help=("The distro release to here the import should go"
                        "Useful when used with --pocket option"),
                  metavar="POCKET_RELEASE",
                  default=None)

parser.add_option("-K", "--katie", dest="katie",
                  help="use KTDB as the katie database for DISTRO",
                  metavar="KTDB",
                  default=None)

parser.add_option("-R", "--run", dest="run",
                  help="actually do the run",
                  default=False, action='store_true')

parser.add_option("-n", "--dry-run", dest="dry_run",
                  help="don't commit changes to database",
                  default=False, action='store_true')

parser.add_option("-s", "--source-only", dest="source_only",
                  help="Import only Source Packages",
                  default=False, action='store_true')

parser.add_option("-S", "--spnames-only", dest="spnames_only",
                  help="Import only Source Package Names",
                  default=False, action='store_true')

(options,args) = parser.parse_args()
