# Copyright 2004 Canonical Ltd.  All rights reserved.

"""Browser views for builders."""

__metaclass__ = type

__all__ = ['BuilderSetNavigation',
           'BuilderSetFacets',
           'BuilderSetOverviewMenu',
           'BuilderSetView',
           'BuilderSetAddView',
           'BuilderNavigation',
           'BuilderFacets',
           'BuilderOverviewMenu',
           'BuilderView']

import datetime
import pytz

from sqlobject import SQLObjectNotFound

import zope.security.interfaces
from zope.component import getUtility
from zope.event import notify
from zope.app.form.browser.add import AddView
from zope.app.event.objectevent import ObjectCreatedEvent

from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

from canonical.launchpad.browser.build import BuildRecordsView

from canonical.launchpad.interfaces import (
    IPerson, IBuilderSet, IBuilder, IBuildSet
    )

from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, GetitemNavigation, stepthrough, Link,
    ApplicationMenu, enabled_with_permission)


class BuilderSetNavigation(GetitemNavigation):
    """Navigation methods for IBuilderSet."""
    usedfor = IBuilderSet

    def breadcrumb(self):
        return 'Build Farm'

    @stepthrough('+build')
    def traverse_build(self, name):
        try:
            build_id = int(name)
        except ValueError:
            return None
        try:
            return getUtility(IBuildSet).getByBuildID(build_id)
        except SQLObjectNotFound:
            return None


class BuilderNavigation(GetitemNavigation):
    """Navigation methods for IBuilder."""
    usedfor = IBuilder

    def breadcrumb(self):
        return self.context.title


class BuilderSetFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an IBuilderSet."""
    enable_only = ['overview']

    usedfor = IBuilderSet


class BuilderFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an IBuilder."""
    enable_only = ['overview']

    usedfor = IBuilder


class BuilderSetOverviewMenu(ApplicationMenu):
    """Overview Menu for IBuilderSet."""
    usedfor = IBuilderSet
    facet = 'overview'
    links = ['add']

    @enabled_with_permission('launchpad.Admin')
    def add(self):
        text = 'Add New Builder'
        return Link('+new', text, icon='add')


class BuilderOverviewMenu(ApplicationMenu):
    """Overview Menu for IBuilder."""
    usedfor = IBuilder
    facet = 'overview'
    links = ['edit', 'mode', 'cancel']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Edit Details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def mode(self):
        text = 'Change Mode'
        return Link('+mode', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def cancel(self):
        text = 'Cancel Current Job'
        return Link('+cancel', text, icon='edit')


class CommonBuilderView:
    """Common builder methods used in this file."""

    def now(self):
        """Offers the timestamp for page rendering."""
        UTC = pytz.timezone('UTC')
        return datetime.datetime.now(UTC)


class BuilderSetView(CommonBuilderView):
    """Default BuilderSet view class

    Simply provides CommonBuilderView for the BuilderSet pagetemplate.
    """
    __used_for__ = IBuilderSet


class BuilderView(CommonBuilderView, BuildRecordsView):
    """Default Builder view class

    Implements useful actions and colect useful set for the pagetemplate.
    """
    __used_for__ = IBuilder

    def cancelBuildJob(self):
        """Cancel curent job in builder."""
        builder_id = self.request.form.get('BUILDERID')
        if not builder_id:
            return
        # XXX cprov 20051014
        # The 'self.context.slave.abort()' seems to work with the new
        # BuilderSlave class added by dsilvers, but I won't release it
        # until we can test it properly, since we can only 'abort' slaves
        # in BUILDING state it does depends of the major issue for testing
        # Auto Build System, getting slave building something sane. 
        return '<p>Cancel (%s). Not implemented yet</p>' % builder_id

    def showBuilderInfo(self):
        """Hide Builder info, see BuildRecordsView for further details"""
        return False

class BuilderSetAddView(AddView):
    """Builder add view

    Extends zope AddView and uses IBuilderSet utitlity to create a new IBuilder
    """
    __used_for__ = IBuilderSet

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # add the owner information for the product
        owner = IPerson(self.request.principal, None)
        if not owner:
            raise zope.security.interfaces.Unauthorized(
                "Need an authenticated Launchpad owner")

        kw = {}
        for key, value in data.items():
            kw[str(key)] = value
        kw['owner'] = owner

        # grab a BuilderSet utility
        builder_util = getUtility(IBuilderSet)
        # XXX cprov 20050621
        # expand dict !!
        builder = builder_util.new(**kw)
        notify(ObjectCreatedEvent(builder))
        self._nextURL = kw['name']
        return builder

    def nextURL(self):
        return self._nextURL
