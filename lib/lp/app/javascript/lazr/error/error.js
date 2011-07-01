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

YUI.add('lazr.error', function(Y) {

/*
 * Module docstring goes here...
 *
 * @module lazr.error
 * @namespace lazr.error
 */

Y.namespace('lazr.error');

var BasicErrorWidget = function() {
    BasicErrorWidget.superclass.constructor.apply(this, arguments);
};

// The basic error widget is just a pretty overlay - we don't
// want to create extra styles for it.
BasicErrorWidget.NAME = 'lazr-basic-error-widget';
BasicErrorWidget.ERROR_LIST_TEMPLATE = '<ul class="errors" />';
Y.extend(BasicErrorWidget, Y.lazr.PrettyOverlay, {

    initializer: function() {
        this.error_list = [];
        this.content = null;

        /**
        * Fires when the user presses the 'Cancel' button.
        *
        * We want to ensure that the error list is cleared
        * when the basic error widget is dismissed.
        * @event cancel
        */
        this.publish('cancel', {
            defaultFn: function() {
                this.error_list = [];

                // Ensure the pretty overlay's default cancel
                // handler is also called.
                this._defaultCancel();
            }
        });

    },

    renderUI: function() {
        this.content = Y.Node.create(
            '<p>The following errors were encountered:</p>');
        var error_list_node = Y.Node.create(
            BasicErrorWidget.ERROR_LIST_TEMPLATE);
        this.content.appendChild(error_list_node);
        var dismiss_button = Y.Node.create(
            '<button class="dismiss">Dismiss</button>');
        this.content.appendChild(dismiss_button);

        this.setStdModContent(
            Y.WidgetStdMod.BODY, this.content,
            Y.WidgetStdMod.REPLACE);
    },

    bindUI: function() {
        var self = this;
        var dismiss_button = this.content.one('button.dismiss');
        dismiss_button.on('click', function(e) {
            e.halt();
            self.fire('cancel');
        });
    },

    syncUI: function() {
        // Create a new list of error nodes based on the current errors.
        var new_error_list_node = Y.Node.create(
            BasicErrorWidget.ERROR_LIST_TEMPLATE);
        Y.each(this.error_list, function(error_msg){
            var error_list_item = Y.Node.create("<li />");
            error_list_item.appendChild(document.createTextNode(error_msg));
            new_error_list_node.appendChild(error_list_item);
        });

        // Swap the new error list in.
        var old_error_list_node = this.content.one('ul.errors');
        this.content.replaceChild(new_error_list_node, old_error_list_node);
    },

    showError: function(error_msg) {
        this.error_list.push(error_msg);
        this.syncUI();
        this.show();
    }
});


/*
 * Get or create the error widget to use when encountering errors.
 *
 * @method get_error_widget
*/
var get_error_widget = function() {
    if (Y.lazr.error.widget === undefined) {
        Y.lazr.error.widget = new BasicErrorWidget({
            headerContent: '<h2>Error</h2>',
            centered: true,
            visible: false
        });

        Y.lazr.error.widget.render();
    }
};

/**
 * Run a callback, optionally flashing a specified node red beforehand.
 *
 * If the supplied node evaluates false, the callback is invoked immediately.
 *
 * @method maybe_red_flash
 * @param flash_node The node to flash red, or null for no flash.
 * @param callback The callback to invoke.
 */
var maybe_red_flash = function(flash_node, callback)
{
    if (flash_node) {
        var anim = Y.lazr.anim.red_flash({ node: flash_node });
        anim.on('end', callback);
        anim.run();
    } else {
        callback();
    }
};


/*
 * Take an error message and display in an error widget
 * (creating it if necessary).
 *
 * @method display_error
 * @param msg {String} The message to display.
 * @param flash_node {Node} The node to red flash.
*/
var display_error = function(msg, flash_node) {
    get_error_widget();
    maybe_red_flash(flash_node, function(){
        Y.lazr.error.widget.showError(msg);
    });
};

Y.lazr.error.display_error = display_error;

Y.namespace('lazr.error_widgets');
Y.lazr.error_widgets.BasicErrorWidget = BasicErrorWidget;

}, "0.1", {"skinnable": true, "requires":["lazr.overlay"]});
