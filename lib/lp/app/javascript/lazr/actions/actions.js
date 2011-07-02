/* Copyright (c) 2009, Canonical Ltd. All rights reserved. */

YUI.add('lazr.actions', function(Y) {

Y.namespace('lazr.actions');

var ACTION = "action",
    ACTIONCLASS = "Action",
    ACTIONS = "actions",
    ACTIONS_HELPER = "ActionsHelper",
    ACTIONS_ID = "actionsId",
    ITEM = "item",
    ITEMCLASSNAME = "itemClassName",
    LABEL = "label",
    LAZR_ACTION_DISABLED = 'lazr-action-disabled',
    LINK = "link",
    LINKCLASSNAME = "linkClassName",
    PERMISSION = "permission",
    RUNNING = "running",
    TITLE = "title";

/*
 * The Actions and ActionsHelper widgets allow for creating arbitrary collections of behavioral
 * links and situating them in DOM elements on the page. In the absence of a label attribute,
 * they can be presented with CSS sprites for graphical representation. When actions are running,
 * they have their primary linkClassName CSS class replaced with lazr-waiting, which can be
 * styled as needed (spinner, hidden, greyed-out, &amp;c). Each action can be governed by a
 * permission, which will fire at the time of rendering and, if failing, decorate the action with
 * the lazr-action-disabled class, which can be styled as needed (hidden, greyed-out, &amp;c).
*/

/*
 * The ActionsHelper widget collects and delegates Action
 * widgets associated with a common Node
 *
 * @class ActionsHelper
 */
var ActionsHelper = function(config) {
    ActionsHelper.superclass.constructor.apply(this, arguments);
};

ActionsHelper.NAME = ACTIONS_HELPER;

ActionsHelper.ATTRS = {
    actions: { valueFn: function() { return []; }},
    actionsId: { valueFn: function() { return Y.guid(); }},
};

Y.extend(ActionsHelper, Y.Base, {
    /**
     * Render actions
     * <p>
     * This method is called to render each of its Actions in turn, in the specified node.
     * </p>
     *
     * @method render
     * @param node {Node} The node that should contain the ActionsHelper
     */
    render: function(node) {
        var doc = Y.config.doc;
        var actions = this.get(ACTIONS);
        var actionsId = this.get(ACTIONS_ID);

        // Check if we already have an instance of the
        // container in the DOM.
        var actionsContainer = Y.one("#" + actionsId);

        if (actionsContainer) {
            // If the container already exists in the DOM,
            // unattach it so that it can be moved to a
            // new parent.
            actionsContainer.remove()
        } else {
            actionsContainer = new Y.Node.create(
                "<ul id='" + actionsId + "' />");
        }
        // If there are no icons to be displayed, don't bother
        // creating the container.
        if (actions.length) {
            // Render each action as a separate item inside
            // the container.
            for (var i=0; i<actions.length; i++){
                var action = actions[i];
                action.render(actionsContainer);
            }
        }

        // Finally, if a container was created or an existing
        // one was found, append it to the Document Fragment
        // for later attachment to the new destination node.
        if (actionsContainer !== null) {
            node.appendChild(Y.Node.getDOMNode(actionsContainer));
        }
    },
});

Y.lazr.actions.ActionsHelper = ActionsHelper;

/**
 * This class provides a self-protecting action, governed by permissions,  attached
 * to a link that can have its style updated when running.
 *
 * @class Action
 * @constructor
 */
var Action = function(config) {
    Action.superclass.constructor.apply(this, arguments);
};

/**
 * Dictionary of selectors to define subparts of the widget that we care about.
 * YUI calls ATTRS.set(foo) for each foo defined here
 *
 * @property Action.NAME
 * @type String
 * @static
 */
Action.NAME = ACTIONCLASS;

Action.ATTRS = {
    /**
     * A function representing the underlying behavior of this action.
     *
     * @attribute action
     * @type Function
     */
    action: {
        value: null
    },

    /**
     * A function which runs at render time, evaluating to true or fase, determining
     * whether or not the action should be disabled.
     *
     * @attribute permission
     * @type Function
     */
    permission: {
        value: null
    },

    /**
     * Optional text label for the Action. If present, it will be the text of the
     * anchor tag
     *
     * @attribute label
     * @type String
     */
    label: {
        value: null
    },

    /**
     * Title attribute of the inner anchor tag
     *
     * @attribute title
     * @type String
     */
    title: {
        value: null
    },

    /**
     * A special CSS class name for the list element of the Action
     *
     * @attribute itemClassName
     * @type String
     */
    itemClassName: {
        value: null
    },

    /**
     * A special CSS class name for the inner anchor element of the Action, will get
     * swapped out with Y.lazr.ui.CSS_WAITING when the action is running.
     *
     * @attribute linkClassName
     * @type String
     */
    linkClassName: {
        value: null
    },

    /**
     * A flag determining whether the current Action is engaged in its action
     *
     * @attribute running
     * @type Boolean
     */
    running: {
        value: false,
        setter: function(v) { return this._updateRunState(v); },
        getter: function(v) { return v; }
    },

    /**
     * A list element, decorated with our CSS class and with our link attached.
     *
     * @attribute item
     * @type Node
     */
    item: {
        valueFn: function() { return this._createItem(); }
    },

    /**
     * An anchor element, decorated with our CSS class and with our behavior attached.
     *
     * @attribute link
     * @type Node
     */
    link: {
        valueFn: function() { return this._createLink(); }
    }

};

Y.extend(Action, Y.Base, {

    /**
     * Helper method to toggle the CSS_WAITING class on the link element
     *
     * @method
     * @private
     */
    _updateRunState: function(isRunning) {
        // when we get set to true:
        //   - turn our icon to a spinner, if appropriate
        if (this.get(LINKCLASSNAME) !== null) {
            if (isRunning) {
                this.get(LINK).replaceClass(
                    this.get(LINKCLASSNAME),
                    Y.lazr.ui.CSS_WAITING);
            } else {
                this.get(LINK).replaceClass(
                    Y.lazr.ui.CSS_WAITING,
                    this.get(LINKCLASSNAME));
            }
        }
        return isRunning;
    },

    /**
     * Helper method to create the link element, and perform initial decoration
     *
     * @method
     * @private
     */
    _createLink: function() {
        var label = this.get(LABEL);
        var title = this.get(TITLE);
        var linkClassName = this.get(LINKCLASSNAME);
        var link = Y.Node.create(
        "<a href='#' alt='" + title +
            "' title='" + title + "'></a>");
        link.on("click", this.actionRunner, this);

        if (label !== null) {
            link.append(Y.Node.create(label));
        }

        if (linkClassName !== null) {
            link.addClass(linkClassName);
        }

        return link;
    },

    /**
     * Helper method to create the list item element, and perform initial decoration
     *
     * @method
     * @private
     */
    _createItem: function() {
        var itemClassName = this.get(ITEMCLASSNAME);
        var link = this.get(LINK);
        var item = Y.Node.create('<li/>'); 

        if (itemClassName !== null) {
            item.addClass(itemClassName);
        }

        item.append(link);

        return item;
    },

    /**
     * Render the action and attach it to a node
     *
     * @method render
     */
    render: function(node) {
        // Build the link, labeling it if necessary
        // Compose the item, decorating it if necessary
        var item = this.get(ITEM);
        var permission = this.get(PERMISSION);

        if (permission && !permission()) {
            item.addClass(LAZR_ACTION_DISABLED);
        } else {
            item.removeClass(LAZR_ACTION_DISABLED);
        }

        // Place the item
        node.append(item);
    },

    /**
     * Wrap the actual function so that it short-circuits if the action is currently
     * running
     *
     * @method actionRunner
     */
    actionRunner: function() {
        if (!this.get(RUNNING)) {
            // Not running, fire.
            this.get(ACTION)();
        }
    }
});

Y.lazr.actions.Action = Action;

}, "0.1.", {"requires": ["oop", "base", "node", "lazr.base"]});
