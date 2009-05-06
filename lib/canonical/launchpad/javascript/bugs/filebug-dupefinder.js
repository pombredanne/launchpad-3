/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Handling of form overlay widgets for bug pages.
 *
 * @module DupeFinder
 * @requires base, node
 */
YUI.add('bugs.dupe_finder', function(Y) {

var BUGS = 'bugs',
    DISPLAY = 'display',
    NONE = 'none',
    BLOCK = 'block';

var bugs = Y.namespace(BUGS);

/*
 * The NodeList of radio buttons in the list of possible duplicates.
 */
var bug_already_reported_buttons;

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
    Y.each(bug_already_reported_buttons, function(radio_button) {
        bug_details_div = get_details_div(radio_button);

        if (radio_button.get('checked')) {
            bug_details_div.setStyle(DISPLAY, BLOCK);
        } else {
            bug_details_div.setStyle(DISPLAY, NONE);
        }
    });
}

Y.bugs.setup_dupe_finder = function() {
    /*
     * Hook up the toggle_bug_details() function to the onchange events of
     * the radio buttons.
     */
    Y.on('domready', function() {
        bug_already_reported_buttons = Y.all('input.duplicate-bug-button');

        if (bug_already_reported_buttons) {
            // Collapse all the details divs, since we don't want them
            // expanded first up.
            Y.each(Y.all('div.duplicate-details'), function(div) {
                div.setStyle(DISPLAY, NONE);
            });

            // Set up the onclick handlers for the expanders.
            Y.each(bug_already_reported_buttons, function(radio_button) {
                radio_button.on('change', toggle_bug_details);
            });

            // Hide the bug reporting form.
            Y.get('#bug-reporting-form').setStyle(DISPLAY, NONE);
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
