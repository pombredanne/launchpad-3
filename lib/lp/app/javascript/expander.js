/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Expander widget.  Can be used to let the user toggle the visibility of
 * existing elements on the page, or to make the page load elements on demand
 * as the user expands them.
 *
 * Synonyms: collapsible, foldable.
 *
 * Each expander needs two tags as "connection points":
 *  * Icon tag, to be marked up with the expander icon.
 *  * Content tag, to be exposed by the expander.
 *
 * Either may have initial contents.  The initial contents of the icon tag
 * stays in place, so it could say something like "Details..." that explains
 * what the icon means.  You'll want to hide it using the "unseen" class if
 * these contents should only be shown once the expander has been set up.
 *
 * Any initial contents of the content tag will be revealed when the expander
 * is opened; hide them using the "unseen" class if they should not be shown
 * when the expander has not been enabled.  An optional loader function may
 * produce new contents for this tag when the user first opens the expander.
 *
 * If you provide a loader function, the expander runs it when the user first
 * opens it.  The loader should produce a DOM node or node list(it may do this
 * asynchronously) and feed that back to the expander by passing it to the
 * expander's "receive" method.  The loader gets a reference to the expander
 * as its first argument.
 *
 * The expander is set up in its collapsed state by default.  If you want it
 * created in its expanded state instead, mark your content tag with the
 * "expanded" class.
 *
 * @module lp.app.widgets.expander
 * @requires node, event
 */

