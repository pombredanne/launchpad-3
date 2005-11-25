#!/usr/bin/python

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""
Build and manage chroots for launchpad (slave tool)
"""

__metaclass__ = type

import sys, os

from ConfigParser import SafeConfigParser
import tempfile

class ChrootError(Exception):
    pass

slavebin = ""

def execute(cmd):
    """convenience method to raise an error if a command fails to run ok."""
    if os.system(cmd) != 0:
        raise OSError("Command %s failed" % cmd)

def affirmed(response):
    return response in ('y', 'yes', 'happy', 'gay', '')

class SlaveChrootBuilder:
    """Manage the process of building a chroot."""

    def __init__(self, conffile, slavebin):
        self.conffile = conffile
        self.bin = slavebin

    def loadConfig(self):
        """Parse the configuration file and check for expected values."""
        self.conf = SafeConfigParser()
        self.conf.read(self.conffile)
        self.config = {}

        required_config_items = [
            ('chroot', ['distribution', 'distrorelease', 'distrorelease',
                        'architecture', 'debootstraparchive', 'variant']),
            ('apt', ['archiveroot', 'components', 'pockets',
                     'signingdisabled']),
            ('buildd', ['user', 'group', 'paths', 'touchfiles', 'extrapkgs']),
            ('intervention', ['postbootstrap', 'postextrapkgs', 'postfinalapt',
                              'pretarup']),
            ]
        self.config = {}
        for section, keys in required_config_items:
            self.config[section] = {}
            for key in keys:
                if not self.conf.has_option(section, key):
                    raise ChrootError("Expected key %s in section %s" %
                                      (key,section))
                self.config[section][key] = self.conf.get(section, key)
                
    def makeTreeRoot(self):
        self.treeroot = tempfile.mkdtemp(dir=os.environ["HOME"],
                                         prefix="build-")
        self.buildid = "-".join(self.treeroot.split("-")[1:])
        print "Temporary work directory: %s" % self.treeroot
        print "Using build id %s for slave binaries" % self.buildid

    def intervene(self, stage):
        """Run a chroot if intervention at this stage is requested."""
        if self.config["intervention"][stage] == "1":
            print "Intervening at stage %s" % stage
            os.system("sudo chroot %s/chroot-autobuild /bin/su -" %
                      self.treeroot)
    def debootstrap(self):
        """Run debootstrap with the arguments from the config."""
        chrconf = self.config["chroot"]
        
        if chrconf["architecture"] == "host":
            print "Obtaining host architecture..."
            chrconf["architecture"] = \
                os.popen("dpkg --print-installation-architecture").read().strip()
        print "Debootstrapping %s/%s/%s (%s) from %s ..." % (
            chrconf["distribution"],
            chrconf["distrorelease"],
            chrconf["architecture"],
            chrconf["variant"],
            chrconf["debootstraparchive"])

        execute("sudo debootstrap --resolve-deps --arch %s --variant=%s %s %s %s" % (
            chrconf["architecture"],
            chrconf["variant"],
            chrconf["distrorelease"],
            self.treeroot+"/chroot-autobuild",
            chrconf["debootstraparchive"]))

        # Make the user, paths and chown them...
        self.makeUserAndPaths()
        self.setupApt(True)
        
        print "Mouting chroot..."
        execute(self.bin+"/mount-chroot %s" % self.buildid)
        self.intervene("postbootstrap")

    def makeUserAndPaths(self):
        """Make the paths specified in the buildd group and touch files etc."""
        # 1. transfer the user and group
        print "Transferring user %s and group %s..." % (
            self.config['buildd']['user'],
            self.config['buildd']['group'])

        def xfer_element(what, filename):
            execute("sudo grep %s /etc/%s | "
                    "sudo sh -c 'cat >> %s/chroot-autobuild/etc/%s'"
                    %(what, filename, self.treeroot, filename))

        xfer_element(self.config['buildd']['user'], 'passwd')
        xfer_element(self.config['buildd']['user'], 'shadow')
        xfer_element(self.config['buildd']['group'], 'group')
        xfer_element(self.config['buildd']['group'], 'gshadow')

        print "Making paths..."
        for path in self.config['buildd']['paths'].split():
            execute("sudo mkdir %s/chroot-autobuild/%s" % (
                self.treeroot, path))
            execute("sudo chown %s:%s %s/chroot-autobuild/%s" % (
                self.config['buildd']['user'],
                self.config['buildd']['group'],
                self.treeroot, path))
            
        print "Touching files..."
        for file in self.config['buildd']['touchfiles'].split():
            execute("sudo touch %s/chroot-autobuild/%s" % (
                self.treeroot, file))
            execute("sudo chown %s:%s %s/chroot-autobuild/%s" % (
                self.config['buildd']['user'],
                self.config['buildd']['group'],
                self.treeroot, file))

    def setupApt(self, bootstrap=False):
        root = self.config['apt']['archiveroot']
        if bootstrap:
            root = self.config['chroot']['debootstraparchive']
        pockets = ["-"+pocket for pocket in
                   self.config['apt']['pockets'].split()]
        pockets.append('')
        execute("sudo rm -f %s/chroot-autobuild/etc/apt/sources.list" %
                self.treeroot)
        execute("sudo touch %s/chroot-autobuild/etc/apt/sources.list" %
                self.treeroot)
        
        for pocket in pockets:
            execute("echo deb %s %s%s %s | "
                    "sudo sh -c 'cat >> "
                    "%s/chroot-autobuild/etc/apt/sources.list'" %(
                root, self.config['chroot']['distrorelease'],
                pocket, self.config['apt']['components'],
                self.treeroot))

        if self.config['apt']['signingdisabled'] == '1':
            execute(r'echo APT::Get::AllowUnauthenticated \"1\"\; | '
                    r'sudo sh -c "cat >> '
                    r'%s/chroot-autobuild/etc/apt/apt.conf.d/99buildd"' %
                    self.treeroot)
        else:
            execute("sudo rm -f "
                    "%s/chroot-autobuild/etc/apt/apt.conf.d/99buildd" %
                    self.treeroot)

    def umount(self):
        """Unmount the chroot ready for tarring up."""

        self.intervene("pretarup")
        execute(self.bin+"/scan-for-processes %s || true" % self.buildid)
        execute(self.bin+"/umount-chroot %s" % self.buildid)
        
    def run(self):
        self.loadConfig()
        # Okay, we know all the configuration we're expecting has been
        # loaded into self.config (dict of dicts)
        self.makeTreeRoot()
        self.debootstrap()
        # The chroot is made and currently configured for pre-buildd
        # package installation, so update it...
        execute(self.bin+"/update-debian-chroot %s" % self.buildid)
        # And install anything asked for in the config
        execute("sudo chroot %s/chroot-autobuild apt-get install %s" % (
            self.treeroot, self.config['buildd']['extrapkgs']))
        self.intervene('postextrapkgs')
        # Set us up for the internal apt config
        self.setupApt()
        self.intervene('postfinalapt')
        
        self.umount()
        # And tar it up...

        print "Happy to repack? [Y]"
        yesno = sys.stdin.readline().strip().lower()
        if affirmed(yesno):
            print "Preparing chroot tarball..."
            execute("sudo tar -C %s -cjf "
                    "chroot-%s-%s-%s.tar.bz2 chroot-autobuild" %(
                self.treeroot, self.config['chroot']['distribution'],
                self.config['chroot']['distrorelease'],
                self.config['chroot']['architecture']))
            execute("sudo chown $USER %s" % chroottar)

        print "Cleaning up..."
        execute(self.bin+"/remove-build %s" % self.buildid)
        
        if affirmed(yesno):
            print "Constructed chroot-%s-%s-%s.tar.bz2" % (
                self.config['chroot']['distribution'],
                self.config['chroot']['distrorelease'],
                self.config['chroot']['architecture'])

def do_generate(conffile):
    """Generate a chroot based on the configuration file supplied"""
    # Simple override which helps a lot during bootstrapping
    os.environ["LC_ALL"] = "C"
    SlaveChrootBuilder(conffile, slavebin).run()

def do_intervene(chroottar):
    """Unpack, mount, chroot in, umount, repack, the chroot"""
    # We use the slavebin for the buildds to do some tasks
    execute("mkdir $HOME/build-chroot-tool")
    print "Unpacking..."
    execute(slavebin+"/unpack-chroot chroot-tool "+chroottar)
    print "Mounting..."
    execute(slavebin+"/mount-chroot chroot-tool")
    print "Chrooting in..."
    execute("sudo chroot $HOME/build-chroot-tool/chroot-autobuild /bin/su -")
    # We eat the result code of scanning for processes
    print "Scanning for processes to kill..."
    os.system(slavebin+"/scan-for-processes chroot-tool")
    print "Unmounting..."
    execute(slavebin+"/umount-chroot chroot-tool")
    print "Happy to repack? [Y]"
    yesno = sys.stdin.readline().strip().lower()
    if affirmed(yesno):
        print "Re-packing..."
        execute("sudo tar -C $HOME/build-chroot-tool -cjf %s chroot-autobuild" %
                chroottar)
        execute("sudo chown $USER %s" % chroottar)
    print "Cleaning up..."
    execute(slavebin+"/remove-build chroot-tool")
    if affirmed(yesno):
        print "Done, updated %s" % chroottar
    else:
        print "Done, did not update %s" % chroottar

if __name__ == "__main__":
    from optparse import OptionParser
    oparser = OptionParser()
    oparser.add_option("-r", "--binaryroot",
                       dest="binaryroot",
                       help="root of slave binaries",
                       metavar="BINARYROOT",
                       default="/usr/share/launchpad-buildd/slavebin")
    
    oparser.add_option( "-g", "--generate",
                        dest="generator",
                        help="configuration file for a chroot to generate",
                        metavar="CONFIG",
                        default=None)

    oparser.add_option("-i", "--intervene",
                       dest="intervention",
                       help="chroot to unpack and chroot into",
                       metavar="CHROOT",
                       default=None)

    (opts,args) = oparser.parse_args()

    # xnor
    if not ((opts.generator is None) ^  (opts.intervention is None)):
        oparser.print_help(sys.stderr)
        sys.exit(1)

    slavebin = opts.binaryroot

    if opts.generator:
        do_generate(opts.generator)
    else:
        do_intervene(opts.intervention)

