#!/usr/bin/env python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os
import pprint
import re
import sys

import boto

owners = {
    'gary': 255383312499,
    'francis': 559320013529}

_image_match = re.compile(
    r'launchpad-ec2test(\d+)/image.manifest.xml$').match

if __name__ == '__main__':
    if len(sys.argv) == 1:
        owner = os.environ['USER']
    elif len(sys.argv) == 2:
        owner = sys.argv[1]
    else:
        raise RuntimeError('Too many arguments')
    try:
        owner = int(owner)
    except ValueError:
        owner = owners[owner]
    # Get the AWS identifier and secret identifier.
    aws_id = os.path.join(os.environ['HOME'], '.ec2', 'aws_id')
    if not os.path.exists(aws_id):
        raise RuntimeError(
            "Please put your aws access key identifier and secret access "
            "key identifier in %s. (On two lines).\n" % (aws_id,))
    aws_file = open(aws_id, 'r')
    try:
        identifier = aws_file.readline().strip()
        secret = aws_file.readline().strip()
    finally:
        aws_file.close()
    # Make the EC2 connection.
    conn = boto.connect_ec2(identifier, secret)
    # get images
    images = {}
    for image in conn.get_all_images(owners=owners.values()):
        match = _image_match(image.location)
        if match:
            val = int(match.group(1))
            if val not in images:
                images[val] = [image]
            else:
                images[val].append(image)
    images = images.items()
    images.sort()
    # set
    last, recent = images[-2:]
    for tmp in (last, recent):
        if len(tmp[1]) > 1:
            raise ValueError(
                'more than one image of value %d found: %r' % tmp)
    recent = recent[1][0]
    last = last[1][0]
    perms = last.get_launch_permissions()
    perms['user_ids'].extend(owners.values())
    recent.set_launch_permissions(**perms)
    # done
    pprint.pprint(recent.get_launch_permissions())
