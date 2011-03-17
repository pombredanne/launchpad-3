/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: false
    }).use('test', 'console', 'node', 'lp.client',
        'lp.registry.structural_subscription', function(Y) {

    var suite = new Y.Test.Suite("Structural subscription overlay tests");

    var context;
    var test_case;

    // Local aliases
    var Assert = Y.Assert,
        module = Y.lp.registry.structural_subscription;

    // Expected content box.
    var content_box_name = 'ss-content-box';
    var content_box_id = '#' + content_box_name;

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
    }

    function test_checked(list, expected) {
        var item, i;
        var length = list.size();
        for (i=0; i < length; i++) {
            item = list.item(i);
            if (item.get('checked') != expected)
                return false;
        }
        return true;
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
            LP.cache.administratedTeams = [];
            this.configuration = {
                content_box: content_box_id,
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
        },

        test_make_selector_controls: function() {
            var name = 'sharona';
            var selectors = module.make_selector_controls(name);
            Assert.areEqual('sharona-select-all', selectors['all_name']);
            Assert.areEqual('sharona-select-none', selectors['none_name']);
            Assert.areEqual('<div id="sharona-selectors"', selectors['html'].slice(0, 27));
        }
    });
    suite.add(test_case);

    test_case = new Y.Test.Case({
        // Test the setup method.
        name: 'Structural Subscription Overlay save_subscription',

        _should: {
            error: {}
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
            LP.cache.administratedTeams = [];
            LP.links.me = 'https://launchpad.dev/api/~someone';

            this.content_node = create_test_node();

            Y.one('body').appendChild(this.content_node);

            this.configuration = {
                content_box: content_box_id
            };

            this.bug_filter = {
                lp_original_uri: '/api/devel/firefox/+subscription/mark/+filter/28'
            };
            this.form_data = {
                recipient: ['user']
            };
            context = {};
        },

        tearDown: function() {
            delete this.configuration;
            remove_test_node();
            delete this.content_node;
        },

        test_user_recipient: function() {
            module.setup(this.configuration);
            this.form_data.recipient = ['user'];
            module.save_subscription(this.form_data);
            Assert.areEqual(LP.links.me, context.config.parameters.subscriber);
        },

        test_team_recipient: function() {
            module.setup(this.configuration);
            this.form_data.recipient = ['team'];
            this.form_data.team = ['https://launchpad.dev/api/~super-team'];
            module.save_subscription(this.form_data);
            Assert.areEqual(this.form_data.team[0], context.config.parameters.subscriber);
        }
    });
    suite.add(test_case);

    test_case = new Y.Test.Case({
        // Test the setup method.
        name: 'Structural Subscription interaction tests',

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
            LP.cache.administratedTeams = [];
            LP.cache.importances = ['Unknown', 'Critical', 'High', 'Medium',
                                   'Low', 'Wishlist', 'Undecided'];
            LP.cache.statuses = ['New', 'Incomplete', 'Opinion',
                                 'Invalid', 'Won\'t Fix', 'Expired',
                                 'Confirmed', 'Triaged', 'In Progress',
                                 'Fix Committed', 'Fix Released', 'Unknown'];
            LP.links.me = 'https://launchpad.dev/api/~someone';

            var lp_client = function() {};
            this.configuration = {
                content_box: content_box_id,
                lp_client: lp_client
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
            var header = Y.one(content_box_id).one('h2');
            Assert.areEqual(
                'Add a mail subscription for Test Project bugs',
                header.get('text'));
        },

        test_initial_state: function() {
            // When initialized the <div> elements for the filter
            // wrapper and the accordion wrapper should be collapsed.
            // Since the collapsing is done via animation, we must
            // wait a bit for it to happen.
            module.setup(this.configuration);
            this.wait(function() {
                var filter_wrapper = Y.one('#filter-wrapper');
                var accordion_wrapper = Y.one('#accordion-wrapper');
                Assert.isTrue(filter_wrapper.hasClass('lazr-closed'));
                Assert.isTrue(accordion_wrapper.hasClass('lazr-closed'));
            }, 500);
        },

        test_added_or_changed_toggles: function() {
            // Test that the filter wrapper opens and closes in
            // response to the added_or_changed radio button.
            module.setup(this.configuration);
            var added_changed = Y.one('#added-or-changed');
            Assert.isFalse(added_changed.get('checked'));
            var filter_wrapper = Y.one('#filter-wrapper');
            // Initially closed.
            this.wait(function() {
                Assert.isTrue(filter_wrapper.hasClass('lazr-closed'));
            }, 500);
            // Opens when selected.
            added_changed.set('checked', true);
            this.wait(function() {
                Assert.isTrue(filter_wrapper.hasClass('lazr-opened'));
            }, 500);
            // Closes when deselected.
            added_changed.set('checked', false);
            this.wait(function() {
                Assert.isTrue(filter_wrapper.hasClass('lazr-closed'));
            }, 500);
        },

        test_advanced_filter_toggles: function() {
            // Test that the accordion wrapper opens and closes in
            // response to the advanced filter check box.
            module.setup(this.configuration);
            var added_changed = Y.one('#added-or-changed');
            added_changed.set('checked', true);

            // Initially closed.
            var advanced_filter = Y.one('#advanced-filter');
            Assert.isFalse(advanced_filter.get('checked'));
            var accordion_wrapper = Y.one('#accordion-wrapper');
            this.wait(function() {
                Assert.isTrue(accordion_wrapper.hasClass('lazr-closed'));
            }, 500);
            // Opens when selected.
            advanced_filter.set('checked') = true;
            this.wait(function() {
                Assert.isTrue(accordion_wrapper.hasClass('lazr-opened'));
            }, 500);
            // Closes when deselected.
            advanced_filter.set('checked') = false;
            this.wait(function() {
                Assert.isTrue(accordion_wrapper.hasClass('lazr-closed'));
            }, 500);
        },

        test_importances_select_all_none: function() {
            module.setup(this.configuration);
            var checkboxes = Y.all('input[name="importances"]');
            var select_all = Y.one('#importances-select-all');
            var select_none = Y.one('#importances-select-none');
            Assert.isTrue(test_checked(checkboxes, true));
            // Simulate a click on the select_none control.
            Y.Event.simulate(Y.Node.getDOMNode(select_none), 'click');
            Assert.isTrue(test_checked(checkboxes, false));
            // Simulate a click on the select_all control.
            Y.Event.simulate(Y.Node.getDOMNode(select_all), 'click');
            Assert.isTrue(test_checked(checkboxes, true));
        },

        test_statuses_select_all_none: function() {
            module.setup(this.configuration);
            var checkboxes = Y.all('input[name="statuses"]');
            var select_all = Y.one('#statuses-select-all');
            var select_none = Y.one('#statuses-select-none');
            Assert.isTrue(test_checked(checkboxes, true));
            // Simulate a click on the select_none control.
            Y.Event.simulate(Y.Node.getDOMNode(select_none), 'click');
            Assert.isTrue(test_checked(checkboxes, false));
            // Simulate a click on the select_all control.
            Y.Event.simulate(Y.Node.getDOMNode(select_all), 'click');
            Assert.isTrue(test_checked(checkboxes, true));
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

    // The following two lines may be commented out for debugging but
    // must be restored before being checked in or the tests will fail
    // in the test runner.
    var console = new Y.Console({newestOnTop: false});
    console.render('#log');

    Y.on('domready', function() {
        Y.Test.Runner.run();
    });
});
