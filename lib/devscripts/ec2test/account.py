# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A representation of an Amazon Web Services account."""

__metaclass__ = type
__all__ = [
    'EC2Account',
    ]

import cStringIO
import re
import sys
import urllib

from datetime import datetime, timedelta

from boto.exception import EC2ResponseError
from devscripts.ec2test.utils import (
    find_datetime_string, make_datetime_string, make_random_string)

import paramiko

VALID_AMI_OWNERS = (
    255383312499, # gary
    559320013529, # flacoste
    200337130613, # mwhudson
    # ...anyone else want in on the fun?
    )


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
        self.unique_name = "%s-%s-%s" % (
            self.name, make_datetime_string(), make_random_string())
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
        key_pair = self.conn.create_key_pair(self.unique_name)
        return paramiko.RSAKey.from_private_key(
            cStringIO.StringIO(key_pair.material.encode('ascii')))

    def delete_previous_key_pairs(self):
        """Delete previously used keypairs, if found."""
        expire_before = datetime.utcnow() - timedelta(hours=6)
        try:
            for key_pair in self.conn.get_all_key_pairs():
                if key_pair.name == self.name:
                    self.log('Deleting key pair %r\n' % key_pair.name)
                    key_pair.delete()
                elif key_pair.name.startswith(self.name):
                    creation_datetime = find_datetime_string(key_pair.name)
                    if creation_datetime is None:
                        self.log('Found key pair %r without creation date; '
                                 'leaving.\n' % key_pair.name)
                    elif creation_datetime >= expire_before:
                        self.log('Found recent key pair %r; '
                                 'leaving\n' % key_pair.name)
                    else:
                        self.log('Deleting old key pair %r\n' % key_pair.name)
                        key_pair.delete()
                else:
                    self.log('Found other key pair %r; '
                             'leaving.\n' % key_pair.name)
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
