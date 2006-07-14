# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Specification views."""

__metaclass__ = type

__all__ = [
    'SpecificationContextMenu',
    'SpecificationNavigation',
    'SpecificationView',
    'SpecificationAddView',
    'SpecificationEditView',
    'SpecificationGoalSetView',
    'SpecificationRetargetingView',
    'SpecificationSupersedingView',
    'SpecificationTreePNGView',
    'SpecificationTreeImageTag',
    ]

import xmlrpclib
from subprocess import Popen, PIPE
from operator import attrgetter

from zope.component import getUtility
from zope.app.form.browser.itemswidgets import DropdownWidget

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _

from canonical.launchpad.interfaces import (
    IProduct, IDistribution, ISpecification, ISpecificationSet)

from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.addview import SQLObjectAddView

from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, enabled_with_permission,
    LaunchpadView, Navigation, GeneralFormView)

from canonical.launchpad.helpers import check_permission

from canonical.lp.dbschema import (
    SpecificationStatus, SpecificationGoalStatus)


class SpecificationNavigation(Navigation):

    usedfor = ISpecification

    def traverse(self, sprintname):
        return self.context.getSprintSpecification(sprintname)


class SpecificationContextMenu(ContextMenu):

    usedfor = ISpecification
    links = ['edit', 'people', 'status', 'priority', 'setseries',
             'setrelease',
             'milestone', 'requestfeedback', 'givefeedback', 'subscription',
             'subscribeanother',
             'linkbug', 'unlinkbug', 'adddependency', 'removedependency',
             'dependencytree', 'linksprint', 'supersede',
             'retarget', 'administer']

    def edit(self):
        text = 'Edit Details'
        return Link('+edit', text, icon='edit')

    def people(self):
        text = 'Change People'
        return Link('+people', text, icon='edit')

    def status(self):
        text = 'Change Status'
        return Link('+status', text, icon='edit')

    def priority(self):
        text = 'Change Priority'
        return Link('+priority', text, icon='edit')

    def supersede(self):
        text = 'Mark Superseded'
        return Link('+supersede', text, icon='edit')

    def setseries(self):
        text = 'Set Series Goal'
        enabled = self.context.product is not None
        return Link('+setseries', text, icon='edit', enabled=enabled)

    def setrelease(self):
        text = 'Set Release Goal'
        enabled = self.context.distribution is not None
        return Link('+setrelease', text, icon='edit', enabled=enabled)

    def milestone(self):
        text = 'Set Milestone'
        return Link('+milestone', text, icon='edit')

    def requestfeedback(self):
        text = 'Request Feedback'
        return Link('+requestfeedback', text, icon='edit')

    def givefeedback(self):
        text = 'Give Feedback'
        enabled = (self.user is not None and
                   self.context.getFeedbackRequests(self.user))
        return Link('+givefeedback', text, icon='edit', enabled=enabled)

    def subscription(self):
        user = self.user
        if user is not None and has_spec_subscription(user, self.context):
            text = 'Unsubscribe Yourself'
        else:
            text = 'Subscribe Yourself'
        return Link('+subscribe', text, icon='edit')

    def subscribeanother(self):
        text = 'Subscribe Someone'
        return Link('+addsubscriber', text, icon='add')

    def linkbug(self):
        text = 'Link to Bug'
        return Link('+linkbug', text, icon='add')

    def unlinkbug(self):
        text = 'Remove Bug Link'
        enabled = bool(self.context.bugs)
        return Link('+unlinkbug', text, icon='add', enabled=enabled)

    def adddependency(self):
        text = 'Add Dependency'
        return Link('+linkdependency', text, icon='add')

    def removedependency(self):
        text = 'Remove Dependency'
        enabled = bool(self.context.dependencies)
        return Link('+removedependency', text, icon='add', enabled=enabled)

    def dependencytree(self):
        text = 'Show Dependencies'
        enabled = (
            bool(self.context.dependencies) or bool(self.context.blocked_specs)
            )
        return Link('+deptree', text, icon='info', enabled=enabled)

    def linksprint(self):
        text = 'Add to Meeting'
        return Link('+linksprint', text, icon='add')

    @enabled_with_permission('launchpad.Edit')
    def retarget(self):
        text = 'Retarget'
        return Link('+retarget', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def administer(self):
        text = 'Administer'
        return Link('+admin', text, icon='edit')


def has_spec_subscription(person, spec):
    """Return whether the person has a subscription to the spec.

    XXX: Refactor this to a method on ISpecification.
         SteveAlexander, 2005-09-26
    """
    assert person is not None
    for subscription in spec.subscriptions:
        if subscription.person.id == person.id:
            return True
    return False


class SpecificationView(LaunchpadView):

    __used_for__ = ISpecification

    def initialize(self):
        # The review that the user requested on this spec, if any.
        self.feedbackrequests = []
        self.notices = []
        request = self.request

        # establish if a subscription form was posted
        newsub = request.form.get('subscribe', None)
        if newsub is not None and self.user and request.method == 'POST':
            if newsub == 'Subscribe':
                self.context.subscribe(self.user)
                self.notices.append("You have subscribed to this spec.")
            elif newsub == 'Unsubscribe':
                self.context.unsubscribe(self.user)
                self.notices.append("You have unsubscribed from this spec.")

        if self.user is not None:
            # establish if this user has a review queued on this spec
            self.feedbackrequests = self.context.getFeedbackRequests(self.user)
            if self.feedbackrequests:
                msg = "You have %d feedback request(s) on this specification."
                msg %= len(self.feedbackrequests)
                self.notices.append(msg)

    @property
    def subscription(self):
        """whether the current user has a subscription to the spec."""
        if self.user is None:
            return False
        return has_spec_subscription(self.user, self.context)

    @cachedproperty
    def has_dep_tree(self):
        return self.context.dependencies or self.context.blocked_specs


class SpecificationAddView(SQLObjectAddView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        SQLObjectAddView.__init__(self, context, request)

    def create(self, name, title, specurl, summary, status,
               owner, assignee=None, drafter=None, approver=None):
        """Create a new Specification."""
        # Inject the relevant product or distribution into the kw args.
        product = None
        distribution = None
        if IProduct.providedBy(self.context):
            product = self.context.id
        elif IDistribution.providedBy(self.context):
            distribution = self.context.id
        # clean up name
        name = name.strip().lower()
        spec = getUtility(ISpecificationSet).new(name, title, specurl,
            summary, status, owner, product=product,
            distribution=distribution, assignee=assignee, drafter=drafter,
            approver=approver)
        self._nextURL = canonical_url(spec)
        return spec

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return self._nextURL


class SpecificationEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))


