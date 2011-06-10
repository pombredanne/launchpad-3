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
function setUpOldSubscribersList(root_node, with_dupes) {
    // Set-up subscribers list.
    var direct_links = Y.Node.create('<div></div>')
        .set('id', 'subscribers-links');
    var direct_list = Y.Node.create('<div></div>')
        .set('id', 'subscribers-direct');
    direct_list.appendChild(direct_links);
    root_node.appendChild(direct_list);

    if (with_dupes === true) {
        var dupe_links = Y.Node.create('<div></div>')
            .set('id', 'subscribers-from-duplicates');
        var dupe_list = Y.Node.create('<div></div>')
            .set('id', 'subscribers-from-duplicates-container');
        dupe_list.appendChild(dupe_links);
        root_node.appendChild(dupe_list);
    }
    return direct_list;
}

/**
 * Test resetting of the subscribers list.
 */
suite.add(new Y.Test.Case({
    name: 'Resetting subscribers list',

    setUp: function() {
        this.root = Y.Node.create('<div></div>');
        Y.one('body').appendChild(this.root);
    },

    tearDown: function() {
        this.root.remove();
    },

    test_no_subscribers: function() {
        // There are no subscribers left in the subscribers_list
        // (iow, subscribers_links is empty).
        var subscribers_list = setUpOldSubscribersList(this.root);

        // Resetting the list adds a 'None' div to the
        // subscribers_list (and not to the subscriber_links).
        module._reset();
        var none_node = subscribers_list.one('#none-subscribers');
        Y.Assert.isNotNull(none_node);
        Y.Assert.areEqual('No subscribers.', none_node.get('innerHTML'));
        Y.Assert.areEqual(subscribers_list,
                          none_node.get('parentNode'));

    },

    test_subscribers: function() {
        // When there is at least one subscriber, nothing
        // happens when reset() is called.
        var subscribers_list = setUpOldSubscribersList(this.root);
        var subscribers_links = subscribers_list.one('#subscribers-links');
        subscribers_links.appendChild(
            Y.Node.create('<div>Subscriber</div>'));

        // Resetting the list is a no-op.
        module._reset();
        var none_node = subscribers_list.one('#none-subscribers');
        Y.Assert.isNull(none_node);
    },


    test_empty_duplicates: function() {
        // There are no subscribers among the duplicate subscribers.
        var subscribers_list = setUpOldSubscribersList(this.root, true);
        var dupe_subscribers = this.root.one('#subscribers-from-duplicates');

        // Resetting the list removes the entire duplicate subscribers node.
        module._reset();
        Y.Assert.isNull(Y.one('#subscribers-from-duplicates'));

    },

    test_duplicates: function() {
        // There are subscribers among the duplicate subscribers,
        // and nothing changes.
        var subscribers_list = setUpOldSubscribersList(this.root, true);
        var dupe_subscribers = this.root.one('#subscribers-from-duplicates');
        dupe_subscribers.appendChild(Y.Node.create('<div>Subscriber</div>'));

        // Resetting the list does nothing.
        module._reset();

        // The list is still there.
        var dupes_node = this.root.one('#subscribers-from-duplicates');
        Y.Assert.isNotNull(dupes_node);
        Y.Assert.areEqual(1, dupes_node.all('div').size());
    }
}));


/**
 * Test removal of a single person link from the subscribers list.
 */
