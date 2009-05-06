/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Handling of form overlay widgets for bug pages.
 *
 * @module DupeFinder
 * @requires base, node
 */
YUI.add('bugs.dupe_finder', function(Y) {

var BLOCK = 'block',
    BUGS = 'bugs',
    DISPLAY = 'display',
    EXPANDER_COLLAPSED = '/@@/treeCollapsed',
    EXPANDER_EXPANDED = '/@@/treeExpanded',
    NONE = 'none',
    SRC = 'src';

var bugs = Y.namespace(BUGS);

/*
 * The NodeList of expanders in the list of possible duplicates.
 */
var bug_already_reported_expanders;

/**
 * Return the relevant duplicate-details div for a bug-already-reported
 * radio button.
 * @param radio_button The radio button for which to return the relevant
 *                     div.
 */
function get_details_div(radio_button) {
    table_row = radio_button.get('parentNode').get('parentNode');
    return table_row.query('div.duplicate-details');
}

/**
 * Show or hide each duplicate-details div depending on whether the
 * relevant radio button is selected.
 */
function toggle_bug_details() {
    // Toggle the expander that's being clicked. We have to use the
    // display attribute of the associated details div because the SRC
    // attribute of the image changes depending on what host we're on
    // (i.e. production or edge).
    bug_details_div = get_details_div(this);

    Y.log(bug_details_div.getStyle(DISPLAY));
    if (bug_details_div.getStyle(DISPLAY) == BLOCK) {
        this.set(SRC, EXPANDER_COLLAPSED);
        bug_details_div.setStyle(DISPLAY, NONE);
    } else {
        this.set(SRC, EXPANDER_EXPANDED);
        bug_details_div.setStyle(DISPLAY, BLOCK);
    }
}

Y.bugs.setup_dupe_finder = function() {
    /*
     * Hook up the toggle_bug_details() function to the onchange events of
     * the radio buttons.
     */
    Y.on('domready', function() {
        bug_already_reported_expanders = Y.all(
            'img.bug-already-reported-expander');

        if (bug_already_reported_expanders) {
            // Collapse all the details divs, since we don't want them
            // expanded first up.
            Y.each(Y.all('div.duplicate-details'), function(div) {
                div.setStyle(DISPLAY, NONE);
            });

            // Set up the onclick handlers for the expanders.
            Y.each(bug_already_reported_expanders, function(expander) {
                Y.log(expander);
                expander.on('click', toggle_bug_details);
            });

            // Hide the bug reporting form.
            Y.get('#bug_reporting_form').setStyle(DISPLAY, NONE);
        }

        bug_not_reported_button = Y.get('#bug-not-already-reported');
        if (bug_not_reported_button) {
            // The bug_not_reported_button won't show up if there aren't any
            // possible duplicates.
            bug_not_reported_button.on('change', function() {
                if (this.get('checked')) {
                    Y.each(Y.all('div.duplicate-details'), function(div) {
                        div.setStyle(DISPLAY, NONE);
                    });
                }
            });
        }
    });
}

});
