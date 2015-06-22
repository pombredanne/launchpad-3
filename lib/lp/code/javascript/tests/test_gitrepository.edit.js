/* Copyright 2015 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Test driver for gitrepository.edit.js.
 */
YUI.add('lp.code.gitrepository.edit.test', function(Y) {
    var tests = Y.namespace('lp.code.gitrepository.edit.test');
    var module = Y.lp.code.gitrepository.edit;
    tests.suite = new Y.Test.Suite('code.gitrepository.edit Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'code.gitrepository.edit_tests',

        setUp: function() {
            this.tbody = Y.one('#gitrepository.edit');

            // Get the individual target type radio buttons.
            this.target_personal = Y.DOM.byId('field.target.option.personal');
            this.target_package = Y.DOM.byId('field.target.option.package');
            this.target_project = Y.DOM.byId('field.target.option.project');

            // Get the input widgets.
            this.input_package = Y.one('input[name="field.target.package"]');
            this.input_project = Y.one('input[name="field.target.project"]');
            this.owner_default = Y.DOM.byId('field.owner_default');
        },

        tearDown: function() {
            delete this.tbody;
        },

        test_handlers_connected: function() {
            // Manually invoke the setup function to ensure the handlers are
            // set.
            module.setup();

            var check_handler = function(field, expected) {
                var custom_events = Y.Event.getListeners(field, 'click');
                var click_event = custom_events[0];
                var subscribers = click_event.subscribers;
                Y.each(subscribers, function(sub) {
                    Y.Assert.isTrue(sub.contains(expected),
                                    'handler not set up');
                });
            };

            check_handler(this.target_personal, module.onclick_target);
            check_handler(this.target_package, module.onclick_target);
            check_handler(this.target_project, module.onclick_target);
        },

        test_select_target_personal: function() {
            this.target_personal.checked = true;
            module.onclick_target();
            // The owner_default checkbox is disabled.
            Y.Assert.isTrue(this.owner_default.disabled,
                            'owner_default not disabled');
        },

        test_select_target_package: function() {
            this.target_package.checked = true;
            module.onclick_target();
            // The owner_default checkbox is enabled.
            Y.Assert.isFalse(this.owner_default.disabled,
                             'owner_default not disabled');
        },

        test_select_target_project: function() {
            this.target_project.checked = true;
            module.onclick_target();
            // The owner_default checkbox is enabled.
            Y.Assert.isFalse(this.owner_default.disabled,
                             'owner_default not disabled');
        },

        test_keypress_package: function() {
            this.target_personal.checked = true;
            this.owner_default.disabled = true;
            this.input_package.simulate('keypress', { charCode: 97 });
            Y.Assert.isTrue(this.target_package.checked);
            // The owner_default checkbox is enabled.
            Y.Assert.isFalse(this.owner_default.disabled,
                             'owner_default not disabled');
        },

        test_keypress_project: function() {
            this.target_personal.checked = true;
            this.owner_default.disabled = true;
            this.input_project.simulate('keypress', { charCode: 97 });
            Y.Assert.isTrue(this.target_project.checked);
            // The owner_default checkbox is enabled.
            Y.Assert.isFalse(this.owner_default.disabled,
                             'owner_default not disabled');
        },
    }));
}, '0.1', {
    requires: ['lp.testing.runner', 'test', 'test-console',
               'Event', 'node-event-simulate',
               'lp.code.gitrepository.edit']
});
