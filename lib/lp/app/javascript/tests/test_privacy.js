/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

// Set the "enabled" variable, normally set by base-layout-macros.
// This must be a global variable for the code being tested to work.
var privacy_notification_enabled = true;

YUI().use('lp.testing.runner', 'test', 'console', 'node',
          'lp.app.privacy', 'node-event-simulate', function(Y) {

    var suite = new Y.Test.Suite("lp.app.privacy Tests");

    suite.add(new Y.Test.Case({
        name: 'privacy',

        test_display_shows_ribbon: function () {
            ribbon = Y.one('.global-notification'); 
            Y.Assert.isTrue(ribbon.hasClass('hidden'));
            Y.lp.app.privacy.display_privacy_notification();
            Y.Assert.isFalse(ribbon.hasClass('hidden'));
        },

        _check_ribbon_is_hidden: function () {
            var ribbon = Y.one('.global-notification');
            Y.Assert.isTrue(ribbon.hasClass('hidden'));
        },

        test_hide_removes_ribbon: function () {
            Y.lp.app.privacy.display_privacy_notification();
            Y.Assert.isFalse(ribbon.hasClass('hidden'));
            Y.lp.app.privacy.hide_privacy_notification(false);

            // We listen for a fadeout event to get around the timing issues, o
            Y.on('fadeout', this._check_ribbon_is_hidden());
        }
    }));

    Y.lp.testing.Runner.run(suite);
});

