# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Attribute

from canonical.launchpad.interfaces.rosettastats import IRosettaStats

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

__metaclass__ = type

__all__ = ('IDistroReleaseLanguage', )

class IDistroReleaseLanguage(IRosettaStats):
    """A placeholder for the statistics in the translation of a
    distrorelease into a language, for example, Ubuntu Hoary into French.
    This exists to cache stats, and be a useful object for traversal in
    Rosetta."""

    id = Attribute("A unique ID")

    language = Attribute("The language.")

    distrorelease = Attribute("The distro release which has been "
        "translated.")

    dateupdated = Attribute("The date these statistics were last updated.")

    title = Attribute("The title.")

    pofiles = Attribute("The set of pofiles in this distrorelease for this "
        "language.")

    translator_count = Attribute("The number of registered translators "
        "for this language in the distribution.")

    contributor_count = Attribute("The number of contributors in total "
        "for this language in the distribution.")


