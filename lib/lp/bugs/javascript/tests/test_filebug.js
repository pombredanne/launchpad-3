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
                    private_types: ['EMBARGOEDSECURITY', 'USERDATA']
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
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'event', 'node-event-simulate',
        'lp.app.banner.privacy', 'lp.bugs.filebug_dupefinder',
        'lp.bugs.filebug'
        ]});
