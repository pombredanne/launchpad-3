/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI().use('lp.testing.runner', 'test', 'console', 'node',
          'node-event-simulate', 'lazr.effects', 'lp.app.calendar',
          'lp.app.errors', 'lp.client', 'lp.testing.mockio',
          'lp.registry.milestoneoverlay',
    function(Y) {

    var suite = new Y.Test.Suite("Milestone creation overlay tests");
    var module = Y.lp.registry.milestoneoverlay;

    test_case = new Y.Test.Case({
        // Test the setup method.
        name: 'Milestone creation error handling',

        _should: {
            error: {
                }
        },

        setUp: function() {
            this.mockio = new Y.lp.testing.mockio.MockIo();
            this.client = new Y.lp.client.Launchpad({
                io_provider: this.mockio});
            this.config = {
                milestone_form_uri: "milestone/++form++",
                series_uri: 'https://launchpad.dev/series',
                lp_client: this.client
            };
            module.configure(this.config);
        },

        test_io_provider_default: function() {
            // If no io_provider is configured, the form will use Y.
            var config = {
                milestone_form_uri: "milestone/++form++",
                series_uri: 'https://launchpad.dev/series'
            };
            module.configure(config);
            var form = module.setup_milestone_form();
            Y.Assert.areSame(Y, form.get("io_provider"));
        },

        test_io_provider_mockio: function() {
            // The provided mockio provider (defined in setUp) is used.
            var form = module.setup_milestone_form();
            Y.Assert.areSame(this.mockio, form.get("io_provider"));
        },

        test_error_creating_milestone: function() {
            var params = {
                'field.name': ['milestone_name'],
                'field.code_name': ['code_name'],
                'field.dateexpected': [''],
                'field.tags': [''],
                'field.summary': ['']
            };

            module.save_new_milestone(params);
            this.mockio.failure();

            // The page has rendered the error overlay.
            var error_box = Y.one('.yui3-lazr-formoverlay-errors');
            Y.Assert.isTrue(Y.Lang.isValue(error_box));
            Y.Assert.areEqual(
                'Server error, please contact an administrator.',
                error_box.get('text'));
        },

        test_error_setting_tags_delete_milestone_ok: function() {
            var params = {
                'field.name': ['milestone_name'],
                'field.code_name': ['code_name'],
                'field.dateexpected': [''],
                'field.tags': ['foo'],
                'field.summary': ['']
            };

            module.save_new_milestone(params);
            // Simulate the creation of the milestone succeeding and
            // returning a valid milestone.
            this.mockio.success({
                responseText:
                    '{"resource_type_link": "foo"}',
                responseHeaders: {'Content-Type': 'application/json'}
            });
            // Fail the call to setTags.
            this.mockio.failure();
            // And succeed on deleting the milestone.
            this.mockio.success();

            // The page has rendered the error overlay.
            var error_box = Y.one('.yui3-lazr-formoverlay-errors');
            Y.Assert.isTrue(Y.Lang.isValue(error_box));
            Y.Assert.areEqual(
                'Server error, please contact an administrator.',
                error_box.get('text'));
        },

        test_error_setting_tags_delete_milestone_fails: function() {
            var params = {
                'field.name': ['milestone_name'],
                'field.code_name': ['code_name'],
                'field.dateexpected': [''],
                'field.tags': ['foo'],
                'field.summary': ['']
            };

            module.save_new_milestone(params);
            // Simulate the creation of the milestone succeeding and
            // returning a valid milestone.
            this.mockio.success({
                responseText:
                    '{"resource_type_link": "foo"}',
                responseHeaders: {'Content-Type': 'application/json'}
            });
            // Fail the call to setTags.
            this.mockio.failure();
            // And fail on deleting the milestone.
            this.mockio.failure();

            // The page has rendered the error overlay.
            var error_box = Y.one('.yui3-lazr-formoverlay-errors');
            Y.Assert.isTrue(Y.Lang.isValue(error_box));
            Y.Assert.areEqual(
                'The following errors were encountered:' +
                'Server error, please contact an administrator.'+
                'The new milestone has been created without the tags.',
                error_box.get('text').trim());
        }
    });

    suite.add(test_case);

    Y.lp.testing.Runner.run(suite);

});
