#! /usr/bin/python2.4
# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

__metaclass__ = type

import _pythonpath

# This script merges POTMsgSets for sharing POTemplates.  This involves
# deleting records that we'd never delete otherwise.  So before running,
# make sure rosettaadmin has the privileges to delete POTMsgSets and
# TranslationTemplateItems:
#
# GRANT DELETE ON POTMsgSET TO rosettaadmin;
# GRANT DELETE ON  TranslationTemplateItem TO rosettaadmin; 

from canonical.launchpad.scripts.message_sharing_migration import (
    MergePOTMsgSets)


if __name__ == '__main__':
    script = MergePOTMsgSets(
        'canonical.launchpad.scripts.merge-potmsgsets', dbuser='rosettaadmin')
    script.run()
