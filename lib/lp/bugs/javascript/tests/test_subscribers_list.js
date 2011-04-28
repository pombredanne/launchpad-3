YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
   }).use('test', 'console', 'lp.bugs.subscriber', 'lp.bugs.subscribers_list',
          'node-event-simulate',
          function(Y) {

var suite = new Y.Test.Suite("lp.bugs.subscribers_list Tests");
var module = Y.lp.bugs.subscribers_list;


/**
 * Set-up all the nodes required for subscribers list testing.
 */
function setUpSubscribersList(root_node, with_dupes) {
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
        var subscribers_list = setUpSubscribersList(this.root);

        // Resetting the list adds a 'None' div to the
        // subscribers_list (and not to the subscriber_links).
        module._reset();
        var none_node = subscribers_list.one('#none-subscribers');
        Y.Assert.isNotNull(none_node);
        Y.Assert.areEqual('None', none_node.get('innerHTML'));
        Y.Assert.areEqual(subscribers_list,
                          none_node.get('parentNode'));

    },

    test_subscribers: function() {
        // When there is at least one subscriber, nothing
        // happens when reset() is called.
        var subscribers_list = setUpSubscribersList(this.root);
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
        var subscribers_list = setUpSubscribersList(this.root, true);
        var dupe_subscribers = this.root.one('#subscribers-from-duplicates');

        // Resetting the list removes the entire duplicate subscribers node.
        module._reset();
        Y.Assert.isNull(Y.one('#subscribers-from-duplicates'));

    },

    test_duplicates: function() {
        // There are subscribers among the duplicate subscribers,
        // and nothing changes.
        var subscribers_list = setUpSubscribersList(this.root, true);
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
        setUpSubscribersList(this.root);

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

    test_direct_subscriber: function() {
        // If there is a direct subscriber, removal works fine.

        // Set-up subscribers list.
        setUpSubscribersList(this.root);

        var person = new Y.lp.bugs.subscriber.Subscriber({
            uri: 'myself',
            subscriber_ids: this.subscriber_ids
        });
        this.addSubscriber(this.root, person);

        module.remove_user_link(person);

        this.wait(function() {
            // There is no subscriber link anymore.
            Y.Assert.isNull(this.root.one('.' + person.get('css_name')));
            // And the reset() call adds the "None" node.
            Y.Assert.isNotNull(this.root.one('#none-subscribers'));
        }, 1100);
    },

    test_direct_subscriber_remove_dupe: function() {
        // If there is only a direct subscriber, attempting removal of
        // a duplicate subscription link does nothing.

        // Set-up subscribers list.
        setUpSubscribersList(this.root);

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
        setUpSubscribersList(this.root, true);

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
        setUpSubscribersList(this.root, true);

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
        setUpSubscribersList(this.root, true);

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
            Y.Assert.areEqual(1, nodes.size())
            Y.Assert.areEqual('direct-' + person.get('css_name'),
                              nodes.pop().get('id'));
        }, 1100);
    },

    test_direct_and_dupe_subscriber_remove_direct: function() {
        // If there a subscriber is both directly subscribed and
        // subscribed through duplicate, removal removes only one link.

        // Set-up subscribers list.
        setUpSubscribersList(this.root, true);

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
            Y.Assert.areEqual(1, nodes.size())
            Y.Assert.areEqual('dupe-' + person.get('css_name'),
                              nodes.pop().get('id'));
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
