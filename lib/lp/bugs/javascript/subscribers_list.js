/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Functions for managing the subscribers list.
 *
 * @module bugs
 * @submodule subscribers_list
 */

YUI.add('lp.bugs.subscribers_list', function(Y) {

var namespace = Y.namespace('lp.bugs.subscribers_list');

/**
 * Reset the subscribers list if needed.
 *
 * Adds the "None" div to the subscribers list if
 * there aren't any subscribers left, and clears up
 * the duplicate subscribers list if empty.
 *
 * @method reset
 */
function reset() {
    var subscriber_list = Y.one('#subscribers-links');
    // Assume if subscriber_list has no child divs
    // then the list of subscribers is empty.
    if (!Y.Lang.isValue(subscriber_list.one('div')) &&
        !Y.Lang.isValue(Y.one('#none-subscribers'))) {
        var none_div = Y.Node.create('<div id="none-subscribers">None</div>');
        var subscribers = subscriber_list.get('parentNode');
        subscribers.appendChild(none_div);
    }

    // Clear the empty duplicate subscribers list if it exists.
    var dup_list = Y.one('#subscribers-from-duplicates');
    if (Y.Lang.isValue(dup_list) &&
        !Y.Lang.isValue(dup_list.one('div'))) {
        dup_list.remove();
    }
}
namespace._reset = reset;

/**
 * Remove the user's name from the subscribers list.
 * It uses the green-flash animation to indicate successful removal.
 *
 * @method remove_user_link
 * @param subscriber {Subscriber} Subscriber that you want to remove.
 * @param is_dupe {Boolean} Uses subscription link from the duplicates
 *     instead.
 */
function remove_user_link(subscriber, is_dupe) {
    var user_node_id;
    if (is_dupe === true) {
        user_node_id = '#dupe-' + subscriber.get('css_name');
    } else {
        user_node_id = '#direct-' + subscriber.get('css_name');
    }
    var user_node = Y.one(user_node_id);
    if (Y.Lang.isValue(user_node)) {
        var anim = Y.lazr.anim.green_flash({ node: user_node });
        anim.on('end', function() {
            user_node.remove();
            reset();
        });
        anim.run();
    }
}
namespace.remove_user_link = remove_user_link;

}, "0.1", {"requires": ["node", "lazr.anim"]});
