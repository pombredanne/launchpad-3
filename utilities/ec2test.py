#!/bin/sh

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

exec $(dirname $0)/ec2 test "$@"
