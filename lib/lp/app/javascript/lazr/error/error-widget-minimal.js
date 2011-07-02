/*
    Copyright (c) 2009, Canonical Ltd.  All rights reserved.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

/*
 * Widgets for displaying errors.
 *
 * @module lazr.error
 * @namespace lazr.error
 */
YUI.add('lazr.error.minimal-error-widget', function(Y) {
Y.namespace('lazr.error.minimal_error_widget');

/**
 * This class provides a minimal display of lazr errors, enabling
 * viewing of one error at a time.
 *
 * @class MinimalErrorWidget
 * @extends Widget
 * @constructor
 */
var CLICK = 'click',
    CONTENT_BOX = 'contentBox',
    CURRENT = 'current',
    CURRENT_ERROR_INDEX = 'current_error_index',
    DISMISS_ALL = 'dismiss_all',
    NEXT = 'next',
    PREV = 'prev';

var MinimalErrorWidget = function() {
    MinimalErrorWidget.superclass.constructor.apply(this, arguments);
};

MinimalErrorWidget.NAME = 'lazr-minimal-error-widget';

/**
 * Static html template to use for creating the list of errors.
 *
 * @property InlineEditor.SUBMIT_TEMPLATE
 * @type string
 * @static
 */
MinimalErrorWidget.ERROR_LIST_TEMPLATE = '<ul class="errors" />';

MinimalErrorWidget.ATTRS = {

    /**
     * Records the index of the currently displayed error.
     *
     * @attribute current_error_index
     * @type Integer
     * @default 0
     */
    current_error_index: {
        value: 0
    }
};

Y.extend(MinimalErrorWidget, Y.Widget, {

    initializer: function() {
        this.error_list = [];

        /**
        * Fires when the user presses the 'Dismiss' button.
        *
        * We want to ensure that the error list is cleared
        * when the basic error widget is dismissed.
        * @event dismiss_all
        */
        this.publish(DISMISS_ALL, {
            defaultFn: function() {
                this.error_list = [];
                this.set(CURRENT_ERROR_INDEX, 0);
                this.hide();
            }
        });

        /**
        * Fires when the user presses the 'next' link.
        *
        * We shift the display of errors by +1 to display the next error.
        * @event next
        */
        this.publish(NEXT, {
            defaultFn: function() {
                // We simply move the current class to the next
                // error.
                this._shift_current_error(1);
            }
        });

        /**
        * Fires when the user presses the 'prev' link.
        *
        * We shift the display of errors by -1 to display the next error.
        * @event prev
        */
        this.publish(PREV, {
            defaultFn: function() {
                // We move the current class to the prev
                // error.
                this._shift_current_error(-1);
            }
        });
    },

    /**
     * A convenience method to update navigation display 'Viewing 1 of ..'
     *
     * @method _update_navigation
     */
    _update_navigation: function() {
        var content_box = this.get(CONTENT_BOX);
        content_box.one('span.error-num').set(
            'innerHTML', this.get(CURRENT_ERROR_INDEX) + 1);
        content_box.one('span.error-count').set(
            'innerHTML', this.error_list.length);
    },

    /**
     * A convenience method for shifting the current error displayed.
     *
     * @method _shift_current_error
     * @param amount {Integer} The distance to shift from the current error.
     */
    _shift_current_error: function(amount) {
        // Wrap back to the start if necessary.
        var new_index = this._wrap_index(
            this.get(CURRENT_ERROR_INDEX) + amount);
        this.set(CURRENT_ERROR_INDEX, new_index);
    },


    /**
     * A convenience method for wrapping the current error index so
     * we don't have to worry about disabling next/prev links.
     *
     * @method _wrap_index
     */
    _wrap_index: function(new_index) {
        if (new_index >= this.error_list.length) {
            return 0;
        }
        if (new_index < 0) {
            return this.error_list.length - 1;
        }
        return new_index;
    },

     /**
     * A convenience method for setting the current error so that
     * it is displayed in the UI.
     *
     * @method _update_displayed_error
     */
    _update_displayed_error: function() {
        var content_box = this.get(CONTENT_BOX);
        var error_nodes = content_box.one('div.error-info ul.errors').get(
            'children');

        error_nodes.removeClass(CURRENT);
        var error_index = 0;
        var this_widget = this;
        var current_error_index = this_widget.get(CURRENT_ERROR_INDEX);
        error_nodes.each(function(error_node) {
            if (error_index == current_error_index) {
                error_node.addClass(CURRENT);
            }
            error_index += 1;
        });
    },

    /**
     * Bind the widget's DOM elements to their event handlers.
     *
     * @method bindUI
     * @protected
     */
    bindUI: function() {
        // Ensure that the ui is updated after the current error index
        // changes.
        this.after(CURRENT_ERROR_INDEX + 'Change', function() {
            this._update_displayed_error();

            // Update the 'Viewing 1 of 3'.
            this._update_navigation();
        });

        var self = this;
        var contentBox = this.get(CONTENT_BOX);
        contentBox.one('button.dismiss_all').on(CLICK, function(e) {
            e.halt();
            self.fire(DISMISS_ALL);
        });

        contentBox.one('div.error-controls a.next').on(CLICK, function(e) {
            e.halt();
            self.fire(NEXT);
        });

        contentBox.one('div.error-controls a.prev').on(CLICK, function(e) {
            e.halt();
            self.fire(PREV);
        });
    },

    /**
     * Sync the UI with the widget's current state.
     *
     * @method syncUI
     * @protected
     */
    syncUI: function() {
        // Create a new list of error nodes based on the current errors.
        var new_error_list_node = Y.Node.create(
            MinimalErrorWidget.ERROR_LIST_TEMPLATE);

        var error_index = 0;
        var this_widget = this;
        Y.each(this.error_list, function(error_msg){
            var error_list_item = Y.Node.create("<li />");
            error_list_item.appendChild(document.createTextNode(error_msg));

            if (error_index == this_widget.get(CURRENT_ERROR_INDEX)) {
                error_list_item.addClass(CURRENT);
            }
            new_error_list_node.appendChild(error_list_item);

            error_index += 1;
        });

        // Swap the new error list in.
        var content_box = this.get(CONTENT_BOX);

        var error_info = content_box.one('div.error-info');
        var old_error_list_node = error_info.one('ul.errors');
        error_info.replaceChild(new_error_list_node, old_error_list_node);

        // Set the 'Viewing 1 of 3' state.
        this._update_navigation();
    },

    /**
     * Add an error to this error widget.
     *
     * @method showError
     * @param error_msg The error to add to the error widget.
     */
    showError: function(error_msg) {
        this.error_list.push(error_msg);
        this.syncUI();
        this.show();
    }
});


/**
* The HTML representation of this error widget.
*
* @property CONTENT_TEMPLATE
*/
MinimalErrorWidget.prototype.CONTENT_TEMPLATE = [
    '<div>',
    '  <div class="error-controls">',
    '    Viewing <span class="error-num">1</span> of ',
    '    <span class="error-count">1</span>',
    '    <a href="#" class="prev">Prev</a> ',
    '    <a href="#" class="next">Next</a>',
    '    <button class="dismiss_all">Dismiss</button>',
    '  </div>',
    '  <div class="error-info">',
    '  ' + MinimalErrorWidget.ERROR_LIST_TEMPLATE,
    '  </div>',
    '</div>'].join('');

Y.lazr.error.minimal_error_widget.MinimalErrorWidget = MinimalErrorWidget;
}, "0.1", {
    "skinnable": true,
    "requires": ["oop", "event", "widget", "lazr.error"]});
