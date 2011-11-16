YUI.add('lp.app.beta_features', function(Y) {

var namespace = Y.namespace('lp.app.beta_features');

var beta_notification_node = null;

/**
 * For unit tests - we need to reset the notification setup to run more than
   one test.
 */
namespace._reset_beta_notification = function () {
    notification_node = null;
};

/*
 * Display beta feature notifications.
 *
 * This should be called after the page has loaded e.g. on 'domready'.
 */
function display_beta_notification() {
    if (LP.cache.related_features.length === 0) {
        return;
    }

    var related_features = LP.cache.related_features;
    var body = Y.one('body');
    body.addClass('global-notification-visible');
    var main = Y.one('#maincontent');
    beta_notification_node = Y.Node.create('<div></div>')
        .addClass('beta-banner');
    main.appendChild(beta_notification_node);
    var beta_warning = Y.Node.create(
        '<span class="beta-warning">BETA</span>');
    beta_notification_node.appendChild(beta_warning);
    var close_box = Y.Node.create(
        '<a href="#" class="global-notification-close">Hide' +
        '<span class="notification-close sprite" /></a>');
    beta_notification_node.appendChild(close_box);
    beta_notification_node.append('Some parts of this page are in beta: ');
    var index;
    for (index = 0; index < related_features.length; index++) {
        var feature_name = related_features[index][4];
        var info_link = related_features[index][5];
        if (info_link.length > 0) {
            info_link =
                ' (<a href="' + info_link + '" class="info-link">' +
                'read more</a>)';
        }
        beta_notification_node.appendChild(Y.Node.create(
            '<span class="beta-feature"> ' + feature_name + info_link +
            '</span>'));
    }
    close_box.on('click', function(e) {
        e.halt();
        var fade_out = new Y.Anim({
            node: '.beta-banner',
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
    });
}
namespace.display_beta_notification = display_beta_notification;

}, "0.1", {"requires": ["base", "node", "anim"]});
