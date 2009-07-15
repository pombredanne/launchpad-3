YUI({
    base: '../../../icing/yui/current/build/',
    filter: 'raw', combine: false
    }).use('yuitest', 'console', 'lp.subscriber', function(Y) {

var suite = new Y.Test.Suite("lp.subscriber Tests");

/*
 * Test that all the parts of the user name
 * are set when given just a URI.
 */
suite.add(new Y.Test.Case({
    name: 'Subscriber From Simple Config',

    setUp: function() {
        this.config = {
            uri: '/~deryck'
        };
        this.subscriber = new Y.lp.Subscriber(this.config);
    },

    tearDown: function() {
        delete this.config;
        delete this.subscriber;
    },

    test_uri_config: function() {
        Y.Assert.areEqual(
            '/~deryck',
            this.subscriber.get('uri'),
            'User URI should be /~deryck');
        Y.Assert.areEqual(
            'deryck',
            this.subscriber.get('name'),
            'User name should be deryck');
        Y.Assert.areEqual(
            this.subscriber.get('uri'),
            this.subscriber.get('escaped_uri'),
            'The escaped user uri should be the same as the unescaped uri.');
        Y.Assert.areEqual(
            this.subscriber.get('name'),
            this.subscriber.get('escaped_name'),
            'The escaped user name should be the same as the unescaped name.');
        Y.Assert.isNull(
            this.subscriber.get('user_node'),
            'User node should not be known and should be null at this point.');
        Y.Assert.areSame(
            '',
            this.subscriber.get('display_name'),
            'Without a user node or client, the display name should be empty.');
    }
}));

/*
 * Test that all the parts of the user name
 * are set correctly when a name needs escaping.
 */
suite.add(new Y.Test.Case({
    name: 'Escaping Subscriber From Simple Config',

    setUp: function() {
        this.config = {
            uri: '/~foo+bar'
        };
        this.subscriber = new Y.lp.Subscriber(this.config);
    },

    tearDown: function() {
        delete this.config;
        delete this.subscriber;
    },

    test_escaping_uri_config: function() {
        Y.Assert.areEqual(
            '/~foo+bar',
            this.subscriber.get('uri'),
            'User URI should be /~foo+bar');
        Y.Assert.areEqual(
            'foo+bar',
            this.subscriber.get('name'),
            'User name should be foo+bar');
        Y.Assert.areEqual(
            '/~foo%2Bbar',
            this.subscriber.get('escaped_uri'),
            'Escaped user URI should be /~foo%2Bbar');
        Y.Assert.areEqual(
            'foo-bar',
            this.subscriber.get('escaped_name'),
            'Escaped user name should be foo-Bbar');
    }
}));

/*
 * Test that the display_name is correctly worked out
 * when passed a Node.
 */
suite.add(new Y.Test.Case({
    name: 'Subscriber Name When Passed Node',

    setUp: function() {
        var node = Y.get('.subscriber-tester');
        this.config = {
            uri: '/~tester',
            user_node: node
        };
        this.subscriber = new Y.lp.Subscriber(this.config);
    },

    tearDown: function() {
        delete this.config;
        delete this.subscriber;
    },

    test_display_name: function() {
        Y.Assert.areEqual(
            'JS Test User',
            this.subscriber.get('display_name'),
            'The user name should be JS Test User.');
    }
}));

/*
 * Test that display_name is correctly worked out from
 * the DOM when not passed a Node.
 */
suite.add(new Y.Test.Case({
    name: 'Subscriber Name When Not Passed Node',

    setUp: function() {
        this.config = {
            uri: '/~tester'
        };
        this.subscriber = new Y.lp.Subscriber(this.config);
    },

    tearDown: function() {
        delete this.config;
        delete this.subscriber;
    },

    test_display_name_from_dom: function() {
        Y.Assert.areEqual(
            'JS Test User',
            this.subscriber.get('display_name'),
            'The user name should be JS Test User.');
    }
}));

/*
 * Test that the displaynameload event fires.
 */
suite.add(new Y.Test.Case({
    name: 'Subscriber displaynameload',

    test_display_name_load_event: function() {
        var test = this;
        var event_fired = false;
        var subscriber = new Y.lp.Subscriber();
        subscriber.on('displaynameload', function(e) {
            event_fired = true;
            test.resume(Y.Assert.areSame(
                true, event_fired, 'The event should have been fired.'));
        });
        subscriber.set('uri', '/~tester');
        subscriber.initializer();
        test.wait(2000);
    }
}));

/*
 * Test that a Subscription is properly initialized from
 * a simple config and that the basic methods work.
 */
suite.add(new Y.Test.Case({
    name: 'Subscription Test',

    setUp: function() {
        this.config = {
            can_be_unsubscribed: false,
            is_direct: true,
            is_team: true
        };
        this.subscription = new Y.lp.Subscription(this.config);
    },

    tearDown: function() {
        delete this.config;
        delete this.subscription;
    },

    test_subscription_config: function() {
        Y.Assert.isFalse(
            this.subscription.can_be_unsubscribed_by_user(),
            'The user should not be able to unsubscribed this subscription.');
        Y.Assert.isTrue(
            this.subscription.is_team(),
            'This subscription should be for a team.');
        Y.Assert.isTrue(
            this.subscription.is_direct_subscription(),
            'This should be a direct subscription.');
        // Also check that the defaults were set.
        Y.Assert.isNull(
            this.subscription.get('person'),
            'The subscription should not be setup for a person.');
        Y.Assert.isNull(
            this.subscription.get('subscriber'),
            'The subscription should not be setup for a subscriber.');
    },

    test_subscription_is_node: function() {
        Y.Assert.isFalse(
            this.subscription.is_node(),
            'Initially, no node should be supplied to the config.');
        var link = Y.get('.menu-link-subscription');
        this.subscription.set('link', link);
        Y.Assert.isTrue(
            this.subscription.is_node(),
            'This subscription should have a node for subscription link.');
    },

    test_already_subscribed: function() {
        var person = new Y.lp.Subscriber({uri: '/~tester'});
        this.subscription.set('person', person);
        Y.Assert.isTrue(
            this.subscription.is_already_subscribed(),
            'The JS Test User should be already subscribed.');
    },

    test_is_current_user_subscribing: function() {
        var person = new Y.lp.Subscriber({uri: '/~tester'});
        this.subscription.set('person', person);
        var subscriber = this.subscription.get('person');
        this.subscription.set('subscriber', subscriber);
        Y.Assert.isTrue(
            this.subscription.is_current_user_subscribing(),
            'Current user should be the same person being subscribed.');
    }
}));


Y.Test.Runner.add(suite);

var console = new Y.Console({newestOnTop: false});
console.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});
});

