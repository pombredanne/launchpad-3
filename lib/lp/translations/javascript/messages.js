/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * @module lp.translations.messages
 * @requires node
 */

YUI.add('lp.translations.messages', function(Y) {

var namespace = Y.namespace('lp.translations.messages');

/**
 * Add listeners to widgets associated with translation messages.
 */
namespace.addListeners = function() {
    Y.all('.handle-click').each(function(node) {
        node.on('click', function(e) {
            e.halt();
            var from_id = node.getAttribute('data-from-id');
            var to_id = node.getAttribute('data-to-id');
            var source_node = Y.one('#' + from_id);
            var text_field = Y.one('#' + to_id);
            text_field._node.value = source_node.get('text');
            // We may have a checkbox/radio button to select also.
            var selectWidgetId = to_id + '_select';
            if (Y.Lang.isValue(Y.one('#' + selectWidgetId))) {
                selectWidget(selectWidgetId, e);
            }
        });
    });
};

}, "0.1", {"requires": ["node"]});

