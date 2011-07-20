YUI.add('lp.app.privacy', function(Y) {

var namespace = Y.namespace('lp.app.privacy');
/*
 * Display privacy notifications
 *
 * This should be called after the page has loaded e.g. on 'domready'.
 */
namespace.display_privacy_notification = function () {
    /* Check if the feature flag is set for this notification. */
    if (bugs_private_notification_enabled) {
        /* Set a temporary class on the body for the feature flag,
         this is because we have no way to use feature flags in
         css directly. This should be remove if the feature
         is accepted. */
        var body = Y.one('body');
        body.addClass('feature-flag-bugs-private-notification-enabled');
        /* Set the visible flag so that the content moves down. */
        body.addClass('global-notification-visible');

        if (Y.one('.global-notification').hasClass('hidden')) {
            Y.one('.global-notification').addClass('transparent');
            Y.one('.global-notification').removeClass('hidden');
            var fade_in = new Y.Anim({
                node: '.global-notification',
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

        Y.on('click', function(e) {
            hide_privacy_notification(true);
            e.halt();
        }, '.global-notification-close');
    }
}


/*
 * Hide privacy notifications
 *
 * This should be called after the page has loaded e.g. on 'domready'.
 */
namespace.hide_privacy_notification = function(highlight_portlet) {
    if (bugs_private_notification_enabled) {
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


}, "0.1", {"requires": ["base", "oop", "node", "lazr.anim", "lazr.base",
                        "lazr.overlay", "lazr.choiceedit", "lp.app.picker"]});
