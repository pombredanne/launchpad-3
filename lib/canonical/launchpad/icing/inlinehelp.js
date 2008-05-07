/*
 *  This library depends on the MochiKit JavaScript library v1.6+.
 */


/****  Page Setup  ****/


function initInlineHelp(event) {
    /*
    Activate the popup help system by connecting all of the actionable
    page elements.
    */
    logDebug("Setting up page help system");
    forEach(findHelpLinks(), linkHelpContent);
    initHelpPane();
}

function findHelpLinks() {
    /*
    Return all of the links in the document that have a target="help"
    attribute value.
    */
    has_target = function (e) {
	return MochiKit.DOM.getNodeAttribute(e, 'target') == 'help';
    }
    return filter(
	has_target, MochiKit.DOM.getElementsByTagAndClassName('*', 'inline-help'));
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


function showHelpFor(elem) {
    /*
    Show the help popup for an element.
    */
    var inline_help_content = $('help-content-pane') || logError(
	"OOPS! Couldn't find the main help content pane!");
    var offsite_help_content = $('offsite-help-content') || logError(
	"OOPS! Couldn't find the offsite help content pane!")

    // The element holding out help content.
    var content = $(elem.id + '-content');

    if (content) {
	logDebug("Showing inline help for link: " + elem.id);

	// Populate the help frame as fast as possible.
	inline_help_content.innerHTML = content.innerHTML;

	makeInvisible(offsite_help_content);
	makeVisible(inline_help_content);
    } else {
	// Assume we are using an <iframe> for the help.
	logDebug("Showing offsite help for link: " + elem.id);

	// Assume an <a> tag is the source, and we want to target an
	// <iframe> at it's href.
	MochiKit.DOM.setNodeAttribute(
	    offsite_help_content, 'src', elem.href);

	makeInvisible(inline_help_content);
	makeVisible(offsite_help_content);
    }
    makeVisible($('inline-help-pane'));
}

function dismissHelp() {
    makeInvisible($('inline-help-pane'));
}

function findBestScreenPos() {
    /*
    Find the best position at which we should draw the help popup:
    shifted left or right, towards the top or bottom, and so forth.
    */
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
    } else (trigger != last_help_trigger) {
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
	!isInside(help, event.mouse().client)) {
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
};

function isInside(element, point) {
    pos = getElementPosition(help);
    size = getElementDimensions(help);
    // Are we inside the help window?
    return ((point.x > pos.x) &&
	    (point.x < pos.x + size.w) &&
	    (point.y > pos.y) &&
	    (point.y < pos.y + size.h));
}


MochiKit.Signal.connect(window, 'onload', setupPageHelp);
MochiKit.Signal.connect(window, 'onclick', handleClickOnPage);
