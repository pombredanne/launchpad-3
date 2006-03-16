# Copyright 2006 Canonical Ltd.  All rights reserved.

from canonical.launchpad.scripts.supermirror.bzr_5_6 import BZR_5_6


class BranchFactory:
# XXX At the time this  was written it was meant to be a garbage
# collectable object. It could have just as easily been just a standalone
# function... Its a moot point anyways, as when bzr_5_6 get refactored into
# GenericBranch, there won't be much of a need for a factory anyways -
# jblack 2006-05-13

    def produce(self, src, dest=None, type = None):
        """Production facility for branch factory.
        
        This method Examines the location for a branch and returns the
        actual supermirror branch object
        @param: src - the source location for the branch
        @param: dest - the optional location to push the branch to
        """
        if type is not None:
            if type == "bzr_5_6":
                return BZR_5_6(src, dest)
            return None
        else:
            prospect = BZR_5_6(src, dest)
            if prospect.supportsFormat() is True:
                return prospect

        return None
