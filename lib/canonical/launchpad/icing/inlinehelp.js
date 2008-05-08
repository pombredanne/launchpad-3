/*
 *  This library depends on the MochiKit JavaScript library v1.6+.
 */


/****  Page Setup  ****/


function initInlineHelp() {
    /*
    Activate the popup help system by connecting all of the actionable
    page elements.
    */
    forEach(findHelpLinks(), linkHelpContent);
    initHelpPane();
}

function findHelpLinks() {
    /*
    Return all of the links in the document that have a target="help"
    attribute value.
    */
    has_target = function (elem) {
	return MochiKit.DOM.getNodeAttribute(elem, 'target') == 'help';
    }
    return filter(
	has_target,
	MochiKit.DOM.getElementsByTagAndClassName('*', 'inline-help'));
}

function linkHelpContent(elem) {
    /*
    Link an element to it's associated help content.
    */
    MochiKit.Signal.connect(elem, 'onclick', handleClickOnHelp);
}


/****  Functions for using the help window.  ****/


var last_help_trigger = null;  // The last element to trigger a help window.

function initHelpPane() {
    MochiKit.Signal.connect($('help-close-btn'), 'onclick', dismissHelp);
    dismissHelp();
}

function showHelpFor(trigger) {
    /*
    Show the help popup for an element.
    */
    var inline_help_content = $('help-content-pane')
    var offsite_help_content = $('offsite-help-content')

    // The element holding out help content.
    var content = findHelpForTrigger(trigger);

    if (content) {
	// Populate the help frame as fast as possible.
	inline_help_content.innerHTML = content.innerHTML;

	makeInvisible(offsite_help_content);
	makeVisible(inline_help_content);
    } else {
	// Assume we are using an <iframe> for the help.
	// Also assume an <a> tag is the source, and we want to target the
	// <iframe> at it's href.
	logDebug("Showing offsite help popup for " + trigger.href);
	MochiKit.DOM.setNodeAttribute(
	    offsite_help_content, 'src', trigger.href);

	makeInvisible(inline_help_content);
	makeVisible(offsite_help_content);
    }

    var help_pane = $('inline-help-pane');
    setElementPosition(help_pane, findBestScreenPos(help_pane, trigger));
    makeVisible(help_pane);
}

function findHelpForTrigger(trigger) {
    return $(trigger.id + '-content');
}

function dismissHelp() {
    makeInvisible($('inline-help-pane'));
}

function findBestScreenPos(help_pane, trigger) {
    /*
    Find the best position at which we should draw the help popup:
    shifted left or right, towards the top or bottom, and so forth.
    */
    var viewport_pos = getViewportPosition();
    var viewport_dim = getViewportDimensions();
    var viewport_x_mid = Math.round(viewport_pos.x / 2);
    var viewport_y_mid = Math.round(viewport_pos.y / 2);
    var trigger_pos = getElementPosition(trigger);
    var trigger_dim = getElementDimensions(trigger);

    // Fake some dimensions to use while positioning the help pane.
    // This is needed because you can't take the corrdinates of an
    // un-displayed element.
    var helppane_dim = new Dimensions(300, 200);
    logDebug("Help popup dimensions: " + helppane_dim);

    var left_bias = trigger_pos.x < viewport_x_mid;
    var top_bias = trigger_pos.y < viewport_y_mid;

    // Try to move "X" pixels away from the trigger.
    var desired_distance = 50;

    if (left_bias && top_bias) {
	// Top left corner.
	var new_x = trigger_pos.x + trigger_dim.x + desired_distance;
	var new_y = trigger_pos.y + trigger_dim.y + desired_distance;
    } else if (!left_bias && top_bias) {
	// Top right corner.
	var new_x = trigger_pos.x - desired_distance;
	var new_y = trigger_pos.y + trigger_dim.y + desired_distance;
    } else if (!left_bias && !top_bias) {
	// Bottom right corner.
	var new_x = trigger_pos.x - desired_distance - helppane_dim.w;
	var new_y = trigger_pos.y - desired_distance;
    } else if (left_bias && !top_bias) {
	// Bottom left corner.
	var new_x = trigger_pos.x + trigger_dim.x + desired_distance;
	var new_y = trigger_pos.y - desired_distance - helppane_dim.h;
    }

    // Try to be 30px away from the screen edges.
    var edge_padding = 30;
    var min_pt = new Coordinates(
	viewport_pos.x + edge_padding,
	viewport_pos.y + edge_padding);
    var max_pt = new Coordinates(
	viewport_pos.x + viewport_dim.w - edge_padding,
	viewport_pos.y + viewport_dim.h - edge_padding);

    if (new_x < min_pt.x) {
	// Too far left.
	new_x = min_pt.x + edge_padding;
    } else if (new_x + helppane_dim.w > max_pt.x) {
	// Too far right.
	new_x = max_pt.x - helppane_dim.w;
    }
    if (new_y < min_pt.y) {
	// Too far up.
	new_y = min_pt.y + edge_padding;
    } else if (new_y + helppane_dim.h > max_pt.y) {
	// Too far down.
	new_y = max_pt.y - helppane_dim.h;
	// But not too far up.
	if (new_y < min_pt.y) {
	    new_y = min_pt.y + edge_padding;
	}
    }

    logDebug("Showing help popup at position: " + new_x + ", " + new_y);
    return new Coordinates(new_x, new_y);
}


function handleClickOnHelp(event) {
    event.stop(); // We don't want <a> tags to navigate.
    var trigger = event.src();
    var help = $('inline-help-pane');

    if (!isVisible(help)) {
	showHelpFor(trigger);
    } else if (trigger == last_help_trigger) {
	// Clicking on the same link that opened a help window closes it
	// again.
	dismissHelp();
    } else {
	// The user clicked on a different help link, so open it instead.
	dismissHelp();
	showHelpFor(trigger);
    }
    last_help_trigger = trigger;
}

function handleClickOnPage(event) {
    /*
    Check to see if a click was inside a help window.  If it wasn't,
    and the window is open, then dismiss it.
    */
    var help = $('inline-help-pane');
    var src = event.src();
    if ((src != help) &&
	isVisible(help) &&
	!isInside(event.mouse().client, help)) {
	dismissHelp();
    }
}


/****  Helpers and utility functions. ****/


function toggleVisible(elem) {
    toggleElementClass("invisible", elem);
}

function makeVisible(elem) {
    removeElementClass(elem, "invisible");
}

function makeInvisible(elem) {
    addElementClass(elem, "invisible");
}

function isVisible(elem) {
    // you may also want to check for
    // getElement(elem).style.display == "none"
    return !hasElementClass(elem, "invisible");
}

function isInside(point, element) {
    // Is `point' inside the supplied `element'?
    return intersect(point,
		     getElementPosition(element),
		     getElementDimensions(element));
}

function intersect(point, dim_point, dimensions) {
    // Is `point' inside the box draw by `dimensions' at point `dim_point'?
    return ((point.x > dim_point.x) &&
	    (point.x < dim_point.x + dimensions.w) &&
	    (point.y > dim_point.y) &&
	    (point.y < dim_point.y + dimensions.h));
}


MochiKit.Signal.connect(window, 'onclick', handleClickOnPage);
