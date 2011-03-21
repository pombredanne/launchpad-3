# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Enumerations relating to Bazaar formats."""

__metaclass__ = type
__all__ = [
    'BranchFormat',
    'ControlFormat',
    'CURRENT_BRANCH_FORMATS',
    'CURRENT_REPOSITORY_FORMATS',
    'get_branch_formats',
    'RepositoryFormat',
    ]


# FIRST Ensure correct plugins are loaded. Do not delete this comment or the
# line below this comment.
import lp.codehosting

from bzrlib.branch import (
    BranchReferenceFormat,
    BzrBranchFormat4,
    BzrBranchFormat5,
    BzrBranchFormat6,
    BzrBranchFormat7,
    )
from bzrlib.bzrdir import (
    BzrDirFormat4,
    BzrDirFormat5,
    BzrDirFormat6,
    BzrDirMetaFormat1,
    )
from bzrlib.plugins.loom.branch import (
    BzrBranchLoomFormat1,
    BzrBranchLoomFormat6,
    )
from bzrlib.repofmt.groupcompress_repo import RepositoryFormat2a
from bzrlib.repofmt.knitrepo import (
    RepositoryFormatKnit1,
    RepositoryFormatKnit3,
    RepositoryFormatKnit4,
    )
from bzrlib.repofmt.pack_repo import (
    RepositoryFormatKnitPack1,
    RepositoryFormatKnitPack3,
    RepositoryFormatKnitPack4,
    RepositoryFormatKnitPack5,
    )
from bzrlib.repofmt.weaverepo import (
    RepositoryFormat4,
    RepositoryFormat5,
    RepositoryFormat6,
    RepositoryFormat7,
    )
from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )


def _format_enum(num, format, format_string=None, description=None):
    instance = format()
    if format_string is None:
        format_string = instance.get_format_string()
    if description is None:
        description = instance.get_format_description()
    return DBItem(num, format_string, description)


class BazaarFormatEnum(DBEnumeratedType):
    """Base class for the format enums."""

    @classmethod
    def get_enum(klass, format_name):
        """Find the matching enum value for the format name specified."""
        for value in klass.items:
            if value.title == format_name:
                return value
        else:
            return klass.UNRECOGNIZED


class BranchFormat(BazaarFormatEnum):
    """Branch on-disk format.

    This indicates which (Bazaar) format is used on-disk.  The list must be
    updated as the list of formats supported by Bazaar is updated.
    """

    UNRECOGNIZED = DBItem(1000, '!Unrecognized!', 'Unrecognized format')

    # Branch 4 was only used with all-in-one formats, so it didn't have its
    # own marker.  It was implied by the control directory marker.
    BZR_BRANCH_4 = _format_enum(
        4, BzrBranchFormat4, 'Fake Bazaar Branch 4 marker')

    BRANCH_REFERENCE = _format_enum(1, BranchReferenceFormat)

    BZR_BRANCH_5 = _format_enum(5, BzrBranchFormat5)

    BZR_BRANCH_6 = _format_enum(6, BzrBranchFormat6)

    BZR_BRANCH_7 = _format_enum(7, BzrBranchFormat7)

    # Format string copied from Bazaar 1.15 code. This should be replaced with
    # a line that looks like _format_enum(8, BzrBranchFormat8) when we upgrade
    # to Bazaar 1.15.
    BZR_BRANCH_8 = DBItem(
        8, "Bazaar Branch Format 8 (needs bzr 1.15)\n", "Branch format 8")

    BZR_LOOM_1 = _format_enum(101, BzrBranchLoomFormat1)

    BZR_LOOM_2 = _format_enum(106, BzrBranchLoomFormat6)

    BZR_LOOM_3 = DBItem(
        107, "Bazaar-NG Loom branch format 7\n", "Loom branch format 7")