suite.add(new Y.Test.Case({
    name: 'Removal of a subscriber link',

    addSubscriber: function(root_node, subscriber, through_dupe) {
        var css_class = subscriber.get('css_name');
        var id;
        if (through_dupe === true) {
            links = root_node.one('#subscribers-from-duplicates');
            id = 'dupe-' + css_class;
        } else {
            links = root_node.one('#subscribers-links');
            id = 'direct-' + css_class;
        }
        return links.appendChild(
            Y.Node.create('<div></div>')
                .addClass(css_class)
                .set('id', id)
                .set('text', subscriber.get('uri')));
    },

    setUp: function() {
        this.root = Y.Node.create('<div></div>');
        Y.one('body').appendChild(this.root);
        this.subscriber_ids = {};
    },

    tearDown: function() {
        this.root.remove();
        delete this.subscriber_ids;
    },

    test_no_matching_subscriber: function() {
        // If there is no matching subscriber, removal silently passes.

        // Set-up subscribers list.
        setUpOldSubscribersList(this.root);

        var person = new Y.lp.bugs.subscriber.Subscriber({
            uri: 'myself',
            subscriber_ids: this.subscriber_ids
        });
        var other_person = new Y.lp.bugs.subscriber.Subscriber({
            uri: 'someone',
            subscriber_ids: this.subscriber_ids
        });
        this.addSubscriber(this.root, other_person);

        module.remove_user_link(person);

        // `other_person` is not removed.
        Y.Assert.isNotNull(
            this.root.one('.' + other_person.get('css_name')));
    },

    test_unsubscribe_icon_removal: function() {
        // If there is an unsubscribe icon, it gets removed
        // before animation starts.

        // Set-up subscribers list.
        setUpOldSubscribersList(this.root);

        var person = new Y.lp.bugs.subscriber.Subscriber({
            uri: 'myself',
            subscriber_ids: this.subscriber_ids
        });
        this.addSubscriber(this.root, person);
        var css_name = person.get('css_name');
        this.root.one('.' + css_name)
            .appendChild('<div></div>')
            .appendChild('<img></img>')
            .set('id', 'unsubscribe-icon-' + css_name);

        module.remove_user_link(person);

        // Unsubscribe icon is removed immediatelly.
        Y.Assert.isNull(this.root.one('#unsubscribe-icon-' + css_name));
    },

    test_direct_subscriber: function() {
        // If there is a direct subscriber, removal works fine.

        // Set-up subscribers list.
        setUpOldSubscribersList(this.root);

        var person = new Y.lp.bugs.subscriber.Subscriber({
            uri: 'myself',
            subscriber_ids: this.subscriber_ids
        });
        this.addSubscriber(this.root, person);

        module.remove_user_link(person);

        this.wait(function() {
            // There is no subscriber link anymore.
            Y.Assert.isNull(this.root.one('.' + person.get('css_name')));
            // And the reset() call adds the "No subscribers" node.
            Y.Assert.isNotNull(this.root.one('#none-subscribers'));
        }, 1100);
    },

    test_direct_subscriber_remove_dupe: function() {
        // If there is only a direct subscriber, attempting removal of
        // a duplicate subscription link does nothing.

        // Set-up subscribers list.
        setUpOldSubscribersList(this.root);

        var person = new Y.lp.bugs.subscriber.Subscriber({
            uri: 'myself',
            subscriber_ids: this.subscriber_ids
        });
        this.addSubscriber(this.root, person);

        module.remove_user_link(person, true);

        this.wait(function() {
            // There is no subscriber link anymore.
            Y.Assert.isNotNull(this.root.one('.' + person.get('css_name')));
        }, 1100);
    },

    test_dupe_subscriber: function() {
        // If there is a duplicate subscriber, removal works fine.

        // Set-up subscribers list.
        setUpOldSubscribersList(this.root, true);

        var person = new Y.lp.bugs.subscriber.Subscriber({
            uri: 'myself',
            subscriber_ids: this.subscriber_ids
        });
        this.addSubscriber(this.root, person, true);

        module.remove_user_link(person, true);

        this.wait(function() {
            // There is no subscriber link anymore.
            Y.Assert.isNull(this.root.one('.' + person.get('css_name')));
            // And the reset() call cleans up the entire duplicate section.
            Y.Assert.isNull(this.root.one('#subscribers-from-duplicates'));
        }, 1100);
    },

    test_dupe_subscriber_remove_direct: function() {
        // If there is a duplicate subscriber, trying to remove the
        // direct subscription user link doesn't do anything.

        // Set-up subscribers list.
        setUpOldSubscribersList(this.root, true);

        var person = new Y.lp.bugs.subscriber.Subscriber({
            uri: 'myself',
            subscriber_ids: this.subscriber_ids
        });
        this.addSubscriber(this.root, person, true);

        module.remove_user_link(person);

        this.wait(function() {
            // There is no subscriber link anymore.
            Y.Assert.isNotNull(this.root.one('.' + person.get('css_name')));
        }, 1100);
    },

    test_direct_and_dupe_subscriber_remove_dupe: function() {
        // If there a subscriber is both directly subscribed and
        // subscribed through duplicate, removal removes only one link.

        // Set-up subscribers list.
        setUpOldSubscribersList(this.root, true);

        var person = new Y.lp.bugs.subscriber.Subscriber({
            uri: 'myself',
            subscriber_ids: this.subscriber_ids
        });
        this.addSubscriber(this.root, person);
        this.addSubscriber(this.root, person, true);

        // Remove the duplicate subscription link.
        module.remove_user_link(person, true);

        this.wait(function() {
            // Remaining entry is the direct subscription one.
            var nodes = this.root.all('.' + person.get('css_name'));
            Y.Assert.areEqual(1, nodes.size());
            Y.Assert.areEqual('direct-' + person.get('css_name'),
                              nodes.pop().get('id'));
        }, 1100);
    },

    test_direct_and_dupe_subscriber_remove_direct: function() {
        // If there a subscriber is both directly subscribed and
        // subscribed through duplicate, removal removes only one link.

        // Set-up subscribers list.
        setUpOldSubscribersList(this.root, true);

        var person = new Y.lp.bugs.subscriber.Subscriber({
            uri: 'myself',
            subscriber_ids: this.subscriber_ids
        });
        this.addSubscriber(this.root, person);
        this.addSubscriber(this.root, person, true);

        // Remove the direct subscription link.
        module.remove_user_link(person);

        this.wait(function() {
            // Remaining entry is the duplicate subscription one.
            var nodes = this.root.all('.' + person.get('css_name'));
            Y.Assert.areEqual(1, nodes.size());
            Y.Assert.areEqual('dupe-' + person.get('css_name'),
                              nodes.pop().get('id'));
        }, 1100);
    }
}));

