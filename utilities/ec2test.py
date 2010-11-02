#!/bin/sh

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

echo "You should run $(dirname $0)/ec2 test" $@ "instead." >/dev/null 1>&2
echo "Waiting for 5 seconds in case you're not reading this." >/dev/null 1>&2
sleep 5

exec $(dirname $0)/ec2 test "$@"
