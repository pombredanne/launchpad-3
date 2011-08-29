/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI.add('lazr.confirmationoverlay', function(Y) {

/**
 * Display a confirmation overlay before submitting a form.
 *
 * @module lazr.confirmationoverlay
 */


var NAME = 'lazr-confirmationoverlay';

/**
 * The ConfirmationOverlay class builds on the lazr.FormOverlay
 * class.  It 'wraps' itself around a button so that a confirmation
 * pop-up is displayed when the button is clicked to let the user
 * a chance to cancel the form submission.  Note that the button
 * can be simply 'disabled' if it's desirable to prevent the usage
 * of that button if the user's browser has no Javascript support.
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
    },

    /**
     * An optional function (must return a string) that will be run to
     * populate the form_content of the confirmation overlay when it's
     * displayed.  This is useful if the confirmation overlay must displayed
     * information that is only available at form submission time.
     *
     * @attribute form_content_fn
     * @type Function
     * @default null
     *
     */
    form_content_fn: {
        value: null
    },

    /**
     * An optional function (must return a string) that will be run to
     * populate the header_content of the confirmation overlay when it's
     * displayed.  This is useful if the confirmation overlay must displayed
     * information that is only available at form submission time.
     *
     * @attribute header_content_fn
     * @type Function
     * @default null
     *
     */
    header_content_fn: {
        value: null
    },

    /**
     * An optional function (must return a boolean) that will be run to
     * before the confirmation overlay is shown to decide whether it
     * should really be displayed.
     *
     * @attribute display_confirmation_fn
     * @type Function
     * @default null
     *
     */
    display_confirmation_fn: {
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

        this.set('form', this.get('button').ancestor('form'));

        // When ok is clicked, submit the form.
        var self = this;
        var submit_form = function() {
            self._createHiddenDispatcher();
            self.get('form').submit();
        };
        this.set('form_submit_callback', submit_form);

        // Enable the button if it's disabled.
        this.get('button').set('disabled', false);

        // Wire this._handleButtonClicked to the button.
        this.get(
            'button').on('click', Y.bind(this._handleButtonClicked, this));

        // Hide the overlay.
        this.hide();
    },

    /**
     * Prevent form submission and display the confirmation overlay.
     *
     * @method  _handleButtonClicked
     */
     _handleButtonClicked: function(e) {
        var display_confirmation_fn = this.get('display_confirmation_fn');
        if (display_confirmation_fn === null || display_confirmation_fn()) {
            // Stop the event to prevent the form submission.
            e.preventDefault();
            // Update the overlay's content.
            this._fillContent();
            this._positionOverlay();
            // Render and display the overlay.
            this.render();
            this._setFormContent();
            this.show();
        }
    },

    /**
     * Update the header and the content of the overlay.
     *
     * @method  _fillContent
     */
     _fillContent: function() {
        var form_content_fn = this.get('form_content_fn');
        if (form_content_fn !== null) {
            this.set('form_content', form_content_fn());
        }
        var header_content_fn = this.get('header_content_fn');
        if (header_content_fn !== null) {
            this.set('form_header', header_content_fn());
        }
     },


    /**
     * Center the overlay in the viewport.
     *
     * @method  _positionOverlay
     */
     _positionOverlay: function() {
        this.set(
            'align',
            {points: [
              Y.WidgetPositionAlign.CC,
              Y.WidgetPositionAlign.CC]
            });
    },

    /**
     * Create a hidden input to simulate the click on the right
     * button.
     *
     * @method _createHiddenDispatcher
     */
    _createHiddenDispatcher: function() {
        var dispatcher = Y.Node.create('<input>')
            .set('type', 'hidden')
            .set('name', this.get('button').get('name'))
            .set('value', this.get('button').get('value'));
        this.get('form').appendChild(dispatcher);
    }

});

Y.lazr.ConfirmationOverlay = ConfirmationOverlay;

}, "0.1", {"skinnable": true, "requires": ["lazr.formoverlay"]});
