/* Copyright (c) 2012 Canonical Ltd. All rights reserved. */

YUI.add('lp.bugs.duplicates.test', function (Y) {

    var tests = Y.namespace('lp.bugs.duplicates.test');
    tests.suite = new Y.Test.Suite('lp.bugs.duplicates Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.bugs.duplicates_tests',

        setUp: function () {
            window.LP = {
                links: {},
                cache: {
                    bug: {
                        id: 1,
                        self_link: 'api/devel/bugs/1',
                        duplicate_of_link: ''
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
            Y.Assert.isObject(Y.lp.bugs.duplicates,
                "Could not locate the lp.bugs.duplicates module");
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
            var widget = new Y.lp.bugs.duplicates.MarkBugDuplicate({
                srcNode: '#duplicate-actions',
                lp_bug_entry: this.lp_bug_entry,
                use_animation: false,
                io_provider: this.mockio
            });
            widget.render();
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
                Y.lp.bugs.duplicates.MarkBugDuplicate,
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
                Y.lp.bugs.duplicates.MarkBugDuplicate,
                this.widget,
                "Mark bug duplicate failed to be instantiated");
            var url = this.widget.get('update_dupe_link').get('href');
            Y.Assert.areEqual('http://foo/+duplicate', url);
        },

        // The search form renders and submits the expected data.
        _assert_search_form_submission: function(bug_id) {
            var form = Y.one('#duplicate-form-container');
            Y.Assert.isTrue(
                form.one('div.pretty-overlay-window')
                    .hasClass('yui3-lazr-formoverlay-hidden'));
            this.widget.get('update_dupe_link').simulate('click');
            Y.Assert.isFalse(
                Y.one('#duplicate-form-container div.pretty-overlay-window')
                    .hasClass('yui3-lazr-formoverlay-hidden'));
            Y.DOM.byId('field.duplicateof').value = bug_id;
            form.one('[name="field.actions.change"]').simulate('click');
            if (bug_id !== '') {
                Y.Assert.areEqual(
                    'file:///api/devel/bugs',
                    this.mockio.last_request.url);
                Y.Assert.areEqual(
                    this.mockio.last_request.config.data,
                    'ws.accept=application.json&ws.op=getBugData&' +
                    'bug_id=' + bug_id);
            } else {
                Y.Assert.areEqual(
                    '/api/devel/bugs/1', this.mockio.last_request.url);
            }
        },

        // The bug entry form is visible and the confirmation form is invisible
        // or visa versa.
        _assert_form_state: function(confirm_form_visible) {
            Y.Assert.areEqual(
                confirm_form_visible,
                Y.one('#duplicate-form-container form')
                    .hasClass('hidden'));
            var bug_info = Y.one('#duplicate-form-container ' +
                    '.confirmation-node #client-listing');
            if (confirm_form_visible) {
                Y.Assert.isNotNull(bug_info);
            } else {
                Y.Assert.isNull(bug_info);
            }
        },

        // Invoke a successful search operation and check the form state.
        _assert_search_form_success: function(bug_id) {
            var expected_updated_entry = [{
                id: bug_id,
                uri: 'api/devel/bugs/' + bug_id,
                duplicate_of_link: 'api/devel/bugs/' + bug_id,
                self_link: 'api/devel/bugs/' + bug_id}];
            this.mockio.last_request.successJSON(expected_updated_entry);
            this._assert_form_state(true);
        },

        // Attempt to make a bug as a duplicate of itself is detected and an
        // error is displayed immediately.
        test_mark_bug_as_dupe_of_self: function() {
            this.widget = this._createWidget(false);
            this.widget.get('update_dupe_link').simulate('click');
            this.mockio.last_request = null;
            Y.DOM.byId('field.duplicateof').value = 1;
            var form = Y.one('#duplicate-form-container');
            form.one('[name="field.actions.change"]').simulate('click');
            Y.Assert.isNull(this.mockio.last_request);
            this._assert_error_display(
                'A bug cannot be marked as a duplicate of itself.');
            this._assert_form_state(false);
        },

        // Attempt to make a bug as a duplicate of it's existing dupe is
        // detected and an error is displayed immediately.
        test_mark_bug_as_dupe_of_existing_dupe: function() {
            this.widget = this._createWidget(false);
            this.widget.get('update_dupe_link').simulate('click');
            this.mockio.last_request = null;
            window.LP.cache.bug.duplicate_of_link
                = 'file:///api/devel/bugs/4';
            Y.DOM.byId('field.duplicateof').value = 4;
            var form = Y.one('#duplicate-form-container');
            form.one('[name="field.actions.change"]').simulate('click');
            Y.Assert.isNull(this.mockio.last_request);
            this._assert_error_display(
                'This bug is already marked as a duplicate of bug 4.');
            this._assert_form_state(false);
        },

        // A successful search for a bug displays the confirmation form.
        test_initial_bug_search_success: function() {
            this.widget = this._createWidget(false);
            this._assert_search_form_submission(3);
            this._assert_search_form_success(3);
        },

        // After a successful search, hitting the Search Again button takes us
        // back to the bug details entry form.
        test_initial_bug_search_try_again: function() {
            this.widget = this._createWidget(false);
            this._assert_search_form_submission(3);
            this._assert_search_form_success(3);
            Y.one('#duplicate-form-container .no_button')
                .simulate('click');
            this._assert_form_state(false);
        },

        // After a successful search, hitting the Select bug button initiates
        // the mark as duplicate operation.
        test_bug_search_select_bug: function() {
            this.widget = this._createWidget(false);
            this._assert_search_form_submission(3);
            this._assert_search_form_success(3);
            var update_bug_duplicate_called = false;
            this.widget._update_bug_duplicate = function(bug_id) {
                update_bug_duplicate_called = true;
                Y.Assert.areEqual(3, bug_id);
            };
            Y.one('#duplicate-form-container .yes_button')
                .simulate('click');
            this._assert_form_state(true);
            Y.Assert.isTrue(update_bug_duplicate_called);
        },

        // The specified error message is displayed.
        _assert_error_display: function(message) {
            var selector
                = '#duplicate-form-container div.pretty-overlay-window';
            Y.Assert.isFalse(
                Y.one(selector).hasClass('yui3-lazr-formoverlay-hidden'));
            var error_msg = Y.one('.yui3-lazr-formoverlay-errors p');
            Y.Assert.areEqual(message, error_msg.get('text'));
        },

        // The error is displayed as expected when the initial bug search
        // fails with a generic error.
        test_initial_bug_search_generic_failure: function() {
            this.widget = this._createWidget(false);
            this._assert_search_form_submission(3);
            var response = {
                status: 500,
                responseText: 'An error occurred'
            };
            this.mockio.respond(response);
            this._assert_error_display('An error occurred');
        },

        // The error is displayed as expected when the initial bug search
        // fails with a 404 (invalid/not found bug id).
        test_initial_bug_search_invalid_bug_failure: function() {
            this.widget = this._createWidget(false);
            this._assert_search_form_submission(3);
            var response = {
                status: 404,
                responseText: 'An error occurred'
            };
            this.mockio.respond(response);
            this._assert_error_display('3 is not a valid bug number.');
        },

        // The duplicate entry form renders and submits the expected data.
        _assert_confirmation_form_submission: function(bug_id) {
            this._assert_search_form_submission(bug_id);
            this._assert_search_form_success(bug_id);
            Y.one('#duplicate-form-container .yes_button')
                .simulate('click');
            this._assert_form_state(true);
            Y.Assert.areEqual(
                '/api/devel/bugs/1', this.mockio.last_request.url);
            var expected_link =
                    '{"duplicate_of_link":"api/devel/bugs/' + bug_id + '"}';
            Y.Assert.areEqual(
                expected_link, this.mockio.last_request.config.data);
        },

        // Submitting a bug dupe works as expected.
        test_duplicate_form_submission_success: function() {
            this.widget = this._createWidget(false);
            this._assert_confirmation_form_submission(3);
            var success_called = false;
            this.widget._update_bug_duplicate_success =
                function(updated_entry, new_dup_url, new_dup_id) {
                    Y.Assert.areEqual(
                        expected_updated_entry.duplicate_of_link,
                        updated_entry.duplicate_of_link);
                    Y.Assert.areEqual('api/devel/bugs/3', new_dup_url);
                    Y.Assert.areEqual(3, new_dup_id);
                    success_called = true;
                };
            var expected_updated_entry = {
                uri: 'api/devel/bugs/1',
                duplicate_of_link: 'api/devel/bugs/3',
                self_link: 'api/devel/bugs/1'};
            this.mockio.last_request.successJSON(expected_updated_entry);
            Y.Assert.isTrue(success_called);
        },

        // A submission failure is handled as expected.
        test_duplicate_form_submission_failure: function() {
            this.widget = this._createWidget(false);
            this._assert_confirmation_form_submission(3);
            var failure_called = false;
            this.widget._update_bug_duplicate_failure =
                function(response, old_dup_url, new_dup_id) {
                    Y.Assert.areEqual(
                        'There was an error', response.responseText);
                    Y.Assert.areEqual('', old_dup_url);
                    Y.Assert.areEqual(3, new_dup_id);
                    failure_called = true;
                };
            this.mockio.respond({
                status: 400,
                responseText: 'There was an error',
                responseHeaders: {'Content-Type': 'text/html'}});
            Y.Assert.isTrue(failure_called);
        },

        // Submitting a dupe removal request works as expected.
        test_duplicate_form_submission_remove_dupe: function() {
            this.widget = this._createWidget(false);
            this._assert_search_form_submission('');
            var success_called = false;
            this.widget._update_bug_duplicate_success =
                function(updated_entry, new_dup_url, new_dup_id) {
                    Y.Assert.areEqual(expected_updated_entry, updated_entry);
                    Y.Assert.areEqual(null, new_dup_url);
                    Y.Assert.areEqual('', new_dup_id);
                    success_called = true;
                };
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
            this.widget._update_bug_duplicate_success(
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
            this.widget._update_bug_duplicate_success(new_bug_entry, null, '');
            // Test the updated bug entry.
            Y.Assert.isNull(
                this.widget.get('lp_bug_entry').get('duplicate_of_link'));
            // Test the Mark as Duplicate link.
            Y.Assert.isNotNull(
                Y.one('#mark-duplicate-text .menu-link-mark-dupe'));
            // Test the duplicate warning message is gone.
            Y.Assert.isNull(Y.one('#warning-comment-on-duplicate'));
        }
    }));

}, '0.1', {
    requires: [
        'test', 'lp.testing.helpers', 'event', 'node-event-simulate',
        'console', 'lp.client', 'lp.testing.mockio', 'lp.anim',
        'lp.bugs.duplicates']
});
