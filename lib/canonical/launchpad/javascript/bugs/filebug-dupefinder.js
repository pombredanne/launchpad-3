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
 * The div in which the bug reporting form resides.
 */
var bug_reporting_form;

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

    Y.log(bug_details_div.getStyle(DISPLAY));
    if (bug_details_div.getStyle(DISPLAY) == BLOCK) {
        collapse_bug_details(image);
    } else {
        image.set(SRC, EXPANDER_EXPANDED);
        bug_details_div.setStyle(DISPLAY, BLOCK);
    }

    // If the bug reporting form is shown, hide it.
    if (bug_reporting_form.getStyle(DISPLAY) == BLOCK) {
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

Y.bugs.setup_dupe_finder = function() {
    Y.on('domready', function() {
        bug_already_reported_expanders = Y.all(
            'img.bug-already-reported-expander');
        bug_reporting_form = Y.get('#bug_reporting_form');

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

            // Hide the bug reporting form.
            bug_reporting_form.setStyle(DISPLAY, NONE);
        }

        bug_not_reported_button = Y.get('#bug-not-already-reported');
        if (bug_not_reported_button !== null &&
            bug_not_reported_button !== undefined) {
            // The bug_not_reported_button won't show up if there aren't any
            // possible duplicates.
            bug_not_reported_button.on('click', show_bug_reporting_form);
        }
    });
};

});
