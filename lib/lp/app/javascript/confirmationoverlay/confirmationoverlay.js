/* Copyright (c) 20011, Canonical Ltd. All rights reserved. */

YUI.add('lazr.confirmationoverlay', function(Y) {

/**
 * Display a confirmation overlay before submitting a form.
 *
 * @module lazr.confirmationoverlay
 */


var NAME = 'lazr-confirmationoverlay';

/**
 * The ConfirmationOverlay class builds on the lazr.FormOverlay
 * class.
 *
 * @class ConfirmationOverlay
 * @namespace lazr
 */
function ConfirmationOverlay(config) {
    ConfirmationOverlay.superclass.constructor.apply(this, arguments);
}

ConfirmationOverlay.NAME = NAME;

ConfirmationOverlay.ATTRS = {

    /**
     * The input button what should be 'guarded' by this confirmation
     * overlay.
     *
     * @attribute button
     * @type Node
     * @default null
     */
    button: {
        value: null
    },

    /**
     * The form that should be submitted once the confirmation has been
     * passed.
     *
     * @attribute form
     * @type Node
     * @default null
     */
    form: {
        value: null
    }


};

Y.extend(ConfirmationOverlay, Y.lazr.FormOverlay, {

    initializer: function(cfg) {
        var submit_button = Y.Node.create(
            '<button type="submit" class="lazr-pos lazr-btn" />')
            .set("text", "OK");
        var cancel_button = Y.Node.create(
            '<button type="button" class="lazr-neg lazr-btn" />')
            .set("text", "Cancel");
        this.set('form_submit_button', submit_button);
        this.set('form_cancel_button', cancel_button);

        var self = this;
        var submit_form = function() {
            self.createHiddenDispatcher();
            self.get('form').submit();
        };
        this.set('form_submit_callback', submit_form);

        this._set('destroy_on_hide', true);

        // Center the overlay in the viewport.
        this.set(
            'align',
            {points: [
              Y.WidgetPositionAlign.CC,
              Y.WidgetPositionAlign.CC]
            });

    },

    createHiddenDispatcher: function() {
        var dispatcher = Y.Node.create('<input>')
            .set('type', 'hidden')
            .set('name', this.get('button').get('name'))
            .set('value', this.get('button').get('value'));
        this.get('form').appendChild(dispatcher);
    }

});

Y.lazr.ConfirmationOverlay = ConfirmationOverlay;

}, "0.1", {"skinnable": true, "requires": ["lazr.formoverlay"]});
