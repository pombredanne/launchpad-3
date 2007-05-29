#!/usr/bin/python2.4

# "Sync" a source package by generating an upload
# Copyright (C) 2005, 2006  Canonical Software Ltd. <james.troup@canonical.com>

################################################################################

# This is a straight port of the original dak 'josie' tool to soyuz.
# Long term once soyuz is monitoring other archives regularly, syncing
# will become a matter of simply 'publishing' source from Debian
# unstable wherever) into Ubuntu dapper and the whole fake upload
# trick can go away.

################################################################################

import commands
import errno
import optparse
import os
import re
import shutil
import stat
import string
import tempfile
import time
import urllib
import apt_pkg

import _pythonpath

from zope.component import getUtility

from canonical.database.sqlbase import cursor
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts,logger, logger_options)
from canonical.launchpad.interfaces import (
    IDistributionSet, IPersonSet)
from canonical.librarian.client import LibrarianClient
from canonical.lp import (dbschema, initZopeless)
from contrib.glock import GlobalLock
from canonical.launchpad.scripts.ftpmaster import (
    SyncSource, SyncSourceError)

import dak_utils

################################################################################

reject_message = ""
re_strip_revision = re.compile(r"-([^-]+)$")
re_changelog_header = re.compile(r"^\S+ \((?P<version>.*)\) .*;.*urgency=(?P<urgency>\w+).*")
re_closes = re.compile(r"closes:\s*(?:bug)?\#?\s?\d+(?:,\s*(?:bug)?\#?\s?\d+)*", re.I)
re_bug_numbers = re.compile(r"\#?\s?(\d+)")

################################################################################

Blacklisted = None
Library = None
Lock = None
Log = None
Options = None

################################################################################