class SpecificationGoalSetView(GeneralFormView):

    def process(self, productseries=None, distrorelease=None,
        whiteboard=None):
        # XXX sabdfl it would be better to display only one or the other
        # option in the form, with a radio button, as kiko pointed out in
        # his review. XXX MPT feel free to help me here, I don't know how to
        # make the form display either/or.
        if productseries and distrorelease:
            return 'Please choose a series OR a release, not both.'
        goal = None
        if productseries is not None:
            self.context.productseries = productseries
            goal = productseries
        if distrorelease is not None:
            self.context.distrorelease = distrorelease
            goal = distrorelease
        # By default, all new goals start out PROPOSED
        self.context.goalstatus = SpecificationGoalStatus.PROPOSED
        # If the goals were cleared then reflect that
        if goal is None:
            self.context.productseries = None
            self.context.distrorelease = None
        # Now we want to auto-approve the goal if the person making
        # the proposal has permission to do this anyway
        if goal is not None and check_permission('launchpad.Driver', goal):
            self.context.goalstatus = SpecificationGoalStatus.ACCEPTED
        self._nextURL = canonical_url(self.context)
        return 'Done.'


class SpecificationRetargetingView(GeneralFormView):

    def process(self, product=None, distribution=None):
        if product and distribution:
            return 'Please choose a product OR a distribution, not both.'
        if not (product or distribution):
            return 'Please choose a product or distribution for this spec.'
        # we need to ensure that there is not already a spec with this name
        # for this new target
        if product:
            if product.getSpecification(self.context.name) is not None:
                return '%s already has a spec called %s' % (
                    product.name, self.context.name)
        elif distribution:
            if distribution.getSpecification(self.context.name) is not None:
                return '%s already has a spec called %s' % (
                    distribution.name, self.context.name)
        self.context.retarget(product=product, distribution=distribution)
        self._nextURL = canonical_url(self.context)
        return 'Done.'


