YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
}).use('test', 'console', 'lp.app.picker', 'lp.bugs.subscriber',
       'lp.bugs.subscribers_list', 'node-event-simulate',
       function(Y) {

var suite = new Y.Test.Suite("lp.bugs.subscribers_list Tests");
var module = Y.lp.bugs.subscribers_list;


/**
 * Set-up all the nodes required for subscribers list testing.
 */
function setUpSubscribersList(root_node) {
    // Set-up subscribers list.
    var node = Y.Node.create('<div />')
        .set('id', 'other-subscribers-container');
    root_node.appendChild(node);
    var config = {
        container_box: '#other-subscribers-container'
    };
    return new module.SubscribersList(config);
}


/**
 * Test resetting of the no subscribers indication.
 */
suite.add(new Y.Test.Case({
    name: 'SubscribersList constructor test',

    _should: {
        error: {
            test_no_container_error:
            new Error(
                'Container node must be specified in config.container_box.'),
            test_multiple_containers_error:
            new Error(
                "Multiple container nodes for selector '.container' "+
                    "present in the page. You need to be more explicit.")
        }
    },

    setUp: function() {
        this.root = Y.Node.create('<div />');
        Y.one('body').appendChild(this.root);
    },

    tearDown: function() {
        this.root.remove();
    },

    test_no_container_error: function() {
        // When there is no matching container node in the DOM tree,
        // an exception is thrown.
        var sl = new module.SubscribersList({container_box: '#not-found'});
    },

    test_single_container: function() {
        // With an exactly single container node matches, all is well.
        var container_node = Y.Node.create('<div />')
            .set('id', 'container');
        this.root.appendChild(container_node);
        var list = new module.SubscribersList({container_box: '#container'});
        Y.Assert.areSame(container_node, list.container_node);
    },

    test_multiple_containers_error: function() {
        // With two nodes matching the given CSS selector,
        // an exception is thrown.
        this.root.appendChild(
            Y.Node.create('<div />').addClass('container'));
        this.root.appendChild(
            Y.Node.create('<div />').addClass('container'));
        var sl = new module.SubscribersList({container_box: '.container'});
    }
}));


/**
 * Test resetting of the no subscribers indication.
 */
suite.add(new Y.Test.Case({
    name: 'SubscribersList.resetNoSubscribers() test',

    setUp: function() {
        this.root = Y.Node.create('<div />');
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

    test_no_subscribers_force_hide: function() {
        // When resetNoSubscribers() is called on an empty
        // SubscribersList but with force_hide parameter set to true,
        // indication of no subscribers is not added.
        var subscribers_list = setUpSubscribersList(this.root);
        subscribers_list.resetNoSubscribers(true);
        var no_subs_nodes = this.root.all(
            '.no-subscribers-indicator');
        Y.Assert.areEqual(0, no_subs_nodes.size());
    },

    test_no_subscribers_force_hide_removal: function() {
        // When resetNoSubscribers() is called on an empty
        // SubscribersList which already has a no-subscribers
        // indication shown, it is removed.
        var subscribers_list = setUpSubscribersList(this.root);
        subscribers_list.resetNoSubscribers();
        subscribers_list.resetNoSubscribers(true);
        var no_subs_nodes = this.root.all(
            '.no-subscribers-indicator');
        Y.Assert.areEqual(0, no_subs_nodes.size());
    },

    test_subscribers_no_addition: function() {
        // When resetNoSubscribers() is called on a SubscribersList
        // with some subscribers, no indication of no subscribers is added.
        var subscribers_list = setUpSubscribersList(this.root);
        // Hack a section node into the list so it appears as if
        // there are subscribers.
        subscribers_list.container_node.appendChild(
            Y.Node.create('<div />')
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
            Y.Node.create('<div />')
                .addClass('subscribers-section'));
        subscribers_list.container_node.appendChild(
            Y.Node.create('<div />')
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
 * Test activity/progress indication for the entire subscribers list.
 */
suite.add(new Y.Test.Case({
    name: 'SubscribersList.startActivity() and stopActivity() test',

    _should: {
        error: {
            test_setActivityErrorIcon_error: true,
            test_setActivityText_error: true
        }
    },

    setUp: function() {
        this.root = Y.Node.create('<div />');
        Y.one('body').appendChild(this.root);
    },

    tearDown: function() {
        this.root.remove();
    },

    test_ensureActivityNode: function() {
        // With no activity node present, one is created and put
        // into the subscribers list container node.
        var subscribers_list = setUpSubscribersList(this.root);
        var node = subscribers_list._ensureActivityNode();
        Y.Assert.isNotNull(node);
        Y.Assert.isTrue(node.hasClass('global-activity-indicator'));
        Y.Assert.areSame(
            subscribers_list.container_node, node.get('parentNode'));
    },

    test_ensureActivityNode_contents: function() {
        // Created node contains an img tag with the spinner icon
        // and a span tag for the text.
        var subscribers_list = setUpSubscribersList(this.root);
        var node = subscribers_list._ensureActivityNode();
        var icon = node.one('img');
        Y.Assert.isNotNull(icon);
        Y.Assert.areEqual('file:///@@/spinner', icon.get('src'));
        var text = node.one('span');
        Y.Assert.isNotNull(text);
        Y.Assert.isTrue(text.hasClass('global-activity-text'));
    },

    test_ensureActivityNode_existing: function() {
        // When activity node already exists, it is returned
        // and no new one is created.
        var subscribers_list = setUpSubscribersList(this.root);
        var existing_node = subscribers_list._ensureActivityNode();
        var new_node = subscribers_list._ensureActivityNode();
        Y.Assert.areSame(existing_node, new_node);
        Y.Assert.areEqual(
            1,
            subscribers_list
                .container_node
                .all('.global-activity-indicator')
                .size());
    },

    test_setActivityErrorIcon_error_icon: function() {
        // With the activity node passed in, error icon is set
        // when desired.
        var subscribers_list = setUpSubscribersList(this.root);
        var node = subscribers_list._ensureActivityNode();
        var icon_node = node.one('img');
        subscribers_list._setActivityErrorIcon(node, true);
        Y.Assert.areEqual('file:///@@/error', icon_node.get('src'));
    },

    test_setActivityErrorIcon_spinner_icon: function() {
        // With the activity node passed in, spinner icon is restored
        // when requested (error parameter !== true).
        var subscribers_list = setUpSubscribersList(this.root);
        var node = subscribers_list._ensureActivityNode();
        var icon_node = node.one('img');
        subscribers_list._setActivityErrorIcon(node, false);
        Y.Assert.areEqual('file:///@@/spinner', icon_node.get('src'));
    },

    test_setActivityErrorIcon_error: function() {
        // With non-activity node passed in, it fails.
        var subscribers_list = setUpSubscribersList(this.root);
        var node = Y.Node.create('<div />');
        subscribers_list._setActivityErrorIcon(node, true);
    },

    test_setActivityText: function() {
        // With activity node and text passed in, proper
        // text is set in the activity text node.
        var subscribers_list = setUpSubscribersList(this.root);
        var node = subscribers_list._ensureActivityNode();
        subscribers_list._setActivityText(node, "Blah");
        // Single whitespace is prepended to better separate
        // icon from the text.
        Y.Assert.areEqual(" Blah", node.one('span').get('text'));
    },

    test_setActivityText_error: function() {
        // With non-activity node passed in, it fails.
        var subscribers_list = setUpSubscribersList(this.root);
        var node = Y.Node.create('<div />');
        subscribers_list._setActivityText(node, "Blah");
    },

    test_startActivity: function() {
        // startActivity adds the spinner icon and sets the appropriate text.
        var subscribers_list = setUpSubscribersList(this.root);
        subscribers_list.startActivity("Blah");

        var node = subscribers_list._ensureActivityNode();

        Y.Assert.areEqual('file:///@@/spinner', node.one('img').get('src'));
        Y.Assert.areEqual(" Blah", node.one('span').get('text'));
    },

    test_startActivity_restores_state: function() {
        // startActivity removes the no-subscribers indicator if present
        // and restores the activity node icon.
        var subscribers_list = setUpSubscribersList(this.root);
        // Add a no-subscribers indication.
        subscribers_list.resetNoSubscribers();
        // Create an activity node and set the error icon.
        var node = subscribers_list._ensureActivityNode();
        subscribers_list._setActivityErrorIcon(node, true);

        // Call startActivity() and see how it restores everything.
        subscribers_list.startActivity();
        Y.Assert.areEqual('file:///@@/spinner', node.one('img').get('src'));
        Y.Assert.isNull(
            subscribers_list.container_node.one('.no-subscribers-indicator'));
    },

    test_stopActivity: function() {
        // stopActivity without parameters assumes a successful completion
        // of the activity, so it removes the activity node and restores
        // no-subscribers indication if needed.
        var subscribers_list = setUpSubscribersList(this.root);
        subscribers_list.startActivity("Blah");
        subscribers_list.stopActivity();

        var node = subscribers_list.container_node.one(
            '.global-activity-indicator');
        Y.Assert.isNull(node);
        // Indication of no subscribers is restored.
        Y.Assert.isNotNull(
            subscribers_list.container_node.one('.no-subscribers-indicator'));
    },

    test_stopActivity_noop: function() {
        // stopActivity without parameters assumes a successful completion
        // of the activity.  If no activity was in progress, nothing happens.
        var subscribers_list = setUpSubscribersList(this.root);
        subscribers_list.stopActivity();

        var node = subscribers_list.container_node.one(
            '.global-activity-indicator');
        Y.Assert.isNull(node);
    },

    test_stopActivity_with_error_message: function() {
        // stopActivity with error message passed in creates an activity
        // node even if activity was not in progress and sets the error
        // icon and error text to the passed in message..
        var subscribers_list = setUpSubscribersList(this.root);
        subscribers_list.stopActivity("Problem!");
        var node = subscribers_list._ensureActivityNode();
        Y.Assert.areEqual('file:///@@/error', node.one('img').get('src'));
        Y.Assert.areEqual(" Problem!", node.one('span').get('text'));

        // Indication of no subscribers is not added.
        Y.Assert.isNull(
            subscribers_list.container_node.one('.no-subscribers-indicator'));
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
}

/**
 * Test subscribers section creation and helper methods.
 */
suite.add(new Y.Test.Case({
    name: 'SubscribersList._getOrCreateSection() test',

    setUp: function() {
        this.root = Y.Node.create('<div />');
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

        var section_node = Y.Node.create('<div />')
            .addClass('subscribers-section-lifecycle')
            .addClass('subscribers-section');
        subscribers_list.container_node.appendChild(section_node);

        Y.Assert.areEqual(section_node,
                          subscribers_list._getSection('lifecycle'));
    },

    test_getSection_none: function() {
        // When there is no requested section, returns null.
        var subscribers_list = setUpSubscribersList(this.root);

        var section_node = Y.Node.create('<div />')
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
        var section_node2 = subscribers_list._createSectionNode('Maybe');

        subscribers_list._insertSectionNode('Discussion', section_node1);
        Y.ArrayAssert.itemsAreEqual(
            [section_node1],
            _getAllSections(subscribers_list));

        subscribers_list._insertSectionNode('Maybe', section_node2);
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
        // When there is an existing section, _getOrCreateSection
        // returns the existing node.
        var subscribers_list = setUpSubscribersList(this.root);

        var section_node = subscribers_list._createSectionNode('Details');
        subscribers_list._insertSectionNode('Details', section_node);

        Y.Assert.areSame(section_node,
                         subscribers_list._getOrCreateSection('Details'));

    },

    test_getOrCreateSection_new: function() {
        // When there is no existing matching section, a new one
        // is created and added to the subscribers list.
        var subscribers_list = setUpSubscribersList(this.root);

        var section_node = subscribers_list._getOrCreateSection('Details');
        Y.ArrayAssert.itemsAreEqual(
            [section_node],
            _getAllSections(subscribers_list));
    },

    test_getOrCreateSection_positioning: function() {
        // When new sections are created, they are inserted into proper
        // positions using _insertSectionNode.
        var subscribers_list = setUpSubscribersList(this.root);

        var section_node2 = subscribers_list._getOrCreateSection('Details');
        var section_node1 = subscribers_list._getOrCreateSection(
            'Discussion');
        Y.ArrayAssert.itemsAreEqual(
            [section_node1, section_node2],
            _getAllSections(subscribers_list));
    },

    test_getOrCreateSection_removes_no_subscribers_indication: function() {
        // When there is a div indicating no subscribers, _getOrCreateSection
        // removes it because it's adding a section where subscribers are
        // to come in.
        var subscribers_list = setUpSubscribersList(this.root);

        // Add a div saying 'No other subscribers.'
        subscribers_list.resetNoSubscribers();
        Y.Assert.isNotNull(this.root.one('.no-subscribers-indicator'));

        // And there is no matching div after _getOrCreateSection call.
        subscribers_list._getOrCreateSection('Details');
        Y.Assert.isNull(this.root.one('.no-subscribers-indicator'));
    }

}));


/**
 * Test removal of a subscribers section.
 */
suite.add(new Y.Test.Case({
    name: 'SubscribersList._removeSectionNodeIfEmpty() test',

    _should: {
        error: {
            test_sectionNodeHasSubscribers_error:
            new Error(
                'No div.subscribers-list found inside the passed `node`.'),
            test_removeSectionNodeIfEmpty_non_section_error:
            new Error(
                'Node is not a section node.')
        }
    },

    setUp: function() {
        this.root = Y.Node.create('<div />');
        Y.one('body').appendChild(this.root);
    },

    tearDown: function() {
        this.root.remove();
    },

    test_sectionNodeHasSubscribers_error: function() {
        // When called on a node not containing the subscribers list,
        // it throws an error.
        var subscribers_list = setUpSubscribersList(this.root);
        var node = Y.Node.create('<div />');
        subscribers_list._sectionNodeHasSubscribers(node);
    },

    test_sectionNodeHasSubscribers_no_subscribers: function() {
        // When called on a proper section node but with no subscribers,
        // it returns false.
        var subscribers_list = setUpSubscribersList(this.root);
        var node = subscribers_list._getOrCreateSection('Details');
        Y.Assert.isFalse(subscribers_list._sectionNodeHasSubscribers(node));
    },

    test_sectionNodeHasSubscribers_subscribers: function() {
        // When called on a proper section node with subscribers,
        // it returns true.
        var subscribers_list = setUpSubscribersList(this.root);
        var node = subscribers_list._getOrCreateSection('Details');
        var subscriber = Y.Node.create('<div />')
            .addClass('subscriber');
        node.one('.subscribers-list').appendChild(subscriber);
        Y.Assert.isTrue(subscribers_list._sectionNodeHasSubscribers(node));
    },

    test_removeSectionNodeIfEmpty_noop: function() {
        // When there is no requested section, nothing happens.
        var subscribers_list = setUpSubscribersList(this.root);
        var section_node = subscribers_list._getSection('Details');
        subscribers_list._removeSectionNodeIfEmpty(section_node);
    },

    test_removeSectionNodeIfEmpty_non_section_error: function() {
        // When called on a node which is not a section, it throws
        // an exception.
        var subscribers_list = setUpSubscribersList(this.root);
        var section_node = Y.Node.create('<div />');
        subscribers_list._removeSectionNodeIfEmpty(section_node);
    },

    test_removeSectionNodeIfEmpty_remove: function() {
        // When there is an empty section, it's removed.
        var subscribers_list = setUpSubscribersList(this.root);
        var section_node = subscribers_list._getOrCreateSection('Details');

        subscribers_list._removeSectionNodeIfEmpty(section_node);
        Y.ArrayAssert.itemsAreEqual(
            [],
            _getAllSections(subscribers_list));

        // Indication that there are no subscribers is added.
        Y.Assert.isNotNull(this.root.one('.no-subscribers-indicator'));
    },

    test_removeSectionNodeIfEmpty_keep: function() {
        // When there is a section with a subscriber, it's not removed.
        var subscribers_list = setUpSubscribersList(this.root);
        var section_node = subscribers_list._getOrCreateSection('Details');

        // Add a subscriber.
        section_node.one('.subscribers-list').appendChild(
            Y.Node.create('<div />')
                .addClass('subscriber'));

        subscribers_list._removeSectionNodeIfEmpty(section_node);
        Y.ArrayAssert.itemsAreEqual(
            [section_node],
            _getAllSections(subscribers_list));
        // Indication that there are no subscribers is not added.
        Y.Assert.isNull(this.root.one('.no-subscribers-indicator'));
    },

    test_removeSectionNodeIfEmpty_keeps_others: function() {
        // With two empty sections, only the requested one is removed.
        var subscribers_list = setUpSubscribersList(this.root);
        var section_node1 = subscribers_list._getOrCreateSection('Details');
        var section_node2 = subscribers_list._getOrCreateSection(
            'Discussion');

        var section_node = subscribers_list._getSection('Details');
        subscribers_list._removeSectionNodeIfEmpty(section_node);
        Y.ArrayAssert.itemsAreEqual(
            [section_node2],
            _getAllSections(subscribers_list));
        // Indication that there are no subscribers is not added.
        Y.Assert.isNull(this.root.one('.no-subscribers-indicator'));
    }

}));


/**
 * Test adding of subscribers and relevant helper methods.
 */
suite.add(new Y.Test.Case({
    name: 'SubscribersList.addSubscriber() test',

    setUp: function() {
        this.root = Y.Node.create('<div />');
        Y.one('body').appendChild(this.root);
    },

    tearDown: function() {
        this.root.remove();
    },

    _should: {
        error: {
            test_validateSubscriber_no_name_error:
            new Error('No `name` passed in `subscriber`.'),
            test_addSubscriber_incorrect_level:
            new Error(
                'Level "Test" is not an acceptable subscription level.'),
            test_addSubscriber_not_in_section_error:
            new Error(
                "Matching subscriber node doesn't seem to be in any " +
                    "subscribers list sections.")
        }
    },

    test_getNodeIdForSubscriberName: function() {
        // Returns a CSS class name to use as the ID for subscribers
        // prefixed with 'subscriber-'.
        // Uses launchpad_to_css for escaping (eg. it replaces '+' with '_y').
        var subscribers_list = setUpSubscribersList(this.root);
        Y.Assert.areEqual(
            'subscriber-danilo_y',
            subscribers_list._getNodeIdForSubscriberName('danilo+'));
    },

    test_validateSubscriber: function() {
        // Ensures a passed in subscriber object has at least the
        // `name` attribute.  Presets display_name and web_link
        // values based on it.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' };
        subscriber = subscribers_list._validateSubscriber(subscriber);
        Y.Assert.areEqual('user', subscriber.name);
        Y.Assert.areEqual('user', subscriber.display_name);
        Y.Assert.areEqual('/~user', subscriber.web_link);
    },

    test_validateSubscriber_no_name_error: function() {
        // When no name attribute is present, an exception is thrown.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { };
        subscribers_list._validateSubscriber(subscriber);
    },

    test_validateSubscriber_no_overriding: function() {
        // Attributes display_name and web_link are not overridden if
        // already set.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = {
            name: 'user',
            display_name: 'User Name',
            web_link: 'http://launchpad.net/'
        };
        subscriber = subscribers_list._validateSubscriber(subscriber);
        Y.Assert.areEqual('user', subscriber.name);
        Y.Assert.areEqual('User Name', subscriber.display_name);
        Y.Assert.areEqual('http://launchpad.net/', subscriber.web_link);
    },

    test_createSubscriberNode: function() {
        // When passed a subscriber object, it constructs a node
        // containing a link to the subscriber (using web_link for the
        // link target, and display name for the text).
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = {
            name: 'user',
            display_name: 'User Name',
            web_link: 'http://launchpad.net/~user'
        };
        var node = subscribers_list._createSubscriberNode(subscriber);
        Y.Assert.isTrue(node.hasClass('subscriber'));

        var link = node.one('a');
        Y.Assert.areEqual('http://launchpad.net/~user', link.get('href'));

        var text = link.one('span');
        Y.Assert.areEqual('User Name', text.get('text'));
        Y.Assert.isTrue(text.hasClass('sprite'));
        Y.Assert.isTrue(text.hasClass('person'));
    },

    test_createSubscriberNode_team: function() {
        // When passed a subscriber object which has is_team === true,
        // a constructed node uses a 'sprite team' CSS classes instead
        // of 'sprite person' for display.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = {
            name: 'team',
            display_name: 'Team Name',
            web_link: 'http://launchpad.net/~team',
            is_team: true
        };
        var node = subscribers_list._createSubscriberNode(subscriber);
        var link_text = node.one('a span');
        Y.Assert.isTrue(link_text.hasClass('sprite'));
        Y.Assert.isTrue(link_text.hasClass('team'));
    },

    test_addSubscriber: function() {
        // When there is no subscriber in the subscriber list,
        // new node is constructed and appropriate section is added.
        var subscribers_list = setUpSubscribersList(this.root);
        var node = subscribers_list.addSubscriber(
            { name: 'user' }, 'Details');

        // Node is constructed using _createSubscriberNode.
        Y.Assert.isTrue(node.hasClass('subscriber'));
        // And the ID is set inside addSubscriber() method.
        Y.Assert.areEqual('subscriber-user', node.get('id'));

        // And it nested in the subscribers-list of a 'Details' section.
        var list_node = node.ancestor('.subscribers-list');
        Y.Assert.isNotNull(list_node);
        var section_node = list_node.ancestor('.subscribers-section-details');
        Y.Assert.isNotNull(section_node);
    },

    test_addSubscriber_incorrect_level: function() {
        // When an incorrect level is passed in, an exception is thrown.
        var subscribers_list = setUpSubscribersList(this.root);
        subscribers_list.addSubscriber(
            { name: 'user' }, 'Test');
    },

    test_addSubscriber_change_level: function() {
        // addSubscriber also allows changing a subscribtion level
        // for a subscriber when they are moved to a different section.
        var subscribers_list = setUpSubscribersList(this.root);
        var node = subscribers_list.addSubscriber(
            { name: 'user' }, 'Details');
        Y.Assert.isNotNull(node.ancestor('.subscribers-section-details'));

        // Move the subscriber to lifecycle section.
        node = subscribers_list.addSubscriber(
            { name: 'user' }, 'Lifecycle');
        // It's now in 'Lifecycle' section.
        Y.Assert.isNotNull(node.ancestor('.subscribers-section-lifecycle'));
        // And 'Details' section is removed.
        Y.Assert.isNull(subscribers_list._getSection('Details'));
    },

    test_addSubscriber_not_in_section_error: function() {
        // addSubscriber throws an exception if a subscriber node is found,
        // but it is not properly nested inside a subscribers-section node.
        var subscribers_list = setUpSubscribersList(this.root);
        var node = Y.Node.create('<div />')
            .set('id', 'subscriber-user');
        // We hack the node directly into the entire subscribers list node.
        subscribers_list.container_node.appendChild(node);

        // And addSubscriber now throws an exception.
        subscribers_list.addSubscriber(
            { name: 'user' }, 'Details');
    },

    test_addSubscriber_ordering: function() {
        // With multiple subscribers being added to the same section,
        // the last one is listed first.
        var subscribers_list = setUpSubscribersList(this.root);
        var node1 = subscribers_list.addSubscriber(
            { name: 'user1' }, 'Details');
        var node2 = subscribers_list.addSubscriber(
            { name: 'user2' }, 'Details');

        var list_node = subscribers_list._getSection('Details')
            .one('.subscribers-list');
        var all_subscribers = list_node.all('.subscriber');

        var returned_nodes = [];
        var index;
        for (index = 0; index < all_subscribers.size(); index++) {
            returned_nodes.push(all_subscribers.item(index));
        }
        Y.ArrayAssert.itemsAreSame(
            [node2, node1],
            returned_nodes);
    },

    test_addSubscriber_unsubscribe_callback: function() {
        // When config.unsubscribe_callback is passed in,
        // addUnsubscribeAction(subscriber, callback) is
        // called as well.

        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' };
        var callback = function() {};

        var callback_setup = false;
        subscribers_list.addUnsubscribeAction = function(
            unsub_subscriber, unsub_callback) {
            callback_setup = true;
            Y.Assert.areSame(subscriber, unsub_subscriber);
            Y.Assert.areSame(callback, unsub_callback);
        };
        subscribers_list.addSubscriber(subscriber, 'Details',
                                       { unsubscribe_callback: callback });
        // Setting up a callback was performed.
        Y.Assert.isTrue(callback_setup);
    }

}));


/**
 * Test adding of unsubscribe action for a subscriber, removal of subscribers
 * and relevant helper methods.
 */
suite.add(new Y.Test.Case({
    name: 'SubscribersList.addUnsubscribeAction() and ' +
        'removeSubscriber() test',

    setUp: function() {
        this.root = Y.Node.create('<div />');
        Y.one('body').appendChild(this.root);
    },

    tearDown: function() {
        this.root.remove();
    },

    _should: {
        error: {
            test_getSubscriberNode_error:
            new Error('Subscriber is not present in the subscribers list. ' +
                      'Please call addSubscriber(subscriber) first.'),
            test_addUnsubscribeAction_error:
            new Error('Passed in callback for unsubscribe action ' +
                      'is not a function.'),
            test_removeSubscriber_error:
            new Error(
                'Subscriber is not present in the subscribers list. ' +
                    'Please call addSubscriber(subscriber) first.'),
            test_removeSubscriber_not_in_section_error:
            new Error(
                "Matching subscriber node doesn't seem to be in any " +
                    "subscribers list sections.")
        }
    },

    test_getSubscriberNode: function() {
        // Gets a subscriber node from the subscribers list when present.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' };
        var node = subscribers_list.addSubscriber(subscriber, 'Details');
        Y.Assert.areSame(
            node, subscribers_list._getSubscriberNode(subscriber));
    },

    test_getSubscriberNode_error: function() {
        // When subscriber node is not present, throws an error.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' };
        subscribers_list._getSubscriberNode(subscriber);
    },

    test_getOrCreateActionsNode: function() {
        // When no actions node is present, one is created, appended
        // to the subscriber node, and returned.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber_node = subscribers_list.addSubscriber(
            { name: 'user' }, "Discussion");
        var actions_node = subscribers_list._getOrCreateActionsNode(
            subscriber_node);
        // Newly created node has 'subscriber-actions' CSS class.
        Y.Assert.isTrue(actions_node.hasClass('subscriber-actions'));

        // It is also nested inside the subscriber_node.
        Y.Assert.areSame(subscriber_node, actions_node.get('parentNode'));
    },

    test_getOrCreateActionsNode_already_exists: function() {
        // When actions node is present, it is returned.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber_node = subscribers_list.addSubscriber(
            { name: 'user' }, "Discussion");
        var old_actions_node = subscribers_list._getOrCreateActionsNode(
            subscriber_node);
        var new_actions_node = subscribers_list._getOrCreateActionsNode(
            subscriber_node);
        Y.Assert.areSame(old_actions_node, new_actions_node);
    },

    test_addUnsubscribeAction_node: function() {
        // Adding an unsubscribe action creates an unsubscribe icon
        // nested inside the actions node for the subscriber.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user', display_name: 'User Name' };
        var callback = function() {};

        var subscriber_node = subscribers_list.addSubscriber(
            subscriber, "Discussion");
        subscribers_list.addUnsubscribeAction(subscriber, callback);
        // An actions node is created.
        var actions_node = subscriber_node.one('.subscriber-actions');
        Y.Assert.isNotNull(actions_node);
        // It contains an A tag for the unsubscribe action.
        var unsub_node = actions_node.one('a.unsubscribe-action');
        Y.Assert.isNotNull(unsub_node);
        Y.Assert.areEqual('Unsubscribe User Name', unsub_node.get('title'));
        var unsub_icon = unsub_node.one('img');
        Y.Assert.isNotNull(unsub_icon);
        Y.Assert.areEqual('Remove', unsub_icon.get('alt'));
        // Getting a URI returns an absolute one, and with this being run
        // from the local file system, that's what we get.
        Y.Assert.areEqual('file:///@@/remove', unsub_icon.get('src'));
    },

    test_addUnsubscribeAction_node_exists: function() {
        // When an unsubscribe node already exists, a new one is not created.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user', display_name: 'User Name' };
        var callback = function() {};
        var subscriber_node = subscribers_list.addSubscriber(
            subscriber, "Discussion");
        subscribers_list.addUnsubscribeAction(subscriber, callback);
        var unsub_node = subscriber_node.one('a.unsubscribe-action');

        subscribers_list.addUnsubscribeAction(subscriber, callback);
        var unsub_nodes = subscriber_node.all('a.unsubscribe-action');
        Y.Assert.areEqual(1, unsub_nodes.size());
        Y.Assert.areSame(unsub_node, unsub_nodes.item(0));
    },

    test_addUnsubscribeAction_error: function() {
        // Adding an unsubscribe action with callback not a function
        // fails with an exception.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' };
        var subscriber_node = subscribers_list.addSubscriber(
            subscriber, "Discussion");
        subscribers_list.addUnsubscribeAction(subscriber, "not-function");
    },

    test_addUnsubscribeAction_callback_on_click: function() {
        // When unsubscribe link is clicked, callback is activated
        // and passed in the subscribers_list and subscriber parameters.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user', display_name: 'User Name' };

        var callback_called = false;
        var callback = function(my_list, my_subscriber) {
            callback_called = true;
            Y.Assert.areSame(subscribers_list, my_list);
            Y.Assert.areSame(subscriber, my_subscriber);
        };
        var subscriber_node = subscribers_list.addSubscriber(
            subscriber, "Discussion");
        subscribers_list.addUnsubscribeAction(subscriber, callback);
        var unsub_node = subscriber_node.one('a.unsubscribe-action');
        unsub_node.simulate('click');

        Y.Assert.isTrue(callback_called);
    },

    test_removeSubscriber_error: function() {
        // Removing a non-existent subscriber fails with an error.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' };
        subscribers_list.removeSubscriber(subscriber);
    },

    test_removeSubscriber_section_removed: function() {
        // Removing a subscriber works when the subscriber is in the list.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' };
        var subscriber_node = subscribers_list.addSubscriber(
            subscriber, 'Details');
        var section_node = subscriber_node.ancestor('.subscribers-section');
        subscribers_list.removeSubscriber(subscriber);
        // Entire section is removed along with the subscriber.
        Y.Assert.areEqual(0, _getAllSections(subscribers_list).length);
    },

    test_removeSubscriber_section_remains: function() {
        // Removing a subscriber works when the subscriber is in the list.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' };
        var other_node = subscribers_list.addSubscriber(
            { name: 'other' }, 'Details');
        var subscriber_node = subscribers_list.addSubscriber(
            subscriber, 'Details');
        var section_node = subscriber_node.ancestor('.subscribers-section');
        subscribers_list.removeSubscriber(subscriber);
        // Section is not removed because it still has 'other' subscriber.
        var all_sections = _getAllSections(subscribers_list);
        Y.Assert.areEqual(1, all_sections.length);
        // User is removed.
        Y.Assert.isNull(all_sections[0].one('#subscriber-user'));
        // Other is still in the list.
        Y.Assert.areSame(
            other_node, all_sections[0].one('#subscriber-other'));
    },

    test_removeSubscriber_not_in_section_error: function() {
        // If subscriber is not in a section, an exception is thrown.
        var subscribers_list = setUpSubscribersList(this.root);
        var node = Y.Node.create('<div />')
            .set('id', 'subscriber-user');
        // We hack the node directly into the entire subscribers list node.
        subscribers_list.container_node.appendChild(node);
        subscribers_list.removeSubscriber({ name: 'user' });
    }
}));


/**
 * Test showing/stopping indication of activity for a subscriber.
 */
suite.add(new Y.Test.Case({
    name: 'SubscribersList.indicateSubscriberActivity() and ' +
        'SubscribersList.stopSubscriberActivity() test',

    setUp: function() {
        this.root = Y.Node.create('<div />');
        Y.one('body').appendChild(this.root);
    },

    tearDown: function() {
        this.root.remove();
    },

    _should: {
        error: {
            test_indicateSubscriberActivity_error:
            new Error('Subscriber is not present in the subscribers list. ' +
                      'Please call addSubscriber(subscriber) first.'),
            test_stopSubscriberActivity_error:
            new Error('Subscriber is not present in the subscribers list. ' +
                      'Please call addSubscriber(subscriber) first.')
        }
    },

    test_indicateSubscriberActivity_error: function() {
        // When subscriber is not in the list, fails with an exception.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' };
        subscribers_list.indicateSubscriberActivity(subscriber);
    },

    test_indicateSubscriberActivity_node: function() {
        // Creates a node with spinner image in it.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' };
        var node = subscribers_list.addSubscriber(subscriber, 'Details');
        subscribers_list.indicateSubscriberActivity(subscriber);

        // This is the created node.
        var progress_node = node.one('.subscriber-activity-indicator');
        Y.Assert.isNotNull(progress_node);
        var progress_icon = progress_node.one('img');
        // We get an absolute URI, instead of the relative one which
        // the code sets.  Since the test runs from the local file system,
        // that means "file://".
        Y.Assert.areEqual('file:///@@/spinner', progress_icon.get('src'));
    },

    test_indicateSubscriberActivity_actions_hidden: function() {
        // If there are any actions (in an actions node), they are
        // all hidden.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' };
        var node = subscribers_list.addSubscriber(subscriber, 'Details');
        var actions_node = subscribers_list._getOrCreateActionsNode(node);

        subscribers_list.indicateSubscriberActivity(subscriber);
        Y.Assert.areEqual('none', actions_node.getStyle('display'));
    },

    test_stopSubscriberActivity_error: function() {
        // When subscriber is not in the list, fails with an exception.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' };
        subscribers_list.stopSubscriberActivity(subscriber);
    },

    test_stopSubscriberActivity_noop: function() {
        // When there's no activity in progress, nothing happens.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' };
        var node = subscribers_list.addSubscriber(subscriber, 'Details');
        subscribers_list.stopSubscriberActivity(subscriber);
    },

    test_stopSubscriberActivity_spinner_removed: function() {
        // When there is some activity in progress, spinner is removed.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' };
        var node = subscribers_list.addSubscriber(subscriber, 'Details');
        // Create the spinner.
        subscribers_list.indicateSubscriberActivity(subscriber);
        // And remove it.
        subscribers_list.stopSubscriberActivity(subscriber);
        Y.Assert.isNull(node.one('.subscriber-activity-indicator'));
    },

    test_stopSubscriberActivity_actions_restored: function() {
        // When there is some activity in progress, spinner is removed.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' };
        var node = subscribers_list.addSubscriber(subscriber, 'Details');
        var actions_node = subscribers_list._getOrCreateActionsNode(node);
        // Hide actions.
        actions_node.setStyle('display', 'none');
        // And restore actions.
        subscribers_list.stopSubscriberActivity(subscriber);
        Y.Assert.areEqual('inline', actions_node.getStyle('display'));
    },

    test_stopSubscriberActivity_success_callback: function() {
        // When we are indicating successful/failed operation,
        // green_flash/red_flash animation is executed and callback
        // function is called when it ends.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' };
        subscribers_list.addSubscriber(subscriber, 'Details');
        var callback_called = false;
        var callback = function() {
            callback_called = true;
        };

        subscribers_list.stopSubscriberActivity(
            subscriber, true, callback);
        // Callback is not called immediatelly.
        Y.Assert.isFalse(callback_called);
        this.wait(function() {
            // But after waiting for animation to complete,
            // callback is called.
            Y.Assert.isTrue(callback_called);
        }, 1100);
    },

    test_stopSubscriberActivity_no_callback: function() {
        // When we pass the callback in, but success is neither
        // 'true' nor 'false', callback is not called.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' };
        subscribers_list.addSubscriber(subscriber, 'Details');
        var callback_called = false;
        var callback = function() {
            callback_called = true;
        };

        subscribers_list.stopSubscriberActivity(
            subscriber, "no-callback", callback);
        // Callback is not called.
        Y.Assert.isFalse(callback_called);
        this.wait(function() {
            // Nor is it called after any potential animations complete.
            Y.Assert.isFalse(callback_called);
        }, 1100);
    }

}));


/**
 * Set-up all the nodes required for BugSubscriberLoader.
 */
function setUpLoader(root_node, config, barebone) {
    // Set-up subscribers list node.
    var node = Y.Node.create('<div />')
        .set('id', 'other-subscribers-container');
    var container_config = {
        container_box: '#other-subscribers-container'
    };
    if (barebone !== true) {
        container_config.bug = { web_link: '/base', self_link: '/bug/1' };
        container_config.subscribers_details_view = '/+details';
    }
    root_node.appendChild(node);
    if (Y.Lang.isValue(config)) {
        config = Y.mix(container_config, config);
    } else {
        config = container_config;
    }
    window.LP = { links: { me : "/~viewer" } };
    return new module.BugSubscribersLoader(config);
}

/**
 * Test BugSubscribersLoader class construction.
 */
suite.add(new Y.Test.Case({
    name: 'BugSubscribersLoader() construction test',

    _should: {
        error: {
            test_BugSubscribersLoader_container_error:
            new Error(
                'Container node must be specified in config.container_box.'),
            test_BugSubscribersLoader_bug_error:
            new Error(
                "No bug specified in `config' or bug.web_link is invalid."),
            test_BugSubscribersLoader_bug_web_link_error:
            new Error(
                "No bug specified in `config' or bug.web_link is invalid."),
            test_BugSubscribersLoader_portlet_link_error:
            new Error(
                "No config.subscribers_details_view specified to load " +
                    "other bug subscribers from.")
        }
    },

    setUp: function() {
        this.root = Y.Node.create('<div />');
        Y.one('body').appendChild(this.root);
    },

    tearDown: function() {
        this.root.remove();
    },

    test_BugSubscribersLoader_container_error: function() {
        // If no container node to hold the subscribers list is specified,
        // it fails with an error.
        var loader =
            new module.BugSubscribersLoader({container_box: '#not-found'});
    },

    test_BugSubscribersLoader_bug_error: function() {
        // Bug needs to be passed in as well.
        // setUpLoader constructs the container node for us.
        var config = {};
        setUpLoader(this.root, config, true);
    },

    test_BugSubscribersLoader_bug_web_link_error: function() {
        // Fails if the passed in bug has no web_link attribute defined.
        var config = { bug: {} };
        setUpLoader(this.root, config, true);
    },

    test_BugSubscribersLoader_portlet_link_error: function() {
        // Fails if the passed in config has no passed in
        // portlet URI for loading bug subscribers details.
        var config = { bug: { web_link: '' } };
        setUpLoader(this.root, config, true);
    },

    test_BugSubscribersLoader: function() {
        // With all the parameters specified, it returns an instance
        // with subscribers_portlet_uri, subscribers_list, error_handler,
        // and calls the _loadSubscribers() method.
        var config = {
            bug: { web_link: '/base' },
            subscribers_details_view: '/+details'
        };

        // Save original method for restoring later.
        var old_load = module.BugSubscribersLoader.prototype._loadSubscribers;

        var loading_started = false;
        module.BugSubscribersLoader.prototype._loadSubscribers = function() {
            loading_started = true;
        };
        var loader = setUpLoader(this.root, config);
        Y.Assert.areEqual('/base/+details', loader.subscribers_portlet_uri);
        Y.Assert.isNotNull(loader.subscribers_list);
        Y.Assert.isTrue(
            loader.subscribers_list instanceof module.SubscribersList);
        Y.Assert.isNotNull(loader.error_handler);
        Y.Assert.isTrue(loading_started);

        // Restore original method.
        module.BugSubscribersLoader.prototype._loadSubscribers = old_load;
    }
}));


/**
 * Test BugSubscribersLoader subscribers loading and helper methods.
 */
suite.add(new Y.Test.Case({
    name: 'BugSubscribersLoader() subscribers loading test',

    _should: {
        error: {
            test_loadSubscribersFromList_not_list_error:
            new Error('Got non-array "Not-a-list" in ' +
                      '_loadSubscribersFromList().'),
            test_loadSubscribersFromList_no_objects_error:
            new Error('Subscriber details at index 0 (Subscriber)' +
                      ' are not an object.')
        }
    },

    setUp: function() {
        this.root = Y.Node.create('<div />');
        Y.one('body').appendChild(this.root);
    },

    tearDown: function() {
        this.root.remove();
    },

    test_addSubscriber_wraps_list_addSubscriber: function() {
        // addSubscriber wraps the SubscribersList.addSubscriber.
        // When no can_edit is set on the subscriber, no unsubscribe
        // callback is added.
        var subscriber = { name: "user" };
        var level = "Discussion";
        var call_passed_through = false;
        // Save the old method for restoring later.
        var old_addSub = module.SubscribersList.prototype.addSubscriber;
        module.SubscribersList.prototype.addSubscriber = function(
            passed_subscriber, passed_level) {
            call_passed_through = true;
            Y.Assert.areSame(subscriber, passed_subscriber);
            Y.Assert.areSame(level, passed_level);
        };
        var loader = setUpLoader(this.root);
        loader._addSubscriber(subscriber, level);
        Y.Assert.isTrue(call_passed_through);

        // Restore the real method.
        module.SubscribersList.prototype.addSubscriber = old_addSub;
    },

    test_addSubscriber_normalizes_level: function() {
        // addSubscriber normalizes the subscription level to 'Maybe'
        // when it's otherwise unknown subscription level.
        var subscriber = { name: "user" };
        var level = "Not a level";

        // Save the old method for restoring later.
        var old_addSub = module.SubscribersList.prototype.addSubscriber;
        module.SubscribersList.prototype.addSubscriber = function(
            passed_subscriber, passed_level, passed_config) {
            Y.Assert.areSame('Maybe', passed_level);
            Y.Assert.isUndefined(passed_config);
        };
        var loader = setUpLoader(this.root);
        loader._addSubscriber(subscriber, level);

        // Restore the real method.
        module.SubscribersList.prototype.addSubscriber = old_addSub;
    },

    test_addSubscriber_unsubscribe_callback: function() {
        // addSubscriber sets the unsubscribe callback to function
        // returned by BugSubscribersLoader._getUnsubscribeCallback()
        // if subscriber.can_edit === true.
        var subscriber = { name: "user", can_edit: true };
        var unsubscribe_callback = function() {};

        // Save old methods for restoring later.
        var old_getUnsub = module.BugSubscribersLoader.prototype
            ._getUnsubscribeCallback;
        var old_addSub = module.SubscribersList.prototype.addSubscriber;

        // Make _getUnsubscribeCallback return the new callback.
        module.BugSubscribersLoader.prototype._getUnsubscribeCallback =
            function() {
                return unsubscribe_callback;
            };

        // Assert in addSubscriber that it's being passed the new
        // callback in the config parameter.
        module.SubscribersList.prototype.addSubscriber = function(
            passed_subscriber, passed_level, passed_config) {
            Y.Assert.areSame(unsubscribe_callback,
                             passed_config.unsubscribe_callback);
        };

        var loader = setUpLoader(this.root);
        loader._addSubscriber(subscriber);

        // Restore original methods.
        module.BugSubscribersLoader.prototype._getUnsubscribeCallback =
            old_getUnsub;
        module.SubscribersList.prototype.addSubscriber = old_addSub;
    },


    test_loadSubscribersFromList: function() {
        // Accepts a list of dicts with 'subscriber' and 'subscription_level'
        // fields, passing them directly to _addSubscriber() method.
        var data = [{ subscriber: { name: "Subscriber 1" },
                      subscription_level: "Lifecycle" },
                    { subscriber: { name: "Subscriber 2" },
                      subscription_level: "Unknown" }];

        // Save the original method for restoring later.
        var old_addSub = module.BugSubscribersLoader.prototype._addSubscriber;

        var call_count = 0;
        module.BugSubscribersLoader.prototype._addSubscriber =
            function(subscriber, level) {
                call_count++;
                if (call_count === 1) {
                    Y.Assert.areEqual("Subscriber 1", subscriber.name);
                    Y.Assert.areEqual("Lifecycle", level);
                } else if (call_count === 2) {
                    Y.Assert.areEqual("Subscriber 2", subscriber.name);
                    Y.Assert.areEqual("Unknown", level);
                }
            };

        var loader = setUpLoader(this.root);
        loader._loadSubscribersFromList(data);

        // Two subscribers have been processed total.
        Y.Assert.areEqual(2, call_count);

        // Restore the original method.
        module.BugSubscribersLoader.prototype._addSubscriber = old_addSub;
    },

    test_loadSubscribersFromList_not_list_error: function() {
        // When the data is not a list, it throws an error.
        var data = "Not-a-list";

        var loader = setUpLoader(this.root);
        loader._loadSubscribersFromList(data);
    },

    test_loadSubscribersFromList_no_objects_error: function() {
        // When the data is not a list of objects, it throws an error.
        var data = ["Subscriber"];

        var loader = setUpLoader(this.root);
        loader._loadSubscribersFromList(data);
    },

    test_loadSubscribers_success: function() {
        // Testing successful operation of _loadSubscribers.
        var details = [
            { subscriber: { name: "subscriber" },
              subscription_level: "Details" }
        ];

        // Override loadSubscribersList to ensure it gets called with
        // the right parameters.
        var old_loadSubsList =
            module.BugSubscribersLoader.prototype._loadSubscribersFromList;
        var loading_done = false;
        module.BugSubscribersLoader.prototype._loadSubscribersFromList =
            function(my_details) {
                Y.Assert.areSame(details, my_details);
                loading_done = true;
            };

        var loader = setUpLoader(this.root);

        // Mock lp_client for testing.
        loader.lp_client = {
            get: function(uri, get_config) {
                // Assert that there is activity in progress.
                var node = loader.subscribers_list.container_node
                    .one('.global-activity-indicator');
                Y.Assert.isNotNull(node);
                // Call the success handler.
                get_config.on.success(details);
            }
        };
        // Re-run _loadSubscribers with our mock methods in place.
        loader._loadSubscribers();

        // Assert that _loadSubscribersList was run in the process.
        Y.Assert.isTrue(loading_done);

        // And activity node was removed when everything was done.
        var node = loader.subscribers_list.container_node
            .one('.global-activity-indicator');
        Y.Assert.isNull(node);

        // Restore original method.
        module.BugSubscribersLoader.prototype._loadSubscribersFromList =
            old_loadSubsList;
    },

    test_loadSubscribers_failure: function() {
        // On failure to load, activity indication is set to an error
        // message received from the server.
        var details = [
            { subscriber: { name: "subscriber" },
              subscription_level: "Details" }
        ];

        var loader = setUpLoader(this.root);

        // Mock lp_client for testing erroring out with 'BOOM'.
        loader.lp_client = {
            get: function(uri, get_config) {
                // Assert that there is activity in progress.
                var node = loader.subscribers_list.container_node
                    .one('.global-activity-indicator');
                Y.Assert.isNotNull(node);
                // Call the success handler.
                get_config.on.failure(1,{ status: 403,
                                          statusText: 'BOOM',
                                          responseText: '' });
            }
        };
        // Re-run _loadSubscribers with our mock methods in place.
        loader._loadSubscribers();

        // And activity node is there with an error message.
        var node = loader.subscribers_list.container_node
            .one('.global-activity-indicator');
        Y.Assert.isNotNull(node);
        Y.Assert.areEqual('file:///@@/error', node.one('img').get('src'));
        Y.Assert.areEqual(' Problem loading subscribers. 403 BOOM',
                          node.one('span').get('text'));
    }
}));



/**
 * Test BugSubscribersLoader unsubscribe callback function.
 */
suite.add(new Y.Test.Case({
    name: 'BugSubscribersLoader() subscribers loading test',

    setUp: function() {
        this.root = Y.Node.create('<div />');
        Y.one('body').appendChild(this.root);
    },

    tearDown: function() {
        this.root.remove();
    },

    test_unsubscribe_callback_success: function() {
        // _getUnsubscribeCallback returns a function which takes
        // subscribers list and subscriber as the two parameters.
        // That function calls 'unsubscribe' API method on the bug
        // to unsubscribe the user, and on successful completion,
        // it removes the user from the subscribers list.

        // Mock LP client.
        var received_uri, received_method, received_params;
        var config = {};
        config.lp_client = {
            named_post: function(uri, method, my_conf) {
                received_uri = uri;
                received_method = method;
                received_params = my_conf.parameters;
                my_conf.on.success();
            },
            get: function() {}
        };
        var subscriber = { name: "user", "can_edit": true,
                           self_link: "user-self-link" };

        // Mock removeSubscriber method to ensure it's called.
        var removed_subscriber = false;
        var old_rmSub = module.SubscribersList.prototype.removeSubscriber;
        module.SubscribersList.prototype.removeSubscriber = function(
            my_subscriber) {
            Y.Assert.areSame(subscriber.name, my_subscriber.name);
            removed_subscriber = true;
        };

        var loader = setUpLoader(this.root, config);
        var unsub_callback = loader._getUnsubscribeCallback();
        loader._addSubscriber(subscriber);
        unsub_callback(loader.subscribers_list, subscriber);

        Y.Assert.areSame(loader.bug.self_link, received_uri);
        Y.Assert.areSame('unsubscribe', received_method);
        Y.Assert.areSame(subscriber.self_link, received_params.person);

        this.wait(function() {
            // Removal is triggered from the stopSubscriberActivity,
            // which shows the success animation first.
            Y.Assert.isTrue(removed_subscriber);
        }, 1100);

        // Restore the real method.
        module.SubscribersList.prototype.removeSubscriber = old_rmSub;
    },

    test_unsubscribe_callback_failure: function() {
        // Function returned by _getUnsubscribeCallback calls
        // 'unsubscribe' API method on the bug, and on failure,
        // it keeps the user in the list and calls
        // stopSubscriberActivity to indicate the failure.

        // Mock LP client.
        var config = {};
        config.lp_client = {
            named_post: function(uri, method, my_conf) {
                my_conf.on.failure(0, { status: 500, statusText: "BOOM!" });
            },
            get: function() {}
        };
        var subscriber = { name: "user", "can_edit": true,
                           self_link: "user-self-link" };

        // Mock stopSubscriberActivity to ensure it's called.
        var subscriber_activity_stopped = false;
        var old_method =
            module.SubscribersList.prototype.stopSubscriberActivity;
        module.SubscribersList.prototype.stopSubscriberActivity = function(
            my_subscriber, success, callback) {
            Y.Assert.areSame(subscriber.name, my_subscriber.name);
            // The passed-in parameter indicates failure.
            Y.Assert.isFalse(success);
            // And there is no callback.
            Y.Assert.isUndefined(callback);
            subscriber_activity_stopped = true;
        };

        // Ensure display_error is called.
        var error_shown = false;
        var old_error_method = Y.lp.app.errors.display_error;
        Y.lp.app.errors.display_error = function(text) {
            error_shown = true;
        };

        var loader = setUpLoader(this.root, config);
        var unsub_callback = loader._getUnsubscribeCallback();
        loader._addSubscriber(subscriber);
        unsub_callback(loader.subscribers_list, subscriber);

        Y.Assert.isTrue(subscriber_activity_stopped);
        Y.Assert.isTrue(error_shown);

        // Restore original methods.
        module.SubscribersList.prototype.stopSubscriberActivity = old_method;
        Y.lp.app.errors.display_error = old_error_method;
    }

}));



/**
 * Test BugSubscribersLoader subscribe-someone-else functionality.
 */
suite.add(new Y.Test.Case({
    name: 'BugSubscribersLoader() subscribe-someone-else test',

    _should: {
        error: {
            test_setupSubscribeSomeoneElse_error:
            new Error("No link matching CSS selector " +
                      "'#sub-someone-else-link' " +
                      "for subscribing someone else found.")
        }
    },

    setUp: function() {
        this.root = Y.Node.create('<div />');
        Y.one('body').appendChild(this.root);
    },

    tearDown: function() {
        this.root.remove();
    },

    test_constructor_calls_setup: function() {
        // When subscribe_someone_else_link is passed in the constructor,
        // link identified by that CSS selector is set to pop up a person
        // picker for choosing a person/team to subscribe to the bug.
        var config = {
            subscribe_someone_else_link: '#sub-someone-else-link'
        };

        var setup_called = false;
        // Replace the original method to ensure it's getting called.
        var old_method =
            module.BugSubscribersLoader.prototype._setupSubscribeSomeoneElse;
        module.BugSubscribersLoader.prototype._setupSubscribeSomeoneElse =
            function() {
                setup_called = true;
            };

        var loader = setUpLoader(this.root, config);

        Y.Assert.isTrue(setup_called);

        // Restore original method.
        module.BugSubscribersLoader.prototype._setupSubscribeSomeoneElse =
            old_method;
    },

    test_setupSubscribeSomeoneElse_error: function() {
        // When link is not found in the page, exception is raised.

        // Initialize the loader with no subscribe-someone-else link.
        var loader = setUpLoader(this.root);
        loader.subscribe_someone_else_link = '#sub-someone-else-link';
        loader._setupSubscribeSomeoneElse();
    },

    test_setupSubscribeSomeoneElse_not_logged_in: function() {
        // When user is not logged in (LP.links.me undefined),
        // it silently does nothing.

        // Initialize the loader and make sure the user is not logged in.
        var loader = setUpLoader(this.root);
        window.LP.links.me = undefined;
        loader._setupSubscribeSomeoneElse();
        // Nothing happens, not even a person picker is set up.
        Y.Assert.isUndefined(loader._picker);
    },

    test_setupSubscribeSomeoneElse: function() {
        // _setupSubscribeSomeoneElse ties in a link with
        // the appropriate person picker and with the save
        // handler that calls _subscribeSomeoneElse with the
        // selected person as the parameter.

        // Initialize the loader with no subscribe-someone-else link.
        var loader = setUpLoader(this.root);

        // Mock LP client that always returns a person-like object.
        var subscriber = { name: "user", "can_edit": true,
                           self_link: "/~user",
                           api_uri: "/~user" };
        loader.lp_client = {
            get: function(uri, conf) {
                conf.on.success(subscriber);
            }
        };

        loader.subscribe_someone_else_link = '#sub-someone-else-link';
        var link = Y.Node.create('<a />').set('id', 'sub-someone-else-link');
        this.root.appendChild(link);

        // Mock subscribeSomeoneElse method to ensure it's called.
        var subscribe_done = false;
        var old_method =
            module.BugSubscribersLoader.prototype._subscribeSomeoneElse;
        module.BugSubscribersLoader.prototype._subscribeSomeoneElse =
            function(person) {
                Y.Assert.areSame(subscriber, person);
                subscribe_done = true;
            };

        // Mock the picker creation as well.
        var picker_shown = false;
        var old_create_picker = Y.lp.app.picker.create;
        Y.lp.app.picker.create = function(vocabulary, my_config) {
            Y.Assert.areSame('ValidPersonOrTeam', vocabulary);
            // On link click, simulate the save action.
            link.on('click', function() {
                picker_shown = true;
                my_config.save(subscriber);
            });
        };

        loader._setupSubscribeSomeoneElse();

        // Show the picker and simulate the save action.
        link.simulate('click');

        Y.Assert.isTrue(picker_shown);
        Y.Assert.isTrue(subscribe_done);

        // Restore original methods.
        module.BugSubscribersLoader.prototype._subscribeSomeoneElse =
            old_method;
        Y.lp.app.picker.create = old_create_picker;
    },

    test_setupSubscribeSomeoneElse_failure: function() {
        // When fetching a person as returned by the picker fails
        // error message is shown.

        // Initialize the loader with no subscribe-someone-else link.
        var loader = setUpLoader(this.root);

        // Mock LP client that always returns a person-like object.
        var subscriber = { name: "user", "can_edit": true,
                           self_link: "/~user",
                           api_uri: "/~user" };
        loader.lp_client = {
            get: function(uri, conf) {
                conf.on.failure(99, { status: 500,
                                      statusText: "BOOM" });
            }
        };
        var expected_error_msg = "500 (BOOM)\n" +
            "Couldn't get subscriber details from the " +
            "server, so they have not been subscribed.\n";
        var received_error_msg;

        // Mock display_error to ensure it's called.
        var old_display_error = Y.lp.app.errors.display_error;
        Y.lp.app.errors.display_error = function(animate, msg) {
            Y.Assert.isFalse(animate);
            received_error_msg = msg;
        };

        loader.subscribe_someone_else_link = '#sub-someone-else-link';
        var link = Y.Node.create('<a />').set('id', 'sub-someone-else-link');
        this.root.appendChild(link);

        // Mock the picker creation as well.
        var old_create_picker = Y.lp.app.picker.create;
        Y.lp.app.picker.create = function(vocabulary, my_config) {
            Y.Assert.areSame('ValidPersonOrTeam', vocabulary);
            // On link click, simulate the save action.
            link.on('click', function() {
                my_config.save(subscriber);
            });
        };

        loader._setupSubscribeSomeoneElse();

        // Show the picker and simulate the save action.
        link.simulate('click');

        // display_error was called with the appropriate error message.
        Y.Assert.areSame(expected_error_msg, received_error_msg);

        // Restore original methods.
        Y.lp.app.errors.display_error = old_display_error;
        Y.lp.app.picker.create = old_create_picker;
    },

    test_subscribeSomeoneElse: function() {
        // _subscribeSomeoneElse method takes a Person object as returned
        // by the API, and adds that subscriber at 'Discussion' level.

        var subscriber = { self_link: "/~user" };

        // Mock-up addSubscriber method to ensure subscriber is added.
        var subscriber_added = false;
        var old_addSub = module.SubscribersList.prototype.addSubscriber;
        module.SubscribersList.prototype.addSubscriber = function(
            my_subscriber, level) {
            Y.Assert.areSame(subscriber, my_subscriber);
            subscriber_added = true;
        };

        // Mock-up indicateSubscriberActivity to ensure it's called.
        var activity_on = false;
        var old_indicate =
            module.SubscribersList.prototype.indicateSubscriberActivity;
        module.SubscribersList.prototype.indicateSubscriberActivity =
            function(my_subscriber) {
                Y.Assert.areSame(subscriber, my_subscriber);
                activity_on = true;
            };

        // Initialize the loader.
        var loader = setUpLoader(this.root);

        // Mock lp_client which records the call.
        var received_method, received_uri, received_params;
        loader.lp_client = {
            named_post: function(uri, method, conf) {
                received_uri = uri;
                received_method = method;
                received_params = conf.parameters;
            }
        };

        // Wrap subscriber like an API-returned value.
        var person = {
            getAttrs: function() {
                return subscriber;
            }
        };

        loader._subscribeSomeoneElse(person);

        Y.Assert.isTrue(subscriber_added);
        Y.Assert.isTrue(activity_on);

        Y.Assert.areEqual('subscribe', received_method);
        Y.Assert.areEqual(loader.bug.self_link, received_uri);
        Y.Assert.areEqual(subscriber.self_link, received_params.person);

        // Restore original methods.
        module.SubscribersList.prototype.addSubscriber = old_addSub;
        module.SubscribersList.prototype.indicateSubscriberActivity =
            old_indicate;
    },

    test_subscribeSomeoneElse_success: function() {
        // When subscribing someone else succeeds, stopSubscriberActivity
        // is called indicating success, and _addUnsubscribeLinkIfTeamMember
        // is called to add unsubscribe-link when needed.

        var subscriber = { name: "user", self_link: "/~user" };

        // Initialize the loader.
        var loader = setUpLoader(this.root);
        loader.subscribers_list.addSubscriber(subscriber, "Maybe");

        // Mock-up addUnsubscribeLinkIfTeamMember method to
        // ensure it's called with the right parameters.
        var subscriber_link_added = false;
        var old_addLink =
            module.BugSubscribersLoader
            .prototype._addUnsubscribeLinkIfTeamMember;
        module.BugSubscribersLoader.prototype
            ._addUnsubscribeLinkIfTeamMember =
            function(my_subscriber) {
                Y.Assert.areSame(subscriber, my_subscriber);
                subscriber_link_added = true;
            };

        // Mock-up stopSubscriberActivity to ensure it's called.
        var activity_on = true;
        var old_indicate =
            module.SubscribersList.prototype.stopSubscriberActivity;
        module.SubscribersList.prototype.stopSubscriberActivity =
            function(my_subscriber, success) {
                Y.Assert.areSame(subscriber, my_subscriber);
                Y.Assert.isTrue(success);
                activity_on = false;
            };

        // Mock lp_client which calls the success handler.
        loader.lp_client = {
            named_post: function(uri, method, conf) {
                conf.on.success();
            }
        };

        // Wrap subscriber like an API-returned value.
        var person = {
            getAttrs: function() {
                return subscriber;
            }
        };

        loader._subscribeSomeoneElse(person);

        Y.Assert.isTrue(subscriber_link_added);
        Y.Assert.isFalse(activity_on);

        // Restore original methods.
        module.BugSubscribersLoader.prototype.addUnsubscribeLinkIfTeamMember =
            old_addLink;
        module.SubscribersList.prototype.stopSubscriberActivity =
            old_indicate;

    },

    test_subscribeSomeoneElse_failure: function() {
        // When subscribing someone else fails, stopSubscriberActivity
        // is called indicating failure and it calls removeSubscriber
        // from the callback when animation completes.
        // Error is shown as well.

        var subscriber = { name: "user", self_link: "/~user",
                           display_name: "User Name" };

        // Initialize the loader.
        var loader = setUpLoader(this.root);
        loader.subscribers_list.addSubscriber(subscriber, "Maybe");

        // Mock-up removeSubscriber to ensure it's called.
        var remove_called = false;
        var old_remove =
            module.SubscribersList.prototype.removeSubscriber;
        module.SubscribersList.prototype.removeSubscriber =
            function(my_subscriber) {
                Y.Assert.areSame(subscriber, my_subscriber);
                remove_called = true;
            };

        // Ensure display_error is called.
        var old_error_method = Y.lp.app.errors.display_error;
        var received_error;
        Y.lp.app.errors.display_error = function(anim, text) {
            received_error = text;
        };

        // Mock lp_client which calls the failure handler.
        loader.lp_client = {
            named_post: function(uri, method, conf) {
                conf.on.failure(99, { status: 500,
                                      statusText: "BOOM" });
            }
        };

        // Wrap subscriber like an API-returned value.
        var person = {
            getAttrs: function() {
                return subscriber;
            }
        };

        loader._subscribeSomeoneElse(person);

        Y.Assert.areSame('500 (BOOM). Failed to subscribe User Name.',
                         received_error);

        // Remove function is only called after animation completes.
        this.wait(function() {
            Y.Assert.isTrue(remove_called);
        }, 1100);

        // Restore original methods.
        module.SubscribersList.prototype.removeSubscriber = old_remove;
        Y.lp.app.errors.display_error = old_error_method;

    }
}));

var handle_complete = function(data) {
    window.status = '::::' + JSON.stringify(data);
    };
Y.Test.Runner.on('complete', handle_complete);
Y.Test.Runner.add(suite);

var console = new Y.Console({newestOnTop: false});
console.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});
});
