/**
 * Copyright 2011 Canonical Ltd. This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Auto Resizing Textarea Widget.
 *
 * Usage:
 *     Y.one('#myid').plug(ResizingTextarea);
 *     Y.one('#settings').plug(ResizingTextarea, {
 *         min_height: 100
 *     });
 *
 *     Y.all('textarea').plug(ResizingTextarea);
 *
 * @module lp.app.formwidgets
 * @submodule resizing_textarea
 */
YUI.add('lp.app.formwidgets.resizing_textarea', function(Y) {

var module = Y.namespace("lp.app.formwidgets"),
    ResizingTextarea = function(cfg) {
        ResizingTextarea.superclass.constructor.apply(this, arguments);
    };

ResizingTextarea.NAME = "resizing_textarea";
ResizingTextarea.NS = "resizing_textarea";

/**
 * ATTRS you can set on initialization to determine how we size the textarea
 *
 */
ResizingTextarea.ATTRS = {
    /**
     * Min height to allow the textarea to shrink to in px
     *
     * We check if there's a css rule for existing height and make that the min
     * height in case it's there
     *
     * @property min_height
     *
     */
    min_height: {
        value: 10,

        valueFn: function () {
            var target = this.get("host"),
                css_height = target.getStyle('height');

            return css_height !== undefined ?
                       this._clean_size(css_height) : undefined;
        }
    },

    /**
     * Max height to allow the textarea to grow to in px
     *
     * @property max_height
     *
     */
    max_height: {
        value: 450
    },

    /**
     * Should we bypass animating changes in height
     * Mainly used to turn off for testing to prevent needing to set timeouts
     *
     * @property skip_animations
     *
     */
    skip_animations: {value: false}
};

Y.extend(ResizingTextarea, Y.Plugin.Base, {

    // special css we add to clones to make sure they're hidden from view
    CLONE_CSS: {
        position: 'absolute',
        top: -9999,
        left: -9999,
        opacity: 0,
        overflow: 'hidden',
        resize: 'none'
    },

    /**
     * Helper function to turn the string from getComputedStyle to int
     *
     */
    _clean_size: function (val) {
        return parseInt(val.replace('px', ''), 10);
    },

    // used to track if we're growing/shrinking for each event fired
    _prev_scroll_height: 0,

    /**
     * This is the entry point for the event of change
     *
     * Here we update the clone and resize based on the update
     *
     */
    _run_change: function (new_value) {
        // we need to update the clone with the content so it resizes
        this.clone.set('text', new_value);
        this.resize();
    },

    /**
     * Given a node, setup a clone so that we can use it for sizing
     *
     * We need to copy this, move it way off the screen and setup some css we
     * use to make sure that we match the original as best as possible.
     *
     * This clone is then checked for the size to use
     *
     */
    _setup_clone: function (node) {
        var clone = node.cloneNode(true);

        clone.setStyles(this.CLONE_CSS);
        // remove attributes so we don't accidentally grab this node in the
        // future
        clone.removeAttribute('id');
        clone.removeAttribute('name');
        clone.generateID();
        clone.setAttrs({
            'tabIndex': -1,
            'height': 'auto'
        });
        Y.one('body').append(clone);

        return clone;
    },

    /**
     * We need to apply some special css to our target we want to resize
     *
     */
    _setup_css: function () {
        // don't let this text area be resized in the browser, it'll mess with our
        // calcs and we'll be fighting the whole time for the right size
        this.t_area.setStyle('resize', 'none');
        this.t_area.setStyle('overflow', 'hidden');

        // we want to add some animation to our adjusting of the size, using
        // css animation to smooth all height changes
        if (!this.get('skip_animations')) {
            this.t_area.setStyle('transition', 'height 0.3s ease');
            this.t_area.setStyle('-webkit-transition', 'height 0.3s ease');
            this.t_area.setStyle('-moz-transition', 'height 0.3s ease');
        }
    },

    initializer : function(cfg) {
        this.t_area = this.get("host");
        this._setup_css(this.t_area);

        // we need to setup the clone of this node so we can check how big it
        // is, but way off the screen so you don't see it
        this.clone = this._setup_clone(this.t_area);

        // we want to start out saying we're at our minimum size
        this._prev_scroll_height = this.get('min_height');

        // look at adjusting the size on any value change event including
        // pasting and such
        this.t_area.on('valueChange', function(e) {
            this._run_change(e.newVal);
        }, this);


        // initial sizing in case there's existing content to match to
        this.resize();
    },

    /**
     * Adjust the size of the textarea as needed
     *
     * @method resize
     *
     */
    resize: function() {
        var scroll_height = this.clone.get('scrollHeight');

        // only update the height if we've changed
        if (this._prev_scroll_height !== scroll_height) {
            new_height = Math.max(this.get('min_height'),
                             Math.min(scroll_height, this.get('max_height')));

            this.t_area.setStyle('height', new_height);

            // check if the changes above require us to change our overflow setting
            // to allow for a scrollbar now that our max size has been reached
            this.set_overflow();

            this._prev_scroll_height = scroll_height;
        }
    },

    /**
     * Check if we're larger than the max_height setting and enable scrollbar
     *
     * @method set_overflow
     *
     */
    set_overflow: function() {
        var overflow = "hidden";
        if (this.clone.get('scrollHeight') >= this.get('max_height')) {
            overflow = "auto";
        }
        this.t_area.setStyle('overflow', overflow);
    }
});

// add onto the formwidget namespace
module.ResizingTextarea = ResizingTextarea;

}, "0.1", {
    "requires": ["plugin", "node", "event-valuechange"]
});