class SpecificationSupersedingView(GeneralFormView):

    def process(self, superseded_by=None):
        self.context.superseded_by = superseded_by
        if superseded_by is not None:
            # set the state to superseded
            self.context.status = SpecificationStatus.SUPERSEDED
        else:
            # if the current state is SUPERSEDED and we are now removing the
            # superseded-by then we should move this spec back into the
            # drafting pipeline by resetting its status to BRAINDUMP
            if self.context.status == SpecificationStatus.SUPERSEDED:
                self.context.status = SpecificationStatus.BRAINDUMP
        self.request.response.redirect(canonical_url(self.context))
        return 'Done.'


class SupersededByWidget(DropdownWidget):
    """Custom select widget for specification superseding.

    This is just a standard DropdownWidget with the (no value) text
    rendered as something meaningful to the user, as per Bug #4116.

    TODO: This should be replaced with something more scalable as there
    is no upper limit to the number of specifications.
    -- StuartBishop 20060704
    """
    _messageNoValue = _("(Not Superseded)")


class SpecGraph:
    """A directed linked graph of nodes representing spec dependencies."""

    # We want to be able to test SpecGraph and SpecGraphNode without setting
    # up canonical_urls.  This attribute is used by tests to generate URLs for
    # nodes without calling canonical_url.
    # The pattern is either None (meaning use canonical_url) or a string
    # containing one '%s' replacement marker.
    url_pattern_for_testing = None

    def __init__(self):
        self.nodes = set()
        self.edges = set()
        self.root_node = None

    def newNode(self, spec, root=False):
        """Return a new node based on the given spec.

        If root=True, make this the root node.

        There can be at most one root node set.
        """
        assert self.getNode(spec.name) is None, (
            "A spec called %s is already in the graph" % spec.name)
        node = SpecGraphNode(spec, root=root,
                url_pattern_for_testing=self.url_pattern_for_testing)
        self.nodes.add(node)
        if root:
            assert not self.root_node
            self.root_node = node
        return node

    def getNode(self, name):
        """Return the node with the given name.

        Return None if there is no such node.
        """
        # Efficiency: O(n)
        for node in self.nodes:
            if node.name == name:
                return node
        return None

    def newOrExistingNode(self, spec):
        """Return the node for the spec.

        If there is already a node for spec.name, return that node.
        Otherwise, create a new node for the spec, and return that.
        """
        node = self.getNode(spec.name)
        if node is None:
            node = self.newNode(spec)
        return node

    def link(self, from_node, to_node):
        """Form a direction link from from_node to to_node."""
        assert from_node in self.nodes
        assert to_node in self.nodes
        assert (from_node, to_node) not in self.edges
        self.edges.add((from_node, to_node))

    def addDependencyNodes(self, spec):
        """Add nodes for the specs that the given spec depends on,
        transitively.
        """
        get_related_specs_fn = attrgetter('dependencies')
        def link_nodes_fn(node, dependency):
            self.link(dependency, node)
        self.walkSpecsMakingNodes(spec, get_related_specs_fn, link_nodes_fn)

    def addBlockedNodes(self, spec):
        """Add nodes for the specs that the given spec blocks, transitively."""
        get_related_specs_fn = attrgetter('blocked_specs')
        def link_nodes_fn(node, blocked_spec):
            self.link(node, blocked_spec)
        self.walkSpecsMakingNodes(spec, get_related_specs_fn, link_nodes_fn)

    def walkSpecsMakingNodes(self, spec, get_related_specs_fn, link_nodes_fn):
        """Walk the specs, making and linking nodes.

        Examples of functions to use:

        get_related_specs_fn = lambda spec: spec.blocked_specs

        def link_nodes_fn(node, related):
            graph.link(node, related)
        """
        # This is a standard pattern for "flattening" a recursive algorithm.
        to_search = set([spec])
        visited = set()
        while to_search:
            current_spec = to_search.pop()
            visited.add(current_spec)
            node = self.newOrExistingNode(current_spec)
            related_specs = set(get_related_specs_fn(current_spec))
            for related_spec in related_specs:
                link_nodes_fn(node, self.newOrExistingNode(related_spec))
            to_search.update(related_specs.difference(visited))

    def getNodesSorted(self):
        """Return a list of all nodes, sorted by name."""
        return sorted(self.nodes, key=attrgetter('name'))

    def getEdgesSorted(self):
        """Return a list of all edges, sorted by name.

        An edge is a tuple (from_node, to_node).
        """
        return sorted(self.edges,
            key=lambda (from_node, to_node): (from_node.name, to_node.name))

    def listNodes(self):
        """Return a string of diagnostic output of nodes and edges.

        Used for debugging and in unit tests.
        """
        L = []
        edges = self.getEdgesSorted()
        if self.root_node:
            L.append('Root is %s' % self.root_node)
        else:
            L.append('Root is undefined')
        for node in self.getNodesSorted():
            L.append('%s:' % node)
            to_nodes = [to_node for from_node, to_node in edges
                        if from_node == node]
            L += ['    %s' % to_node.name for to_node in to_nodes]
        return '\n'.join(L)

    def getDOTGraphStatement(self):
        """Return a unicode string that is the DOT representation of this
        graph.

        graph : [ strict ] (graph | digraph) [ ID ] '{' stmt_list '}'
        stmt_list : [ stmt [ ';' ] [ stmt_list ] ]
        stmt : node_stmt | edge_stmt | attr_stmt | ID '=' ID | subgraph

        """
        graphname = 'deptree'
        graph_attrs = dict(mode='hier', sep=0.5, bgcolor='transparent')

        # Global node and edge attributes.
        node_attrs = dict(
            fillcolor='white',
            style='filled',
            fontname='Sans',
            fontsize=11)
        edge_attrs = dict(arrowhead='normal')

        L = []
        L.append('digraph %s {' % to_DOT_ID(graphname))
        L.append('graph')
        L.append(dict_to_DOT_attrs(graph_attrs))
        L.append('node')
        L.append(dict_to_DOT_attrs(node_attrs))
        L.append('edge')
        L.append(dict_to_DOT_attrs(edge_attrs))
        for node in self.getNodesSorted():
            L.append(node.getDOTNodeStatement())
        for from_node, to_node in self.getEdgesSorted():
            L.append('%s -> %s' % (
                to_DOT_ID(from_node.name), to_DOT_ID(to_node.name)))
        L.append('}')
        return u'\n'.join(L)


