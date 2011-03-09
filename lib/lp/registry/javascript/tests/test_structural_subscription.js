/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    // XXX: This gives us pretty CSS; change it to false before landing.
    fetchCSS: true
    }).use('test', 'console', 'node', 'lp.client',
        'lp.registry.structural_subscription', function(Y) {

    var suite = new Y.Test.Suite("Structural subscription overlay tests");

    var context;

    // Local aliases
    var Assert = Y.Assert,
        ArrayAssert = Y.ArrayAssert,
        module = Y.lp.registry.structural_subscription;

    // Insert elements into the DOM that are expected.
    var content_box_name = 'ss-content-box';
    var node = Y.Node.create(
            '<div id="' + content_box_name + '"></div>' +
            '<div id="global-actions"></div>'
    );


    function array_compare(a,b) {
        if (a.length != b.length)
            return false;
        a.sort();
        b.sort();
        for (i in a) {
            if (a[i] != b[i])
                return false;
        }
        return true;
    }

    suite.add(new Y.Test.Case({
        // Test the setup method.
        name: 'structural_subscription_overlay',

        _should: {
            error: {
                test_setup_config_none: new Error(
                    'Missing config for structural_subscription.'),
                test_setup_config_no_content_box: new Error(
                    'Structural_subscription configuration has undefined properties.')
                }
        },

        setUp: function() {
            // Monkeypatch LP to avoid network traffic and to allow
            // insertion of test data.
            window.LP = {
                links: {},
                cache: {}
            };
            var lp_client = function() {};
            lp_client.prototype.named_post =
                function(url, func, config) {
                    config.on.success();
                };
            lp_client.prototype.patch =
                function(url, func, config) {
                    Y.log('patch from test case 1 called');
                    context.url = url;
                    context.func = func;
                    context.config = config;
                };
            LP.cache.context = {
                title: 'Test Project',
                self_link: 'https://launchpad.dev/api/test_project'
            };
            LP.links.me = 'https://launchpad.dev/api/~someone';
            this.config = {
                content_box: '#' + content_box_name,
                lp_client: new lp_client()
            };
            Y.one('body').appendChild(node);
            context = {};
        },

        tearDown: function() {
            delete this.config;
            delete module.lp_client;
        },

        test_setup_config_none: function() {
            // The config passed to setup may not be null.
            module.setup();
        },

        test_setup_config_no_content_box: function() {
            // The config passed to setup must contain a content_box.
            module.setup({});
        },

        test_anonymous: function() {
            // The link should not be shown to anonymous users so
            // 'setup' should not do anything in that case.  If it
            // were successful, the lp_client would be defined after
            // setup is called.
            LP.links.me = undefined;
            Assert.isUndefined(module.lp_client);
            module.setup(this.config);
            Assert.isUndefined(module.lp_client);
        },

        test_logged_in_user: function() {
            Assert.isUndefined(module.lp_client);
            module.setup(this.config);
        },

        test_list_contains: function() {
            var list = ['a', 'b', 'c'];
            Assert.isTrue(module.list_contains(list, 'b'));
            Assert.isFalse(module.list_contains(list, 'd'));
            Assert.isFalse(module.list_contains([], 'a'));
            Assert.isTrue(module.list_contains(['a', 'a'], 'a'));
            Assert.isFalse(module.list_contains([], ''));
            Assert.isFalse(module.list_contains([], null));
            Assert.isFalse(module.list_contains(['a'], null));
            Assert.isFalse(module.list_contains([]));
        },

        test_something: function() {
        //importances:["999","50","40","30","20","10","5"],
        //statuses:["10","15","16","17","18","19","20","21","22","25","30","999"]
        }

    }));

    suite.add(new Y.Test.Case({
        // Test the setup method.
        name: 'Structural Subscription Overlay patch_bug_filter',

        _should: {
            error: {
                }
        },

        setUp: function() {
            // Monkeypatch LP to avoid network traffic and to allow
            // insertion of test data.
            window.LP = {
                links: {},
                cache: {}
            };
            var lp_client = function() {};
            lp_client.prototype.named_post =
                function(url, func, config) {
                    config.on.success();
                };
            lp_client.prototype.patch =
                function(url, func, config) {
                    Y.log('patch from test case 2 called');
                    context.url = url;
                    context.func = func;
                    context.config = config;
                };
            // We set up the module's lp_client here because
            // module.setup() nees to wait for a domready event before
            // doing all its lp_client stuff. Tests are run
            // asynchronously so that can cause problems.
            module.lp_client = new lp_client();
            LP.cache.context = {
                title: 'Test Project',
                self_link: 'https://launchpad.dev/api/test_project'
            };
            LP.links.me = 'https://launchpad.dev/api/~someone';
            Y.one('body').appendChild(node);

            this.config = {
                content_box: '#' + content_box_name
            };

            this.bug_filter = {
                lp_original_uri: '/api/devel/firefox/+subscription/mark/+filter/28'
            };
            this.form_data = {
                recipient: ['user'],
                name: ['my ui bugs'],
                events:["added-or-changed"],
                filters:["filter-out-comments","advanced-filter"],
                tag_match:["match_all"],
                tags:["ui"],
                importances:[],
                statuses:[]
            };
            context = {};
            module.setup(this.config);
        },

        tearDown: function() {
            delete this.config;
        },

        test_basics: function() {
            module.patch_bug_filter(this.bug_filter, this.form_data);
            Assert.areEqual(this.bug_filter.lp_original_uri, context.url);
            Assert.areEqual(this.form_data.name, context.func.description);
            Assert.areEqual('Discussion', context.func.bug_notification_level);
            Assert.isTrue(array_compare(this.form_data.tags, context.func.tags));
        },

        test_events_added_or_closed: function() {
            this.form_data.events = ['added-or-closed'];
            module.patch_bug_filter(this.bug_filter, this.form_data);
            Assert.areEqual('Lifecycle', context.func.bug_notification_level);
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

    // Comment out the next two lines for better debugging interaction.
    //var console = new Y.Console({newestOnTop: false});
    //console.render('#log');

    Y.on('domready', function() {
        Y.Test.Runner.run();
    });
});
