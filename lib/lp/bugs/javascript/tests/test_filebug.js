/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI.add('lp.bugs.filebug.test', function (Y) {

    var tests = Y.namespace('lp.bugs.filebug.test');
    tests.suite = new Y.Test.Suite(
        'lp.bugs.filebug Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.bugs.filebug_tests',

        setUp: function () {
            window.LP = {
                links: {},
                cache: {
                    private_types: ['EMBARGOEDSECURITY', 'USERDATA'],
                    bugtask_status_data: [
                        {name: 'New', value: 'New'},
                        {name: 'Incomplete', value: 'Incomplete'}
                    ],
                    bugtask_importance_data: [
                        {name: 'Undecided', value: 'Undecided'},
                        {name: 'High', value: 'High'}
                    ]
                }
            };
            this.fixture = Y.one('#fixture');
            var banner = Y.Node.create(
                    Y.one('#privacy-banner-template').getContent());
            this.fixture.appendChild(banner);
        },

        tearDown: function () {
            if (this.fixture !== null) {
                this.fixture.empty(true);
            }
            delete this.fixture;
            delete window.LP;
        },

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.bugs.filebug,
                "Could not locate the " +
                "lp.bugs.filebug module");
        },

        // Filing a public bug does not show the privacy banner.
        test_setup_filebug_public: function () {
            Y.lp.bugs.filebug.setup_filebug(true);
            var banner_hidden = Y.one('.yui3-privacybanner-hidden');
            Y.Assert.isNotNull(banner_hidden);
        },

        // Filing a bug for a project with private bugs shows the privacy
        // banner.
        test_setup_filebug_private: function () {
            window.LP.cache.bug_private_by_default = true;
            Y.lp.bugs.filebug.setup_filebug(true);
            var banner_hidden = Y.one('.yui3-privacybanner-hidden');
            Y.Assert.isNull(banner_hidden);
            var banner_text = Y.one('.banner-text').get('text');
            Y.Assert.areEqual(
                'This report will be private. ' +
                'You can disclose it later.', banner_text);
        },

        // Selecting a private info type turns on the privacy banner.
        test_select_private_info_type: function () {
            window.LP.cache.show_information_type_in_ui = true;
            Y.lp.bugs.filebug.setup_filebug(true);
            var banner_hidden = Y.one('.yui3-privacybanner-hidden');
            Y.Assert.isNotNull(banner_hidden);
            Y.one('[id=field.information_type.2]').simulate('click');
            banner_hidden = Y.one('.yui3-privacybanner-hidden');
            Y.Assert.isNull(banner_hidden);
            var banner_text = Y.one('.banner-text').get('text');
            Y.Assert.areEqual(
                'This report will be private. ' +
                'You can disclose it later.', banner_text);
        },

        // Selecting a public info type turns off the privacy banner.
        test_select_public_info_type: function () {
            window.LP.cache.show_information_type_in_ui = true;
            window.LP.cache.bug_private_by_default = true;
            Y.lp.bugs.filebug.setup_filebug(true);
            var banner_hidden = Y.one('.yui3-privacybanner-hidden');
            Y.Assert.isNull(banner_hidden);
            Y.one('[id=field.information_type.0]').simulate('click');
            banner_hidden = Y.one('.yui3-privacybanner-hidden');
            Y.Assert.isNotNull(banner_hidden);
        },

        // The dupe finder functionality is setup.
        test_dupe_finder_setup: function () {
            window.LP.cache.enable_bugfiling_duplicate_search = true;
            var orig_setup_dupe_finder =
                Y.lp.bugs.filebug_dupefinder.setup_dupe_finder;
            var orig_setup_dupes =
                Y.lp.bugs.filebug_dupefinder.setup_dupes;
            var setup_dupe_finder_called = false;
            var setup_dupes_called = false;
            Y.lp.bugs.filebug_dupefinder.setup_dupe_finder = function() {
                setup_dupe_finder_called = true;
            };
            Y.lp.bugs.filebug_dupefinder.setup_dupes = function() {
                setup_dupes_called = true;
            };
            Y.lp.bugs.filebug.setup_filebug(true);
            Y.Assert.isTrue(setup_dupe_finder_called);
            Y.Assert.isTrue(setup_dupes_called);
            Y.lp.bugs.filebug_dupefinder.setup_dupes = orig_setup_dupes;
            Y.lp.bugs.filebug_dupefinder.setup_dupe_finder
                = orig_setup_dupe_finder;
        },

        // The bugtask status choice popup is rendered.
        test_status_setup: function () {
            Y.lp.bugs.filebug.setup_filebug(true);
            var status_node = Y.one('#status-content .value');
            Y.Assert.areEqual('New', status_node.get('text'));
            var status_edit_node = Y.one('#status-content a.sprite.edit');
            Y.Assert.isNotNull(status_edit_node);
            var legacy_dropdown = Y.one('[id=field.status]');
            Y.Assert.isTrue(legacy_dropdown.hasClass('unseen'));
        },

        // The bugtask importance choice popup is rendered.
        test_importance_setup: function () {
            Y.lp.bugs.filebug.setup_filebug(true);
            var importance_node = Y.one('#importance-content .value');
            Y.Assert.areEqual('Undecided', importance_node.get('text'));
            var importance_edit_node =
                Y.one('#importance-content a.sprite.edit');
            Y.Assert.isNotNull(importance_edit_node);
            var legacy_dropdown = Y.one('[id=field.importance]');
            Y.Assert.isTrue(legacy_dropdown.hasClass('unseen'));
        },

        // The bugtask status choice popup updates the form.
        test_status_selection: function() {
            Y.lp.bugs.filebug.setup_filebug(true);
            var status_popup = Y.one('#status-content a');
            status_popup.simulate('click');
            var status_choice = Y.one(
                '.yui3-ichoicelist-content a[href=#Incomplete]');
            status_choice.simulate('click');
            var legacy_dropdown = Y.one('[id=field.status]');
            Y.Assert.areEqual('Incomplete', legacy_dropdown.get('value'));
        },

        // The bugtask importance choice popup updates the form.
        test_importance_selection: function() {
            Y.lp.bugs.filebug.setup_filebug(true);
            var status_popup = Y.one('#importance-content a');
            status_popup.simulate('click');
            var status_choice = Y.one(
                '.yui3-ichoicelist-content a[href=#High]');
            status_choice.simulate('click');
            var legacy_dropdown = Y.one('[id=field.importance]');
            Y.Assert.areEqual('High', legacy_dropdown.get('value'));
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'event', 'node-event-simulate',
        'lp.app.banner.privacy', 'lp.app.choice',
        'lp.bugs.filebug_dupefinder', 'lp.bugs.filebug'
        ]});
