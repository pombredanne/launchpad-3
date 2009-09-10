#!/usr/bin/python
# Run tests on a branch in an EC2 instance.
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metatype__ = type

import cStringIO
import code
import optparse
import os
import pickle
import re
import socket
import sys
import urllib
import traceback
# The rlcompleter and readline modules change the behavior of the python
# interactive interpreter just by being imported.
import readline
import rlcompleter
# Shut up pyflakes.
rlcompleter

import boto
from boto.exception import EC2ResponseError

from bzrlib.plugin import load_plugins
load_plugins()
from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.config import GlobalConfig
from bzrlib.errors import UncommittedChanges
from bzrlib.plugins.launchpad.account import get_lp_login
from bzrlib.plugins.pqm.pqm_submit import (
    NoPQMSubmissionAddress, PQMSubmission)

import paramiko

from devscripts.ec2test.ec2instance import EC2Instance


TRUNK_BRANCH = 'bzr+ssh://bazaar.launchpad.net/~launchpad-pqm/launchpad/devel'
DEFAULT_INSTANCE_TYPE = 'c1.xlarge'
AVAILABLE_INSTANCE_TYPES = ('m1.large', 'm1.xlarge', 'c1.xlarge')
VALID_AMI_OWNERS = (
    255383312499, # gary
    559320013529, # flacoste
    200337130613, # mwhudson
    # ...anyone else want in on the fun?
    )

readline.parse_and_bind('tab: complete')

#############################################################################
# Try to guide users past support problems we've encountered before
if not paramiko.__version__.startswith('1.7.4'):
    raise RuntimeError('Your version of paramiko (%s) is not supported.  '
                       'Please use 1.7.4.' % (paramiko.__version__,))
# maybe add similar check for bzrlib?
# End
#############################################################################

#############################################################################
# Modified from paramiko.config.  The change should be pushed upstream.
# Our fork supports Host lines with more than one host.

import fnmatch


