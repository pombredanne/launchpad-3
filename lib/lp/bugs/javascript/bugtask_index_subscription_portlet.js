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

function jslink() {
    return tag('a')
        .set('href', '#')
        .addClass('js-action')
        .addClass('sprite')
        .addClass('modify')
        .addClass('edit');
}

function ws() {
    // Hack to work around YUI whitespace trim behavior. :-(
    return Y.Node.create('<span> </span>');
}

function setup_subscription_link_handlers() {
    var link = Y.one('#current_user_subscription a');
    if (!Y.Lang.isValue(link)) {
        return;
    }
    link.addClass('js-action');
    var mute_link = Y.one('.menu-link-mute_subscription');
    var header = tag('h2')
        .setStyle('display', 'block')
        .setStyle('overflow', 'hidden')
        .setStyle('textOverflow', 'ellipsis')
        .setStyle('whiteSpace', 'nowrap')
        .setStyle('width', '21em');
    var level_node = tag('div')
        .setStyle('margin-top', '1em')
        .append(tag('div')
            .set('id', 'Discussion')
            .append(jslink()
                .set('text', 'Receive all emails about this bug')
            ).append(tag('span')
                .set('text',
                     'You currently receive all emails about this bug.')
                .addClass('sprite')
            )
        ).append(tag('div')
            .set('id', 'Details')
            .append(jslink()
                .set('text',
                     'Receive all emails about this bug except comments')
            ).append(tag('span')
                .set('text',
                     'You currently receive all emails about this bug '+
                     'except comments.')
                .addClass('sprite')
            )
        ).append(tag('div')
            .set('id', 'Lifecycle')
            .append(jslink()
                .set('text',
                     'Only receive email when this bug is closed')
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
            ).append(jslink()
                .replaceClass('edit', 'remove')
                .set('text', 'remove your direct subscription')
            ).append(tag('span')
                .set('text',
                     ', but this might not stop all your email about the bug.')
            ).append(ws()
            ).append(jslink()
                .replaceClass('edit', 'mute')
                .set('text', 'Mute bug mail')
            ).append(ws()
            ).append(tag('span')
                .set('text',
                     'to make sure you never receive email about it, or ')
            ).append(jslink()
                .removeClass('js-action')
                .set('href', LP.cache.context.web_link + '/+subscriptions')
                .set('text', 'Edit bug mail')
            ).append(ws()
            ).append(tag('span')
                .set('text',
                     'to see details of all your subscriptions to this bug.')
            );
    } else {
        unsubscribe_node = tag('div')
            .setStyle('margin-top', '1.5em')
            .append(jslink()
                .set('text', 'Remove your direct subscription')
                .replaceClass('edit', 'remove')
            );
    }
            
    link.on('click', function (e) {
        e.halt();
        if (link.hasClass('spinner') || mute_link.hasClass('spinner')) {
            return;
        }
        link.replaceClass('edit', 'spinner');
        var body = tag('div');
        level_node.all('a').setStyle('display', 'inline');
        level_node.all('span').setStyle('display', 'none');
        if (Y.Lang.isValue(LP.cache.subscription)) {
            // Edit the subscription.
            header.set('text',
                       'Change your mail subscription for this bug');
            current_level_div = level_node.one(
                '#'+LP.cache.subscription.bug_notification_level);
            current_level_div.one('a').setStyle('display', 'none');
            current_level_div.one('span').setStyle('display', 'inline');
            body.append(level_node).append(unsubscribe_node);
        } else {
            // Create a new subscription.
            // Edit the subscription.
            header.set('text',
                       'Add a  mail subscription for this bug');
            body.append(level_node);
        }
        var overlay = new Y.lazr.PrettyOverlay({
            headerContent: header,
            bodyContent: body,
            visible: false,
            centered: true
        });
        var clean_up = function() {
            overlay.hide();
            overlay.destroy();
            link.replaceClass('spinner', 'edit');
        }
        overlay.set('form_submit_callback', function(formdata) {
            // Do not clean up if saving was not successful.
            clean_up;
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
