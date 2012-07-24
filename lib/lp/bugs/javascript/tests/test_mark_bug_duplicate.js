/* Copyright (c) 2012 Canonical Ltd. All rights reserved. */

YUI.add('lp.bugs.mark_bug_duplicate.test', function (Y) {

    var tests = Y.namespace('lp.bugs.mark_bug_duplicate.test');
    tests.suite = new Y.Test.Suite('lp.bugs.mark_bug_duplicate Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.bugs.mark_bug_duplicate_tests',

        setUp: function () {
            window.LP = {
                links: {},
                cache: {
                    bug: {
                        self_link: 'api/devel/bugs/1',
                        duplicate_of_link: null
                    }
                }
            };
            this.mockio = new Y.lp.testing.mockio.MockIo();
            this.lp_client = new Y.lp.client.Launchpad({
                io_provider: this.mockio
            });
            var bug_repr = window.LP.cache.bug;
            this.lp_bug_entry = new Y.lp.client.Entry(
                this.lp_client, bug_repr, bug_repr.self_link);
        },

        tearDown: function () {
            Y.one('#fixture').empty(true);
            delete this.lp_bug_entry;
            delete this.mockio;
            delete window.LP;
        },

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.bugs.mark_bug_duplicate,
                "Could not locate the lp.bugs.mark_bug_duplicate module");
        },

        _createWidget: function(existing_duplicate) {
            var fixture_id;
            if (existing_duplicate) {
                fixture_id = "existing-duplicate";
            } else {
                fixture_id = "no-existing-duplicate";
            }
            Y.one('#fixture').appendChild(
                Y.Node.create(Y.one('#' + fixture_id).getContent()));
            var widget = new Y.lp.bugs.mark_bug_duplicate.MarkBugDuplicate({
                srcNode: '#duplicate-actions',
                lp_bug_entry: this.lp_bug_entry,
                anim_duration: 0,
                io_provider: this.mockio
            });
            Y.Assert.areEqual(
                'http://foo/+duplicate/++form++',
                this.mockio.last_request.url);
            this.mockio.success({
                responseText: this._fake_duplicate_form(),
                responseHeaders: {'Content-Type': 'text/html'}});
            return widget;
        },

        _fake_duplicate_form: function() {
            return [
                '<div>',
                '<input type="text" value="" name="field.duplicateof"',
                'id="field.duplicateof" class="textType">',
                '</div>'
            ].join('');
        },

        // The widget is created when there are no bug duplicates.
        test_widget_creation_no_duplicate_exists: function() {
            this.widget = this._createWidget(false);
            Y.Assert.isInstanceOf(
                Y.lp.bugs.mark_bug_duplicate.MarkBugDuplicate,
                this.widget,
                "Mark bug duplicate failed to be instantiated");
            var url = this.widget.get('update_dupe_link').get('href');
            Y.Assert.areEqual('http://foo/+duplicate', url);
            Y.Assert.isNotNull(
                Y.one('#mark-duplicate-text a.menu-link-mark-dupe'));
        },

        // The widget is created when there are bug duplicates.
        test_widget_creation_duplicate_exists: function() {
            this.widget = this._createWidget(true);
            Y.Assert.isInstanceOf(
                Y.lp.bugs.mark_bug_duplicate.MarkBugDuplicate,
                this.widget,
                "Mark bug duplicate failed to be instantiated");
            var url = this.widget.get('update_dupe_link').get('href');
            Y.Assert.areEqual('http://foo/+duplicate', url);
        },

        // The duplicate entry form renders and submits the expected data.
        _assert_duplicate_form_submission: function(bug_id) {
            var form = Y.one('#duplicate-form-container');
            Y.Assert.isTrue(
                form.one('div.pretty-overlay-window')
                    .hasClass('yui3-lazr-formoverlay-hidden'));
            this.widget.get('update_dupe_link').simulate('click');
            Y.Assert.isFalse(
                Y.one('#duplicate-form-container div.pretty-overlay-window')
                    .hasClass('yui3-lazr-formoverlay-hidden'));
            Y.DOM.byId('field.duplicateof').value = bug_id;
            form.one('.lazr-pos').simulate('click');
            Y.Assert.areEqual(
                '/api/devel/bugs/1',
                this.mockio.last_request.url);
            var expected_link = '{}';
            if (bug_id !== '') {
                expected_link =
                    '{"duplicate_of_link":"api/devel/bugs/' + bug_id + '"}';
            }
            Y.Assert.areEqual(
                expected_link, this.mockio.last_request.config.data);
        },

        // Submitting a bug dupe works as expected.
        test_duplicate_form_submission_success: function() {
            this.widget = this._createWidget(false);
            var success_called = false;
            this.widget.update_bug_duplicate_success =
                function(updated_entry, new_dup_url, new_dup_id) {
                    Y.Assert.areEqual(
                        expected_updated_entry.duplicate_of_link,
                        updated_entry.duplicate_of_link);
                    Y.Assert.areEqual('api/devel/bugs/3', new_dup_url);
                    Y.Assert.areEqual(3, new_dup_id);
                    success_called = true;
                };
            this._assert_duplicate_form_submission(3);
            var expected_updated_entry = {
                lp_original_uri: 'api/devel/bugs/1',
                duplicate_of_link: 'api/devel/bugs/3',
                self_link: 'api/devel/bugs/1'};
            this.mockio.last_request.successJSON(expected_updated_entry);
            Y.Assert.isTrue(success_called);
        },

        // A submission failure is handled as expected.
        test_duplicate_form_submission_failure: function() {
            this.widget = this._createWidget(false);
            var failure_called = false;
            this.widget.update_bug_duplicate_failure =
                function(response, old_dup_url, new_dup_id) {
                    Y.Assert.areEqual(
                        'There was an error', response.responseText);
                    Y.Assert.areEqual(null, old_dup_url);
                    Y.Assert.areEqual(3, new_dup_id);
                    failure_called = true;
                };
            this._assert_duplicate_form_submission(3);
            this.mockio.respond({
                status: 400,
                responseText: 'There was an error',
                responseHeaders: {'Content-Type': 'text/html'}});
            Y.Assert.isTrue(failure_called);
        },

        // Submitting a dupe removal request works as expected.
        test_duplicate_form_submission_remove_dupe: function() {
            this.widget = this._createWidget(true);
            var success_called = false;
            this.widget.update_bug_duplicate_success =
                function(updated_entry, new_dup_url, new_dup_id) {
                    Y.Assert.areEqual(expected_updated_entry, updated_entry);
                    Y.Assert.areEqual(null, new_dup_url);
                    Y.Assert.areEqual('', new_dup_id);
                    success_called = true;
                };
            this._assert_duplicate_form_submission('');
            var expected_updated_entry =
                '{"duplicate_of_link":""}';
            this.mockio.success({
                responseText: expected_updated_entry,
                responseHeaders: {'Content-Type': 'text/html'}});
            Y.Assert.isTrue(success_called);
        },

        // The mark bug duplicate success function works as expected.
        test_update_bug_duplicate_success: function() {
            this.widget = this._createWidget(false);
            var data = {
                self_link: 'api/devel/bugs/1'};
            var new_bug_entry = new Y.lp.client.Entry(
                this.lp_client, data, data.self_link);
            this.widget.update_bug_duplicate_success(
                new_bug_entry, 'api/devel/bugs/3', 3);
            // Test the updated bug entry.
            Y.Assert.areEqual(
                'api/devel/bugs/3',
                this.widget.get('lp_bug_entry').get('duplicate_of_link'));
            // Test the Change Duplicate link.
            Y.Assert.isNotNull(
                Y.one('#mark-duplicate-text #change_duplicate_bug'));
            // Test the duplicate warning message.
            Y.Assert.isNotNull(Y.one('#warning-comment-on-duplicate'));
            // Any previously listed duplicates are removed.
            Y.Assert.isNull(Y.one('#portlet-duplicates'));
        },

        // The remove bug duplicate success function works as expected.
        test_remove_bug_duplicate_success: function() {
            this.widget = this._createWidget(true);
            var data = {
                self_link: 'api/devel/bugs/1'};
            var new_bug_entry = new Y.lp.client.Entry(
                this.lp_client, data, data.self_link);
            this.widget.update_bug_duplicate_success(new_bug_entry, null, '');
            // Test the updated bug entry.
            Y.Assert.isNull(
                this.widget.get('lp_bug_entry').get('duplicate_of_link'));
            // Test the Mark as Duplicate link.
            Y.Assert.isNotNull(
                Y.one('#mark-duplicate-text .menu-link-mark-dupe'));
            // Test the duplicate warning message is gone.
            Y.Assert.isNull(Y.one('#warning-comment-on-duplicate'));
        },

        // The remove bug duplicate error function works as expected for
        // generic errors.
        test_update_bug_duplicate_generic_failure: function() {
            this.widget = this._createWidget(false);
            var data = {
                self_link: 'api/devel/bugs/1'};
            var new_bug_entry = new Y.lp.client.Entry(
                this.lp_client, data, data.self_link);
            var response = {
                status: 500,
                responseText: 'An error occurred'
            };
            this.widget.update_bug_duplicate_failure(response, null, 3);
            Y.Assert.isFalse(
                Y.one('#duplicate-form-container div.pretty-overlay-window')
                    .hasClass('yui3-lazr-formoverlay-hidden'));
            var error_msg = Y.one('.yui3-lazr-formoverlay-errors ul li');
            Y.Assert.areEqual('An error occurred', error_msg.get('text'));
        },

        // The remove bug duplicate error function works as expected for
        // invalid bug errors.
        test_update_bug_duplicate_invalid_bug_failure: function() {
            this.widget = this._createWidget(false);
            var data = {
                self_link: 'api/devel/bugs/1'};
            var new_bug_entry = new Y.lp.client.Entry(
                this.lp_client, data, data.self_link);
            var response = {
                status: 400,
                responseText: 'An error occurred'
            };
            this.widget.update_bug_duplicate_failure(response, null, 3);
            Y.Assert.isFalse(
                Y.one('#duplicate-form-container div.pretty-overlay-window')
                    .hasClass('yui3-lazr-formoverlay-hidden'));
            var error_msg = Y.one('.yui3-lazr-formoverlay-errors ul li');
            Y.Assert.areEqual(
                '3 is not a valid bug number or nickname.',
                error_msg.get('text'));
        }
    }));

}, '0.1', {
    requires: [
        'test', 'lp.testing.helpers', 'event', 'node-event-simulate',
        'console', 'lp.client', 'lp.testing.mockio', 'lp.anim',
        'lp.bugs.mark_bug_duplicate']
});
