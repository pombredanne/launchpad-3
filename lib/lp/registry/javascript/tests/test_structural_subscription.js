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
        ArrayAssert = Y.ArrayAssert,
        module = Y.lp.registry.structural_subscription;

    // Expected content box.
    var content_box_name = 'ss-content-box';
    var content_box_id = '#' + content_box_name;

    var target_link_class = '.menu-link-subscribe_to_bug_mail';

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
        name: 'structural_subscription_overlay',

        _should: {
            error: {
                test_setup_config_none: new Error(
                    'Missing config for structural_subscription.'),
                test_setup_config_no_content_box: new Error(
                    'Structural_subscription configuration has undefined '+
                    'properties.')
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
            LP.cache.importances = [];
            LP.cache.statuses = [];

            this.configuration = {
                content_box: content_box_id,
            };
            this.content_node = create_test_node();
            Y.one('body').appendChild(this.content_node);
        },

        tearDown: function() {
            //delete this.configuration;
            remove_test_node();
            delete this.content_node;
            delete this.configuration.lp_client;
            delete this.content_node;
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
            // If there is a logged-in user, setup is successful
            LP.links.me = 'https://launchpad.dev/api/~someone';
            Assert.isUndefined(module.lp_client);
            module.setup(this.configuration);
            Assert.isNotUndefined(module.lp_client);
        },

        test_list_contains: function() {
            // Validate that the list_contains function actually reports
            // whether or not an element is in a list.
            var list = ['a', 'b', 'c'];
            Assert.isTrue(module._list_contains(list, 'b'));
            Assert.isFalse(module._list_contains(list, 'd'));
            Assert.isFalse(module._list_contains([], 'a'));
            Assert.isTrue(module._list_contains(['a', 'a'], 'a'));
            Assert.isFalse(module._list_contains([], ''));
            Assert.isFalse(module._list_contains([], null));
            Assert.isFalse(module._list_contains(['a'], null));
            Assert.isFalse(module._list_contains([]));
        },

        test_make_selector_controls: function() {
            // Verify the creation of select all/none controls.
            var selectors = module.make_selector_controls('sharona');
            Assert.areEqual('sharona-select-all', selectors['all_name']);
            Assert.areEqual('sharona-select-none', selectors['none_name']);
            Assert.areEqual(
                '<div id="sharona-selectors"',
                selectors['html'].slice(0, 27));
        }
    });
    suite.add(test_case);

    test_case = new Y.Test.Case({
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
            LP.links.me = 'https://launchpad.dev/api/~someone';
            LP.cache.administratedTeams = [];
            LP.cache.importances = [];
            LP.cache.statuses = [];

            this.configuration = {
                content_box: content_box_id
            };
            this.content_node = create_test_node();
            Y.one('body').appendChild(this.content_node);

            this.bug_filter = {
                lp_original_uri:
                    '/api/devel/firefox/+subscription/mark/+filter/28'
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
            // When the user selects themselves as the recipient, the current
            // user's URI is used as the recipient value.
            module.setup(this.configuration);
            this.form_data.recipient = ['user'];
            module.save_subscription(this.form_data);
            Assert.areEqual(
                LP.links.me,
                context.config.parameters.subscriber);
        },

        test_team_recipient: function() {
            // When the user selects a team as the recipient, the selected
            // team's URI is used as the recipient value.
            module.setup(this.configuration);
            this.form_data.recipient = ['team'];
            this.form_data.team = ['https://launchpad.dev/api/~super-team'];
            module.save_subscription(this.form_data);
            Assert.areEqual(
                this.form_data.team[0],
                context.config.parameters.subscriber);
        }
    });
    suite.add(test_case);

    test_case = new Y.Test.Case({
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
            LP.cache.importances = [];
            LP.cache.statuses = [];
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
            module.setup(this.configuration);
            // Simulate a click on the link to open the overlay.
            var link = Y.one('.menu-link-subscribe_to_bug_mail');
            Y.Event.simulate(
                Y.Node.getDOMNode(link), 'click');
            var filter_wrapper = Y.one('#filter-wrapper');
            var accordion_wrapper = Y.one('#accordion-wrapper');
            Assert.isTrue(filter_wrapper.hasClass('lazr-closed'));
            Assert.isTrue(accordion_wrapper.hasClass('lazr-closed'));
        },

        test_added_or_changed_toggles: function() {
            // Test that the filter wrapper opens and closes in
            // response to the added_or_changed radio button.
            module.setup(this.configuration);
            // Simulate a click on the link to open the overlay.
            var link = Y.one('.menu-link-subscribe_to_bug_mail');
            Y.Event.simulate(
                Y.Node.getDOMNode(link), 'click');
            var added_changed = Y.one('#added-or-changed');
            Assert.isFalse(added_changed.get('checked'));
            var filter_wrapper = Y.one('#filter-wrapper');
            // Initially closed.
            Assert.isTrue(filter_wrapper.hasClass('lazr-closed'));
            // Opens when selected.
            Y.Event.simulate(Y.Node.getDOMNode(added_changed), 'click');
            this.wait(function() {
                Assert.isTrue(filter_wrapper.hasClass('lazr-opened'));
            }, 500);
            // Closes when deselected.
            Y.Event.simulate(
                Y.Node.getDOMNode(Y.one('#added-or-closed')), 'click');
            this.wait(function() {
                Assert.isTrue(filter_wrapper.hasClass('lazr-closed'));
            }, 500);
        },

        test_advanced_filter_toggles: function() {
            // Test that the accordion wrapper opens and closes in
            // response to the advanced filter check box.
            module.setup(this.configuration);
            // Simulate a click on the link to open the overlay.
            var link = Y.one('.menu-link-subscribe_to_bug_mail');
            Y.Event.simulate(
                Y.Node.getDOMNode(link), 'click');
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
            // Test the select all/none functionality for the importances
            // accordion pane.
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
            // Test the select all/none functionality for the statuses
            // accordion pane.
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

    test_case = new Y.Test.Case({
        // Test the setup method.
        name: 'Structural Subscription error handling',

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

        test_overlay_error_handling_adding: function() {
            // Verify that errors generated during adding of a filter are
            // displayed to the user.
            this.configuration.lp_client.named_post =
                function(url, func, config) {
                config.on.failure(true, true);
                };
            module.setup(this.configuration);
            // After the setup the overlay should be in the DOM.
            overlay = Y.one('#accordion-overlay');
            Assert.isNotNull(overlay);
            submit_button = Y.one('.yui3-lazr-formoverlay-actions button');
            Y.Event.simulate(Y.Node.getDOMNode(submit_button), 'click');

            var error_box = Y.one('.yui3-lazr-formoverlay-errors');
            Assert.areEqual(
                'The following errors were encountered: ',
                error_box.get('text'));
        },

        test_overlay_error_handling_patching: function() {
            // Verify that errors generated during patching of a filter are
            // displayed to the user.
            var original_delete_filter = module._delete_filter;
            module._delete_filter = function() {};
            this.configuration.lp_client.patch =
                function(bug_filter, data, config) {
                    config.on.failure(true, true);
                };
            var bug_filter = {
                'getAttrs': function() { return {}; }
            };
            this.configuration.lp_client.named_post =
                function(url, func, config) {
                    config.on.success(bug_filter);
                };
            module.setup(this.configuration);
            // After the setup the overlay should be in the DOM.
            overlay = Y.one('#accordion-overlay');
            Assert.isNotNull(overlay);
            submit_button = Y.one('.yui3-lazr-formoverlay-actions button');
            Y.Event.simulate(Y.Node.getDOMNode(submit_button), 'click');

            // Put this stubbed function back.
            module._delete_filter = original_delete_filter;

            var error_box = Y.one('.yui3-lazr-formoverlay-errors');
            Assert.areEqual(
                'The following errors were encountered: ',
                error_box.get('text'));
        }

    });
    suite.add(test_case);

    suite.add(new Y.Test.Case({
        name: 'Structural Subscription: deleting failed filters',

        _should: {error: {}},

        setUp: function() {
            // Monkeypatch LP to avoid network traffic and to allow
            // insertion of test data.
            this.original_lp = window.LP;
            window.LP = {
                links: {},
                cache: {}
            };
            LP.cache.context = {
                self_link: 'https://launchpad.dev/api/test_project'
            };
            LP.links.me = 'https://launchpad.dev/api/~someone';
            LP.cache.administratedTeams = [];
        },

        tearDown: function() {
            window.LP = this.original_lp;
        },

        test_delete_on_patch_failure: function() {
            // Creating a filter is a two step process.  First it is created
            // and then patched.  If the PATCH fails, then we should DELETE
            // the undifferentiated filter.

            // First we inject our own delete_filter implementation that just
            // tells us that it was called.
            var original_delete_filter = module._delete_filter;
            var delete_called = false;
            module._delete_filter = function() {
                delete_called = true;
            };
            var patch_failed = false;

            var TestBugFilter = function() {};
            TestBugFilter.prototype = {
                'getAttrs': function () {
                    return {};
                },
            };

            // Now we need an lp_client that will appear to succesfully create
            // the filter but then fail to patch it.
            var TestClient = function() {};
            TestClient.prototype = {
                'named_post': function (uri, operation_name, config) {
                    if (operation_name === 'addBugSubscriptionFilter') {
                        config.on.success(new TestBugFilter());
                    } else {
                        throw new Error('unexpected operation');
                    }
                },
                'patch': function(uri, representation, config, headers) {
                    config.on.failure(true, {'status':400});
                    patch_failed = true;
                },
            };
            module.lp_client = new TestClient();

            // OK, we're ready to add the bug filter and let the various
            // handlers be called.
            module._add_bug_filter(LP.links.me, 'this is a test');
            // Put some functions back.
            module._delete_filter = original_delete_filter;

            // Delete should have been called and the patch has failed.
            Assert.isTrue(delete_called);
            Assert.isTrue(patch_failed);
        },

    }));

    suite.add(new Y.Test.Case({
        name: 'Structural Subscription validate_config',

        _should: {
            error: {
                test_setup_config_none: new Error(
                    'Missing config for structural_subscription.'),
                test_setup_config_no_content_box: new Error(
                    'Structural_subscription configuration has undefined '+
                    'properties.')
                }
        },

        // Included in _should/error above.
        test_setup_config_none: function() {
            // The config passed to setup may not be null.
            module._validate_config();
        },

        // Included in _should/error above.
        test_setup_config_no_content_box: function() {
            // The config passed to setup must contain a content_box.
            module._validate_config({});
        }
    }));

    suite.add(new Y.Test.Case({
        name: 'Structural Subscription extract_form_data',

        // Verify that all the different values of the structural subscription
        // add/edit form are correctly extracted by the extract_form_data
        // function.

        _should: {
            error: {
                }
            },

        test_extract_description: function() {
            var form_data = {
                name: ['filter description'],
                events: [],
                filters: [],
            };
            var patch_data = module._extract_form_data(form_data);
            Assert.areEqual(patch_data.description, form_data.name[0]);
        },

        test_extract_description_trim: function() {
            // Any leading or trailing whitespace is stripped from the
            // description.
            var form_data = {
                name: ['  filter description  '],
                events: [],
                filters: [],
            };
            var patch_data = module._extract_form_data(form_data);
            Assert.areEqual('filter description', patch_data.description);
        },

        test_extract_chattiness_lifecycle: function() {
            var form_data = {
                name: [],
                events: ['added-or-closed'],
                filters: [],
            };
            var patch_data = module._extract_form_data(form_data);
            Assert.areEqual(
                patch_data.bug_notification_level, 'Lifecycle');
        },

        test_extract_chattiness_discussion: function() {
            var form_data = {
                name: [],
                events: [],
                filters: ['filter-comments'],
            };
            var patch_data = module._extract_form_data(form_data);
            Assert.areEqual(
                patch_data.bug_notification_level, 'Details');
        },

        test_extract_chattiness_details: function() {
            var form_data = {
                name: [],
                events: [],
                filters: [],
            };
            var patch_data = module._extract_form_data(form_data);
            Assert.areEqual(
                patch_data.bug_notification_level, 'Discussion');
        },

        test_extract_tags: function() {
            var form_data = {
                name: [],
                events: [],
                filters: ['advanced-filter'],
                tags: ['one two THREE'],
                tag_match: [''],
                importances: [],
                statuses: [],
            };
            var patch_data = module._extract_form_data(form_data);
            // Note that the tags are converted to lower case.
            ArrayAssert.itemsAreEqual(
                patch_data.tags, ['one', 'two', 'three']);
        },

        test_extract_find_all_tags_true: function() {
            var form_data = {
                name: [],
                events: [],
                filters: ['advanced-filter'],
                tags: ['tag'],
                tag_match: ['match-all'],
                importances: [],
                statuses: [],
            };
            var patch_data = module._extract_form_data(form_data);
            Assert.isTrue(patch_data.find_all_tags);
        },

        test_extract_find_all_tags_false: function() {
            var form_data = {
                name: [],
                events: [],
                filters: ['advanced-filter'],
                tags: ['tag'],
                tag_match: [],
                importances: [],
                statuses: [],
            };
            var patch_data = module._extract_form_data(form_data);
            Assert.isFalse(patch_data.find_all_tags);
        },

        test_all_values_set: function() {
            // We need all the values to be set (even if empty) because
            // PATCH expects a set of changes to make and any unspecified
            // attributes will retain the previous value.
            var form_data = {
                name: [],
                events: [],
                filters: [],
                tags: ['tag'],
                tag_match: ['match-all'],
                importances: ['importance1'],
                statuses: ['status1'],
            };
            var patch_data = module._extract_form_data(form_data);
            // Since advanced-filter isn't set, all the advanced values should
            // be empty/false despite the form values.
            Assert.isFalse(patch_data.find_all_tags);
            ArrayAssert.isEmpty(patch_data.tags)
            ArrayAssert.isEmpty(patch_data.importances)
            ArrayAssert.isEmpty(patch_data.statuses)
        },

    }));

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
