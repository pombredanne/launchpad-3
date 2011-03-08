/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    // XXX: This gives us pretty CSS; change it to false before landing.
    fetchCSS: true
    }).use('test', 'console', 'lp.registry.structural_subscription', function(Y) {

    var suite = new Y.Test.Suite("Structural subscription overlay tests");

    // Local aliases
    var Assert = Y.Assert,
        ArrayAssert = Y.ArrayAssert,
        module = Y.lp.registry.structural_subscription;

    suite.add(new Y.Test.Case({
        // Test the setup method.
        name: 'structural_subscription_overlay',

        _should: {
            error: {
                test_setup_config_none: true,
                test_setup_config_no_content_box: true
                }
        },

        setUp: function() {
            // Monkeypatch LP to avoid network traffic and to allow
            // insertion of test data.
            // window is magic?
            window.LP = {
                links: {},
                cache: {}
            };
            Y.lp.client.Launchpad = function() {};
            Y.lp.client.Launchpad.prototype.named_post =
                function(url, func, config) {
                    config.on.success();
                };
            LP.cache.context = {
                title: 'Test Project',
                self_link: 'https://launchpad.dev/api/test_project'
            };
            LP.links.me = 'https://launchpad.dev/api/~someone';
            this.config = {
                content_box: '#structural-subscription-content-box'
            };
        },

        tearDown: function() {
            delete this.config;
        },

        test_setup_config_none: function() {
            // The config passed to setup may not be null.
            Y.lp.registry.structural_subscription.setup();
        },

        test_setup_config_no_content_box: function() {
            // The config passed to setup must contain a content_box.
            Y.lp.registry.structural_subscription.setup({});
        },

        test_anonymous: function() {
            // The link should not be shown to anonymous users so
            // 'setup' should not do anything in that case.  If it
            // were successful, the lp_client would be defined after
            // setup is called.
            LP.links.me = undefined;
            Assert.isUndefined(Y.lp.registry.structural_subscription.lp_client);
            Y.lp.registry.structural_subscription.setup(this.config);
            Assert.isUndefined(Y.lp.registry.structural_subscription.lp_client);
        },

        test_logged_in_user: function() {
            Assert.isUndefined(Y.lp.registry.structural_subscription.lp_client);
            Y.lp.registry.structural_subscription.setup(this.config);
        },

        test_list_contains: function() {
            var list = ['a', 'b', 'c'];
            Assert.isTrue(Y.)
        },

        test_something: function() {
        }

    }));

    suite.add(new Y.Test.Case({
        // Test the setup method.
        name: 'Structural Subscription Overlay',

        _should: {
            error: {
                }
        },

        setUp: function() {
        },

        tearDown: function() {
        },

        test_something: function() {
        }
    }));

    // Lock, stock, and two smoking barrels.
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