/**
 * Set-up all the nodes required for subscribers list testing.
 */
function setUpSubscribersList(root_node) {
    // Set-up subscribers list.
    var node = Y.Node.create('<div></div>')
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
        this.root = Y.Node.create('<div></div>');
        Y.one('body').appendChild(this.root);
    },

    tearDown: function() {
        this.root.remove();
    },

    test_no_container_error: function() {
        // When there is no matching container node in the DOM tree,
        // an exception is thrown.
        new module.SubscribersList({container_box: '#not-found'});
    },

    test_single_container: function() {
        // With an exactly single container node matches, all is well.
        var container_node = Y.Node.create('<div></div>')
            .set('id', 'container');
        this.root.appendChild(container_node);
        var list = new module.SubscribersList({container_box: '#container'});
        Y.Assert.areSame(container_node, list.container_node);
    },

    test_multiple_containers_error: function() {
        // With two nodes matching the given CSS selector,
        // an exception is thrown.
        this.root.appendChild(
            Y.Node.create('<div></div>').addClass('container'));
        this.root.appendChild(
            Y.Node.create('<div></div>').addClass('container'));
        new module.SubscribersList({container_box: '.container'});
    }
}));


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
    name: 'SubscribersList._getOrCreateSection() test',

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
        var section_node1 = subscribers_list._getOrCreateSection('Discussion');
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
        var node = subscribers_list._getOrCreateSection('Details');
        Y.Assert.isFalse(subscribers_list._sectionNodeHasSubscribers(node));
    },

    test_sectionNodeHasSubscribers_subscribers: function() {
        // When called on a proper section node with subscribers,
        // it returns true.
        var subscribers_list = setUpSubscribersList(this.root);
        var node = subscribers_list._getOrCreateSection('Details');
        var subscriber = Y.Node.create('<div></div>')
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
        var section_node = Y.Node.create('<div></div>');
        subscribers_list._removeSectionNodeIfEmpty(section_node);
    },

    test_removeSectionNodeIfEmpty_remove: function() {
        // When there is an empty section, it's removed.
        var subscribers_list = setUpSubscribersList(this.root);
        var section_node = subscribers_list._getOrCreateSection('Details');

        var section_node = subscribers_list._getSection('Details');
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
            Y.Node.create('<div></div>')
                .addClass('subscriber'));

        var section_node = subscribers_list._getSection('Details');
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
        var section_node2 = subscribers_list._getOrCreateSection('Discussion');

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
        this.root = Y.Node.create('<div></div>');
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
        var node = subscribers_list.addSubscriber(
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
        var node = Y.Node.create('<div></div>')
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
        for (var index = 0; index < all_subscribers.size(); index++) {
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
        }
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
        this.root = Y.Node.create('<div></div>');
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
        var subscriber = { name: 'user', display_name: 'User Name' }
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
        var subscriber = { name: 'user', display_name: 'User Name' }
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
        var subscriber = { name: 'user' }
        var subscriber_node = subscribers_list.addSubscriber(
            subscriber, "Discussion");
        subscribers_list.addUnsubscribeAction(subscriber, "not-function");
    },

    test_addUnsubscribeAction_callback_on_click: function() {
        // When unsubscribe link is clicked, callback is activated
        // and passed in the subscribers_list and subscriber parameters.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user', display_name: 'User Name' }

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
        var subscriber = { name: 'user' }
        subscribers_list.removeSubscriber(subscriber);
    },

    test_removeSubscriber_section_removed: function() {
        // Removing a subscriber works when the subscriber is in the list.
        var subscribers_list = setUpSubscribersList(this.root);
        var subscriber = { name: 'user' }
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
        var subscriber = { name: 'user' }
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
        var node = Y.Node.create('<div></div>')
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
        this.root = Y.Node.create('<div></div>');
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
        }

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
        }

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