class SpecGraphNode:
    """Node in the spec dependency graph.

    A SpecGraphNode object has various display-related properties.
    """

    def __init__(self, spec, root=False, url_pattern_for_testing=None):
        self.name = spec.name
        if url_pattern_for_testing:
            self.URL = url_pattern_for_testing % self.name
        else:
            self.URL = canonical_url(spec)
        if root:
            self.color = 'red'
        elif spec.is_complete:
            self.color = 'grey'
        else:
            self.color = 'black'
        self.comment = spec.title
        self.label = self.makeLabel(spec)

    def makeLabel(self, spec):
        """Return a label for the spec."""
        if spec.assignee:
            label = '%s (%s)' % (spec.name, spec.assignee.name)
        else:
            label = spec.name
        return label

    def __str__(self):
        return '<%s>' % self.name

    def getDOTNodeStatement(self):
        """Return this node's data as a DOT unicode.

        This fills in the node_stmt in the DOT BNF:
        http://www.graphviz.org/doc/info/lang.html

        node_stmt : node_id [ attr_list ]
        node_id : ID [ port ]
        attr_list : '[' [ a_list ] ']' [ attr_list ]
        a_list  : ID [ '=' ID ] [ ',' ] [ a_list ]
        port : ':' ID [ ':' compass_pt ] | ':' compass_pt
        compass_pt : (n | ne | e | se | s | sw | w | nw)

        We don't care about the [ port ] part.

        """
        attrnames = ['color', 'URL', 'comment', 'label']
        attrdict = dict((name, getattr(self, name)) for name in attrnames)
        return u'%s\n%s' % (to_DOT_ID(self.name), dict_to_DOT_attrs(attrdict))


