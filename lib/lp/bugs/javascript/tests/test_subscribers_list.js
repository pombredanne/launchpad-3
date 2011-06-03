YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use('test', 'console', 'lp.bugs.subscriber',
           'lp.bugs.subscribers_list', 'node-event-simulate',
           function(Y) {

var suite = new Y.Test.Suite("lp.bugs.subscribers_list Tests");
var module = Y.lp.bugs.subscribers_list;

/**
 * Set-up all the nodes required for subscribers list testing.
 */
function setUpSubscribersList(root_node) {
    // Set-up subscribers list.
    var node = Y.Node.create('<div></div>')
        .set('id', 'other-subscribers-container');
    root_node.appendChild(node);
    var config = {
        container_box: '#other-subscribers-container',
        bug: {}
    };
    return new module.SubscribersList(config);
}


/**
 * Test resetting of the no subscribers indication.
 */
suite.add(new Y.Test.Case({
    name: 'SubscribersList.resetNoSubscribers() test',

    setUp: function() {
        this.root = Y.Node.create('<div></div>');
        Y.one('body').appendChild(this.root);
    },

    tearDown: function() {
        this.root.remove();
    },

    test_initially_empty: function() {
        // When the SubscribersList is set-up, it's initially
        // entirely empty.
        var subscribers_list = setUpSubscribersList(this.root);
        Y.Assert.isTrue(
            subscribers_list.container_node.all().isEmpty());
    },

    test_no_subscribers: function() {
        // When resetNoSubscribers() is called on an empty
        // SubscribersList, indication of no subscribers is added.
        var subscribers_list = setUpSubscribersList(this.root);
        subscribers_list.resetNoSubscribers();
        var no_subs_nodes = this.root.all(
            '.no-subscribers-indicator');
        Y.Assert.areEqual(1, no_subs_nodes.size());
        Y.Assert.areEqual('No other subscribers.',
                          no_subs_nodes.item(0).get('text'));
    },

    test_subscribers_no_addition: function() {
        // When resetNoSubscribers() is called on a SubscribersList
        // with some subscribers, no indication of no subscribers is added.
        var subscribers_list = setUpSubscribersList(this.root);
        // Hack a section node into the list so it appears as if
        // there are subscribers.
        subscribers_list.container_node.appendChild(
            Y.Node.create('<div></div>')
                .addClass('subscribers-section'));

        // There is no indication of no subscribers added by
        // resetNoSubscribers.
        subscribers_list.resetNoSubscribers();
        var no_subs_nodes = this.root.all(
            '.no-subscribers-indicator');
        Y.Assert.isTrue(no_subs_nodes.isEmpty());
    },

    test_subscribers_remove_previous_indication: function() {
        // When resetNoSubscribers() is called on a SubscribersList
        // with some subscribers, existing indication of no subscribers
        // is removed.
        var subscribers_list = setUpSubscribersList(this.root);
        // Hack a section node into the list so it appears as if
        // there are subscribers.
        subscribers_list.container_node.appendChild(
            Y.Node.create('<div></div>')
                .addClass('subscribers-section'));
        subscribers_list.container_node.appendChild(
            Y.Node.create('<div></div>')
                .addClass('no-subscribers-indicator'));

        // There is no indication of no subscribers anymore after
        // the call to resetNoSubscribers.
        subscribers_list.resetNoSubscribers();
        var no_subs_nodes = this.root.all(
            '.no-subscribers-indicator');
        Y.Assert.isTrue(no_subs_nodes.isEmpty());
    }

}));


/**
 * Function to get a list of all the sections present in the
 * subscribers_list (a SubscribersList object).
 */
function _getAllSections(subscribers_list) {
    var nodes = [];
    var node;
    var all = subscribers_list.container_node.all('.subscribers-section');
    node = all.shift();
    while (node !== undefined) {
        nodes.push(node);
        node = all.shift();
    }
    return nodes;
};

/**
 * Test subscribers section creation and helper methods.
 */
suite.add(new Y.Test.Case({
    name: 'SubscribersList.getOrCreateSection() test',

    setUp: function() {
        this.root = Y.Node.create('<div></div>');
        Y.one('body').appendChild(this.root);
    },

    tearDown: function() {
        this.root.remove();
    },

    test_getSectionCSSClass: function() {
        // Returns a CSS class name to use for a section
        // for subscribers with a particular subscription level.
        var subscribers_list = setUpSubscribersList(this.root);
        Y.Assert.areEqual(
            'subscribers-section-details',
            subscribers_list._getSectionCSSClass('Details'));
    },

    test_getSection: function() {
        // Gets a subscribers section for the subscription level.
        var subscribers_list = setUpSubscribersList(this.root);

        var section_node = Y.Node.create('<div></div>')
            .addClass('subscribers-section-lifecycle')
            .addClass('subscribers-section');
        subscribers_list.container_node.appendChild(section_node);

        Y.Assert.areEqual(section_node,
                          subscribers_list._getSection('lifecycle'));
    },

    test_getSection_none: function() {
        // When there is no requested section, returns null.
        var subscribers_list = setUpSubscribersList(this.root);

        var section_node = Y.Node.create('<div></div>')
            .addClass('subscribers-section-lifecycle')
            .addClass('subscribers-section');
        subscribers_list.container_node.appendChild(section_node);

        Y.Assert.isNull(subscribers_list._getSection('details'));
    },

    test_createSectionNode: function() {
        // Creates a subscribers section for the given subscription level.
        var subscribers_list = setUpSubscribersList(this.root);

        var section_node = subscribers_list._createSectionNode('Discussion');

        // A CSS class is added to the node for this particular level.
        Y.Assert.isTrue(
            section_node.hasClass('subscribers-section-discussion'));
        // As well as a generic CSS class to indicate it's a section.
        Y.Assert.isTrue(section_node.hasClass('subscribers-section'));

        // Header is appropriate for the subscription level.
        var header = section_node.one('h3');
        Y.Assert.areEqual('Notified of all changes', header.get('text'));

        // There is a separate node for the subscribers list in this section.
        Y.Assert.isNotNull(section_node.one('.subscribers-list'));
    },

    test_insertSectionNode: function() {
        // Inserts a section node in the subscribers list.
        var subscribers_list = setUpSubscribersList(this.root);

        // Sections we'll be inserting in the order they should end up in.
        var section_node = subscribers_list._createSectionNode('Details');

        subscribers_list._insertSectionNode('Details', section_node);
        Y.ArrayAssert.itemsAreEqual(
            [section_node], _getAllSections(subscribers_list));
    },

    test_insertSectionNode_before: function() {
        // Inserts a section node in front of the existing section
        // in the subscribers list.
        var subscribers_list = setUpSubscribersList(this.root);

        // Sections we'll be inserting in the order they should end up in.
        var section_node1 = subscribers_list._createSectionNode('Discussion');
        var section_node2 = subscribers_list._createSectionNode('Details');

        subscribers_list._insertSectionNode('Details', section_node2);
        Y.ArrayAssert.itemsAreEqual(
            [section_node2],
            _getAllSections(subscribers_list));

        // Details section comes in front of the 'Discussion' section.
        subscribers_list._insertSectionNode('Discussion', section_node1);
        Y.ArrayAssert.itemsAreEqual(
            [section_node1, section_node2],
            _getAllSections(subscribers_list));
    },

    test_insertSectionNode_after: function() {
        // Inserts a section node after the existing section
        // in the subscribers list.
        var subscribers_list = setUpSubscribersList(this.root);

        // Sections we'll be inserting in the order they should end up in.
        var section_node1 = subscribers_list._createSectionNode('Discussion');
        var section_node2 = subscribers_list._createSectionNode('Details');

        subscribers_list._insertSectionNode('Discussion', section_node1);
        Y.ArrayAssert.itemsAreEqual(
            [section_node1],
            _getAllSections(subscribers_list));

        subscribers_list._insertSectionNode('Details', section_node2);
        Y.ArrayAssert.itemsAreEqual(
            [section_node1, section_node2],
            _getAllSections(subscribers_list));
    },

    test_insertSectionNode_full_list: function() {
        // Inserts a section node in the appropriate place in the
        // subscribers list for all the possible subscription levels.
        var subscribers_list = setUpSubscribersList(this.root);

        // Sections we'll be inserting in the order they should end up in.
        var section_node1 = subscribers_list._createSectionNode('Discussion');
        var section_node2 = subscribers_list._createSectionNode('Details');
        var section_node3 = subscribers_list._createSectionNode('Lifecycle');
        var section_node4 = subscribers_list._createSectionNode('Maybe');

        subscribers_list._insertSectionNode('Lifecycle', section_node3);
        Y.ArrayAssert.itemsAreEqual(
            [section_node3], _getAllSections(subscribers_list));

        subscribers_list._insertSectionNode('Discussion', section_node1);
        Y.ArrayAssert.itemsAreEqual(
            [section_node1, section_node3],
            _getAllSections(subscribers_list));

        subscribers_list._insertSectionNode('Details', section_node2);
        Y.ArrayAssert.itemsAreEqual(
            [section_node1, section_node2, section_node3],
            _getAllSections(subscribers_list));

        subscribers_list._insertSectionNode('Maybe', section_node4);
        Y.ArrayAssert.itemsAreEqual(
            [section_node1, section_node2, section_node3, section_node4],
            _getAllSections(subscribers_list));
    },

    test_getOrCreateSection_get_existing: function() {
        // When there is an existing section, getOrCreateSection
        // returns the existing node.
        var subscribers_list = setUpSubscribersList(this.root);

        var section_node = subscribers_list._createSectionNode('Details');
        subscribers_list._insertSectionNode('Details', section_node);

        Y.Assert.areSame(section_node,
                         subscribers_list.getOrCreateSection('Details'));

    },

    test_getOrCreateSection_new: function() {
        // When there is no existing matching section, a new one
        // is created and added to the subscribers list.
        var subscribers_list = setUpSubscribersList(this.root);

        var section_node = subscribers_list.getOrCreateSection('Details');
        Y.ArrayAssert.itemsAreEqual(
            [section_node],
            _getAllSections(subscribers_list));
    },

    test_getOrCreateSection_positioning: function() {
        // When new sections are created, they are inserted into proper
        // positions using _insertSectionNode.
        var subscribers_list = setUpSubscribersList(this.root);

        var section_node2 = subscribers_list.getOrCreateSection('Details');
        var section_node1 = subscribers_list.getOrCreateSection('Discussion');
        Y.ArrayAssert.itemsAreEqual(
            [section_node1, section_node2],
            _getAllSections(subscribers_list));
    },

    test_getOrCreateSection_removes_no_subscribers_indication: function() {
        // When there is a div indicating no subscribers, getOrCreateSection
        // removes it because it's adding a section where subscribers are
        // to come in.
        var subscribers_list = setUpSubscribersList(this.root);

        // Add a div saying 'No other subscribers.'
        subscribers_list.resetNoSubscribers();
        Y.Assert.isNotNull(this.root.one('.no-subscribers-indicator'));

        // And there is no matching div after getOrCreateSection call.
        subscribers_list.getOrCreateSection('Details');
        Y.Assert.isNull(this.root.one('.no-subscribers-indicator'));
    }

}));


/**
 * Test removal of a subscribers section.
 */
suite.add(new Y.Test.Case({
    name: 'SubscribersList.removeSectionIfEmpty() test',

    _should: {
        error: {
            test_sectionNodeHasSubscribers_error:
            new Error(
                'No div.subscribers-list found inside the passed `node`.')
        }
    },

    setUp: function() {
        this.root = Y.Node.create('<div></div>');
        Y.one('body').appendChild(this.root);
    },

    tearDown: function() {
        this.root.remove();
    },

    test_sectionNodeHasSubscribers_error: function() {
        // When called on a node not containing the subscribers list,
        // it throws an error.
        var subscribers_list = setUpSubscribersList(this.root);
        var node = Y.Node.create('<div></div>');
        subscribers_list._sectionNodeHasSubscribers(node);
    },

    test_sectionNodeHasSubscribers_no_subscribers: function() {
        // When called on a proper section node but with no subscribers,
        // it returns false.
        var subscribers_list = setUpSubscribersList(this.root);
        var node = subscribers_list.getOrCreateSection('Details');
        Y.Assert.isFalse(subscribers_list._sectionNodeHasSubscribers(node));
    },

    test_sectionNodeHasSubscribers_subscribers: function() {
        // When called on a proper section node with subscribers,
        // it returns true.
        var subscribers_list = setUpSubscribersList(this.root);
        var node = subscribers_list.getOrCreateSection('Details');
        var subscriber = Y.Node.create('<div></div>')
            .addClass('subscriber');
        node.one('.subscribers-list').appendChild(subscriber);
        Y.Assert.isTrue(subscribers_list._sectionNodeHasSubscribers(node));
    },

    test_removeSectionIfEmpty_noop: function() {
        // When there is no requested section, nothing happens.
        var subscribers_list = setUpSubscribersList(this.root);
        subscribers_list.removeSectionIfEmpty('Details');
    },

    test_removeSectionIfEmpty_remove: function() {
        // When there is an empty section, it's removed.
        var subscribers_list = setUpSubscribersList(this.root);
        var section_node = subscribers_list.getOrCreateSection('Details');

        subscribers_list.removeSectionIfEmpty('Details');
        Y.ArrayAssert.itemsAreEqual(
            [],
            _getAllSections(subscribers_list));

        // Indication that there are no subscribers is added.
        Y.Assert.isNotNull(this.root.one('.no-subscribers-indicator'));
    },

    test_removeSectionIfEmpty_keep: function() {
        // When there is a section with a subscriber, it's not removed.
        var subscribers_list = setUpSubscribersList(this.root);
        var section_node = subscribers_list.getOrCreateSection('Details');

        // Add a subscriber.
        section_node.one('.subscribers-list').appendChild(
            Y.Node.create('<div></div>')
                .addClass('subscriber'));

        subscribers_list.removeSectionIfEmpty('Details');
        Y.ArrayAssert.itemsAreEqual(
            [section_node],
            _getAllSections(subscribers_list));
        // Indication that there are no subscribers is not added.
        Y.Assert.isNull(this.root.one('.no-subscribers-indicator'));
    },

    test_removeSectionIfEmpty_keeps_others: function() {
        // With two empty sections, only the requested one is removed.
        var subscribers_list = setUpSubscribersList(this.root);
        var section_node1 = subscribers_list.getOrCreateSection('Details');
        var section_node2 = subscribers_list.getOrCreateSection('Discussion');

        subscribers_list.removeSectionIfEmpty('Details');
        Y.ArrayAssert.itemsAreEqual(
            [section_node2],
            _getAllSections(subscribers_list));
        // Indication that there are no subscribers is not added.
        Y.Assert.isNull(this.root.one('.no-subscribers-indicator'));
    }

}));


var handle_complete = function(data) {
    status_node = Y.Node.create(
        '<p id="complete">Test status: complete</p>');
    Y.one('body').appendChild(status_node);
    };
Y.Test.Runner.on('complete', handle_complete);
Y.Test.Runner.add(suite);

var console = new Y.Console({newestOnTop: false});
console.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});
});