class RepositoryFormat(BazaarFormatEnum):
    """Repository on-disk format.

    This indicates which (Bazaar) format is used on-disk.  The list must be
    updated as the list of formats supported by Bazaar is updated.
    """

    UNRECOGNIZED = DBItem(1000, '!Unrecognized!', 'Unrecognized format')

    # Repository formats prior to format 7 had no marker because they
    # were implied by the control directory format.
    BZR_REPOSITORY_4 = _format_enum(
        4, RepositoryFormat4, 'Fake Bazaar repository 4 marker')

    BZR_REPOSITORY_5 = _format_enum(
        5, RepositoryFormat5, 'Fake Bazaar repository 5 marker')

    BZR_REPOSITORY_6 = _format_enum(
        6, RepositoryFormat6, 'Fake Bazaar repository 6 marker')

    BZR_REPOSITORY_7 = _format_enum(7, RepositoryFormat7)

    BZR_KNIT_1 = _format_enum(101, RepositoryFormatKnit1)

    BZR_KNIT_3 = _format_enum(103, RepositoryFormatKnit3)

    BZR_KNIT_4 = _format_enum(104, RepositoryFormatKnit4)

    BZR_KNITPACK_1 = _format_enum(201, RepositoryFormatKnitPack1)

    BZR_KNITPACK_3 = _format_enum(203, RepositoryFormatKnitPack3)

    BZR_KNITPACK_4 = _format_enum(204, RepositoryFormatKnitPack4)

    BZR_KNITPACK_5 = _format_enum(
        205, RepositoryFormatKnitPack5,
        description='Packs 5 (needs bzr 1.6, supports stacking)\n')

    BZR_KNITPACK_5_RRB = DBItem(206,
        'Bazaar RepositoryFormatKnitPack5RichRoot (bzr 1.6)\n',
        'Packs 5-Rich Root (needs bzr 1.6, supports stacking)'
        )

    BZR_KNITPACK_5_RR = DBItem(207,
        'Bazaar RepositoryFormatKnitPack5RichRoot (bzr 1.6.1)\n',
        'Packs 5 rich-root (adds stacking support, requires bzr 1.6.1)',
        )

    BZR_KNITPACK_6 = DBItem(208,
        'Bazaar RepositoryFormatKnitPack6 (bzr 1.9)\n',
        'Packs 6 (uses btree indexes, requires bzr 1.9)'
        )

    BZR_KNITPACK_6_RR = DBItem(209,
        'Bazaar RepositoryFormatKnitPack6RichRoot (bzr 1.9)\n',
        'Packs 6 rich-root (uses btree indexes, requires bzr 1.9)'
        )

    BZR_PACK_DEV_0 = DBItem(300,
        'Bazaar development format 0 (needs bzr.dev from before 1.3)\n',
        'Development repository format, currently the same as pack-0.92',
        )

    BZR_PACK_DEV_0_SUBTREE = DBItem(301,
        'Bazaar development format 0 with subtree support (needs bzr.dev from'
        ' before 1.3)\n',
        'Development repository format, currently the same as'
        ' pack-0.92-subtree\n',
        )

    BZR_DEV_1 = DBItem(302,
        "Bazaar development format 1 (needs bzr.dev from before 1.6)\n",
        "Development repository format, currently the same as "
        "pack-0.92 with external reference support.\n"
        )

    BZR_DEV_1_SUBTREE = DBItem(303,
        "Bazaar development format 1 with subtree support "
        "(needs bzr.dev from before 1.6)\n",
        "Development repository format, currently the same as "
        "pack-0.92-subtree with external reference support.\n"
        )

    BZR_DEV_2 = DBItem(304,
        "Bazaar development format 2 (needs bzr.dev from before 1.8)\n",
        "Development repository format, currently the same as "
            "1.6.1 with B+Trees.\n"
        )

    BZR_DEV_2_SUBTREE = DBItem(305,
       "Bazaar development format 2 with subtree support "
        "(needs bzr.dev from before 1.8)\n",
        "Development repository format, currently the same as "
        "1.6.1-subtree with B+Tree indices.\n"
        )

    BZR_CHK1 = DBItem(400,
        "Bazaar development format - group compression and chk inventory"
        " (needs bzr.dev from 1.14)\n",
        "Development repository format - rich roots, group compression"
        " and chk inventories\n",
        )

    BZR_CHK2 = DBItem(410,
        "Bazaar development format - chk repository with bencode revision"
        " serialization (needs bzr.dev from 1.16)\n",
        "Development repository format - rich roots, group compression"
        " and chk inventories\n",
        )

    BZR_CHK_2A = _format_enum(415, RepositoryFormat2a)


class ControlFormat(BazaarFormatEnum):
    """Control directory (BzrDir) format.

    This indicates what control directory format is on disk.  Must be updated
    as new formats become available.
    """

    UNRECOGNIZED = DBItem(1000, '!Unrecognized!', 'Unrecognized format')

    BZR_DIR_4 = _format_enum(4, BzrDirFormat4)

    BZR_DIR_5 = _format_enum(5, BzrDirFormat5)

    BZR_DIR_6 = _format_enum(6, BzrDirFormat6)

    BZR_METADIR_1 = _format_enum(1, BzrDirMetaFormat1)


# A tuple of branch formats that should not suggest upgrading.
CURRENT_BRANCH_FORMATS = (
    None,
    BranchFormat.UNRECOGNIZED,
    BranchFormat.BRANCH_REFERENCE,
    BranchFormat.BZR_BRANCH_7,
    BranchFormat.BZR_BRANCH_8,
    BranchFormat.BZR_LOOM_1,
    BranchFormat.BZR_LOOM_2,
    BranchFormat.BZR_LOOM_3)

# A tuple of repository formats that should not suggest upgrading.
CURRENT_REPOSITORY_FORMATS = (
    None,
    RepositoryFormat.UNRECOGNIZED,
    RepositoryFormat.BZR_PACK_DEV_0,
    RepositoryFormat.BZR_PACK_DEV_0_SUBTREE,
    RepositoryFormat.BZR_DEV_1,
    RepositoryFormat.BZR_DEV_1_SUBTREE,
    RepositoryFormat.BZR_DEV_2,
    RepositoryFormat.BZR_DEV_2_SUBTREE,
    RepositoryFormat.BZR_CHK1,
    RepositoryFormat.BZR_CHK2,
    RepositoryFormat.BZR_CHK_2A)


def get_branch_formats(bzr_branch):
    """Return a tuple of format enumerations for the bazaar branch.

    :returns: tuple of (ControlFormat, BranchFormat, RepositoryFormat)
    """
    control_string = bzr_branch.bzrdir._format.get_format_string()
    branch_string = bzr_branch._format.get_format_string()
    repository_string = bzr_branch.repository._format.get_format_string()
    return (ControlFormat.get_enum(control_string),
            BranchFormat.get_enum(branch_string),
            RepositoryFormat.get_enum(repository_string))
