/*
 * Copyright 2009 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
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
    // The button is inserted in the page dynamically:
    // Changed from an <input type=button> to a <button> since
    // IE8 doesn't handle style.css's input{visibility:inherit} correctly.
    $('help-close').innerHTML =
        '<button id="help-close-btn">Close</button>';
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
    // We want this to be idempotent, so we treat the 'help' class as a
    // marker.
    if (!hasElementClass(elem, 'help')) {
        addElementClass(elem, 'help');
        connect(elem, 'onclick', handleClickOnHelp);
    }
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
    connect('help-close-btn', 'onclick', handleClickOnClose);
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

    /* The help pane is positioned in the center of the screen: */
    var viewport_dim = getViewportDimensions();
    var help_pane_dim = elementDimensions('help-pane');
    var pos_x = Math.round(viewport_dim.w / 2) - (help_pane_dim.w / 2);
    var pos_y = Math.round(viewport_dim.h / 2) - (help_pane_dim.h / 2);
    var viewport_pos = getViewportPosition();
    pos_y += viewport_pos.y;
    setElementPosition(help_pane, new Coordinates(pos_x, pos_y));
    makeVisible(help_pane);

    // XXX mars 2008-05-19
    // Work-around for MochiKit bug #274.  The previous call to
    // setElementPosition() sets "style=none;" as a side-effect!!!
    setStyle(help_pane, {'display': ''});
}

function dismissHelp() {
    makeInvisible('help-pane');
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

function handleClickOnClose(event) {
    // Prevent the <a> tag from navigating.
    event.stop();
    dismissHelp();
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
    // You may also want to check for:
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
