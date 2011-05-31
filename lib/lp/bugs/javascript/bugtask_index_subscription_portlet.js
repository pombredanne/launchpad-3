/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Provide information and actions on all bug subscriptions a person holds.
 *
 * @module bugs
 * @submodule bugtask_index_subscription_portlet
 */

YUI.add('lp.bugs.bugtask_index.portlets.subscription', function(Y) {

var namespace = Y.namespace('lp.bugs.bugtask_index.portlets.subscription');

var MUTED_CLASS = namespace.MUTED_CLASS = 'unmute';
var UNMUTED_CLASS = namespace.UNMUTED_CLASS = 'mute';


function lp_client() {
    // This is a hook point for tests.
    if (!Y.Lang.isValue(namespace._lp_client)) {
        namespace._lp_client = new Y.lp.client.Launchpad();
    }
    return namespace._lp_client;
}

/*
 * Update the text and link at the top of the subscription portlet.
 */
function update_subscription_status() {
    var status = Y.one('#current_user_subscription');
    var span = status.one('span');
    var link = status.one('a');
    var mute_link = Y.one('.menu-link-mute_subscription');
    var is_muted = (Y.Lang.isValue(mute_link) &&
                    mute_link.hasClass(MUTED_CLASS));
    var messages = LP.cache.notifications_text;
    if (is_muted) {
        span.set('text', messages.muted);
        if (!Y.Lang.isUndefined(link)) {
            link.remove();
        };
    } else {
        if (!Y.Lang.isValue(link)) {
            // Make one.
            link = Y.Node.create(
                '<a class="menu-link-subscription sprite modify edit"/>');
            link.set('href', LP.cache.context.web_link + '/+subscribe')
            status.appendChild(link);
            setup_subscription_link_handlers();
        };
        span.set('text', messages.not_only_other_subscription);
        if (Y.Lang.isUndefined(LP.cache.subscription)) {
            if (LP.cache.other_subscription_notifications) {
                span.set('text', messages.only_other_subscription);
            };
            link.set('text', messages.not_direct);
        } else {
            switch (LP.cache.subscription.bug_notification_level) {
                case 'Discussion':
                    link.set('text', messages.direct_all);
                    break;
                case 'Details':
                    link.set('text', messages.direct_metadata);
                    break;
                case 'Lifecycle':
                    link.set('text', messages.direct_lifecycle);
                    break;
                default:
                    Y.error(
                        'Programmer error: unknown bug notification level: '+
                        LP.cache.subscription.bug_notification_level);
            };
        };
    };
    Y.lazr.anim.green_flash({ node: status }).run();
}
namespace.update_subscription_status = update_subscription_status;

/*
 * Set up the handlers for the mute / unmute link.
 */
function setup_mute_link_handlers() {
    var link = Y.one('.menu-link-mute_subscription');
    if (Y.Lang.isNull(link) || link.hasClass('spinner')) {
        return;
    }
    link.addClass('js-action');
    link.on('click', function (e) {
        e.halt();
        var is_muted = link.hasClass(MUTED_CLASS);
        var method_name, current_class, destination_class;
        if (is_muted) {
            method_name = 'unmute';
            current_class = MUTED_CLASS;
            destination_class = UNMUTED_CLASS;
        } else {
            method_name = 'mute';
            current_class = UNMUTED_CLASS;
            destination_class = MUTED_CLASS;
        }
        link.replaceClass(current_class, 'spinner');
        var handler = new Y.lp.client.ErrorHandler();
        handler.showError = function(error_msg) {
            Y.lp.app.errors.display_error(link.get('parentNode'), error_msg);
        };
        handler.clearProgressUI = function () {
            link.replaceClass('spinner', current_class);
        }
        var config = {
            on: {
                success: function(response) {
                    link.replaceClass('spinner', destination_class);
                    update_subscription_status();
                    Y.lazr.anim.green_flash(
                        { node: link.get('parentNode') }).run();
                },
                failure: handler.getFailureHandler()
            },
            parameters: {}
        };
        lp_client().named_post(
            LP.cache.context.bug_link, method_name, config);
    });
}
namespace.setup_mute_link_handlers = setup_mute_link_handlers;

function setup_subscription_link_handlers() {
    var link = Y.one('#current_user_subscription a');
    if (!Y.Lang.isValue(link)) {
        return;
    }
    // XXX Add click handlers here.
    link.addClass('js-action');
}
namespace.setup_subscription_link_handlers = setup_subscription_link_handlers;

namespace.initialize = function () {
    if (LP.links.me === undefined) {
        return;
    }
    setup_subscription_link_handlers();
    setup_mute_link_handlers();
};

}, '0.1', {requires: [
    'dom', 'event', 'node', 'substitute', 'lazr.effects', 'lp.app.errors',
    'lp.client'
]});
