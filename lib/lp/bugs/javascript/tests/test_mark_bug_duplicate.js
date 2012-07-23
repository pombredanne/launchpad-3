/* Copyright (c) 2012 Canonical Ltd. All rights reserved. */

YUI.add('lp.bugs.mark_bug_duplicate.test', function (Y) {

    var tests = Y.namespace('lp.bugs.mark_bug_duplicate.test');
    tests.suite = new Y.Test.Suite('lp.bugs.mark_bug_duplicate Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.bugs.mark_bug_duplicate_tests',

        setUp: function () {
            this.mockio = new Y.lp.testing.mockio.MockIo();
            var lp_client = new Y.lp.client.Launchpad({
                io_provider: this.mockio
            });
            var bug_repr = {
                self_link: 'api/devel/bugs/1'
            };
            this.lp_bug_entry = new Y.lp.client.Entry(
                lp_client, bug_repr, bug_repr.self_link);
        },

        tearDown: function () {
            Y.one('#fixture').empty(true);
            delete this.lp_bug_entry;
            delete this.mockio;
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
            return new Y.lp.bugs.mark_bug_duplicate.MarkBugDuplicate({
                srcNode: '#duplicate-actions',
                lp_bug_entry: this.lp_bug_entry,
                anim_duration: 0
            });
        },

        test_widget_can_be_instantiated: function() {
            this.widget = this._createWidget();
            Y.Assert.isInstanceOf(
                Y.lp.bugs.mark_bug_duplicate.MarkBugDuplicate,
                this.widget,
                "Mark bug duplicate failed to be instantiated");
            var url = this.widget.get('update_dupe_link').get('href');
            Y.Assert.areEqual('http://foo/+duplicate', url);
        }

    }));

}, '0.1', {
    requires: ['test', 'lp.testing.helpers', 'console', 'lp.client',
        'lp.testing.mockio', 'lp.bugs.mark_bug_duplicate']
});