YUI.add('lp.app.widgets.expander', function(Y) {

var namespace = Y.namespace('lp.app.widgets.expander');

function getAnim(node) {
    var slide_effect_defaults = {
        easing: Y.Easing.easeOut,
        duration: 0.4
    };
    var OPENED = 'lazr-opened';
    var CLOSED = 'lazr-closed';

    var cfg = slide_effect_defaults;
    cfg.node = node;
    var node = Y.one(node);

    var default_to_height = function(node) {
        return node.get('scrollHeight');
    };

    // We don't want to stomp on what the user may have given as the
    // from.height and to.height;
    cfg.from        = cfg.from ? cfg.from : {};
    cfg.from.height = cfg.from.height ? cfg.from.height : 0;

    cfg.to          = cfg.to ? cfg.to : {};
    cfg.to.height   = cfg.to.height ? cfg.to.height : default_to_height;

    var anim = new Y.Anim(cfg);
    node.addClass(OPENED);

    // Set what we need to calculate the new content's scrollHeight.
    node.setStyles({
        height:   cfg.from.height,
        overflow: 'hidden'//,
        //display:  'block'
    });
    anim.drawer_closed = false;

    anim.on('directionChange', function() {
        node.getStyle('height');

        if (this.drawer_closed) {
            // We've finished opening the drawer, so show the overflow, just
            // to be safe.
            this.drawer_closed = false;
            node.addClass(OPENED).removeClass(CLOSED);
        } else {
            this.drawer_closed = true;
            node.addClass(CLOSED).removeClass(OPENED);
        }
    });

    anim.on('end', function() {
        if (this.drawer_closed) {
            // We've finished opening the drawer, so show the overflow, just
            // to be safe.
            this.drawer_closed = false;
            node.addClass(OPENED).removeClass(CLOSED);
        } else {
            this.drawer_closed = true;
            node.addClass(CLOSED).removeClass(OPENED);
        }
    });
    return anim;
}

/*
 * Create an expander.
 *
 * @param icon_node Node to serve as connection point for the expander icon.
 * @param content_node Node to serve as connection point for expander content.
 * @param config Object with additional parameters.
 *     loader: A function that will produce a Node or NodeList to replace the
 *         contents of the content tag.  Receives the Expander object
 *         "expander" as its argument.  Once the loader has constructed the
 *         output Node or NodeList it wants to display ("output"), it calls
 *         expander.receive(output) to update the content node.
 */
function Expander(icon_node, content_node, config) {
    if (!Y.Lang.isObject(icon_node)) {
        throw new Error("No icon node given.");
    }
    if (!Y.Lang.isObject(content_node)) {
        throw new Error("No content node given.");
    }
    this.icon_node = icon_node;
    this.content_node = content_node;
    if (Y.Lang.isValue(config)) {
        this.config = config;
    } else {
        this.config = {};
    }
    this.loaded = !Y.Lang.isValue(this.config.loader);
    this._animation = getAnim(this.content_node);
        //new Y.lazr.effects.slide_out(this.content_node);

    // Is setup complete?  Skip any animations until it is.
    this.fully_set_up = false;
}
namespace.Expander = Expander;

namespace.Expander.prototype = {
    /*
     * CSS classes.
     */
    css_classes: {
        expanded: 'expanded',
        unseen: 'unseen'
    },

    /*
     * Return sprite name for given expander state.
     */
    nameSprite: function(expanded) {
        if (expanded) {
            return 'treeExpanded';
        } else {
            return 'treeCollapsed';
        }
    },

    /*
     * Is the content node currently expanded?
     */
    isExpanded: function() {
        var node;
        if (this.content_node instanceof Y.NodeList) {
            node = this.content_node.item(0);
        } else {
            node = this.content_node;
        }
        return node.hasClass(this.css_classes.expanded);
    },

    /*
     * Either add or remove given CSS class from the content tag.
     *
     * @param want_class Whether this class is desired for the content tag.
     *     If it is, then the function may need to add it; if it isn't, then
     *     the function may need to remove it.
     * @param class_name CSS class name.
     */
    setContentClassIf: function(want_class, class_name) {
        if (want_class) {
            this.content_node.addClass(class_name);
        } else {
            this.content_node.removeClass(class_name);
        }
    },

    /*
     * Record the expanded/collapsed state of the content tag.
     */
    setExpanded: function(is_expanded) {
        this.setContentClassIf(is_expanded, this.css_classes.expanded);
    },

    /*
     * Hide or reveal the content node (by adding the "unseen" class to it).
     *
     * @param expand Are we expanding?  If not, we must be collapsing.
     */
    foldContentNode: function(expand, no_animation) {
        var expander = this;
        var has_paused = false;
        if (no_animation === true) {
            expander.setContentClassIf(
                !expand, expander.css_classes.unseen);
            return;
        }
        if (this._animation.get('running')) {
            this._animation.pause();
            has_paused = true;
            if (expand) {
                this._animation.set(
                    'to', { height: this.content_node.get('height') });
            } else {
                this._animation.set(
                    'from', { height: this.content_node.get('height') });
            }
        } else {
            this._animation.set(
                'to', { height: this.content_node.get('scrollHeight') });
            this._animation.set(
                'from', { height: 0 });

        }
        this._animation.set('reverse', !expand);
        if (expand) {
            expander.setContentClassIf(
                !expand, expander.css_classes.unseen);
        } else {
            this._animation.on('end', function() {
                expander.setContentClassIf(
                    !expand, expander.css_classes.unseen);
            });
        }
        // For demonstration purposes, we wait before continuing an
        // animation when it was paused.
        if (has_paused) {
            setTimeout(function() {
                expander._animation.run();
            }, 500);
        } else {
            expander._animation.run();
        }
    },

    revealIcon: function() {
        this.icon_node
            .addClass('sprite').addClass('js-action')
            .removeClass('unseen');
    },

    /*
     * Set icon to either the "expanded" or the "collapsed" state.
     *
     * @param expand Are we expanding?  If not, we must be collapsing.
     */
    setIcon: function(expand) {
        this.icon_node
            .removeClass(this.nameSprite(!expand))
            .addClass(this.nameSprite(expand));
    },

    /*
     * Process the output node being produced by the loader.  To be invoked
     * by a custom loader when it's done.
     *
     * @param output A Node or NodeList to replace the contents of the content
     *     tag with.
     */
    receive: function(output) {
        // We'll animate this later (if this.fully_set_up is false).
        var from_height = this.content_node.get('height');
        this.content_node.setContent(output);
        var to_height = this.content_node.get('scrollHeight');

        if (this._animation.get('running')) {
            // chain the animations?
            this._animation.stop();
        }
        this._animation.set('to', { height: to_height });
        this._animation.set('from', { height: from_height });
        this._animation.run();
    },

    /*
     * Invoke the loader, and record the fact that the loader has been
     * started.
     */
    load: function() {
        this.loaded = true;
        this.config.loader(this);
    },

    /*
     * Set the expander's DOM elements to a consistent, operational state.
     *
     * @param expanded Whether the expander is to be rendered in its expanded
     *     state.  If not, it must be in the collapsed state.
     */
    render: function(expanded, no_animation) {
        this.foldContentNode(expanded, no_animation);
        this.setIcon(expanded);
        if (expanded && !this.loaded) {
            this.load();
        }
        this.setExpanded(expanded);
    },

    /*
     * Set up an expander's DOM and event handler.
     *
     */
    setUp: function() {
        var expander = this;
        function click_handler(e) {
            e.halt();
            expander.render(!expander.isExpanded());
        }

        this.render(this.isExpanded(), true);
        this.icon_node.on('click', click_handler);
        this.revealIcon();
        this.fully_set_up = true;
        return this;
    }
};

/*
 * Initialize expanders based on CSS selectors.
 *
 * @param widget_select CSS selector to specify each tag that will have an
 *     expander created inside it.
 * @param icon_select CSS selector for the icon tag inside each tag matched
 *     by widget_select.
 * @param content_select CSS selector for the content tag inside each tag
 *     matched by widget_select.
 * @param loader Optional loader function for each expander that is set up.
 *     Must take an Expander as its argument, create a Node or NodeList with
 *     the output to be displayed, and feed the output to the expander's
 *     "receive" method.
 */
function createByCSS(widget_select, icon_select, content_select, loader) {
    var config = {
        loader: loader
    };
    var expander_factory = function(widget) {
        var expander = new Expander(
            widget.one(icon_select), widget.one(content_select), config);
        expander.setUp();
    };
    Y.all(widget_select).each(expander_factory);
}
namespace.createByCSS = createByCSS;

}, "0.1", {"requires": ["node", "lazr.effects"]});