def dict_to_DOT_attrs(some_dict, indent='    '):
    r"""Convert some_dict to unicode DOT attrs output.

    attr_list : '[' [ a_list ] ']' [ attr_list ]
    a_list  : ID [ '=' ID ] [ ',' ] [ a_list ]

    The attributes are sorted by dict key.

    >>> some_dict = dict(
    ...     foo='foo',
    ...     bar='bar " \n bar',
    ...     baz='zab')
    >>> print dict_to_DOT_attrs(some_dict, indent='  ')
      [
      "bar"="bar \" \n bar",
      "baz"="zab",
      "foo"="foo"
      ]

    """
    if not some_dict:
        return u''
    L = []
    L.append('[')
    for key, value in sorted(some_dict.items()):
        L.append('%s=%s,' % (to_DOT_ID(key), to_DOT_ID(value)))
    # Remove the trailing comma from the last attr.
    lastitem = L.pop()
    L.append(lastitem[:-1])
    L.append(']')
    return u'\n'.join('%s%s' % (indent, line) for line in L)


def to_DOT_ID(value):
    r"""Accept a value and return the DOT escaped version.

    The returned value is always a unicode string.

    >>> to_DOT_ID(u'foo " bar \n')
    u'"foo \\" bar \\n"'

    """
    if isinstance(value, str):
        unitext = unicode(value, encoding='ascii')
    else:
        unitext = unicode(value)
    output = unitext.replace(u'"', u'\\"')
    output = output.replace(u'\n', u'\\n')
    return u'"%s"' % output


class ProblemRenderingGraph(Exception):
    """There was a problem rendering the graph."""


class SpecificationTreeGraphView(LaunchpadView):
    """View for displaying the dependency tree as a PNG with image map."""

    def makeSpecGraph(self):
        """Return a SpecGraph object rooted on the spec that is self.context.
        """
        graph = SpecGraph()
        root = graph.newNode(self.context, root=True)
        graph.addDependencyNodes(self.context)
        graph.addBlockedNodes(self.context)
        return graph

    def renderGraphvizGraph(self, format):
        """Return graph data in the appropriate format.

        Shell out to `dot` to do the work.
        Raise ProblemRenderingGraph exception if `dot` gives any error output.
        """
        assert format in ('png', 'cmapx')
        specgraph = self.makeSpecGraph()
        input = specgraph.getDOTGraphStatement().encode('UTF-8')
        cmd = 'dot -T%s' % format
        process = Popen(
            cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE,
            close_fds=True)
        process.stdin.write(input)
        process.stdin.close()
        output = process.stdout.read()
        err = process.stderr.read()
        if err:
            raise ProblemRenderingGraph(err, output)
        return output


class SpecificationTreePNGView(SpecificationTreeGraphView):

    def render(self):
        """Render a PNG displaying the specification dependency graph."""
        self.request.response.setHeader('Content-type', 'image/png')
        return self.renderGraphvizGraph('png')


class SpecificationTreeImageTag(SpecificationTreeGraphView):

    def render(self):
        """Render the image and image map tags for this dependency graph."""
        return (u'<img src="deptree.png" usemap="#deptree" />\n' +
                self.renderGraphvizGraph('cmapx'))