origins = {
    "debian": { "name": "Debian",
                "url": "http://ftp.debian.org/debian/",
                "default suite": "unstable",
                "default component": "main",
                "dsc": "must be signed and valid"
              },
    "security": { "name": "Security",
                "url": "http://security.debian.org/debian-security/",
                "default suite": "sarge/updates",
                "default component": "main",
                "dsc": "must be signed and valid"
              },
    "incoming": { "name": "Debian",
                "url": "http://incoming.debian.org/",
                "default suite": "incoming",
                "default component": "main",
                "dsc": "must be signed and valid"
              },
    "blackdown": { "name": "Blackdown",
                   "url": "http://ftp.gwdg.de/pub/languages/java/linux/debian/",
                   "default suite": "unstable",
                   "default component": "non-free",
                   "dsc": "must be signed and valid"
                   },
    "marillat": { "name": "Marillat",
                  "url": "ftp://ftp.nerim.net/debian-marillat/",
                  "default suite": "unstable",
                  "default component": "main",
                  "dsc": "can be unsigned"
                },
    "mythtv": { "name": "MythTV",
                "url": "http://dijkstra.csh.rit.edu/~mdz/debian/",
                "default suite": "unstable",
                "default component": "mythtv",
                "dsc": "can be unsigned"
                },
    "xfce": { "name": "XFCE",
              "url": "http://www.os-works.com/debian/",
              "default suite": "testing",
              "default component": "main",
              "dsc": "must be signed and valid"
              },

####################################

"apt.logreport.org-pub-debian": { "name": "apt.logreport.org-pub-debian",
        "url": "http://apt.logreport.org/pub/debian/",
        "default suite": "local",
        "default component": "contrib",
        "dsc": "can be unsigned"
},

    "apt.pgpackages.org-debian": { "name": "apt.pgpackages.org-debian",
        "url": "http://apt.pgpackages.org/debian/",
        "default suite": "sid",
        "default component": "main",
        "dsc": "can be unsigned"
    },

    "apt.pgpackages.org-debian": { "name": "apt.pgpackages.org-debian",
        "url": "http://apt.pgpackages.org/debian/",
        "default suite": "sid",
        "default component": "contrib",
        "dsc": "can be unsigned"
    },

    "apt.pgpackages.org-debian": { "name": "apt.pgpackages.org-debian",
        "url": "http://apt.pgpackages.org/debian/",
        "default suite": "sid",
        "default component": "non-free",
        "dsc": "can be unsigned"
    },

    "arda.lt-p.net-debian": { "name": "arda.LT-P.net-debian",
        "url": "http://arda.LT-P.net/debian/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "colo.khms.westfalen.de-pakete": { "name": "colo.khms.westfalen.de-Pakete",
        "url": "http://colo.khms.westfalen.de/Pakete/",
        "default suite": "unstable",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "debian.hinterhof.net": { "name": "debian.hinterhof.net",
        "url": "http://debian.hinterhof.net/",
        "default suite": "unstable",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "debian.speedblue.org": { "name": "debian.speedblue.org",
        "url": "http://debian.speedblue.org/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "debian.wgdd.de-debian": { "name": "debian.wgdd.de-debian",
        "url": "http://debian.wgdd.de/debian/",
        "default suite": "unstable",
        "default component": "main",
        "dsc": "can be unsigned"
    },

    "debian.wgdd.de-debian": { "name": "debian.wgdd.de-debian",
        "url": "http://debian.wgdd.de/debian/",
        "default suite": "unstable",
        "default component": "contrib",
        "dsc": "can be unsigned"
    },

    "debian.wgdd.de-debian": { "name": "debian.wgdd.de-debian",
        "url": "http://debian.wgdd.de/debian/",
        "default suite": "unstable",
        "default component": "non-free",
        "dsc": "can be unsigned"
    },

    "dl.gna.org-kazehakase": { "name": "dl.gna.org-kazehakase",
        "url": "http://dl.gna.org/kazehakase/",
        "default suite": "debian",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "elonen.iki.fi-code-unofficial-debs": { "name": "elonen.iki.fi-code-unofficial-debs",
        "url": "http://elonen.iki.fi/code/unofficial-debs/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "erlug.linux.it-%7eda-deb": { "name": "erlug.linux.it-%7Eda-deb",
        "url": "http://erlug.linux.it/~da/deb/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "ftp.arege.jp-debian-arege": { "name": "ftp.arege.jp-debian-arege",
        "url": "http://ftp.arege.jp/debian-arege/",
        "default suite": "sid",
        "default component": "ALL",
        "dsc": "can be unsigned"
    },

    "instantafs.cbs.mpg.de-instantafs-sid": { "name": "instantafs.cbs.mpg.de-instantafs-sid",
        "url": "ftp://instantafs.cbs.mpg.de/instantafs/sid/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "jeroen.coekaerts.be-debian": { "name": "jeroen.coekaerts.be-debian",
        "url": "http://jeroen.coekaerts.be/debian/",
        "default suite": "unstable",
        "default component": "main",
        "dsc": "can be unsigned"
    },

    "jeroen.coekaerts.be-debian": { "name": "jeroen.coekaerts.be-debian",
        "url": "http://jeroen.coekaerts.be/debian/",
        "default suite": "unstable",
        "default component": "contrib",
        "dsc": "can be unsigned"
    },

    "jeroen.coekaerts.be-debian": { "name": "jeroen.coekaerts.be-debian",
        "url": "http://jeroen.coekaerts.be/debian/",
        "default suite": "unstable",
        "default component": "non-free",
        "dsc": "can be unsigned"
    },

    "laylward.com-debian": { "name": "laylward.com-debian",
        "url": "http://laylward.com/debian/",
        "default suite": "unstable",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "mherrn.de-debian": { "name": "mherrn.de-debian",
        "url": "http://mherrn.de/debian/",
        "default suite": "sid",
        "default component": "hatari",
        "dsc": "can be unsigned"
    },

    "mherrn.de-debian": { "name": "mherrn.de-debian",
        "url": "http://mherrn.de/debian/",
        "default suite": "sid",
        "default component": "paranoia",
        "dsc": "can be unsigned"
    },

    "mherrn.de-debian": { "name": "mherrn.de-debian",
        "url": "http://mherrn.de/debian/",
        "default suite": "sid",
        "default component": "exim",
        "dsc": "can be unsigned"
    },

    "mulk.dyndns.org-apt": { "name": "mulk.dyndns.org-apt",
        "url": "http://mulk.dyndns.org/apt/",
        "default suite": "unstable",
        "default component": "main",
        "dsc": "can be unsigned"
    },

    "opensource.polytechnique.org-debian": { "name": "opensource.polytechnique.org-debian",
        "url": "http://opensource.polytechnique.org/debian/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "people.debian.org-%7eamaya-debian": { "name": "people.debian.org-%7Eamaya-debian",
        "url": "http://people.debian.org/~amaya/debian/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "people.debian.org-%7ecostela-debian": { "name": "people.debian.org-%7Ecostela-debian",
        "url": "http://people.debian.org/~costela/debian/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "people.debian.org-%7ercardenes": { "name": "people.debian.org-%7Ercardenes",
        "url": "http://people.debian.org/~rcardenes/",
        "default suite": "sid",
        "default component": "main",
        "dsc": "can be unsigned"
    },

    "people.debian.org-%7etora-deb": { "name": "people.debian.org-%7Etora-deb",
        "url": "http://people.debian.org/~tora/deb/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "piem.homeip.net-%7epiem-debian": { "name": "piem.homeip.net-%7Epiem-debian",
        "url": "http://piem.homeip.net/~piem/debian/",
        "default suite": "source",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "progn.org-debian": { "name": "progn.org-debian",
        "url": "ftp://progn.org/debian/",
        "default suite": "unstable",
        "default component": "main",
        "dsc": "can be unsigned"
    },

    "ressukka.net-%7eressu-deb": { "name": "ressukka.net-%7Eressu-deb",
        "url": "http://ressukka.net/~ressu/deb/",
        "default suite": "unstable",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "sadleder.de-debian": { "name": "sadleder.de-debian",
        "url": "http://sadleder.de/debian/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "security.dsi.unimi.it-%7elorenzo-debian": { "name": "security.dsi.unimi.it-%7Elorenzo-debian",
        "url": "http://security.dsi.unimi.it/~lorenzo/debian/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "silcnet.org-download-client-deb": { "name": "silcnet.org-download-client-deb",
        "url": "http://silcnet.org/download/client/deb/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "src.braincells.com-debian": { "name": "src.braincells.com-debian",
        "url": "http://src.braincells.com/debian/",
        "default suite": "sid",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "themind.altervista.org-debian": { "name": "themind.altervista.org-debian",
        "url": "http://themind.altervista.org/debian/",
        "default suite": "unstable",
        "default component": "main",
        "dsc": "can be unsigned"
    },

    "www.cps-project.org-debian-unstable": { "name": "www.cps-project.org-debian-unstable",
        "url": "http://www.cps-project.org/debian/unstable/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "www.gwhere.org-download-debian": { "name": "www.gwhere.org-download-debian",
        "url": "http://www.gwhere.org/download/debian/",
        "default suite": "unstable",
        "default component": "main",
        "dsc": "can be unsigned"
    },

    "www.knizefamily.net-russ-software-debian": { "name": "www.knizefamily.net-russ-software-debian",
        "url": "http://www.knizefamily.net/russ/software/debian/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "www.litux.org-debian": { "name": "www.litux.org-debian",
        "url": "http://www.litux.org/debian/",
        "default suite": "unstable",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "www.steve.org.uk-apt": { "name": "www.steve.org.uk-apt",
        "url": "http://www.steve.org.uk/apt/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "www.stuff.demon.co.uk-apt": { "name": "www.stuff.demon.co.uk-apt",
        "url": "http://www.stuff.demon.co.uk/apt/",
        "default suite": "source",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "www.thomas-alfeld.de-frank-download-debian": { "name": "www.thomas-alfeld.de-frank-download-debian",
        "url": "http://www.thomas-alfeld.de/frank/download/debian/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "www.zero-based.org-debian": { "name": "www.zero-based.org-debian",
        "url": "http://www.zero-based.org/debian/",
        "default suite": "packagessource",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "kitenet.net-%7ejoey-debian": { "name": "kitenet.net-%7Ejoey-debian",
        "url": "http://kitenet.net/~joey/debian/",
        "default suite": "unstable",
        "default component": "",
        "dsc": "can be unsigned"
    },

    "www.roughtrade.net-debian": { "name": "www.roughtrade.net-debian",
        "url": "http://www.roughtrade.net/debian/",
        "default suite": "sid",
        "default component": "main",
        "dsc": "can be unsigned"
    },

####################################

"ftp.mowgli.ch-pub-debian": { "name": "ftp.mowgli.ch-pub-debian",
        "url": "ftp://ftp.mowgli.ch/pub/debian/",
        "default suite": "sid",
        "default component": "unofficial",
        "dsc": "can be unsigned"
},

"http.debian.or.jp-debian-jp": { "name": "http.debian.or.jp-debian-jp",
        "url": "http://http.debian.or.jp/debian-jp/",
        "default suite": "unstable-jp",
        "default component": "main",
        "dsc": "can be unsigned"
},

"http.debian.or.jp-debian-jp": { "name": "http.debian.or.jp-debian-jp",
        "url": "http://http.debian.or.jp/debian-jp/",
        "default suite": "unstable-jp",
        "default component": "contrib",
        "dsc": "can be unsigned"
},

"http.debian.or.jp-debian-jp": { "name": "http.debian.or.jp-debian-jp",
        "url": "http://http.debian.or.jp/debian-jp/",
        "default suite": "unstable-jp",
        "default component": "non-free",
        "dsc": "can be unsigned"
},

"mywebpages.comcast.net-ddamian-deb": { "name": "mywebpages.comcast.net-ddamian-deb",
        "url": "http://mywebpages.comcast.net/ddamian/deb/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
},

"people.debian.org-%7etora-deb": { "name": "people.debian.org-%7Etora-deb",
        "url": "http://people.debian.org/~tora/deb/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
},

"silcnet.org-download-client-deb": { "name": "silcnet.org-download-client-deb",
        "url": "http://silcnet.org/download/client/deb/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
},

"www.h.shuttle.de-mitch-stuff": { "name": "www.h.shuttle.de-mitch-stuff",
        "url": "http://www.h.shuttle.de/mitch/stuff/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
},

"www.assist.media.nagoya-u.ac.jp-%7ekatsu-debian": { "name": "www.assist.media.nagoya-u.ac.jp-%7Ekatsu-debian",
        "url": "http://www.assist.media.nagoya-u.ac.jp/~katsu/debian/",
        "default suite": "unstable",
        "default component": "ALL",
        "dsc": "can be unsigned"
},

"www.stud.tu-ilmenau.de-%7ethsc-in-debian": { "name": "www.stud.tu-ilmenau.de-%7Ethsc-in-debian",
        "url": "http://www.stud.tu-ilmenau.de/~thsc-in/debian/",
        "default suite": "unstable",
        "default component": "main",
        "dsc": "can be unsigned"
},

"debian.hinterhof.net": { "name": "debian.hinterhof.net",
        "url": "http://debian.hinterhof.net/",
        "default suite": "unstable",
        "default component": "",
        "dsc": "can be unsigned"
},

"home.planet.nl-%7eautar022": { "name": "home.planet.nl-%7Eautar022",
        "url": "http://home.planet.nl/~autar022/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
},

"dept-info.labri.fr-%7edanjean-debian": { "name": "dept-info.labri.fr-%7Edanjean-debian",
        "url": "http://dept-info.labri.fr/~danjean/debian/",
        "default suite": "unstable",
        "default component": "main",
        "dsc": "can be unsigned"
},

"noxa.de-%7esbeyer-debian": { "name": "noxa.de-%7Esbeyer-debian",
        "url": "http://noxa.de/~sbeyer/debian/",
        "default suite": "unstable",
        "default component": "main",
        "dsc": "can be unsigned"
},

"debian.wgdd.de-debian": { "name": "debian.wgdd.de-debian",
        "url": "http://debian.wgdd.de/debian/",
        "default suite": "sid",
        "default component": "main",
        "dsc": "can be unsigned"
},

"debian.wgdd.de-debian": { "name": "debian.wgdd.de-debian",
        "url": "http://debian.wgdd.de/debian/",
        "default suite": "sid",
        "default component": "contrib",
        "dsc": "can be unsigned"
},

"debian.wgdd.de-debian": { "name": "debian.wgdd.de-debian",
        "url": "http://debian.wgdd.de/debian/",
        "default suite": "sid",
        "default component": "non-free",
        "dsc": "can be unsigned"
},

"luca.pca.it-debian": { "name": "luca.pca.it-debian",
        "url": "http://luca.pca.it/debian/",
        "default suite": "",
        "default component": "",
        "dsc": "can be unsigned"
},

########################################

    }

whoami = "Ubuntu Archive Auto-Sync <katie@jackass.ubuntu.com>"

################################################################################


################################################################################

def reject (str, prefix="Rejected: "):
    global reject_message
    if str:
        reject_message += prefix + str + "\n"

################################################################################

def sign_changes(changes, dsc):
    temp_filename = "unsigned-changes"
    keyid = "0C12BDD7"
    secret_keyring = "/srv/launchpad.net/dot-gnupg/secring.gpg"
    pub_keyring = "/srv/launchpad.net/dot-gnupg/pubring.gpg"

    filehandle = open(temp_filename, 'w')
    filehandle.write(changes)
    filehandle.close()

    sane_version = dak_utils.re_no_epoch.sub('', dsc["version"])
    output_filename = "%s_%s_source.changes" % (dsc["source"], sane_version)

    cmd = "gpg --no-options --batch --no-tty --secret-keyring=%s --keyring=%s --default-key=0x%s --output=%s --clearsign %s" % (secret_keyring, pub_keyring, keyid, output_filename, temp_filename)
    (result, output) = commands.getstatusoutput(cmd)
    if (result != 0):
        print " * command was '%s'" % (cmd)
        print dak_utils.prefix_multi_line_string(output, " [gpg output:] "), ""
        dak_utils.fubar("%s: signing .changes failed [return code: %s]." % (output_filename, result))

    os.unlink(temp_filename)

################################################################################

def generate_changes(dsc, dsc_files, suite, changelog, urgency, closes, section,
                     priority, description, requires_orig, requested_by,
                     origin):
    """Generate a .changes as a string"""

    # [xxx] Changed-By can be extracted from most-recent changelog footer, but do we care?
    # [xxx] 'Closes' but could be gotten from changelog, but we don't use them?

    changes = ""
    changes += "Origin: %s/%s\n" % (origin["name"], origin["suite"])
    changes += "Format: 1.7\n"
    changes += "Date: %s\n" % (time.strftime("%a,  %d %b %Y %H:%M:%S %z"))
    changes += "Source: %s\n" % (dsc["source"])
    changes += "Binary: %s\n" % (dsc["binary"])
    changes += "Architecture: source\n"
    changes += "Version: %s\n"% (dsc["version"])
    # XXX: 'suite' forced to string to avoid unicode-vs-str grudge match
    changes += "Distribution: %s\n" % (str(suite)) 
    changes += "Urgency: %s\n" % (urgency)
    changes += "Maintainer: %s\n" % (dsc["maintainer"])
    changes += "Changed-By: %s\n" % (requested_by)
    if description:
        changes += "Description: \n"
        changes += " %s\n" % (description)
    if closes:
        changes += "Closes: %s\n" % (" ".join(closes))
    changes += "Changes: \n"
    changes += changelog
    changes += "Files: \n"
    for filename in dsc_files:
        if filename.endswith(".orig.tar.gz") and requires_orig:
            continue
        changes += " %s %s %s %s %s\n" % (dsc_files[filename]["md5sum"],
                                          dsc_files[filename]["size"],
                                          section, priority, filename)
    # Strip trailing newline
    changes = changes[:-1]

    return changes

################################################################################

# Following two functions are borrowed and (modified) from apt-listchanges

def urgency_to_numeric(u):
    urgency_map = { 'low' : 1,
                    'medium' : 2,
                    'high' : 3,
                    'emergency' : 4,
                    'critical' : 4 }

    return urgency_map.get(u.lower(), 1)

def urgency_from_numeric(n):
    urgency_map = { 1: 'low',
                    2: 'medium',
                    3: 'high',
                    4: 'critical' }

    return urgency_map.get(n, 'low')

################################################################################

def parse_changelog(changelog_filename, previous_version):
    if not os.path.exists(changelog_filename):
        dak_utils.fubar("debian/changelog not found in extracted source.")
    urgency = urgency_to_numeric('low')
    changes = ""
    is_debian_changelog = 0
    changelog_file = open(changelog_filename)
    for line in changelog_file.readlines():
        match = re_changelog_header.match(line)
        if match:
            is_debian_changelog = 1
            if previous_version is None:
                previous_version = "9999:9999"
            elif apt_pkg.VersionCompare(match.group('version'), previous_version) > 0:
                urgency = max(urgency_to_numeric(match.group('urgency')),urgency)
            else:
                break
        changes += line

    if not is_debian_changelog:
        dak_utils.fubar("header not found in debian/changelog")

    closes = []
    for match in re_closes.finditer(changes):
        bug_match = re_bug_numbers.findall(match.group(0))
        closes += map(int, bug_match)

    l = map(int, closes)
    l.sort()
    closes = map(str, l)

    return (changes, urgency_from_numeric(urgency), closes)

################################################################################

def fix_changelog(changelog):
    """Fix debian/changelog entry or entries to be in .changes compatible format."""
    fixed = []
    fixed_idx = -1
    for line in changelog.split("\n"):
        if line == "":
            fixed += [" ."]
            fixed_idx += 1
        elif line.startswith(" --"):
            # Strip any 'blank' lines preceeding the footer
            while fixed[fixed_idx] == " .":
                fixed.pop()
                fixed_idx -= 1
        else:
            fixed += [" %s" % (line)]
            fixed_idx += 1
    # Strip trailing 'blank' lines
    while fixed[fixed_idx] == " .":
        fixed.pop()
        fixed_idx -= 1
    fixed_changelog = "\n".join(fixed)
    fixed_changelog += "\n"
    return fixed_changelog

################################################################################

def parse_control(control_filename):
    """Parse a debian/control file to extract section, priority and
description if possible."""

    source_name = ""
    source_section = "-"
    source_priority = "-"
    source_description = ""

    if not os.path.exists(control_filename):
        dak_utils.fubar("debian/control not found in extracted source.")
    control_filehandle = open(control_filename)
    Control = apt_pkg.ParseTagFile(control_filehandle)
    while Control.Step():
        source = Control.Section.Find("Source")
        package = Control.Section.Find("Package")
        section = Control.Section.Find("Section")
        priority = Control.Section.Find("Priority")
        description = Control.Section.Find("Description")
        if source:
            source_section = section
            source_priority = priority
            source_name = source
        if package and package == source_name:
            source_description = "%-10s - %-.65s" % (package,
                                                     description.split("\n")[0])
    control_filehandle.close()

    return (source_section, source_priority, source_description)

################################################################################

def extract_source(dsc_filename):
    # Create and move into a temporary directory
    tmpdir = tempfile.mktemp()
    os.mkdir(tmpdir)
    old_cwd = os.getcwd()
    os.chdir(tmpdir)

    # Extract the source package
    cmd = "dpkg-source -sn -x %s" % (dsc_filename)
    (result, output) = commands.getstatusoutput(cmd)
    if (result != 0):
        print " * command was '%s'" % (cmd)
        print dak_utils.prefix_multi_line_string(output, " [dpkg-source output:] "), ""
        dak_utils.fubar("'dpkg-source -x' failed for %s [return code: %s]." % (dsc_filename, result))

    return (old_cwd, tmpdir)

################################################################################

def cleanup_source(tmpdir, old_cwd, dsc):
    # Sanity check that'll probably break if people set $TMPDIR, but
    # WTH, shutil.rmtree scares me
    if not tmpdir.startswith("/tmp/"):
        dak_utils.fubar("%s: tmpdir doesn't start with /tmp" % (tmpdir))

    # Move back and cleanup the temporary tree
    os.chdir(old_cwd)
    try:
        shutil.rmtree(tmpdir)
    except OSError, e:
        if errno.errorcode[e.errno] != 'EACCES':
            dak_utils.fubar("%s: couldn't remove tmp dir for source tree." % (dsc["source"]))

        reject("%s: source tree could not be cleanly removed." % (dsc["source"]))
        # We probably have u-r or u-w directories so chmod everything
        # and try again.
        cmd = "chmod -R u+rwx %s" % (tmpdir)
        result = os.system(cmd)
        if result != 0:
            dak_utils.fubar("'%s' failed with result %s." % (cmd, result))
        shutil.rmtree(tmpdir)
    except:
        dak_utils.fubar("%s: couldn't remove tmp dir for source tree." % (dsc["source"]))

################################################################################

def check_dsc(dsc, current_sources, current_binaries):
    source = dsc["source"]
    if current_sources.has_key(source):
        source_component = current_sources[source][1]
    else:
        source_component = "universe"
    for binary in map(string.strip, dsc["binary"].split(',')):
        if current_binaries.has_key(binary):
            (current_version, current_component) = current_binaries[binary]

            # Check that a non-main source package is not trying to
            # override a main binary package
            if current_component == "main" and source_component != "main":
                if not Options.forcemore:
                    dak_utils.fubar("%s is in main but it's source (%s) is not." % (binary, source))
                else:
                    dak_utils.warn("%s is in main but it's source (%s) is not - continuing anyway." % (binary, source))

            # Check that a source package is not trying to override an
            # ubuntu-modified binary package
            if not Options.force and current_binaries[binary][0].find("ubuntu") != -1:
                dak_utils.fubar("%s is trying to override %s_%s without -f/--force." % (source, binary, current_version))

            
            print "I: %s [%s] -> %s_%s [%s]." % (source, source_component,
                                                 binary, current_version,
                                                 current_component)

########################################

def import_dsc(dsc_filename, suite, previous_version, signing_rules,
               requires_orig, requested_by, origin, current_sources,
               current_binaries):
    dsc = dak_utils.parse_changes(dsc_filename, signing_rules)
    dsc_files = dak_utils.build_file_list(dsc, is_a_dsc=1)\
    
    check_dsc(dsc, current_sources, current_binaries)

    # Add the .dsc itself to dsc_files so it's listed in the Files: field
    dsc_base_filename = os.path.basename(dsc_filename)
    dsc_files.setdefault(dsc_base_filename, {})
    dsc_files[dsc_base_filename]["md5sum"] = SyncSource.generateMD5Sum(dsc_filename)
    dsc_files[dsc_base_filename]["size"] = os.stat(dsc_filename)[stat.ST_SIZE]

    (old_cwd, tmpdir) = extract_source(dsc_filename)
    
    # Get the upstream version
    version_minus_epoch = dak_utils.re_no_epoch.sub('', dsc["version"])
    if re_strip_revision.search(version_minus_epoch):
        base_version = re_strip_revision.sub('', version_minus_epoch)
    else:
        base_version = version_minus_epoch

    # Ensure the changelog file exists
    changelog_filename = "%s-%s/debian/changelog" % (dsc["source"], base_version)

    # Parse it and then adapt it for .changes
    (changelog, urgency, closes) = parse_changelog(changelog_filename, previous_version)
    changelog = fix_changelog(changelog)

    # Parse the control file
    control_filename = "%s-%s/debian/control" % (dsc["source"], base_version)
    (section, priority, description) = parse_control(control_filename)

    cleanup_source(tmpdir, old_cwd, dsc)

    changes = generate_changes(dsc, dsc_files, suite, changelog, urgency, closes,
                               section, priority, description, requires_orig,
                               requested_by, origin)

    # XXX Soyuz wants an unsigned changes
    #sign_changes(changes, dsc)
    output_filename = (
        "%s_%s_source.changes" % (dsc["source"], version_minus_epoch))

    filehandle = open(output_filename, 'w')
    # XXX The additional '\n' is to work around a bug in parsing
    #     unsigned changes with our forked copy of parse_changes
    filehandle.write(changes+'\n')
    filehandle.close()

################################################################################

def read_current_source(distrorelease, valid_components="", arguments=None):
    """Returns a dictionary of packages in 'suite' with their version as the
    attribute.  'component' is an optional list of (comma or whitespace
    separated) components to restrict the search to.
"""

    S = {}
    valid_components = dak_utils.split_args(valid_components)

    # XXX FIXME: This searches all pockets of the distrorelease which
    #            is not what we want.
    if Options.all:
        spp = distrorelease.getSourcePackagePublishing(
            status=dbschema.PackagePublishingStatus.PUBLISHED,
            pocket=dbschema.PackagePublishingPocket.RELEASE
            )
    else:
        spp = []
        for package in arguments:
            spp.extend(distrorelease.getPublishedReleases(package))

    for sp in spp:
        component = sp.component.name
        version = sp.sourcepackagerelease.version
        pkg = sp.sourcepackagerelease.sourcepackagename.name

        if valid_components and sp.component.name not in valid_components:
            dak_utils.warn("%s/%s: skipping because %s is not in %s" % (pkg, version,
                                                                        component,
                                                                        valid_components))
            continue
        
        if not S.has_key(pkg):
            S[pkg] = [version, component]
        else:
            if apt_pkg.VersionCompare(S[pkg][0], version) < 0:
                dak_utils.warn("%s: skipping because %s is < %s" % (pkg, version,
                                                                S[pkg][0]))
                S[pkg] = [version, component]

    return S

################################################################################

def read_current_binaries(distrorelease):
    """Returns a dictionary of binaries packages in 'distrorelease' with their
       version and component as the attributes.
"""
    B = {}

    # XXX FIXME: This searches all pockets of the distrorelease which
    #            is not what we want.

    # XXX FIXME: this is insanely slow due to how SQLObject works.  It
    #            can be limited, but only if we know what binaries we
    #            want to check against, which we don't know till we
    #            have the .dsc file and currently this function is
    #            run well before that.
    
    #     for distroarchrelease in distrorelease.architectures:
    #         bpp = distroarchrelease.getAllReleasesByStatus(
    #             dbschema.PackagePublishingStatus.PUBLISHED)

    #         for bp in bpp:
    #             component = bp.component.name
    #             version = bp.binarypackagerelease.version
    #             pkg = bp.binarypackagerelease.binarypackagename.name
    
    #             if not B.has_key(pkg):
    #                 B[pkg] = [version, component]
    #             else:
    #                 if apt_pkg.VersionCompare(B[pkg][0], version) < 0:
    #                     B[pkg] = [version, component]

    # XXX: so... let's fall back on raw SQL
    dar_ids = ", ".join([(str(dar.id)) for dar in distrorelease.architectures])
    cur = cursor()
    query = """
SELECT bpn.name, bpr.version, c.name
  FROM binarypackagerelease bpr, binarypackagename bpn, component c,
       securebinarypackagepublishinghistory sbpph, distroarchrelease dar
 WHERE bpr.binarypackagename = bpn.id AND sbpph.binarypackagerelease = bpr.id
   AND sbpph.component = c.id AND sbpph.distroarchrelease = dar.id
   AND sbpph.status = %s AND sbppd.archive = %s AND dar.id in (%s)""" \
             % (dbschema.PackagePublishingStatus.PUBLISHED,
                distrorelease.main_archive, dar_ids)
    cur.execute(query)
    print "Getting binaries for %s..." % (distrorelease.name)
    for (pkg, version, component) in cur.fetchall():
        if not B.has_key(pkg):
            B[pkg] = [version, component]
        else:
            if apt_pkg.VersionCompare(B[pkg][0], version) < 0:
                B[pkg] = [version, component]

    return B

################################################################################

def read_Sources(filename, origin):
    S = {}

    suite = origin["suite"]
    component = origin["component"]
    if suite:
        suite = "_%s" % (suite)
    if component:
        component = "_%s" % (component)

    filename = "%s%s%s_%s" % (origin["name"], suite, component, filename)
    sources_filehandle = open(filename)
    Sources = apt_pkg.ParseTagFile(sources_filehandle)
    while Sources.Step():
        pkg = Sources.Section.Find("Package")
        version = Sources.Section.Find("Version")

        if S.has_key(pkg) and apt_pkg.VersionCompare(S[pkg]["version"], version) > 0:
            continue
        
        S[pkg] = {}
        S[pkg]["version"] = version

        directory = Sources.Section.Find("Directory", "")
        files = {}
        for line in Sources.Section.Find("Files").split('\n'):
            (md5sum, size, filename) = line.strip().split()
            files[filename] = {}
            files[filename]["md5sum"] = md5sum
            files[filename]["size"] = int(size)
            files[filename]["remote filename"] = os.path.join(directory, filename)
        S[pkg]["files"] = files
    sources_filehandle.close()
    return S

################################################################################
def add_source(pkg, Sources, previous_version, suite, requested_by,
               origin, current_sources, current_binaries):
    print " * Trying to add %s..." % (pkg)

    # Check it's in the Sources file
    if not Sources.has_key(pkg):
        dak_utils.fubar("%s doesn't exist in the Sources file." % (pkg))

    # Download the source
    files = Sources[pkg]["files"]

    # local debug function to be passed to SyncSource
    def local_debug(message):
        print message

    # Use the SyncSource helper class.
    sync_source = SyncSource(
        files=files, origin=origin, debug=local_debug,
        downloader=urllib.urlretrive)

    try:
        orig_filename = sync_source.fetchLibrarianFiles()
        dsc_filename = sync_source.fetchSyncFiles()
        sync_source.checkDownloadedFiles()
    except SyncSourceError, info:
        dak_utils.fubar(info)

    if origin["dsc"] == "must be signed and valid":
        signing_rules = 1
    elif origin["dsc"] == "must be signed":
        signing_rules = 0
    else:
        signing_rules = -1

    # if the orig was found in librarian, it got fetched on disk, but it's
    # not necessary and won't be included in the changesfile, so
    # it *can/should* be removed.
    if orig_filename:
        os.unlink(orig_filename)

    requires_orig = orig_filename is None
    import_dsc(dsc_filename, suite, previous_version, signing_rules,
               requires_orig, requested_by, origin, current_sources,
               current_binaries)

################################################################################

def do_diff(Sources, Suite, origin, arguments, current_binaries):
    stat_us = 0
    stat_cant_update = 0
    stat_updated = 0
    stat_uptodate_modified = 0
    stat_uptodate = 0
    stat_count = 0
    stat_broken = 0
    stat_blacklisted = 0

    if Options.all:
        packages = Suite.keys()
    else:
        packages = arguments
    packages.sort()
    for pkg in packages:
        stat_count += 1
        dest_version = Suite.get(pkg, ["0", ""])[0]

        if not Sources.has_key(pkg):
            if not Options.all:
                dak_utils.fubar("%s: not found" % (pkg))
            else:
                print "[Ubuntu Specific] %s_%s" % (pkg, dest_version)
                stat_us += 1
                continue

        if Blacklisted.has_key(pkg):
            print "[BLACKLISTED] %s_%s" % (pkg, dest_version)
            stat_blacklisted += 1
            continue
        
        if pkg in [ "mozilla-thunderbird", "ncmpc", "ocrad", "gnuradio-core",
                    "gtk-smooth-engine", "libant1.6-java", "glade", "devilspie" ]:
            print "[BROKEN] %s_%s" % (pkg, dest_version)
            stat_broken += 1
            continue

        source_version = Sources[pkg]["version"]
        if apt_pkg.VersionCompare(dest_version, source_version) < 0:
            if  not Options.force and dest_version.find("ubuntu") != -1:
                stat_cant_update += 1
                print "[NOT Updating - Modified] %s_%s (vs %s)" \
                      % (pkg, dest_version, source_version)
            else:
                stat_updated += 1
                print "[Updating] %s (%s [Ubuntu] < %s [%s])" \
                      % (pkg, dest_version, source_version, origin["name"])
                if Options.action:
                    add_source(pkg, Sources, Suite.get(pkg, ["0", ""])[0], Options.tosuite.name,
                               Options.requestor, origin, Suite, current_binaries)
        else:
            if dest_version.find("ubuntu") != -1:
                stat_uptodate_modified += 1;    
                if Options.moreverbose:
                    print "[Nothing to update (Modified)] %s_%s (vs %s)" \
                          % (pkg, dest_version, source_version)
            else:
                stat_uptodate += 1
                if Options.moreverbose:
                    print "[Nothing to update] %s (%s [ubuntu] >= %s [debian])" \
                          % (pkg, dest_version, source_version)

    if Options.all:
        print
        print "Out-of-date BUT modified: %3d (%.2f%%)" \
              % (stat_cant_update, (float(stat_cant_update)/stat_count)*100)
        print "Updated:                  %3d (%.2f%%)" \
              % (stat_updated, (float(stat_updated)/stat_count)*100)
        print "Ubuntu Specific:          %3d (%.2f%%)" \
              % (stat_us, (float(stat_us)/stat_count)*100)
        print "Up-to-date [Modified]:    %3d (%.2f%%)" \
              % (stat_uptodate_modified, (float(stat_uptodate_modified)/stat_count)*100)
        print "Up-to-date:               %3d (%.2f%%)" \
              % (stat_uptodate, (float(stat_uptodate)/stat_count)*100)
        print "Blacklisted:              %3d (%.2f%%)" \
              % (stat_blacklisted, (float(stat_blacklisted)/stat_count)*100)
        print "Broken:                   %3d (%.2f%%)" \
              % (stat_broken, (float(stat_broken)/stat_count)*100)
        print "                          -----------"
        print "Total:                    %s" % (stat_count)


################################################################################

def options_setup():
    global Log, Options

    parser = optparse.OptionParser()
    logger_options(parser)
    parser.add_option("-a", "--all", dest="all",
                      default=False, action="store_true",
                      help="sync all packages")
    parser.add_option("-b", "--requested-by", dest="requestor",
                      help="who the sync was requested by")
    parser.add_option("-f", "--force", dest="force",
                      default=False, action="store_true",
                      help="force sync over the top of Ubuntu changes")
    parser.add_option("-F", "--force-more", dest="forcemore",
                      default=False, action="store_true",
                      help="force sync even when components don't match")
    parser.add_option("-n", "--noaction", dest="action",
                      default=True, action="store_false",
                      help="don't do anything")
    # XXX FIXME: why the heck doesn't -v provide by logger provide Options.verbose?
    parser.add_option("-V", "--moreverbose", dest="moreverbose",
                      default=False, action="store_true",
                      help="be even more verbose")

    # Options controlling where to sync packages to:

    parser.add_option("-c", "--in-component", dest="target_component",
                      help="limit syncs to packages in COMPONENT")
    parser.add_option("-d", "--to-distro", dest="target_distro",
                      help="sync to DISTRO")
    parser.add_option("-s", "--to-suite", dest="target_suite",
                      help="sync to SUITE (aka distrorelease)")

    # Options controlling where to sync packages from:

    parser.add_option("-C", "--from-component", dest="fromcomponent",
                      help="sync from COMPONENT")
    parser.add_option("-D", "--from-distro", dest="fromdistro",
                      help="sync from DISTRO")
    parser.add_option("-S", "--from-suite", dest="fromsuite",
                      help="sync from SUITE (aka distrorelease)")


    (Options, arguments) = parser.parse_args()

    # Defaults
    if not Options.todistro:
        Options.todistro = "ubuntu"

    # XXX FIXME: use distro.currentrelease
    if not Options.tosuite:
        Options.tosuite = "dapper"

    if not Options.fromdistro:
        Options.fromdistro = "debian"

    distro = Options.fromdistro.lower()
    if not Options.fromcomponent:
        Options.fromcomponent = origins[distro]["default component"]
    if not Options.fromsuite:
        Options.fromsuite = origins[distro]["default suite"]

    # Sanity checks on options

    if not Options.all and not arguments:
        dak_utils.fubar("Need -a/--all or at least one package name as an argument.")
        
    return arguments

################################################################################

def objectize_options():
    """Parse given options.

    Convert 'target_distro', 'target_suite' and 'target_component' to objects
    rather than strings.
    """
    Options.target_distro = getUtility(IDistributionSet)[Options.target_distro]

    if not Options.target_suite:
        Options.target_suite = Options.target_distro.currentrelease.name
    Options.target_suite = Options.target_distro.getRelease(Options.target_suite)

    valid_components = (
        dict([(c.name,c) for c in Options.target_suite.components]))
    if (Options.target_component and
        Options.target_component not in valid_components):
        dak_utils.fubar(
            "%s is not a valid component for %s/%s."
            % (Options.target_component, Options.target_distro.name,
               Options.target_suite.name))
    Options.target_component = valid_components[Options.target_component]

    # Fix up Options.requestor
    if Options.requestor:
        PersonSet = getUtility(IPersonSet)
        person = PersonSet.getByName(Options.requestor)
        if not person:
            dak_utils.fubar("Unknown LaunchPad user id '%s'."
                            % (Options.requestor))
        Options.requestor = "%s <%s>" % (person.displayname,
                                         person.preferredemail.email)
        # XXX cprov 20061113: is it ensuring RFC-822 sentence is
        # ASCII ? Don't we support unicodes ?
        Options.requestor = str(Options.requestor)
    else:
        if Options.action and not Options.all:
            dak_utils.fubar(
                "Need -a/--all or an argument for -b/--requested-by.")
        else:
            Options.requestor = whoami


########################################

def init():
    global Blacklisted, Library, Lock, Log

    apt_pkg.init()

    arguments = options_setup()

    Log = logger(Options, "sync-source")

    Log.debug("Acquiring lock")
    Lock = GlobalLock('/var/lock/launchpad-sync-source.lock')
    Lock.acquire(blocking=True)

    Log.debug("Initialising connection.")
    initZopeless(dbuser="ro")

    execute_zcml_for_scripts()

    Library = LibrarianClient()

    objectize_options()

    # Blacklist
    Blacklisted = {}
    # XXX de-hardcode me harder
    blacklist_file = open("/srv/launchpad.net/dak/sync-blacklist.txt")
    for line in blacklist_file:
        line = line.strip()
        if not line or line[0] == "#":
            continue
        Blacklisted[line] = ""
    blacklist_file.close()


    return arguments

def main():
    arguments = init()

    origin = origins[Options.fromdistro]
    origin["suite"] = Options.fromsuite
    origin["component"] = Options.fromcomponent

    Sources = read_Sources("Sources", origin)
    Suite = read_current_source(
        Options.target_suite, Options.target_component, arguments)
    current_binaries = read_current_binaries(Options.target_suite)
    do_diff(Sources, Suite, origin, arguments, current_binaries)

################################################################################

if __name__ == '__main__':
    main()
