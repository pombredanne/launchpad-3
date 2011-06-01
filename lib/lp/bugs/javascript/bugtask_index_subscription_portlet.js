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

function tag(name) {
    return Y.Node.create('<'+name+'/>');
}

function ws() {
    // Hack to work around YUI whitespace trim behavior. :-(
    return Y.Node.create('<span> </span>');
}

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
    var whitespace = status.one('span+span');
    var link = status.one('a');
    var mute_link = Y.one('.menu-link-mute_subscription');
    var is_muted = (Y.Lang.isValue(mute_link) &&
                    mute_link.hasClass(MUTED_CLASS));
    var messages = LP.cache.notifications_text;
    if (is_muted) {
        span.set('text', messages.muted);
        if (Y.Lang.isValue(link)) {
            link.remove();
        };
        if (Y.Lang.isValue(whitespace)) {
            whitespace.remove(); // Tests can be persnickety.
        };
    } else {
        if (!Y.Lang.isValue(link)) {
            if (!Y.Lang.isValue(whitespace)) {
                status.appendChild(ws());
            }
            link = tag('a')
                .addClass('menu-link-subscription')
                .addClass('sprite')
                .addClass('modify')
                .addClass('edit');
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
    if (Y.Lang.isNull(link)) {
        return;
    }
    link.addClass('js-action');
    link.on('click', function (e) {
        e.halt();
        var subscribe_link = Y.one('#current_user_subscription a');
        if (link.hasClass('spinner') ||
            (Y.Lang.isValue(subscribe_link) &&
             subscribe_link.hasClass('spinner'))) {
            return;
        }
        var is_muted = link.hasClass(MUTED_CLASS);
        var method_name, current_class, destination_class, destination_text;
        if (is_muted) {
            method_name = 'unmute';
            current_class = MUTED_CLASS;
            destination_class = UNMUTED_CLASS;
            destination_text = 'Mute bug mail';
        } else {
            method_name = 'mute';
            current_class = UNMUTED_CLASS;
            destination_class = MUTED_CLASS;
            destination_text = 'Unmute bug mail';
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
                    link.set('text', destination_text);
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

function make_link(text, class) {
    return tag('a')
        .set('href', '#')
        .addClass('sprite')
        .addClass('modify')
        .addClass(class)
        .set('text', text);
}

function setup_subscription_link_handlers() {
    var link = Y.one('#current_user_subscription a');
    if (!Y.Lang.isValue(link)) {
        return;
    }
    link.addClass('js-action');
    var mute_link = Y.one('.menu-link-mute_subscription');
    var mute_div = mute_link.get('parentNode');
    var clean_up = function() {
        overlay.hide();
        overlay.destroy();
        link.replaceClass('spinner', 'edit');
    }
    var overlay;
    var make_action = function(text, class, method_name, parameters) {
        result = make_link(text, class)
            .addClass('js-action');
        result.on('click', function (e) {
            e.halt();
            var active_link = e.currentTarget;
            active_link.replaceClass(class, 'spinner');
            var handler = new Y.lp.client.ErrorHandler();
            handler.showError = function(error_msg) {
                Y.lp.app.errors.display_error(
                    active_link.get('parentNode'), error_msg);
            };
            handler.clearProgressUI = function () {
                active_link.replaceClass('spinner', class);
            };
            var config = {
                on: {
                    success: function(response) {
                        if (Y.Lang.isValue(response)) {
                            // This is a subscription.  Update the cache.
                            LP.cache.subscription = response.getAttrs();
                        }
                        if (method_name === 'mute') {
                            // Special case: update main mute link.
                            mute_link.replaceClass(
                                UNMUTED_CLASS, MUTED_CLASS);
                            mute_link.set('text', 'Unmute bug mail');
                            Y.lazr.anim.green_flash(
                                { node: mute_link.get('parentNode') }).run();
                        } else if (method_name === 'unsubscribe') {
                            // Special case: delete cache.
                            delete LP.cache.subscription;
                            if (!LP.cache.other_subscription_notifications) {
                                // Special case: hide mute link.
                                mute_div.addClass('hidden');
                            }
                        } else if (method_name === 'subscribe') {
                            // Special case: reveal mute link.
                            mute_div.removeClass('hidden');
                        }
                        active_link.replaceClass('spinner', class);
                        update_subscription_status();
                        clean_up();
                    },
                    failure: handler.getFailureHandler()
                },
                parameters: parameters
            };
            lp_client().named_post(
                LP.cache.context.bug_link, method_name, config);
            });
        return result;
    }
    var header = tag('h2')
        .setStyle('display', 'block')
        .setStyle('overflow', 'hidden')
        .setStyle('textOverflow', 'ellipsis')
        .setStyle('whiteSpace', 'nowrap')
        .setStyle('width', '21em');
    var level_node = tag('div')
        .set('id', 'subscription-levels') // Useful for tests.
        .setStyle('margin-top', '1em')
        .append(tag('div')
            .set('id', 'Discussion')
            .append(make_action(
                'Receive all emails about this bug', 'edit',
                'subscribe', {person: LP.links.me, level: 'Discussion'})
            ).append(tag('span')
                .set('text',
                     'You currently receive all emails about this bug.')
                .addClass('sprite')
            )
        ).append(tag('div')
            .set('id', 'Details')
            .append(make_action(
                'Receive all emails about this bug except comments', 'edit',
                'subscribe', {person: LP.links.me, level: 'Details'})
            ).append(tag('span')
                .set('text',
                     'You currently receive all emails about this bug '+
                     'except comments.')
                .addClass('sprite')
            )
        ).append(tag('div')
            .set('id', 'Lifecycle')
            .append(make_action(
                'Only receive email when this bug is closed', 'edit',
                'subscribe', {person: LP.links.me, level: 'Lifecycle'})
            ).append(tag('span')
                .set('text',
                     'You currently only receive email when this bug is '+
                     'closed.')
                .addClass('sprite')
            )
        );
    var unsubscribe_node;
    if (LP.cache.other_subscription_notifications) {
        unsubscribe_node = tag('div')
            .setStyle('margin-top', '1.5em')
            .setStyle('width', '50em')
            .append(tag('span')
                .set('text', 'You may also')
            ).append(ws()
            ).append(make_action(
                'remove your direct subscription', 'remove',
                'unsubscribe', {})
            ).append(tag('span')
                .set('text',
                     ', but this might not stop all your email about the '+
                     'bug.')
            ).append(ws()
            ).append(make_action('Mute bug mail', 'mute', 'mute', {})
            ).append(ws()
            ).append(tag('span')
                .set('text',
                     'to make sure you never receive email about it, or ')
            ).append(make_link('edit bug mail', 'edit')
                .set('href', LP.cache.context.web_link + '/+subscriptions')
            ).append(ws()
            ).append(tag('span')
                .set('text',
                     'to see details of all your subscriptions to this bug.')
            );
    } else {
        unsubscribe_node = tag('div')
            .setStyle('margin-top', '1.5em')
            .append(make_action(
                'Remove your direct subscription', 'remove',
                'unsubscribe', {})
            );
    }
            
    link.on('click', function (e) {
        e.halt();
        if (link.hasClass('spinner') || mute_link.hasClass('spinner')) {
            return;
        }
        link.replaceClass('edit', 'spinner');
        var body = tag('div');
        level_node.all('a').removeClass('hidden');
        level_node.all('span').addClass('hidden');
        if (Y.Lang.isValue(LP.cache.subscription)) {
            // Edit the subscription.
            header.set('text',
                       'Change your mail subscription for this bug');
            current_level_div = level_node.one(
                '#'+LP.cache.subscription.bug_notification_level);
            current_level_div.one('a').addClass('hidden');
            current_level_div.one('span').removeClass('hidden');
            body.append(level_node).append(unsubscribe_node);
        } else {
            // Create a new subscription.
            // Edit the subscription.
            header.set('text',
                       'Add a mail subscription for this bug');
            body.append(level_node);
        }
        overlay = new Y.lazr.PrettyOverlay({
            headerContent: header,
            bodyContent: body,
            visible: false,
            centered: true
        });
        overlay.on('cancel', clean_up);
        overlay.render();
        overlay.show();
    });
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
    'dom', 'event', 'node', 'substitute', 'lazr.effects', 'lazr.overlay',
    'lp.app.errors', 'lp.client'
]});
