/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Handling of form overlay widgets for bug pages.
 *
 * @module DupeFinder
 * @requires base, node
 */
YUI.add('bugs.dupe_finder', function(Y) {

var BLOCK = 'block',
    DISPLAY = 'display',
    EXPANDER_COLLAPSED = '/@@/treeCollapsed',
    EXPANDER_EXPANDED = '/@@/treeExpanded',
    NONE = 'none',
    SRC = 'src';

var bugs = Y.namespace('bugs');

/*
 * The NodeList of possible duplicates.
 */
var bug_already_reported_expanders;
/*
 * The HTML for the spinner animation.
 */
var spinner_html;
/*
 * The search field on the +filebug form
 */
var search_field;
/*
 * The search button on the +filebug form
 */
var search_button;
/*
 * The boilerplate elements for the do-you-want-to-subscribe
 * FormOverlay.
 */
var submit_button_html =
    '<button type="submit" name="field.actions.this_is_my_bug" ' +
    'value="Yes, this is the bug I\'m trying to report"' +
    'class="lazr-pos lazr-btn" >OK</button>';
var cancel_button_html =
    '<button type="button" name="field.actions.cancel" ' +
    'class="lazr-neg lazr-btn" >Cancel</button>';

/**
 * Return the relevant duplicate-details div for a bug-already-reported
 * expander.
 * @param expander The expander for which to return the relevant div.
 */
function get_details_div(expander) {
    var details_div = expander.get(
        'parentNode').get('parentNode').query('.duplicate-details');

    // Check that the details_div actually exists and raise an error if
    // we can't find it.
    if (details_div === null) {
        Y.fail(
            "Unable to find details div for expander " + expander.get('id'));
    } else {
        return details_div;
    }
}

/**
 * Show or hide a duplicate DIV based on whether it is currently
 * displayed or hidden.
 * @param e The Event that's triggering the toggle.
 */
function toggle_bug_details(e) {
    // Toggle the expander that's being clicked. We have to use the
    // display attribute of the associated details div because the SRC
    // attribute of the image changes depending on what host we're on
    // (i.e. production or edge).
    var image = e.target;
    var bug_details_div = get_details_div(image);

    if (bug_details_div.getStyle(DISPLAY) == BLOCK) {
        collapse_bug_details(image);
    } else {
        image.set(SRC, EXPANDER_EXPANDED);
        bug_details_div.setStyle(DISPLAY, BLOCK);
    }

    // If the bug reporting form is shown, hide it.
    var bug_reporting_form = Y.get('#bug_reporting_form');
    if (bug_reporting_form !== undefined && bug_reporting_form !== null &&
        bug_reporting_form.getStyle(DISPLAY) == BLOCK) {
        bug_reporting_form.setStyle(DISPLAY, NONE);
    }
}

/**
 * Collapse the details for a bug and set its expander arrow to
 * 'collapsed'
 * @param expander The expander to collapse.
 */
function collapse_bug_details(expander) {
    var bug_details_div = get_details_div(expander);
    bug_details_div.setStyle(DISPLAY, NONE);

    expander.set(SRC, EXPANDER_COLLAPSED);
}

/**
 * Show the bug reporting form and collapse all bug details forms.
 * @param e The Event triggering this function.
 */
function show_bug_reporting_form(e) {
    // Collapse all the duplicate-details divs.
    Y.each(bug_already_reported_expanders, function(expander) {
        collapse_bug_details(expander);
    });

    // Show the bug reporting form.
    var bug_reporting_form = Y.get('#bug_reporting_form');
    bug_reporting_form.setStyle(DISPLAY, BLOCK);
    Y.get(Y.DOM.byId('field.actions.submit_bug')).focus();
    window.location.href = '#form-start';

    // Focus the relevant elements of the form based on
    // whether the package drop-down is displayed.
    var bugtarget_package_btn = Y.get(
        Y.DOM.byId('field.bugtarget.option.package'));
    if (bugtarget_package_btn !== null &&
        bugtarget_package_btn !== undefined) {
        Y.get(Y.DOM.byId('field.bugtarget.package')).focus();
    } else {
        Y.get(Y.DOM.byId('field.comment')).focus();
    }
}

/**
 * Search for bugs that may match the text that the user has entered and
 * display them in-line.
 */
function search_for_and_display_dupes() {
    function show_failure_message() {
        Y.get('#possible-duplicates').set('innerHTML', 'FAIL');
    }

    function on_success(transaction_id, response, arguments) {
        var duplicate_div = Y.get('#possible-duplicates');
        duplicate_div.set('innerHTML', response.responseText);

        // Set up the JavaScript of the duplicates that have been
        // returned.
        set_up_inline_duplicates();

        // Copy the value from the search field into the title field
        // on the filebug form.
        Y.get(Y.DOM.byId('field.title')).set(
            'value', search_field.get('value'))

        // Finally, change the label on the search button.
        search_button.set('value', 'Search again');
    }

    var search_term = encodeURI(search_field.get('value'));
    var search_url_base = Y.get(
        '#duplicate-search-url').getAttribute('href');
    var search_url = search_url_base + '?title=' + search_term;

    Y.get('#possible-duplicates').set('innerHTML', spinner_html);
    Y.get('#possible-duplicates').setStyle('display', 'block');

    config = {on: {success: on_success,
                   failure: show_failure_message}}
    Y.io(search_url, config);
}

/**
 * Set up the inline duplicates so that their JavaScript-powered
 * elements work correctly.
 */
function set_up_inline_duplicates() {
    bug_already_reported_expanders = Y.all(
        'img.bug-already-reported-expander');
    var bug_reporting_form = Y.get('#bug_reporting_form');

    if (bug_already_reported_expanders !== null &&
        bug_already_reported_expanders !== undefined) {
        // Collapse all the details divs, since we don't want them
        // expanded first up.
        Y.each(Y.all('div.duplicate-details'), function(div) {
            div.setStyle(DISPLAY, NONE);
        });

        // Set up the onclick handlers for the expanders.
        Y.each(bug_already_reported_expanders, function(expander) {
            expander.on('click', toggle_bug_details);
        });

        // Hide the bug reporting form and activate the collapsible
        // "Extra options" section.
        if (bug_reporting_form !== undefined &&
            bug_reporting_form !== null) {
            bug_reporting_form.setStyle(DISPLAY, NONE);
            activateCollapsibles();
        }
    }

    bug_not_reported_button = Y.get('#bug-not-already-reported');
    if (bug_not_reported_button !== null &&
        bug_not_reported_button !== undefined) {
        // The bug_not_reported_button won't show up if there aren't any
        // possible duplicates.
        bug_not_reported_button.on('click', show_bug_reporting_form);
    }

    // Attach the form overlay to the "Yes, this is my bug" forms.
    var this_is_my_bug_forms = Y.all('form.this-is-my-bug-form');
    Y.each(this_is_my_bug_forms, function(form) {
        var subscribe_form_overlay = create_subscribe_overlay(form);

        form.on('submit', function(e) {
            // We don't care about the original event, so stop it
            // and show the form overlay that we just created.
            e.halt();
            subscribe_form_overlay.show();
        });
    });

}


/*
 * Create the overlay for a user to optionally subscribe to a bug that
 * affects them.
 * @param form The form to which the FormOverlay is going to be
 *             attached.
 */
function create_subscribe_overlay(form) {
    // Grab the bug id and title from the "Yes, this is my bug" form.
    var bug_id = form.query(
        'input.bug-already-reported-as').get('value');
    var bug_title = Y.get('#bug-' + bug_id + '-title').get('innerHTML');

    if (bug_title.length > 35) {
        // Truncate the bug title if it's more than 35 characters long.
        bug_title = bug_title.substring(0, 35) + '...';
    }

    // Escape things for the sake of belt-and-braces (suspenders if
    // you're of a North-American persuasion).
    bug_id = escape(bug_id);
    bug_title = escape(bug_title);

    // Construct the form. This is a bit hackish but it saves us from
    // having to try to get information from TAL into JavaScript and all
    // the horror that entails.
    var subscribe_form_body =
        '<div style="width: 320px">' +
        '    <p style="width: 100%">#' + bug_id + ' "' + bug_title + '"' +
        '    <br /><br /></p>' +
        '    <p style="font-weight: bold;">' +
        '       <input type="hidden" name="field.bug_already_reported_as" ' +
        '           value="' + bug_id + '" /> ' +
        '       <input type="radio" name="field.subscribe_to_existing_bug" ' +
        '           id="dont-subscribe-to-bug-' + bug_id + '" value="no" ' +
        '           class="subscribe-option" checked="true" /> ' +
        '       <label for="dont-subscribe-to-bug-' + bug_id + '"> ' +
        '         Just mark the bug as affecting me' +
        '       </label>' +
        '    </p>' +
        '    <p>' +
        '       <input type="radio" name="field.subscribe_to_existing_bug" ' +
        '           id="subscribe-to-bug-' + bug_id + '" value="yes" ' +
        '           class="subscribe-option" />' +
        '       <label for="subscribe-to-bug-' + bug_id + '"> ' +
        '         Subscribe me as well' +
        '       </label>' +
        '    </p>' +
        '</div>';

    // Create the do-you-want-to-subscribe FormOverlay.
    subscribe_form_overlay = new Y.lazr.FormOverlay({
        headerContent: '<h2>I am affected by this bug</h2>',
        form_content: subscribe_form_body,
        form_submit_button: Y.Node.create(submit_button_html),
        form_cancel_button: Y.Node.create(cancel_button_html),
        centered: true,
        visible: false
    });
    subscribe_form_overlay.render('#duplicate-overlay-bug-' + bug_id);

    // Alter the overlay's properties to make sure it submits correctly
    // and to the right place.
    form_node = subscribe_form_overlay.form_node;
    form_node.set('action', form.get('action'));
    form_node.set('method', 'post');

    // Add an on-click handler to the radio buttons to ensure that their
    // labels' styles are set correctly when they're selected.
    var radio_buttons = form.queryAll('input.subscribe-option');
    if (radio_buttons !== null && radio_buttons !== undefined) {
        Y.each(radio_buttons, function(radio_button) {
            radio_button.on('click', function(e) {
                // Loop over the radio buttons and set their parent
                // div's font-weight depending on whether they're
                // checked or not.
                Y.each(radio_buttons, function(radio_button) {
                    if (radio_button.get('checked')) {
                        radio_button.get(
                            'parentNode').setStyle('fontWeight', 'bold');
                    } else {
                        radio_button.get(
                            'parentNode').setStyle('fontWeight', 'normal');
                    }
                });
            });
        });
    }

    return subscribe_form_overlay;
}

Y.bugs.setup_dupe_finder = function() {
    Y.on('domready', function() {
        // Grab a copy of the spinner HTML so that we can re-insert it
        // whenever we need it.
        spinner_html = Y.get('#possible-duplicates').get('innerHTML');
        search_button = Y.get(Y.DOM.byId('field.actions.search'));

        // Change the name and id of the search field so that it doesn't
        // confuse the view when we submit a bug report.
        search_field = Y.get(Y.DOM.byId('field.title'));
        search_field.set('name', 'field.search');
        search_field.set('id', 'field.search');

        // Disable the form so that hitting "enter" in the Summary
        // field no longer sends us through to the next page.
        // Y.on('submit', function(e) { e.halt(); }, '#my-form')

        // Update the label on the search button so that it no longer
        // says "Continue".
        search_button.set('value', 'Search');
        search_button.set('type', 'button');

        // Set up the handlers for the search button and the input
        // field.
        search_button.on('click', search_for_and_display_dupes);
    });

};

}, '0.1', {requires: ['base', 'oop', 'node', 'event', 'lazr.formoverlay']});