class SSHConfig (object):
    """
    Representation of config information as stored in the format used by
    OpenSSH.  Queries can be made via L{lookup}.  The format is described in
    OpenSSH's C{ssh_config} man page.  This class is provided primarily as a
    convenience to posix users (since the OpenSSH format is a de-facto
    standard on posix) but should work fine on Windows too.

    @since: 1.6
    """

    def __init__(self):
        """
        Create a new OpenSSH config object.
        """
        self._config = [ { 'host': '*' } ]

    def parse(self, file_obj):
        """
        Read an OpenSSH config from the given file object.

        @param file_obj: a file-like object to read the config file from
        @type file_obj: file
        """
        configs = [self._config[0]]
        for line in file_obj:
            line = line.rstrip('\n').lstrip()
            if (line == '') or (line[0] == '#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip().lower()
            else:
                # find first whitespace, and split there
                i = 0
                while (i < len(line)) and not line[i].isspace():
                    i += 1
                if i == len(line):
                    raise Exception('Unparsable line: %r' % line)
                key = line[:i].lower()
                value = line[i:].lstrip()

            if key == 'host':
                del configs[:]
                # the value may be multiple hosts, space-delimited
                for host in value.split():
                    # do we have a pre-existing host config to append to?
                    matches = [c for c in self._config if c['host'] == host]
                    if len(matches) > 0:
                        configs.append(matches[0])
                    else:
                        config = { 'host': host }
                        self._config.append(config)
                        configs.append(config)
            else:
                for config in configs:
                    config[key] = value

    def lookup(self, hostname):
        """
        Return a dict of config options for a given hostname.

        The host-matching rules of OpenSSH's C{ssh_config} man page are used,
        which means that all configuration options from matching host
        specifications are merged, with more specific hostmasks taking
        precedence.  In other words, if C{"Port"} is set under C{"Host *"}
        and also C{"Host *.example.com"}, and the lookup is for
        C{"ssh.example.com"}, then the port entry for C{"Host *.example.com"}
        will win out.

        The keys in the returned dict are all normalized to lowercase (look for
        C{"port"}, not C{"Port"}.  No other processing is done to the keys or
        values.

        @param hostname: the hostname to lookup
        @type hostname: str
        """
        matches = [
            x for x in self._config if fnmatch.fnmatch(hostname, x['host'])]
        # sort in order of shortest match (usually '*') to longest
        matches.sort(lambda x,y: cmp(len(x['host']), len(y['host'])))
        ret = {}
        for m in matches:
            ret.update(m)
        del ret['host']
        return ret

# END paramiko config fork
#############################################################################


def get_ip():
    """Uses AWS checkip to obtain this machine's IP address.

    Consults an external website to determine the public IP address of this
    machine.

    :return: This machine's net-visible IP address as a string.
    """
    return urllib.urlopen('http://checkip.amazonaws.com').read().strip()


class CredentialsError(Exception):
    """Raised when AWS credentials could not be loaded."""

    def __init__(self, filename, extra=None):
        message = (
            "Please put your aws access key identifier and secret access "
            "key identifier in %s. (On two lines)." % (filename,))
        if extra:
            message += extra
        Exception.__init__(self, message)


class EC2Credentials:
    """Credentials for logging in to EC2."""

    DEFAULT_CREDENTIALS_FILE = '~/.ec2/aws_id'

    def __init__(self, identifier, secret):
        self.identifier = identifier
        self.secret = secret

    @classmethod
    def load_from_file(cls, filename=None):
        """Load the EC2 credentials from 'filename'."""
        if filename is None:
            filename = os.path.expanduser(cls.DEFAULT_CREDENTIALS_FILE)
        try:
            aws_file = open(filename, 'r')
        except (IOError, OSError), e:
            raise CredentialsError(filename, str(e))
        try:
            identifier = aws_file.readline().strip()
            secret = aws_file.readline().strip()
        finally:
            aws_file.close()
        return cls(identifier, secret)

    def connect(self, name):
        """Connect to EC2 with these credentials.

        :param name: ???
        :return: An `EC2Account` connected to EC2 with these credentials.
        """
        conn = boto.connect_ec2(self.identifier, self.secret)
        return EC2Account(name, conn)


class EC2Account:
    """An EC2 account.

    You can use this to manage security groups, keys and images for an EC2
    account.
    """

    # Used to find pre-configured Amazon images.
    _image_match = re.compile(
        r'launchpad-ec2test(\d+)/image.manifest.xml$').match

    def __init__(self, name, connection):
        """Construct an EC2 instance.

        :param name: ???
        :param connection: An open boto ec2 connection.
        """
        self.name = name
        self.conn = connection

    def log(self, msg):
        """Log a message on stdout, flushing afterwards."""
        # XXX: JonathanLange 2009-05-31 bug=383076: Copied from EC2TestRunner.
        # Should change EC2Account to take a logger and use that instead of
        # writing to stdout.
        sys.stdout.write(msg)
        sys.stdout.flush()

    def acquire_security_group(self, demo_networks=None):
        """Get a security group with the appropriate configuration.

        "Appropriate" means configured to allow this machine to connect via
        SSH, HTTP and HTTPS.

        If a group is already configured with this name for this connection,
        then re-use that. Otherwise, create a new security group and configure
        it appropriately.

        The name of the security group is the `EC2Account.name` attribute.

        :return: A boto security group.
        """
        if demo_networks is None:
            demo_networks = []
        try:
            group = self.conn.get_all_security_groups(self.name)[0]
        except EC2ResponseError, e:
            if e.code != 'InvalidGroup.NotFound':
                raise
        else:
            # If an existing security group was configured, try deleting it
            # since our external IP might have changed.
            try:
                group.delete()
            except EC2ResponseError, e:
                if e.code != 'InvalidGroup.InUse':
                    raise
                # Otherwise, it means that an instance is already using
                # it, so simply re-use it. It's unlikely that our IP changed!
                #
                # XXX: JonathanLange 2009-06-05: If the security group exists
                # already, verify that the current IP is permitted; if it is
                # not, make an INFO log and add the current IP.
                self.log("Security group already in use, so reusing.")
                return group

        security_group = self.conn.create_security_group(
            self.name, 'Authorization to access the test runner instance.')
        # Authorize SSH and HTTP.
        ip = get_ip()
        security_group.authorize('tcp', 22, 22, '%s/32' % ip)
        security_group.authorize('tcp', 80, 80, '%s/32' % ip)
        security_group.authorize('tcp', 443, 443, '%s/32' % ip)
        for network in demo_networks:
            # Add missing netmask info for single ips.
            if '/' not in network:
                network += '/32'
            security_group.authorize('tcp', 80, 80, network)
            security_group.authorize('tcp', 443, 443, network)
        return security_group

    def acquire_private_key(self):
        """Create & return a new key pair for the test runner."""
        key_pair = self.conn.create_key_pair(self.name)
        return paramiko.RSAKey.from_private_key(
            cStringIO.StringIO(key_pair.material.encode('ascii')))

    def delete_previous_key_pair(self):
        """Delete previously used keypair, if it exists."""
        try:
            # Only one keypair will match 'self.name' since it's a unique
            # identifier.
            key_pairs = self.conn.get_all_key_pairs(self.name)
            assert len(key_pairs) == 1, (
                "Should be only one keypair, found %d (%s)"
                % (len(key_pairs), key_pairs))
            key_pair = key_pairs[0]
            key_pair.delete()
        except EC2ResponseError, e:
            if e.code != 'InvalidKeyPair.NotFound':
                if e.code == 'AuthFailure':
                    # Inserted because of previous support issue.
                    self.log(
                        'POSSIBLE CAUSES OF ERROR:\n'
                        '  Did you sign up for EC2?\n'
                        '  Did you put a credit card number in your AWS '
                        'account?\n'
                        'Please doublecheck before reporting a problem.\n')
                raise

    def acquire_image(self, machine_id):
        """Get the image.

        If 'machine_id' is None, then return the image with location that
        matches `EC2Account._image_match` and has the highest revision number
        (where revision number is the 'NN' in 'launchpad-ec2testNN').

        Otherwise, just return the image with the given 'machine_id'.

        :raise ValueError: if there is more than one image with the same
            location string.

        :raise RuntimeError: if we cannot find a test-runner image.

        :return: A boto image.
        """
        if machine_id is not None:
            # This may raise an exception. The user specified a machine_id, so
            # they can deal with it.
            return self.conn.get_image(machine_id)

        # We are trying to find an image that has a location that matches a
        # regex (see definition of _image_match, above). Part of that regex is
        # expected to be an integer with the semantics of a revision number.
        # The image location with the highest revision number is the one that
        # should be chosen. Because AWS does not guarantee that two images
        # cannot share a location string, we need to make sure that the search
        # result for this image is unique, or throw an error because the
        # choice of image is ambiguous.
        search_results = None

        # Find the images with the highest revision numbers and locations that
        # match the regex.
        for image in self.conn.get_all_images(owners=VALID_AMI_OWNERS):
            match = self._image_match(image.location)
            if match:
                revision = int(match.group(1))
                if (search_results is None
                    or search_results['revision'] < revision):
                    # Then we have our first, highest match.
                    search_results = {'revision': revision, 'images': [image]}
                elif search_results['revision'] == revision:
                    # Another image that matches and is equally high.
                    search_results['images'].append(image)

        # No matching image.
        if search_results is None:
            raise RuntimeError(
                "You don't have access to a test-runner image.\n"
                "Request access and try again.\n")

        # More than one matching image.
        if len(search_results['images']) > 1:
            raise ValueError(
                ('more than one image of revision %(revision)d found: '
                 '%(images)r') % search_results)

        # We could put a minimum image version number check here.
        image = search_results['images'][0]
        self.log(
            'Using machine image version %d\n'
            % (search_results['revision'],))
        return image

    def get_instance(self, instance_id):
        """Look in all of our reservations for an instance with the given ID.

        Return the instance object if it exists, None otherwise.
        """
        # XXX mars 20090729
        # This method is needed by the ec2-generate-windmill-image.py script,
        # so please do not delete it.
        #
        # This is a strange object on which to put this method, but I did
        # not want to break encapsulation around the self.conn attribute.

        for reservation in self.conn.get_all_instances():
            # We need to look inside each reservation for the instances
            # themselves.
            for instance in reservation.instances:
                if instance.id == instance_id:
                    return instance
        return None


class UnknownBranchURL(Exception):
    """Raised when we try to parse an unrecognized branch url."""

    def __init__(self, branch_url):
        Exception.__init__(
            self,
            "Couldn't parse '%s', not a Launchpad branch." % (branch_url,))


def parse_branch_url(branch_url):
    """Given the URL of a branch, return its components in a dict."""
    _lp_match = re.compile(
        r'lp:\~([^/]+)/([^/]+)/([^/]+)$').match
    _bazaar_match = re.compile(
        r'bzr+ssh://bazaar.launchpad.net/\~([^/]+)/([^/]+)/([^/]+)$').match
    match = _lp_match(branch_url)
    if match is None:
        match = _bazaar_match(branch_url)
    if match is None:
        raise UnknownBranchURL(branch_url)
    owner = match.group(1)
    product = match.group(2)
    branch = match.group(3)
    unique_name = '~%s/%s/%s' % (owner, product, branch)
    url = 'bzr+ssh://bazaar.launchpad.net/%s' % (unique_name,)
    return dict(
        owner=owner, product=product, branch=branch, unique_name=unique_name,
        url=url)


def validate_file(filename):
    """Raise an error if 'filename' is not a file we can write to."""
    if filename is None:
        return

    check_file = filename
    if os.path.exists(check_file):
        if not os.path.isfile(check_file):
            raise ValueError(
                'file argument %s exists and is not a file' % (filename,))
    else:
        check_file = os.path.dirname(check_file)
        if (not os.path.exists(check_file) or
            not os.path.isdir(check_file)):
            raise ValueError(
                'file %s cannot be created.' % (filename,))
    if not os.access(check_file, os.W_OK):
        raise ValueError(
            'you do not have permission to write %s' % (filename,))


def normalize_branch_input(data):
    """Given 'data' return a ('dest', 'src') pair.

    :param data: One of::
       - a double of (sourcecode_location, branch_url).
         If 'sourcecode_location' is Launchpad, then 'branch_url' can
         also be the name of a branch of launchpad owned by
         launchpad-pqm.
       - a singleton of (branch_url,)
       - a singleton of (sourcecode_location,) where
         sourcecode_location corresponds to a Launchpad upstream
         project as well as a rocketfuel sourcecode location.
       - a string which could populate any of the above singletons.

    :return: ('dest', 'src') where 'dest' is the destination
        sourcecode location in the rocketfuel tree and 'src' is the
        URL of the branch to put there. The URL can be either a bzr+ssh
        URL or the name of a branch of launchpad owned by launchpad-pqm.
    """
    # XXX: JonathanLange 2009-06-05: Should convert lp: URL branches to
    # bzr+ssh:// branches.
    if isinstance(data, basestring):
        data = (data,)
    if len(data) == 2:
        # Already in dest, src format.
        return data
    if len(data) != 1:
        raise ValueError(
            'invalid argument for ``branches`` argument: %r' %
            (data,))
    branch_location = data[0]
    try:
        parsed_url = parse_branch_url(branch_location)
    except UnknownBranchURL:
        return branch_location, 'lp:%s' % (branch_location,)
    return parsed_url['product'], parsed_url['url']


def parse_specified_branches(branches):
    """Given 'branches' from the command line, return a sanitized dict.

    The dict maps sourcecode locations to branch URLs, according to the
    rules in `normalize_branch_input`.
    """
    return dict(map(normalize_branch_input, branches))


class EC2TestRunner:

    name = 'ec2-test-runner'

    message = instance = image = None
    _running = False

    def __init__(self, branch, email=False, file=None, test_options='-vv',
                 headless=False, branches=(),
                 machine_id=None, instance_type=DEFAULT_INSTANCE_TYPE,
                 pqm_message=None, pqm_public_location=None,
                 pqm_submit_location=None, demo_networks=None,
                 open_browser=False, pqm_email=None,
                 include_download_cache_changes=None):
        """Create a new EC2TestRunner.

        This sets the following attributes:
          - original_branch
          - test_options
          - headless
          - include_download_cache_changes
          - download_cache_additions
          - branches (parses, validates)
          - message (after validating PQM submisson)
          - email (after validating email capabilities)
          - instance_type (validates)
          - image (after connecting to ec2)
          - file (after checking we can write to it)
          - ssh_config_file_name (after checking it exists)
          - vals, a dict containing
            - the environment
            - trunk_branch (either from global or derived from branches)
            - branch
            - smtp_server
            - smtp_username
            - smtp_password
            - email (distinct from the email attribute)
            - key_type
            - key
            - launchpad_login
        """
        self.original_branch = branch # just for easy access in debugging
        self.test_options = test_options
        self.headless = headless
        self.include_download_cache_changes = include_download_cache_changes
        if demo_networks is None:
            demo_networks = ()
        else:
            demo_networks = demo_networks
        self.open_browser = open_browser
        if headless and file:
            raise ValueError(
                'currently do not support files with headless mode.')
        if headless and not (email or pqm_message):
            raise ValueError('You have specified no way to get the results '
                             'of your headless test run.')

        if test_options != '-vv' and pqm_message is not None:
            raise ValueError(
                "Submitting to PQM with non-default test options isn't "
                "supported")

        trunk_specified = False
        trunk_branch = TRUNK_BRANCH

        # normalize and validate branches
        branches = parse_specified_branches(branches)
        try:
            launchpad_url = branches.pop('launchpad')
        except KeyError:
            # No Launchpad branch specified.
            pass
        else:
            try:
                parsed_url = parse_branch_url(launchpad_url)
            except UnknownBranchURL:
                user = 'launchpad-pqm'
                src = ('bzr+ssh://bazaar.launchpad.net/'
                       '~launchpad-pqm/launchpad/%s' % (launchpad_url,))
            else:
                user = parsed_url['owner']
                src = parsed_url['url']
            if user == 'launchpad-pqm':
                trunk_specified = True
            trunk_branch = src

        self.branches = branches.items()

        # XXX: JonathanLange 2009-05-31: The trunk_specified stuff above and
        # the pqm location stuff below are actually doing the equivalent of
        # preparing a merge directive. Perhaps we can leverage that to make
        # this code simpler.
        self.download_cache_additions = None
        if branch is None:
            config = GlobalConfig()
            if pqm_message is not None:
                raise ValueError('Cannot submit trunk to pqm.')
        else:
            (tree,
             bzrbranch,
             relpath) = BzrDir.open_containing_tree_or_branch(branch)
            # if tree is None, remote...I'm assuming.
            if tree is None:
                config = GlobalConfig()
            else:
                config = bzrbranch.get_config()

            if pqm_message is not None or tree is not None:
                # if we are going to maybe send a pqm_message, we're going to
                # go down this path. Also, even if we are not but this is a
                # local branch, we're going to use the PQM machinery to make
                # sure that the local branch has been made public, and has all
                # working changes there.
                if tree is None:
                    # remote.  We will make some assumptions.
                    if pqm_public_location is None:
                        pqm_public_location = branch
                    if pqm_submit_location is None:
                        pqm_submit_location = trunk_branch
                elif pqm_submit_location is None and trunk_specified:
                    pqm_submit_location = trunk_branch
                # modified from pqm_submit.py
                submission = PQMSubmission(
                    source_branch=bzrbranch,
                    public_location=pqm_public_location,
                    message=pqm_message or '',
                    submit_location=pqm_submit_location,
                    tree=tree)
                if tree is not None:
                    # this is the part we want to do whether or not we're
                    # submitting.
                    submission.check_tree() # any working changes
                    submission.check_public_branch() # everything public
                    branch = submission.public_location
                    if (include_download_cache_changes is None or
                        include_download_cache_changes):
                        # We need to get the download cache settings
                        cache_tree, cache_bzrbranch, cache_relpath = (
                            BzrDir.open_containing_tree_or_branch(
                                os.path.join(
                                    self.original_branch, 'download-cache')))
                        cache_tree.lock_read()
                        try:
                            cache_basis_tree = cache_tree.basis_tree()
                            cache_basis_tree.lock_read()
                            try:
                                delta = cache_tree.changes_from(
                                    cache_basis_tree, want_unversioned=True)
                                unversioned = [
                                    un for un in delta.unversioned
                                    if not cache_tree.is_ignored(un[0])]
                                added = delta.added
                                self.download_cache_additions = (
                                    unversioned + added)
                            finally:
                                cache_basis_tree.unlock()
                        finally:
                            cache_tree.unlock()
                if pqm_message is not None:
                    if self.download_cache_additions:
                        raise UncommittedChanges(cache_tree)
                    # get the submission message
                    mail_from = config.get_user_option('pqm_user_email')
                    if not mail_from:
                        mail_from = config.username()
                    # Make sure this isn't unicode
                    mail_from = mail_from.encode('utf8')
                    if pqm_email is None:
                        if tree is None:
                            pqm_email = (
                                "Launchpad PQM <launchpad@pqm.canonical.com>")
                        else:
                            pqm_email = config.get_user_option('pqm_email')
                    if not pqm_email:
                        raise NoPQMSubmissionAddress(bzrbranch)
                    mail_to = pqm_email.encode('utf8') # same here
                    self.message = submission.to_email(mail_from, mail_to)
                elif (self.download_cache_additions and
                      self.include_download_cache_changes is None):
                    raise UncommittedChanges(
                        cache_tree,
                        'You must select whether to include download cache '
                        'changes (see --include-download-cache-changes and '
                        '--ignore-download-cache-changes, -c and -g '
                        'respectively), or '
                        'commit or remove the files in the download-cache.')
        if email is not False:
            if email is True:
                email = [config.username()]
                if not email[0]:
                    raise ValueError('cannot find your email address.')
            elif isinstance(email, basestring):
                email = [email]
            else:
                tmp = []
                for item in email:
                    if not isinstance(item, basestring):
                        raise ValueError(
                            'email must be True, False, a string, or a list of '
                            'strings')
                    tmp.append(item)
                email = tmp
        else:
            email = None
        self.email = email

        # We do a lot of looking before leaping here because we want to avoid
        # wasting time and money on errors we could have caught early.

        # Validate instance_type and get default kernal and ramdisk.
        if instance_type not in AVAILABLE_INSTANCE_TYPES:
            raise ValueError('unknown instance_type %s' % (instance_type,))

        # Validate and set file.
        validate_file(file)
        self.file = file

        # Make a dict for string substitution based on the environ.
        #
        # XXX: JonathanLange 2009-06-02: Although this defintely makes the
        # scripts & commands easier to write, it makes it harder to figure out
        # how the different bits of the system interoperate (passing 'vals' to
        # a method means it uses...?). Consider changing things around so that
        # vals is not needed.
        self.vals = dict(os.environ)
        self.vals['trunk_branch'] = trunk_branch
        self.vals['branch'] = branch
        home = self.vals['HOME']

        # Email configuration.
        if email is not None or pqm_message is not None:
            server = self.vals['smtp_server'] = config.get_user_option(
                'smtp_server')
            if server is None or server == 'localhost':
                raise ValueError(
                    'To send email, a remotely accessible smtp_server (and '
                    'smtp_username and smtp_password, if necessary) must be '
                    'configured in bzr.  See the SMTP server information '
                    'here: https://wiki.canonical.com/EmailSetup .')
            self.vals['smtp_username'] = config.get_user_option(
                'smtp_username')
            self.vals['smtp_password'] = config.get_user_option(
                'smtp_password')
            from_email = config.username()
            if not from_email:
                raise ValueError(
                    'To send email, your bzr email address must be set '
                    '(use ``bzr whoami``).')
            else:
                self.vals['email'] = (
                    from_email.encode('utf8').encode('string-escape'))

        # Get a public key from the agent.
        agent = paramiko.Agent()
        keys = agent.get_keys()
        if len(keys) == 0:
            self.error_and_quit(
                'You must have an ssh agent running with keys installed that '
                'will allow the script to rsync to devpad and get your '
                'branch.\n')
        key = agent.get_keys()[0]
        self.vals['key_type'] = key.get_name()
        self.vals['key'] = key.get_base64()

        # Verify the .ssh config file
        self.ssh_config_file_name = os.path.join(home, '.ssh', 'config')
        if not os.path.exists(self.ssh_config_file_name):
            self.error_and_quit(
                'This script expects to find the .ssh config in %s.  Please '
                'make sure it exists and contains the necessary '
                'configuration to access devpad.' % (
                    self.ssh_config_file_name,))

        # Get the bzr login.
        login = get_lp_login()
        if not login:
            self.error_and_quit(
                'you must have set your launchpad login in bzr.')
        self.vals['launchpad-login'] = login

        # Get the AWS identifier and secret identifier.
        try:
            credentials = EC2Credentials.load_from_file()
        except CredentialsError, e:
            self.error_and_quit(str(e))

        # Make the EC2 connection.
        controller = credentials.connect(self.name)

        # We do this here because it (1) cleans things up and (2) verifies
        # that the account is correctly set up. Both of these are appropriate
        # for initialization.
        #
        # We always recreate the keypairs because there is no way to
        # programmatically retrieve the private key component, unless we
        # generate it.
        controller.delete_previous_key_pair()

        # get the image
        image = controller.acquire_image(machine_id)
        self._instance = EC2Instance(
            self.name, image, instance_type, demo_networks,
            controller, self.vals)
        # now, as best as we can tell, we should be good to go.

    def error_and_quit(self, msg):
        """Print error message and exit."""
        sys.stderr.write(msg)
        sys.exit(1)

    def log(self, msg):
        """Log a message on stdout, flushing afterwards."""
        # XXX: JonathanLange 2009-05-31 bug=383076: This should use Python
        # logging, rather than printing to stdout.
        sys.stdout.write(msg)
        sys.stdout.flush()

    def start(self):
        """Start the EC2 instance."""
        self._instance.start()

    def shutdown(self):
        if self.headless and self._running:
            self.log('letting instance run, to shut down headlessly '
                     'at completion of tests.\n')
            return
        return self._instance.shutdown()

    def configure_system(self):
        # AS ROOT
        self._instance.connect_as_root()
        if self.vals['USER'] == 'gary':
            # This helps gary debug problems others are having by removing
            # much of the initial setup used to work on the original image.
            self._instance.perform('deluser --remove-home gary',
                          ignore_failure=True)
        p = self._instance.perform
        # Let root perform sudo without a password.
        p('echo "root\tALL=NOPASSWD: ALL" >> /etc/sudoers')
        # Add the user.
        p('adduser --gecos "" --disabled-password %(USER)s')
        # Give user sudo without password.
        p('echo "%(USER)s\tALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers')
            # Make /var/launchpad owned by user.
        p('chown -R %(USER)s:%(USER)s /var/launchpad')
        # Clean out left-overs from the instance image.
        p('rm -fr /var/tmp/*')
        # Update the system.
        p('aptitude update')
        p('aptitude -y full-upgrade')
        # Set up ssh for user
        # Make user's .ssh directory
        p('sudo -u %(USER)s mkdir /home/%(USER)s/.ssh')
        sftp = self._instance.ssh.open_sftp()
        remote_ssh_dir = '/home/%(USER)s/.ssh' % self.vals
        # Create config file
        self.log('Creating %s/config\n' % (remote_ssh_dir,))
        ssh_config_source = open(self.ssh_config_file_name)
        config = SSHConfig()
        config.parse(ssh_config_source)
        ssh_config_source.close()
        ssh_config_dest = sftp.open("%s/config" % remote_ssh_dir, 'w')
        ssh_config_dest.write('CheckHostIP no\n')
        ssh_config_dest.write('StrictHostKeyChecking no\n')
        for hostname in ('devpad.canonical.com', 'chinstrap.canonical.com'):
            ssh_config_dest.write('Host %s\n' % (hostname,))
            data = config.lookup(hostname)
            for key in ('hostname', 'gssapiauthentication', 'proxycommand',
                        'user', 'forwardagent'):
                value = data.get(key)
                if value is not None:
                    ssh_config_dest.write('    %s %s\n' % (key, value))
        ssh_config_dest.write('Host bazaar.launchpad.net\n')
        ssh_config_dest.write('    user %(launchpad-login)s\n' % self.vals)
        ssh_config_dest.close()
        # create authorized_keys
        self.log('Setting up %s/authorized_keys\n' % remote_ssh_dir)
        authorized_keys_file = sftp.open(
            "%s/authorized_keys" % remote_ssh_dir, 'w')
        authorized_keys_file.write("%(key_type)s %(key)s\n" % self.vals)
        authorized_keys_file.close()
        sftp.close()
        # Chown and chmod the .ssh directory and contents that we just
        # created.
        p('chown -R %(USER)s:%(USER)s /home/%(USER)s/')
        p('chmod 644 /home/%(USER)s/.ssh/*')
        self.log(
            'You can now use ssh -A %s to log in the instance.\n' %
            self._instance.hostname)
        # give the user permission to do whatever in /var/www
        p('chown -R %(USER)s:%(USER)s /var/www')
        self._instance.ssh.close()

        # AS USER
        self._instance.connect_as_user()
        sftp = self._instance.ssh.open_sftp()
        # Set up bazaar.conf with smtp information if necessary
        if self.email or self.message:
            p('sudo -u %(USER)s mkdir /home/%(USER)s/.bazaar')
            bazaar_conf_file = sftp.open(
                "/home/%(USER)s/.bazaar/bazaar.conf" % self.vals, 'w')
            bazaar_conf_file.write(
                'smtp_server = %(smtp_server)s\n' % self.vals)
            if self.vals['smtp_username']:
                bazaar_conf_file.write(
                    'smtp_username = %(smtp_username)s\n' % self.vals)
            if self.vals['smtp_password']:
                bazaar_conf_file.write(
                    'smtp_password = %(smtp_password)s\n' % self.vals)
            bazaar_conf_file.close()
        # Copy remote ec2-remote over
        self.log('Copying ec2test-remote.py to remote machine.\n')
        sftp.put(
            os.path.join(os.path.dirname(os.path.realpath(__file__)),
                         'ec2test-remote.py'),
            '/var/launchpad/ec2test-remote.py')
        sftp.close()
        # Set up launchpad login and email
        p('bzr launchpad-login %(launchpad-login)s')
        p("bzr whoami '%(email)s'")
        self._instance.ssh.close()

    def prepare_tests(self):
        self._instance.connect_as_user()
        # Clean up the test branch left in the instance image.
        self._instance.perform('rm -rf /var/launchpad/test')
        # get newest sources
        self._instance.run_with_ssh_agent(
            "rsync -avp --partial --delete "
            "--filter='P *.o' --filter='P *.pyc' --filter='P *.so' "
            "devpad.canonical.com:/code/rocketfuel-built/launchpad/sourcecode/* "
            "/var/launchpad/sourcecode/")
        # Get trunk.
        self._instance.run_with_ssh_agent(
            'bzr branch %(trunk_branch)s /var/launchpad/test')
        # Merge the branch in.
        if self.vals['branch'] is not None:
            self._instance.run_with_ssh_agent(
                'cd /var/launchpad/test; bzr merge %(branch)s')
        else:
            self.log('(Testing trunk, so no branch merge.)')
        # Get any new sourcecode branches as requested
        for dest, src in self.branches:
            fulldest = os.path.join('/var/launchpad/test/sourcecode', dest)
            if dest in ('canonical-identity-provider', 'shipit'):
                # These two branches share some of the history with Launchpad.
                # So we create a stacked branch on Launchpad so that the shared
                # history isn't duplicated.
                self._instance.run_with_ssh_agent(
                    'bzr branch --no-tree --stacked %s %s' %
                    (TRUNK_BRANCH, fulldest))
                # The --overwrite is needed because they are actually two
                # different branches (canonical-identity-provider was not
                # branched off launchpad, but some revisions are shared.)
                self._instance.run_with_ssh_agent(
                    'bzr pull --overwrite %s -d %s' % (src, fulldest))
                # The third line is necessary because of the --no-tree option
                # used initially. --no-tree doesn't create a working tree.
                # It only works with the .bzr directory (branch metadata and
                # revisions history). The third line creates a working tree
                # based on the actual branch.
                self._instance.run_with_ssh_agent(
                    'bzr checkout "%s" "%s"' % (fulldest, fulldest))
            else:
                # The "--standalone" option is needed because some branches
                # are/were using a different repository format than Launchpad
                # (bzr-svn branch for example).
                self._instance.run_with_ssh_agent(
                    'bzr branch --standalone %s %s' % (src, fulldest))
        # prepare fresh copy of sourcecode and buildout sources for building
        p = self._instance.perform
        p('rm -rf /var/launchpad/tmp')
        p('mkdir /var/launchpad/tmp')
        p('cp -R /var/launchpad/sourcecode /var/launchpad/tmp/sourcecode')
        p('mkdir /var/launchpad/tmp/eggs')
        self._instance.run_with_ssh_agent(
            'bzr co lp:lp-source-dependencies '
            '/var/launchpad/tmp/download-cache')
        if (self.include_download_cache_changes and
            self.download_cache_additions):
            sftp = self._instance.ssh.open_sftp()
            root = os.path.realpath(
                os.path.join(self.original_branch, 'download-cache'))
            for info in self.download_cache_additions:
                src = os.path.join(root, info[0])
                self.log('Copying %s to remote machine.\n' % (src,))
                sftp.put(
                    src,
                    os.path.join('/var/launchpad/tmp/download-cache', info[0]))
            sftp.close()
        p('/var/launchpad/test/utilities/link-external-sourcecode '
          '-p/var/launchpad/tmp -t/var/launchpad/test'),
        # set up database
        p('/var/launchpad/test/utilities/launchpad-database-setup %(USER)s')
        p('cd /var/launchpad/test && make build')
        p('cd /var/launchpad/test && make schema')
        # close ssh connection
        self._instance.ssh.close()

    def start_demo_webserver(self):
        """Turn ec2 instance into a demo server."""
        self._instance.connect_as_user()
        p = self._instance.perform
        p('mkdir -p /var/tmp/bazaar.launchpad.dev/static')
        p('mkdir -p /var/tmp/bazaar.launchpad.dev/mirrors')
        p('sudo a2enmod proxy > /dev/null')
        p('sudo a2enmod proxy_http > /dev/null')
        p('sudo a2enmod rewrite > /dev/null')
        p('sudo a2enmod ssl > /dev/null')
        p('sudo a2enmod deflate > /dev/null')
        p('sudo a2enmod headers > /dev/null')
        # Install apache config file.
        p('cd /var/launchpad/test/; sudo make install')
        # Use raw string to eliminate the need to escape the backslash.
        # Put eth0's ip address in the /tmp/ip file.
        p(r"ifconfig eth0 | grep 'inet addr' "
          r"| sed -re 's/.*addr:([0-9.]*) .*/\1/' > /tmp/ip")
        # Replace 127.0.0.88 in Launchpad's apache config file with the
        # ip address just stored in the /tmp/ip file. Perl allows for
        # inplace editing unlike sed.
        p('sudo perl -pi -e "s/127.0.0.88/$(cat /tmp/ip)/g" '
          '/etc/apache2/sites-available/local-launchpad')
        # Restart apache.
        p('sudo /etc/init.d/apache2 restart')
        # Build mailman and minified javascript, etc.
        p('cd /var/launchpad/test/; make')
        # Start launchpad in the background.
        p('cd /var/launchpad/test/; make start')
        # close ssh connection
        self._instance.ssh.close()

    def run_tests(self):
        self._instance.connect_as_user()

        # Make sure we activate the failsafe --shutdown feature.  This will
        # make the server shut itself down after the test run completes, or
        # if the test harness suffers a critical failure.
        cmd = ['python /var/launchpad/ec2test-remote.py --shutdown']

        # Do we want to email the results to the user?
        if self.email:
            for email in self.email:
                cmd.append("--email='%s'" % (
                    email.encode('utf8').encode('string-escape'),))

        # Do we want to submit the branch to PQM if the tests pass?
        if self.message is not None:
            cmd.append(
                "--submit-pqm-message='%s'" % (
                    pickle.dumps(
                        self.message).encode(
                        'base64').encode('string-escape'),))

        # Do we want to disconnect the terminal once the test run starts?
        if self.headless:
            cmd.append('--daemon')

        # Which branch do we want to test?
        if self.vals['branch'] is not None:
            branch = self.vals['branch']
            remote_branch = Branch.open(branch)
            branch_revno = remote_branch.revno()
        else:
            branch = self.vals['trunk_branch']
            branch_revno = None
        cmd.append('--public-branch=%s'  % branch)
        if branch_revno is not None:
            cmd.append('--public-branch-revno=%d' % branch_revno)

        # Add any additional options for ec2test-remote.py
        cmd.extend(self.get_remote_test_options())
        self.log(
            'Running tests... (output is available on '
            'http://%s/)\n' % self._instance.hostname)

        # Try opening a browser pointed at the current test results.
        if self.open_browser:
            try:
                import webbrowser
            except ImportError:
                self.log("Could not open web browser due to ImportError.")
            else:
                status = webbrowser.open(self._instance.hostname)
                if not status:
                    self.log("Could not open web browser.")

        # Run the remote script!  Our execution will block here until the
        # remote side disconnects from the terminal.
        self._instance.perform(' '.join(cmd))
        self._running = True

        if not self.headless:
            sftp = self._instance.ssh.open_sftp()
            # We ran to completion locally, so we'll be in charge of shutting
            # down the instance, in case the user has requested a postmortem.
            #
            # We only have 60 seconds to do this before the remote test
            # script shuts the server down automatically.
            self._instance.perform(
                'kill `cat /var/launchpad/ec2test-remote.pid`')

            # deliver results as requested
            if self.file:
                self.log(
                    'Writing abridged test results to %s.\n' % self.file)
                sftp.get('/var/www/summary.log', self.file)
            sftp.close()
        # close ssh connection
        self._instance.ssh.close()

    def get_remote_test_options(self):
        """Return the test command that will be passed to ec2test-remote.py.

        Returns a tuple of command-line options and switches.
        """
        if '--jscheck' in self.test_options:
            # We want to run the JavaScript test suite.
            return ('--jscheck',)
        else:
            # Run the normal testsuite with our Zope testrunner options.
            # ec2test-remote.py wants the extra options to be after a double-
            # dash.
            return ('--', self.test_options)


# XXX: JonathanLange 2009-05-31: Strongly considering turning this into a
# Bazaar plugin -- probably would make the option parsing and validation
# easier.

def main():
    parser = optparse.OptionParser(
        usage="%prog [options] [branch]",
        description=(
            "Check out a Launchpad branch and run all tests on an Amazon "
            "EC2 instance."))
    parser.add_option(
        '-f', '--file', dest='file', default=None,
        help=('Store abridged test results in FILE.'))
    parser.add_option(
        '-n', '--no-email', dest='no_email', default=False,
        action='store_true',
        help=('Do not try to email results.'))
    parser.add_option(
        '-e', '--email', action='append', dest='email', default=None,
        help=('Email address to which results should be mailed.  Defaults to '
              'the email address from `bzr whoami`. May be supplied multiple '
              'times. The first supplied email address will be used as the '
              'From: address.'))
    parser.add_option(
        '-o', '--test-options', dest='test_options', default='-vv',
        help=('Test options to pass to the remote test runner.  Defaults to '
              "``-o '-vv'``.  For instance, to run specific tests, you might "
              "use ``-o '-vvt my_test_pattern'``."))
    parser.add_option(
        '-b', '--branch', action='append', dest='branches',
        help=('Branches to include in this run in sourcecode. '
              'If the argument is only the project name, the trunk will be '
              'used (e.g., ``-b launchpadlib``).  If you want to use a '
              'specific branch, if it is on launchpad, you can usually '
              'simply specify it instead (e.g., '
              '``-b lp:~username/launchpadlib/branchname``).  If this does '
              'not appear to work, or if the desired branch is not on '
              'launchpad, specify the project name and then the branch '
              'after an equals sign (e.g., '
              '``-b launchpadlib=lp:~username/launchpadlib/branchname``). '
              'Branches for multiple projects may be specified with '
              'multiple instances of this option. '
              'You may also use this option to specify the branch of launchpad '
              'into which your branch may be merged.  This defaults to %s. '
              'Because typically the important branches of launchpad are owned '
              'by the launchpad-pqm user, you can shorten this to only the '
              'branch name, if desired, and the launchpad-pqm user will be '
              'assumed.  For instance, if you specify '
              '``-b launchpad=db-devel`` then this is equivalent to '
              '``-b lp:~launchpad-pqm/launchpad/db-devel``, or the even longer'
              '``-b launchpad=lp:~launchpad-pqm/launchpad/db-devel``.'
              % (TRUNK_BRANCH,)))
    parser.add_option(
        '-t', '--trunk', dest='trunk', default=False,
        action='store_true',
        help=('Run the trunk as the branch'))
    parser.add_option(
        '-s', '--submit-pqm-message', dest='pqm_message', default=None,
        help=('A pqm message to submit if the test run is successful.  If '
              'provided, you will be asked for your GPG passphrase before '
              'the test run begins.'))
    parser.add_option(
        '--pqm-public-location', dest='pqm_public_location', default=None,
        help=('The public location for the pqm submit, if a pqm message is '
              'provided (see --submit-pqm-message).  If this is not provided, '
              'for local branches, bzr configuration is consulted; for '
              'remote branches, it is assumed that the remote branch *is* '
              'a public branch.'))
    parser.add_option(
        '--pqm-submit-location', dest='pqm_submit_location', default=None,
        help=('The submit location for the pqm submit, if a pqm message is '
              'provided (see --submit-pqm-message).  If this option is not '
              'provided, the script will look for an explicitly specified '
              'launchpad branch using the -b/--branch option; if that branch '
              'was specified and is owned by the launchpad-pqm user on '
              'launchpad, it is used as the pqm submit location. Otherwise, '
              'for local branches, bzr configuration is consulted; for '
              'remote branches, it is assumed that the submit branch is %s.'
              % (TRUNK_BRANCH,)))
    parser.add_option(
        '--pqm-email', dest='pqm_email', default=None,
        help=('Specify the email address of the PQM you are submitting to. '
              'If the branch is local, then the bzr configuration is '
              'consulted; for remote branches "Launchpad PQM '
              '<launchpad@pqm.canonical.com>" is used by default.'))
    parser.add_option(
        '-m', '--machine', dest='machine_id', default=None,
        help=('The AWS machine identifier (AMID) on which to base this run. '
              'You should typically only have to supply this if you are '
              'testing new AWS images. Defaults to trying to find the most '
              'recent one with an approved owner.'))
    parser.add_option(
        '-i', '--instance', dest='instance_type',
        default=DEFAULT_INSTANCE_TYPE,
        help=('The AWS instance type on which to base this run. '
              'Available options are %r. Defaults to `%s`.' %
              (AVAILABLE_INSTANCE_TYPES, DEFAULT_INSTANCE_TYPE)))
    parser.add_option(
        '-p', '--postmortem', dest='postmortem', default=False,
        action='store_true',
        help=('Drop to interactive prompt after the test and before shutting '
              'down the instance for postmortem analysis of the EC2 instance '
              'and/or of this script.'))
    parser.add_option(
        '--headless', dest='headless', default=False,
        action='store_true',
        help=('After building the instance and test, run the remote tests '
              'headless.  Cannot be used with postmortem '
              'or file.'))
    parser.add_option(
        '-d', '--debug', dest='debug', default=False,
        action='store_true',
        help=('Drop to pdb trace as soon as possible.'))
    # Use tabs to force a newline in the help text.
    fake_newline = "\t\t\t\t\t\t\t"
    parser.add_option(
        '--demo', action='append', dest='demo_networks',
        help=("Don't run tests. Instead start a demo instance of Launchpad. "
              "You can allow multiple networks to access the demo by "
              "repeating the argument." + fake_newline +
              "Example: --demo 192.168.1.100 --demo 10.1.13.0/24" +
              fake_newline +
              "See" + fake_newline +
              "https://wiki.canonical.com/Launchpad/EC2Test/ForDemos" ))
    parser.add_option(
        '--open-browser', dest='open_browser', default=False,
        action='store_true',
        help=('Open the results page in your default browser'))
    parser.add_option(
        '-c', '--include-download-cache-changes',
        dest='include_download_cache_changes', action='store_true',
        help=('Include any changes in the download cache (added or unknown) '
              'in the download cache of the test run.  Note that, if you have '
              'any changes in your download cache, trying to submit to pqm '
              'will always raise an error.  Also note that, if you have any '
              'changes in your download cache, you must explicitly choose to '
              'include or ignore the changes.'))
    parser.add_option(
        '-g', '--ignore-download-cache-changes',
        dest='include_download_cache_changes', action='store_false',
        help=('Ignore any changes in the download cache (added or unknown) '
              'in the download cache of the test run.  Note that, if you have '
              'any changes in your download cache, trying to submit to pqm '
              'will always raise an error.  Also note that, if you have any '
              'changes in your download cache, you must explicitly choose to '
              'include or ignore the changes.'))
    options, args = parser.parse_args()
    if options.debug:
        import pdb; pdb.set_trace()
    if options.demo_networks:
        # We need the postmortem console to open the ec2 instance's
        # network access, and to keep the ec2 instance from being shutdown.
        options.postmortem = True
    if len(args) == 1:
        if options.trunk:
            parser.error(
                'Cannot supply both a branch and the --trunk argument.')
        branch = args[0]
    elif len(args) > 1:
        parser.error('Too many arguments.')
    elif options.trunk:
        branch = None
    else:
        branch = '.'
    if ((options.postmortem or options.file or options.demo_networks)
        and options.headless):
        parser.error(
            'Headless mode currently does not support postmortem, file '
            'or demo options.')
    if options.no_email:
        if options.email:
            parser.error(
                'May not supply both --no-email and an --email address')
        email = False
    else:
        email = options.email
        if email is None:
            email = True
    if options.instance_type not in AVAILABLE_INSTANCE_TYPES:
        parser.error('Unknown instance type.')
    if options.branches is None:
        branches = ()
    else:
        branches = [data.split('=', 1) for data in options.branches]
    runner = EC2TestRunner(
        branch, email=email, file=options.file,
        test_options=options.test_options, headless=options.headless,
        branches=branches,
        machine_id=options.machine_id, instance_type=options.instance_type,
        pqm_message=options.pqm_message,
        pqm_public_location=options.pqm_public_location,
        pqm_submit_location=options.pqm_submit_location,
        demo_networks=options.demo_networks,
        open_browser=options.open_browser, pqm_email=options.pqm_email,
        include_download_cache_changes=options.include_download_cache_changes,
        )
    e = None
    try:
        try:
            runner.start()
            runner.configure_system()
            runner.prepare_tests()
            if options.demo_networks:
                runner.start_demo_webserver()
            else:
                result = runner.run_tests()
        except Exception, e:
            # If we are running in demo or postmortem mode, it is really
            # helpful to see if there are any exceptions before it waits
            # in the console (in the finally block), and you can't figure
            # out why it's broken.
            traceback.print_exc()
    finally:
        try:
            # XXX: JonathanLange 2009-06-02: Blackbox alert! This gets at the
            # private _instance variable of runner. Instead, it should do
            # something smarter. For example, the demo networks stuff could be
            # extracted out to different, non-TestRunner class that has an
            # instance.
            if options.demo_networks and runner._instance is not None:
                demo_network_string = '\n'.join(
                    '  ' + network for network in options.demo_networks)
                # XXX: JonathanLange 2009-06-02: Blackbox alert! See above.
                ec2_ip = socket.gethostbyname(runner._instance.hostname)
                print (
                    "\n\n"
                    "********************** DEMO *************************\n"
                    "It may take 20 seconds for the demo server to start up."
                    "\nTo demo to other users, you still need to open up\n"
                    "network access to the ec2 instance from their IPs by\n"
                    "entering command like this in the interactive python\n"
                    "interpreter at the end of the setup. "
                    "\n  runner.security_group.authorize("
                    "'tcp', 443, 443, '10.0.0.5/32')\n\n"
                    "These demo networks have already been granted access on "
                    "port 80 and 443:\n" + demo_network_string +
                    "\n\nYou also need to edit your /etc/hosts to point\n"
                    "launchpad.dev at the ec2 instance's IP like this:\n"
                    "  " + ec2_ip + "    launchpad.dev\n\n"
                    "See "
                    "<https://wiki.canonical.com/Launchpad/EC2Test/ForDemos>."
                    "\n*****************************************************"
                    "\n\n")
             # XXX: JonathanLange 2009-06-02: Blackbox alert! This uses the
             # private '_instance' variable and assumes that the runner has
             # exactly one instance.
            if options.postmortem and runner._instance is not None:
                console = code.InteractiveConsole({'runner': runner, 'e': e})
                console.interact((
                    'Postmortem Console.  EC2 instance is not yet dead.\n'
                    'It will shut down when you exit this prompt (CTRL-D).\n'
                    '\n'
                    'Tab-completion is enabled.'
                    '\n'
                    'Test runner instance is available as `runner`.\n'
                    'Also try these:\n'
                    '  http://%(dns)s/current_test.log\n'
                    '  ssh -A %(dns)s') %
                                 # XXX: JonathanLange 2009-06-02: Blackbox
                                 # alert! See above.
                                 {'dns': runner._instance.hostname})
                print 'Postmortem console closed.'
        finally:
            runner.shutdown()
