# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A representation of an Amazon Web Services account."""

__metaclass__ = type
__all__ = [
    'EC2Account',
    'VALID_AMI_OWNERS',
    ]

from collections import defaultdict
import cStringIO
from datetime import datetime
from operator import itemgetter
import re
import sys
import urllib

from boto.exception import EC2ResponseError
from devscripts.ec2test.session import EC2SessionName
import paramiko


VALID_AMI_OWNERS = {
    # Amazon account number: name/nickname (only for logging).
    '255383312499': 'gary',
    '559320013529': 'flacoste',
    '200337130613': 'mwhudson',
    '889698597288': 'henninge',
    '366009196755': 'salgado',
    '036590675370': 'jml',
    '038531743404': 'jelmer',
    '444667466231': 'allenap',
    '441991801793': 'gmb',
    '005470753809': 'bigjools',
    '967591634984': 'jtv',
    '507541322704': 'sinzui',
    '424228475252': 'wallyworld',
    '292290876294': 'stevenk',
    '259696152397': 'bac',
    # ...anyone else want in on the fun?
    }

AUTH_FAILURE_MESSAGE = """\
POSSIBLE CAUSES OF ERROR:
- Did you sign up for EC2?
- Did you put a credit card number in your AWS account?
Please double-check before reporting a problem.
"""


def get_ip():
    """Uses AWS checkip to obtain this machine's IP address.

    Consults an external website to determine the public IP address of this
    machine.

    :return: This machine's net-visible IP address as a string.
    """
    return urllib.urlopen('http://checkip.amazonaws.com').read().strip()


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

    def _find_expired_artifacts(self, artifacts):
        now = datetime.utcnow()
        for artifact in artifacts:
            session_name = EC2SessionName(artifact.name)
            if (session_name in (self.name, self.name.base) or (
                    session_name.base == self.name.base and
                    session_name.expires is not None and
                    session_name.expires < now)):
                yield artifact

    def acquire_security_group(self, demo_networks=None):
        """Get a security group with the appropriate configuration.

        "Appropriate" means configured to allow this machine to connect via
        SSH, HTTP and HTTPS.

        The name of the security group is the `EC2Account.name` attribute.

        :return: A boto security group.
        """
        if demo_networks is None:
            demo_networks = []
        # Create the security group.
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

    def delete_previous_security_groups(self):
        """Delete previously used security groups, if found."""
        expired_groups = self._find_expired_artifacts(
            self.conn.get_all_security_groups())
        for group in expired_groups:
            try:
                group.delete()
            except EC2ResponseError, e:
                if e.code != 'InvalidGroup.InUse':
                    raise
                self.log('Cannot delete; security group '
                         '%r in use.\n' % group.name)
            else:
                self.log('Deleted security group %r.\n' % group.name)

    def acquire_private_key(self):
        """Create & return a new key pair for the test runner."""
        key_pair = self.conn.create_key_pair(self.name)
        return paramiko.RSAKey.from_private_key(
            cStringIO.StringIO(key_pair.material.encode('ascii')))

    def delete_previous_key_pairs(self):
        """Delete previously used keypairs, if found."""
        expired_key_pairs = self._find_expired_artifacts(
            self.conn.get_all_key_pairs())
        for key_pair in expired_key_pairs:
            try:
                key_pair.delete()
            except EC2ResponseError, e:
                if e.code != 'InvalidKeyPair.NotFound':
                    if e.code == 'AuthFailure':
                        # Inserted because of previous support issue.
                        self.log(AUTH_FAILURE_MESSAGE)
                    raise
                self.log('Cannot delete; key pair not '
                         'found %r\n' % key_pair.name)
            else:
                self.log('Deleted key pair %r.\n' % key_pair.name)

    def collect_garbage(self):
        """Remove any old keys and security groups."""
        self.delete_previous_security_groups()
        self.delete_previous_key_pairs()

    def find_images(self):
        # We are trying to find an image that has a location that matches a
        # regex (see definition of _image_match, above). Part of that regex is
        # expected to be an integer with the semantics of a revision number.
        # The image location with the highest revision number is the one that
        # should be chosen. Because AWS does not guarantee that two images
        # cannot share a location string, we need to make sure that the search
        # result for this image is unique, or throw an error because the
        # choice of image is ambiguous.
        results = defaultdict(list)

        # Find the images with the highest revision numbers and locations that
        # match the regex.
        images = self.conn.get_all_images(owners=tuple(VALID_AMI_OWNERS))
        for image in images:
            match = self._image_match(image.location)
            if match is not None:
                revision = int(match.group(1))
                results[revision].append(image)

        return sorted(results.iteritems(), key=itemgetter(0), reverse=True)

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

        images_by_revision = self.find_images()
        if len(images_by_revision) == 0:
            raise RuntimeError(
                "You don't have access to a test-runner image.\n"
                "Request access and try again.\n")

        revision, images = images_by_revision[0]
        if len(images) > 1:
            raise ValueError(
                'More than one image of revision %d found: %r' % (
                    revision, images))

        self.log('Using machine image version %d\n' % revision)
        return images[0]
