#!/bin/bash
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
#
# Outputs the contents of the OOPS report for a given OOPS ID.

OOPS_ID=$1
grep -rl "$OOPS_ID" /var/tmp/lperr* | xargs less
