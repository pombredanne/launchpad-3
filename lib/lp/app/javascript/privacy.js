YUI.add('lp.app.privacy', function(Y) {

var namespace = Y.namespace('lp.app.privacy');
/*
 * Display privacy notifications
 *
 * This should be called after the page has loaded e.g. on 'domready'.
 */
function display_privacy_notification(highlight_portlet_on_close) {
    /* Check if the feature flag is set for this notification. */
    var highlight = true;
    if (highlight_portlet_on_close !== undefined) {
        highlight = highlight_portlet_on_close;
    }
    if (privacy_notification_enabled) {
        /* Set a temporary class on the body for the feature flag,
         this is because we have no way to use feature flags in
         css directly. This should be removed if the feature
         is accepted. */
        var body = Y.one('body');
        body.addClass('feature-flag-bugs-private-notification-enabled');
        /* Set the visible flag so that the content moves down. */
        body.addClass('global-notification-visible');

        var global_notification = Y.one('.global-notification');
        if (global_notification.hasClass('hidden')) {
            global_notification.addClass('transparent');
            global_notification.removeClass('hidden');

            var fade_in = new Y.Anim({
                node: global_notification,
                to: {opacity: 1},
                duration: 0.3
            });
            var body_space = new Y.Anim({
                node: 'body',
                to: {'paddingTop': '40px'},
                duration: 0.2,
                easing: Y.Easing.easeOut
            });
            var login_space = new Y.Anim({
                node: '.login-logout',
                to: {'top': '45px'},
                duration: 0.2,
                easing: Y.Easing.easeOut
            });

            fade_in.run();
            body_space.run();
            login_space.run();
        }

        Y.one('.global-notification-close').on('click', function(e) {
            hide_privacy_notification(highlight);
            e.halt();
        });
    }
}
namespace.display_privacy_notification = display_privacy_notification;

/*
 * Hide privacy notifications
 *
 * This should be called after the page has loaded e.g. on 'domready'.
 */
function hide_privacy_notification(highlight_portlet) {
    if (privacy_notification_enabled) {
        if (!Y.one('.global-notification').hasClass('hidden')) {
            var fade_out = new Y.Anim({
                node: '.global-notification',
                to: {opacity: 0},
                duration: 0.3
            });
            var body_space = new Y.Anim({
                node: 'body',
                to: {'paddingTop': 0},
                duration: 0.2,
                easing: Y.Easing.easeOut
            });
            var login_space = new Y.Anim({
                node: '.login-logout',
                to: {'top': '6px'},
                duration: 0.2,
                easing: Y.Easing.easeOut
            });
            fade_out.on('end', function() {
                fade_out.get('node').addClass('hidden');

                //used to track the event for testing
                this.fire('fadeout');
            });
            body_space.on('end', function() {
                Y.one('body').removeClass('global-notification-visible');
            });

            fade_out.run();
            body_space.run();
            login_space.run();

            if (highlight_portlet) {
                var portlet_colour = new Y.Anim({
                    node: '.portlet.private',
                    to: {
                        color: '#fff',
                        backgroundColor:'#8d1f1f'
                    },
                    duration: 0.4
                });
                portlet_colour.run();
            }
        }
    }
}
namespace.hide_privacy_notification = hide_privacy_notification;


}, "0.1", {"requires": ["base", "node", "anim"]});
