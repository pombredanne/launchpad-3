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

var ns = Y.namespace("lp.app.formwidgets");

var ResizingTextarea = function(cfg) {
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
     * @property min_height
     *
     */
    min_height: {value: null},

    /**
     * Max height to allow the textarea to grow to in px
     *
     * @property max_height
     *
     */
    max_height: {value: null},

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

    // defaults for sizing settings in case they're not supplied
    MIN_HEIGHT: 10,
    MAX_HEIGHT: 450,

    // used to track if we're growing/shrinking for each event fired
    _prev_scroll_height: 0,

    /**
     * If not default height specified, check for html based default height
     *
     * If there's no default passed into the config and no html based default,
     * use our own constants for it
     *
     */
    _set_start_height: function () {
        if (! this.get('min_height')) {
            this.set('min_height',
                     parseInt(this.t_area.getStyle('height'),
                     this.MIN_HEIGHT));
        }

        if (! this.get('max_height')) {
            this.set('max_height', this.MAX_HEIGHT);
        }

        // we want to start out saying we're at our minimum size
        this._prev_scroll_height = this.get('min_height');
    },

    _bind_events: function () {
        // look at adjusting the size on any value change event including
        // pasting and such
        this.t_area.on('valueChange', function(e) {
            // we need to update the clone with the content so it resizes
            this.clone.set('text', e.newVal);
            this.resize();
        }, this);
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
    _setup_css: function (target) {
        // don't let this text area be resized in webkit, it'll mess with our
        // calcs and we'll be fighting the whole time for the right size
        target.setStyle('resize', 'none');
        target.setStyle('overflow', 'hidden');

        // we want to add some animation to our adjusting of the size, using
        // css animation to smooth all height changes
        if (!this.get('skip_animations')) {
            target.setStyle('transition', 'height 0.3s ease');
            target.setStyle('-webkit-transition', 'height 0.3s ease');
            target.setStyle('-moz-transition', 'height 0.3s ease');
        }
    },

    initializer : function(cfg) {
        this.t_area = this.get("host");
        this._setup_css(this.t_area);

        // we need to setup the clone of this node so we can check how big it
        // is, but way off the screen so you don't see it
        this.clone = this._setup_clone(this.t_area);

        this._set_start_height();
        this._bind_events();

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
        // start out just making the hieght the same as the clone's scroll
        // height
        var scroll_height = this.clone.get('scrollHeight');

        if (scroll_height > this._prev_scroll_height &&
            scroll_height > this.get('min_height')) {
            this.t_area.setStyle('height',
                                 Math.min(scroll_height, this.get('max_height')
            ));
        } else if (scroll_height > this.get('max_height')) {
            // a corner case, when we have a lot of text, and we delete some,
            // the scroll height decreases, signalling we should shrink the
            // box, but since we're still larger than the max set...ignore the
            // rule and don't change a thing
        } else {
            this.t_area.setStyle('height',
                                 Math.max(scroll_height, this.get('min_height')
            ));
        }

        // check if the changes above require us to change our overflow setting
        // to allow for a scrollbar now that our max size has been reached
        this.set_overflow();

        this._prev_scroll_height = scroll_height;
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

// add onto the Plugin namespace since this is a YUI Plugin module
ns.ResizingTextarea = ResizingTextarea;

}, "0.1", {
    "requires": ["plugin", "node", "event-valuechange"]
});
