/*
 * Copyright 2008, Canonical Ltd.  All rights reserved.
 *
 * This script defines functions for popping up a 'Help' dialog for an
 * external site.  All links that have a 'target="help"' attribute will
 * be turned into pop-up help links.  A single popup is present on the
 * screen at a time - opening another help link will open a new dialog,
 * and clicking on the same link again closes the dialog.
 *
 * This library depends on the MochiKit JavaScript library v1.4+.
 *
 */


/*
 * Page Setup
 */


function initInlineHelp() {
    /*
      Activate the popup help system by connecting all of the actionable
      page elements.
    */
    forEach(findHelpLinks(), setupHelpTrigger);
    initHelpPane();
}

function findHelpLinks() {
    /*
      Return all of the links in the document that have a target="help"
      attribute value.
    */
    has_help_target = function (elem) {
        return getNodeAttribute(elem, 'target') == 'help';
    };
    return filter(has_help_target,
                  currentDocument().getElementsByTagName('a'));
}

function setupHelpTrigger(elem) {
    /*
      Turn the specified element into a proper help link: add the
      'class="help"' attribute if it is missing, and connect the
      necessary event handlers.
    */
    addElementClass(elem, 'help');
    connect(elem, 'onclick', handleClickOnHelp);
}


/*
 * Functions for using the help window.
 */


// We need to keep track of last element that triggered a help window.
var last_help_trigger = null;


function initHelpPane() {
    /*
      Link the popup help pane to its events, set its visibility, etc.
    */
    connect('help-close-btn', 'onclick', dismissHelp);
    dismissHelp();
}

function showHelpFor(trigger) {
    /*
      Show the help popup for a particular trigger element.
    */

    // Assume we are using an <iframe> for the help.
    // Also assume an <a> tag is the source, and we want to target the
    // <iframe> at its href.

    // Let our "Loading..." background gif show through.
    makeInvisible('help-pane-content');

    // Set our 'onload' event handler *outside* of the MochiKit.Signal
    // framework.  Normally we should not do this, but we need
    // to work around a bug where the 'onload' signal falls silent
    // for all events after the first.
    $('help-pane-content').onload = handleHelpLoaded;

    setNodeAttribute('help-pane-content', 'src', trigger.href);

    var help_pane = $('help-pane');
    setElementPosition(help_pane, findBestScreenPos(help_pane, trigger));
    makeVisible(help_pane);

    // XXX mars 2008-05-19
    // Work-around for MochiKit bug #274.  The previous call to
    // setElementPosition() sets "style=none;" as a side-effect!!!
    setStyle(help_pane, {'display': ''});
}

function dismissHelp() {
    makeInvisible('help-pane');
}

function findBestScreenPos(help_pane, trigger) {
    /*
      Find the best position at which we should draw the help popup,
      and return the Coordinates at which we should place it.

      We will put the help pane towards the center of the screen.  So
      a link clicked in the top-right corner will result in the pane
      appearing a little to the left, and a little below.

      We also try to avoid clipping the pane by having portions
      outside of the current viewport.
    */
    var viewport_pos = getViewportPosition();
    var viewport_dim = getViewportDimensions();
    var viewport_x_mid = Math.round(viewport_pos.x / 2);
    var viewport_y_mid = Math.round(viewport_pos.y / 2);
    var trigger_pos = getElementPosition(trigger);
    var trigger_dim = getElementDimensions(trigger);

    // Fake some dimensions to use while positioning the help pane.
    // This is needed because you can't take the coordinates of an
    // un-displayed element.
    var helppane_dim = getElementDimensions('help-pane');
    if ((helppane_dim.w == 0) || (helppane_dim.h == 0)) {
        logError(
            "Invalid help panel dimensions!  => " + helppane_dim);
    }

    var left_bias = trigger_pos.x < viewport_x_mid;
    var top_bias = trigger_pos.y < viewport_y_mid;

    // Try to move "X" pixels away from the trigger.
    var desired_distance = 50;

    var new_x = null;
    var new_y = null;

    if (left_bias && top_bias) {
        // Top left corner.
        new_x = trigger_pos.x + trigger_dim.x + desired_distance;
        new_y = trigger_pos.y + trigger_dim.y + desired_distance;
    } else if (!left_bias && top_bias) {
        // Top right corner.
        new_x = trigger_pos.x - desired_distance;
        new_y = trigger_pos.y + trigger_dim.y + desired_distance;
    } else if (!left_bias && !top_bias) {
        // Bottom right corner.
        new_x = trigger_pos.x - desired_distance - helppane_dim.w;
        new_y = trigger_pos.y - desired_distance;
    } else if (left_bias && !top_bias) {
        // Bottom left corner.
        new_x = trigger_pos.x + trigger_dim.x + desired_distance;
        new_y = trigger_pos.y - desired_distance - helppane_dim.h;
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

    return new Coordinates(new_x, new_y);
}


function handleClickOnHelp(event) {
    // We don't want <a> tags to navigate.
    event.stop();
    var trigger = event.src();

    if (!isVisible('help-pane')) {
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

function handleHelpLoaded(event) {
    /*
      Show the help contents after the help <iframe> has finished
      loading.
    */
    makeVisible('help-pane-content');
}

function handleClickOnPage(event) {
    /*
      Check to see if a click was inside a help window.  If it wasn't,
      and the window is open, then dismiss it.
    */
    var help = $('help-pane');
    if (isVisible(help) &&
        !isInside(event.mouse().page, help)) {
        dismissHelp();
    }
}


/*
 * Helpers and utility functions.
 */


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
    // You may also want to check for
    // getElement(elem).style.display == "none"
    return !hasElementClass(elem, "invisible");
}

function isInside(point, element) {
    /*
      Is 'point' inside the supplied 'element'?
    */
    return intersect(point,
		     getElementPosition(element),
		     getElementDimensions(element));
}

function intersect(point, dim_point, dimensions) {
    /*
      Is 'point' inside the box draw by 'dimensions' at point 'dim_point'?
    */
    return ((point.x > dim_point.x) &&
            (point.x < dim_point.x + dimensions.w) &&
            (point.y > dim_point.y) &&
            (point.y < dim_point.y + dimensions.h));
}

// Hook up the function that dismisses the help window if we click
// anywhere outside of it.
connect(window, 'onclick', handleClickOnPage);
