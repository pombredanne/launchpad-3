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
            var body = Y.one(document.body);
            
            //replace the container
            var container = Y.one('#notification-area');
            container.remove(true);
            container = Y.Node.create('<div></div>')
                .set('id', 'notification-area');
            body.appendChild(container);
            return container;
        },

        setUp: function () {
            //create the global notification html
            var container = this._reset_container();
            var login_logout = Y.Node.create('<div></div>')
                .addClass('login-logout');
            var notification = Y.Node.create('<div></div>')
                .addClass('global-notification')
                .addClass('hidden');
            var notification_span = Y.Node.create('<span></span>')
                .addClass('sprite')
                .addClass('notification-private')
            var close_link = Y.Node.create('<a></a>')
                .addClass('global-notification-close')
                .set('href', '#');
            var close_span = Y.Node.create('<span></span>')
                .addClass('sprite')
                .addClass('notification-close')
           
            notification.set('text', "This bug is private");
            close_link.set('text', "Hide");

            container.appendChild(login_logout);
            container.appendChild(notification);
            notification.appendChild(notification_span);
            notification.appendChild(close_link);
            close_link.appendChild(close_span);
        },

        test_setup: function() {
            //undo the setup
            var container = this._reset_container();
            var config = {
                notification_text: "stuff is private",
                hidden: true,
                target_id: container.get('id') 
            }
            Y.lp.app.privacy.setup_privacy_notification(config);
            var ribbon = Y.one('.global-notification'); 
            Y.Assert.isTrue(ribbon.hasClass('hidden')); 
            //
            // Text is both the passed in config and the "Hide" button text.
            var expected_text = 'stuff is private' + 'Hide';
            Y.Assert.areEqual(expected_text, ribbon.get('text'));
        },

        test_display_shows_ribbon: function () {
            var ribbon = Y.one('.global-notification'); 
            Y.Assert.isTrue(ribbon.hasClass('hidden'));
            Y.lp.app.privacy.display_privacy_notification()
            Y.Assert.isFalse(ribbon.hasClass('hidden.'));
        },

        test_hide_removes_ribbon: function () {
            var ribbon = Y.one('.global-notification');
            Y.lp.app.privacy.display_privacy_notification();
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

