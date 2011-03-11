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
    var test_case;

    // Local aliases
    var Assert = Y.Assert,
        ArrayAssert = Y.ArrayAssert,
        module = Y.lp.registry.structural_subscription;

    // Insert elements into the DOM that are expected.
    var content_box_name = 'ss-content-box';

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

    function create_test_node() {
        return Y.Node.create(
                '<div id="test-content">' +
                '  <div id="' + content_box_name + '"></div>' +
                '  <div id="global-actions"></div>' +
                '</div>');
    }

    function remove_test_node() {
        Y.one('body').removeChild(Y.one('#test-content'));
        //var parent = this.content_node.get('parentNode');
        //if (Y.Lang.isValue(parent)) {
        //    parent.removeChild(this.content_node);
        //}
    }

    test_case = new Y.Test.Case({
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
            LP.cache.context = {
                title: 'Test Project',
                self_link: 'https://launchpad.dev/api/test_project'
            };
            LP.links.me = 'https://launchpad.dev/api/~someone';
            var lp_client = function() {};
            this.configuration = {
                content_box: '#' + content_box_name,
                lp_client: lp_client
            };

            this.content_node = create_test_node();

            Y.one('body').appendChild(this.content_node);
            context = {};
        },

        tearDown: function() {
            //delete this.configuration;
            remove_test_node();
            delete this.content_node;
            delete this.configuration.lp_client;
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
            module.setup(this.configuration);
            Assert.isUndefined(module.lp_client);
        },

        test_logged_in_user: function() {
            LP.links.me = 'https://launchpad.dev/api/~someone';
            Assert.isUndefined(module.lp_client);
            module.setup(this.configuration);
            Assert.isNotUndefined(module.lp_client);
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
        }
    });
    suite.add(test_case);

    test_case = new Y.Test.Case({
        // Test the setup method.
        name: 'Structural Subscription Overlay save_subscription',

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
            Y.lp.client.Launchpad = function() {};
            Y.lp.client.Launchpad.prototype.named_post =
                function(url, func, config) {
                    context.url = url;
                    context.func = func;
                    context.config = config;
                    // No need to call the on.success handler.
                };
            LP.cache.context = {
                title: 'Test Project',
                self_link: 'https://launchpad.dev/api/test_project'
            };
            LP.links.me = 'https://launchpad.dev/api/~someone';

            this.content_node = create_test_node();

            Y.one('body').appendChild(this.content_node);

            this.configuration = {
                content_box: '#' + content_box_name
            };

            this.bug_filter = {
                lp_original_uri: '/api/devel/firefox/+subscription/mark/+filter/28'
            };
            this.form_data = {
                recipient: ['user']
            };
            context = {};
            module.setup(this.configuration);
        },

        tearDown: function() {
            delete this.configuration;
            remove_test_node();
            delete this.content_node;
        },

        test_user_recipient: function() {
            this.form_data.recipient = ['user'];
            module.save_subscription(this.form_data);
            Assert.areEqual(LP.links.me, context.config.parameters.subscriber);
        },

        test_team_recipient: function() {
            this.form_data.recipient = ['team'];
            this.form_data.team = ['https://launchpad.dev/api/~super-team'];
            module.save_subscription(this.form_data);
            Assert.areEqual(this.form_data.team[0], context.config.parameters.subscriber);
        }
    });
    suite.add(test_case);

    test_case = new Y.Test.Case({
        // Test the setup method.
        name: 'Structural Subscription setup_overlay',

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

            LP.cache.context = {
                title: 'Test Project',
                self_link: 'https://launchpad.dev/api/test_project'
            };
            LP.links.me = 'https://launchpad.dev/api/~someone';

            this.configuration = {
                content_box: '#' + content_box_name
            };

            this.content_node = create_test_node();
            Y.one('body').appendChild(this.content_node);
        },

        tearDown: function() {
            remove_test_node();
            delete this.content_node;
        },

        test_setup_overlay: function() {
            // At the outset there should be no overlay.
            var overlay = Y.one('#accordion-overlay');
            Assert.isNull(overlay);
            module.setup(this.configuration);
            // After the setup the overlay should be in the DOM.
            overlay = Y.one('#accordion-overlay');
            Assert.isNotNull(overlay);
        },

        test_initial_state: function() {
            // When initialized the <div> elements for the filter
            // wrapper and the accordion wrapper should be collapsed.
            module.setup(this.configuration);
            var filter_wrapper = Y.one('#filter-wrapper');
            var accordion_wrapper = Y.one('#accordion-wrapper');
            Assert.isTrue(filter_wrapper.hasClass('lazr-closed'),
                "this test is known to fail but it isn't understood");
            Assert.isTrue(accordion_wrapper.hasClass('lazr-closed'),
                "ditto");
        }
    });
    suite.add(test_case);

    test_case = new Y.Test.Case({
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
            lp_client.named_post =
                function(url, func, config) {
                    config.on.success();
                };
            lp_client.patch =
                function(url, func, config) {
                    Y.log('patch from test case 2 called');
                    context.url = url;
                    context.func = func;
                    context.config = config;
                };

            LP.cache.context = {
                title: 'Test Project',
                self_link: 'https://launchpad.dev/api/test_project'
            };
            LP.links.me = 'https://launchpad.dev/api/~someone';

            this.content_node = create_test_node();

            Y.one('body').appendChild(this.content_node);

            this.configuration = {
                content_box: '#' + content_box_name,
                lp_client: lp_client
            };

            this.bug_filter = {
                lp_original_uri: '/api/devel/firefox/+subscription/mark/+filter/28'
            };
            this.form_data = {
                recipient: ['user'],
                name: ['my ui bugs'],
                events:['added-or-changed'],
                filters:['filter-out-comments','advanced-filter'],
                tag_match:['match-all'],
                tags:['ui'],
                importances:[],
                statuses:[]
            };
            context = {};
            module.setup(this.configuration);
        },

        tearDown: function() {
            delete this.configuration.lp_client;
            delete this.configuration;
            remove_test_node();
            delete this.content_node;
        },

        test_basics: function() {
            module.patch_bug_filter(this.bug_filter, this.form_data);
            Assert.areEqual(this.bug_filter.lp_original_uri, context.url);
            Assert.areEqual(this.form_data.name, context.func.description);
        },

        // Test events and bug notification level.
        test_events_added_or_closed: function() {
            this.form_data.events = ['added-or-closed'];
            module.patch_bug_filter(this.bug_filter, this.form_data);
            Assert.areEqual('Lifecycle', context.func.bug_notification_level);
        },

        test_events_added_or_changed_no_filters: function() {
            this.form_data.events = ['added-or-changed'];
            this.form_data.filters = [];
            module.patch_bug_filter(this.bug_filter, this.form_data);
            Assert.areEqual('Discussion', context.func.bug_notification_level);
        },

        test_events_added_or_changed_with_filters: function() {
            this.form_data.events = ['added-or-changed'];
            this.form_data.filters = ['filter-comments'];
            this.form_data.tags = ['bug-jam'];
            this.form_data.importances = ['High', 'Medium'];
            this.form_data.statuses = ['Confirmed'];
            module.patch_bug_filter(this.bug_filter, this.form_data);
            Assert.areEqual('Details', context.func.bug_notification_level);
            // Since the advanced filter is not on, no tags, statuses,
            // or importances are in the patch even though they were
            // specified in the form data.
            Assert.isUndefined(context.func.tags);
            Assert.isUndefined(context.func.statuses);
            Assert.isUndefined(context.func.importances);
        },
        // Test advanced filter.
        test_advanced_filter: function() {
            this.form_data.events = ['added-or-changed'];
            this.form_data.filters = ['advanced-filter'];
            this.form_data.tags = ['ui bug-jam'];
            this.form_data.importances = ['High', 'Medium'];
            this.form_data.statuses = ['Confirmed'];
            module.patch_bug_filter(this.bug_filter, this.form_data);
            var expected_tags = this.form_data.tags[0].split(' ');
            Assert.isTrue(array_compare(expected_tags, context.func.tags));
            Assert.isTrue(array_compare(this.form_data.statuses, context.func.statuses));
            Assert.isTrue(array_compare(this.form_data.importances,
                context.func.importances));
        },
        test_advanced_filter_no_data: function() {
            this.form_data.events = ['added-or-changed'];
            this.form_data.filters = ['advanced-filter'];
            this.form_data.tags = [];
            this.form_data.importances = [];
            this.form_data.statuses = [];
            module.patch_bug_filter(this.bug_filter, this.form_data);
            Assert.isUndefined(context.func.tags);
            Assert.isUndefined(context.func.statuses);
            Assert.isUndefined(context.func.importances);
        },

        // Test tags conversion to lowercase, as required by Launchpad.
        test_tags_mixed_case: function() {
            this.form_data.events = ['added-or-changed'];
            this.form_data.filters = ['advanced-filter'];
            this.form_data.tags = ['BugJam Helter_Skelter'];
            module.patch_bug_filter(this.bug_filter, this.form_data);
            var expected_tags = this.form_data.tags[0].toLowerCase().split(' ');
            Assert.isTrue(array_compare(expected_tags, context.func.tags));
        },

        test_tags_match_all: function() {
            this.form_data.events = ['added-or-changed'];
            this.form_data.filters = ['advanced-filter'];
            this.form_data.tags = ['bugjam'];
            this.form_data.tag_match = ['match-all'];
            module.patch_bug_filter(this.bug_filter, this.form_data);
            Assert.isTrue(context.func.find_all_tags);
        },

        test_tags_match_any: function() {
            this.form_data.events = ['added-or-changed'];
            this.form_data.filters = ['advanced-filter'];
            this.form_data.tags = ['bugjam'];
            this.form_data.tag_match = ['match-any'];
            module.patch_bug_filter(this.bug_filter, this.form_data);
            Assert.isUndefined(context.func.find_all_tags);
        }
    });
    suite.add(test_case);

    // Lock, stock, and two smoking barrels.
    var handle_complete = function(data) {
        var status_node = Y.Node.create(
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
