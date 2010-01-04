#!/usr/bin/python
#
# python port of the nice maintainace-check script by  Nick Barcet
# 
# taken from:
#  https://code.edge.launchpad.net/~mvo/ubuntu-maintenance-check/python-port
# (where it will vanish once taken here)

import logging
import sys
import urllib2

from optparse import OptionParser

# germinate output base directory
BASE_URL = "http://people.canonical.com/~ubuntu-archive/germinate-output/"

# support timeframe tag used in the Packages file
SUPPORT_TAG = "Supported"

# codename of the lts releases
LTS_RELEASES = [ "dapper", "hardy", "lucid" ]

# what defines the seeds is documented in wiki.ubuntu.com/SeedManagement
SERVER_SEEDS = [ "supported-server"]
DESKTOP_SEEDS = ["ship", "supported-desktop"]
SUPPORTED_SEEDS = ["supported"]

# normal support timeframe
SUPPORT_TIMEFRAME = [
    ("18m", SUPPORTED_SEEDS)
]

# lts support timeframe
SUPPORT_TIMEFRAME_LTS = [
    ("5y", SERVER_SEEDS),
    ("3y", DESKTOP_SEEDS),
    ("18m", SUPPORTED_SEEDS),
]

def get_structure(name, version):
    """ 
    get structure file for named distro and distro version 
    (e.g. kubuntu, lucid)
    """
    f = urllib2.urlopen("%s/%s.%s/structure" % (BASE_URL, name, version))
    structure = f.readlines()
    f.close()
    return structure

def expand_seeds(structure, seedname):
    """ 
    expand seed by its dependencies using the strucure file
    returns a set() for the seed dependencies (excluding the original seedname)
    """
    seeds = []
    for line in structure:
        if line.startswith("%s:" % seedname):
            seeds += line.split(":")[1].split()
            for seed in seeds:
                seeds += expand_seeds(structure, seed)
    return set(seeds)

def get_packages_for_seeds(name, distro, seeds):
    """
    get packages for the given name (e.g. ubuntu) and distro release 
    (e.g. lucid) that are in the given list of seeds
    returns a set() of package names
    """
    pkgs_in_seeds = {}
    for bseed in seeds:
        for seed in [bseed]: #, bseed+".build-depends", bseed+".seed"]:
            pkgs_in_seeds[seed] = set()
            seedurl = "%s/%s.%s/%s" % (BASE_URL,name, distro, seed)
            logging.debug("looking for '%s'" % seedurl)
            try:
                f = urllib2.urlopen(seedurl)
                for line in f:
                    # ignore lines that are not a package name (headers etc)
                    if line[0] < 'a' or line[0] > 'z':
                        continue
                    # lines are (package,source,why,maintainer,size,inst-size)
                    if options.source_packages:
                        pkgname = line.split("|")[1]
                    else:
                        pkgname = line.split("|")[0]
                    pkgs_in_seeds[seed].add(pkgname.strip())
                f.close()
            except Exception, e:
                logging.error("seed %s failed (%s)" % (seedurl, e))
    return pkgs_in_seeds

def what_seeds(pkgname, seeds):
    in_seeds = set()
    for s in seeds:
        if pkgname in seeds[s]:
            in_seeds.add(s)
    return in_seeds

def get_packages_support_time(structure, support_timeframe_list):
    """
    input a structure file and a list of pair<timeframe, seedlist>
    return a dict of pkgnames -> support timeframe string
    """
    pkg_support_time = {}
    for (timeframe, seedlist) in support_timeframe_list:
        expanded = set()
        for s in seedlist:
            expanded.add(s)
            expanded |= expand_seeds(structure, s)
        pkgs_in_seeds = get_packages_for_seeds(name, distro, expanded)
        for seed in pkgs_in_seeds:
            for pkg in pkgs_in_seeds[seed]:
                if not pkg in pkg_support_time:
                    pkg_support_time[pkg] = timeframe
                    if options.with_seeds:
                        pkg_support_time[pkg] += " (%s)" % ", ".join(what_seeds(pkg, pkgs_in_seeds))

    return pkg_support_time

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("--with-seeds", "", default=False,
                      action="store_true", 
                      help="add seed(s) of the package that are responsible for the maintaince time")
    parser.add_option("--source-packages", "", default=False,
                      action="store_true", 
                      help="show as source pkgs")
    (options, args) = parser.parse_args()

    # init
    name = "ubuntu"
    if len(args) > 0:
        distro = args[0]
        if distro[0] < 'h':
            print "ERROR: only hardy or later is supported"
            sys.exit(1)
    else:
        distro = "lucid"
        
    # get basic structure file
    structure = get_structure(name, distro)
    
    # get dicts of pkgname -> support timeframe string
    if distro in LTS_RELEASES:
        pkg_support_time = get_packages_support_time(structure, 
                                                     SUPPORT_TIMEFRAME_LTS)
    else:
        pkg_support_time = get_packages_support_time(structure, 
                                                     SUPPORT_TIMEFRAME)
    
    # output suitable for the extra-override file
    for pkgname in sorted(pkg_support_time.keys()):
        print "%s %s %s" % (pkgname, SUPPORT_TAG, pkg_support_time[pkgname])
