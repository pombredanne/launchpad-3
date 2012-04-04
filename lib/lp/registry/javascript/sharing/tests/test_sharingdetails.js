/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */
YUI.add('lp.registry.sharing.sharingdetails.test', function(Y) {

// Local aliases
    var Assert = Y.Assert;
    var sharing_details = Y.lp.registry.sharing.sharingdetails;

    var tests = Y.namespace('lp.registry.sharing.sharingdetails.test');
    tests.suite = new Y.Test.Suite(
        "lp.registry.sharing.sharingdetails Tests");

    tests.suite.add(new Y.Test.Case({
        name: 'Sharing Details',

        setUp: function () {
            window.LP = {
                links: {},
                cache: {
                    bugs: [
                        {
                            self_link: 'api/devel/bugs/2',
                            web_link:'/bugs/2',
                            bug_id: '2',
                            bug_importance: 'critical',
                            bug_summary:'Everything is broken.'
                        }
                    ],
                    branches: [
                        {
                            self_link: 'api/devel/~someone/+junk/somebranch',
                            web_link:'/~someone/+junk/somebranch',
                            branch_id: '2',
                            branch_name:'lp:~someone/+junk/somebranch'
                        }
                    ]
                }
            };
            this.fixture = Y.one('#fixture');
            var sharing_table = Y.Node.create(
                    Y.one('#sharing-table-template').getContent());
            this.fixture.appendChild(sharing_table);

        },

        tearDown: function () {
            if (this.fixture !== null) {
                this.fixture.empty(true);
            }
            delete this.fixture;
            delete window.LP;
        },

        _create_Widget: function(overrides) {
            if (!Y.Lang.isValue(overrides)) {
                overrides = {};
            }
            var config = Y.merge({
                person_name: 'Fred',
                bugs: window.LP.cache.bugs,
                branches: window.LP.cache.branches,
                write_enabled: true
            }, overrides);
            window.LP.cache.sharee_data = config.sharees;
            return new sharing_details.SharingDetailsTable(config);
        },

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.registry.sharing.sharingdetails,
                "We should be able to locate the " +
                "lp.registry.sharing.sharingdetails module");
        },

        test_widget_can_be_instantiated: function() {
            this.details_widget = this._create_Widget();
            Y.Assert.isInstanceOf(
                Y.lp.registry.sharing.sharingdetails.SharingDetailsTable,
                this.details_widget,
                "Sharing details table failed to be instantiated");
        },

        // Read only mode disables the correct things.
        test_readonly: function() {
            this.details_widget = this._create_Widget({
                write_enabled: false
            });
            this.details_widget.render();
            Y.all('#sharing-table-body .sprite.remove a')
                .each(function(link) {
                    Y.Assert.isTrue(link.hasClass('unseen'));
            });
        },

        // Test that branches are correctly rendered.
        test_render_branches: function () {
            this.details_widget = this._create_Widget();
            this.details_widget.render();
            var expected = "lp:~someone/+junk/somebranch";
            var web_link = Y.one(
                '#sharing-table-body tr#shared-branch-2').one('a');
            var actual_text = web_link.get('text').replace(/\s+/g, '');
            Assert.areEqual(expected, actual_text);
        },

        // Test that bugs are correctly rendered.
        test_render_bugs: function () {
            this.details_widget = this._create_Widget();
            this.details_widget.render();
            var expected = "Everythingisbroken.";
            var web_link = Y.one(
                '#sharing-table-body tr#shared-bug-2').one('a');
            var actual_text = web_link.get('text').replace(/\s+/g, '');
            Assert.areEqual(expected, actual_text);
        },

        // When the bug revoke link is clicked, the correct event is published.
        test_bug_revoke_click: function() {
            this.details_widget = this._create_Widget();
            this.details_widget.render();
            var event_fired = false;
            this.details_widget.subscribe(
                sharing_details.SharingDetailsTable.REMOVE_GRANT,
                function(e) {
                    var delete_link = e.details[0];
                    var artifact_uri = e.details[1];
                    var artifact_name = e.details[2];
                    var artifact_type = e.details[3];
                    Y.Assert.areEqual('api/devel/bugs/2', artifact_uri);
                    Y.Assert.areEqual('Bug 2', artifact_name);
                    Y.Assert.areEqual('bug', artifact_type);
                    Y.Assert.areEqual(delete_link_to_click, delete_link);
                    event_fired = true;
                }
            );
            var delete_link_to_click =
                Y.one('#sharing-table-body span[id=remove-bug-2] a');
            delete_link_to_click.simulate('click');
            Y.Assert.isTrue(event_fired);
        },

        // When the branch revoke link is clicked, the correct event is
        // published.
        test_branch_revoke_click: function() {
            this.details_widget = this._create_Widget();
            this.details_widget.render();
            var event_fired = false;
            this.details_widget.subscribe(
                sharing_details.SharingDetailsTable.REMOVE_GRANT,
                function(e) {
                    var delete_link = e.details[0];
                    var artifact_uri = e.details[1];
                    var artifact_name = e.details[2];
                    var artifact_type = e.details[3];
                    Y.Assert.areEqual(
                        'api/devel/~someone/+junk/somebranch',
                        artifact_uri);
                    Y.Assert.areEqual(
                        'lp:~someone/+junk/somebranch', artifact_name);
                    Y.Assert.areEqual('branch', artifact_type);
                    Y.Assert.areEqual(delete_link_to_click, delete_link);
                    event_fired = true;
                }
            );
            var delete_link_to_click =
                Y.one('#sharing-table-body span[id=remove-branch-2] a');
            delete_link_to_click.simulate('click');
            Y.Assert.isTrue(event_fired);
        }
    }));


}, '0.1', { 'requires':
    [ 'test', 'console', 'event', 'node-event-simulate',
        'lp.registry.sharing.sharingdetails']});
