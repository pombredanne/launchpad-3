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

        _reset_container: function () {
            Y.lp.app.privacy._reset_privacy_notification();
            var body = Y.one(document.body);

            // Replace the container.
            var container = Y.one('#maincontent');
            container.remove(true);
            container = Y.Node.create('<div></div>')
                .set('id', 'maincontent');
            body.appendChild(container);
            return container;
        },

        setUp: function () {
            // Create the global notification html.
            var container = this._reset_container();
            var login_logout = Y.Node.create('<div></div>')
                .addClass('login-logout');
            container.appendChild(login_logout);
        },

        test_setup: function() {
            // Undo the setup.
            var container = this._reset_container();
            var config = {
                notification_text: "stuff is private",
                hidden: true,
                target_id: container.get('id')
            };
            Y.lp.app.privacy.setup_privacy_notification(config);
            var ribbon = Y.one('.global-notification');
            Y.Assert.isTrue(ribbon.hasClass('hidden'));

            Y.Assert.areEqual(config.notification_text, ribbon.get('text'));
        },

        test_display_shows_ribbon: function () {
            Y.lp.app.privacy.display_privacy_notification();
            var ribbon = Y.one('.global-notification');
            Y.Assert.isFalse(ribbon.hasClass('hidden.'));
        },

        test_hide_removes_ribbon: function () {
            Y.lp.app.privacy.display_privacy_notification();
            var ribbon = Y.one('.global-notification');
            Y.Assert.isFalse(ribbon.hasClass('hidden'));
            Y.lp.app.privacy.hide_privacy_notification(false);

            // We wait for the privacy ribbon fadeout to complete.
            // It takes 300ms, but we have to pad that out to avoid a race and
            // intermittent failures.
            var wait_for_anim = 320;
            this.wait(
                function () {
                    Y.Assert.isTrue(ribbon.hasClass('hidden'));
                },
                wait_for_anim);
        }
    }));

    Y.lp.testing.Runner.run(suite);
});

