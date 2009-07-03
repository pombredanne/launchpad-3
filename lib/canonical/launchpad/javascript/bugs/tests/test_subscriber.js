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
                'The escaped user uri is the same as the unescaped uri.');
            Y.Assert.areEqual(
                this.subscriber.get('name'),
                this.subscriber.get('escaped_name'),
                'The escaped user name is the same as the unescaped name.');
            Y.Assert.isNull(
                this.subscriber.get('user_node'),
                'This user node is not known and is null at this point.');
            Y.Assert.areSame(
                '',
                this.subscriber.get('display_name'),
                'Without a user node or client, the display name is empty.');
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
                'foo%2Bbar',
                this.subscriber.get('escaped_name'),
                'Escaped user name should be foo%2Bbar');
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
                'The user name is JS Test User.');
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
                uri: '/~tester',
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
                'The user name is JS Test User.');
        }
    }));

    Y.Test.Runner.add(suite);

    var console = new Y.Console({newestOnTop: false});
    console.render('#log');

    Y.on('domready', function() {
        Y.Test.Runner.run();
    });
});

