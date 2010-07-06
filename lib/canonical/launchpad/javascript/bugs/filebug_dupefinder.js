/* Copyright 2009 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Handling of form overlay widgets for bug pages.
 *
 * @module bugs
 * @submodule filebug_dupefinder
 */
YUI.add('lp.bugs.filebug_dupefinder', function(Y) {

var BLOCK = 'block',
    DISPLAY = 'display',
    EXPANDER_COLLAPSED = '/@@/treeCollapsed',
    EXPANDER_EXPANDED = '/@@/treeExpanded',
    INLINE = 'inline',
    INNER_HTML = 'innerHTML',
    LAZR_CLOSED = 'lazr-closed',
    NONE = 'none',
    SRC = 'src',
    UNSEEN = 'unseen';

var namespace = Y.namespace('lp.bugs.filebug_dupefinder');

/*
 * The NodeList of possible duplicates.
 */
var bug_already_reported_expanders;
/*
 * The search field on the +filebug form
 */
var search_field;
/*
 * The search button on the +filebug form
 */
var search_button;
/**
 * The base URL for similar bug searches.
 */
var search_url_base;
/**
 * The base URL for all inline +filebug work.
 */
var filebug_base_url;
/**
 * The URL of the inline +filebug form.
 */
var filebug_form_url;
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
        'parentNode').get('parentNode').one('.duplicate-details');

    // Check that the details_div actually exists and raise an error if
    // we can't find it.
    if (!Y.Lang.isValue(details_div)) {
        Y.fail(
            "Unable to find details div for expander " + expander.get('id'));
    } else {
        return details_div;
    }
}

/**
 * Collapse the details for a bug and set its expander arrow to
 * 'collapsed'
 * @param expander The expander to collapse.
 */
function collapse_bug_details(expander) {
    var bug_details_div = get_details_div(expander);
    var anim = Y.lazr.effects.slide_in(bug_details_div);
    anim.run();

    expander.set(SRC, EXPANDER_COLLAPSED);
}

/**
 * Show the bug reporting form and collapse all bug details forms.
 * @param e The Event triggering this function.
 */
function show_bug_reporting_form(e) {
    // If the bug reporting form is in a hidden container, as it is on
    // the AJAX dupe search, show it.
    var filebug_form_container = Y.one('#filebug-form-container');
    if (Y.Lang.isValue(filebug_form_container)) {
        filebug_form_container.setStyle(DISPLAY, BLOCK);
    }

    // Show the bug reporting form.
    var bug_reporting_form = Y.one('#bug_reporting_form');
    bug_reporting_form.setStyle(DISPLAY, BLOCK);

    Y.one(Y.DOM.byId('field.actions.submit_bug')).focus();

    // Focus the relevant elements of the form based on
    // whether the package drop-down is displayed.
    var bugtarget_package_btn = Y.one(
        Y.DOM.byId('field.bugtarget.option.package'));
    if (Y.Lang.isValue(bugtarget_package_btn)) {
        Y.one(Y.DOM.byId('field.bugtarget.package')).focus();
    } else {
        Y.one(Y.DOM.byId('field.comment')).focus();
    }
}

/**
 * Search for bugs that may match the text that the user has entered and
 * display them in-line.
 */
function search_for_and_display_dupes() {
    function show_failure_message(transaction_id, response, args) {
        // If the request failed due to a timeout, display a message
        // explaining how the user may be able to work around it.
        var error_message = '';
        if (response.status == 503) {
            // We treat 503 (service unavailable) as a timeout because
            // that's what timeouts in LP return.
            error_message =
                "Searching for your bug in Launchpad took too long. " +
                "Try reducing the number of words in the summary " +
                "field and click \"Check again\" to retry your search. " +
                "Alternatively, you can enter the details of your bug " +
                "below.";
        } else {
            // Any other error code gets a generic message.
            error_message =
                "An error occured whilst trying to find bugs matching " +
                "the summary you entered. Click \"Check again\" to retry " +
                "your search. Alternatively, you can enter the " +
                "details of your bug below.";
        }

        var error_node = Y.Node.create('<p></p>');
        error_node.set('text', error_message);
        Y.one('#possible-duplicates').appendChild(error_node);

        Y.one('#spinner').addClass(UNSEEN);
        show_bug_reporting_form();

        Y.one(Y.DOM.byId('field.title')).set(
            'value', search_field.get('value'));
        search_button.set('value', 'Check again');
        search_button.removeClass(UNSEEN);
    }

    function on_success(transaction_id, response, args) {
        // Hide the spinner and show the duplicates.
        Y.one('#spinner').addClass(UNSEEN);

        var duplicate_div = Y.one('#possible-duplicates');
        duplicate_div.set(INNER_HTML, response.responseText);

        bug_already_reported_expanders = Y.all(
            'img.bug-already-reported-expander');
        if (bug_already_reported_expanders.size() > 0) {
            // If there are duplicates shown, set up the JavaScript of
            // the duplicates that have been returned.
            Y.lp.bugs.filebug_dupefinder.setup_dupes();
        } else {
            // Otherwise, show the bug reporting form.
            show_bug_reporting_form();
        }

        // Copy the value from the search field into the title field
        // on the filebug form.
        Y.one('#bug_reporting_form input[name=field.title]').set(
            'value', search_field.get('value'));

        // Finally, change the label on the search button and show it
        // again.
        search_button.set('value', 'Check again');
        search_button.removeClass(UNSEEN);
    }

    var search_term = encodeURI(search_field.get('value'));
    var search_url = search_url_base + '?title=' + search_term;

    // Hide the button and +filebug form, show the spinner and clear the
    // contents of the possible duplicates div.
    search_button.addClass(UNSEEN);
    Y.one('#spinner').removeClass(UNSEEN);
    Y.one('#possible-duplicates').set(INNER_HTML, '');
    Y.one('#bug_reporting_form').setStyle(DISPLAY, NONE);

    config = {on: {success: on_success,
                   failure: show_failure_message}};
    Y.io(search_url, config);
}

/*
 * Create the overlay for a user to optionally subscribe to a bug that
 * affects them.
 * @param form The form to which the FormOverlay is going to be
 *             attached.
 */
function create_subscribe_overlay(form) {
    // Grab the bug id and title from the "Yes, this is my bug" form.
    var bug_id = form.one(
        'input.bug-already-reported-as').get('value');
    var bug_title = Y.one('#bug-' + bug_id + '-title').get(INNER_HTML);

    if (bug_title.length > 35) {
        // Truncate the bug title if it's more than 35 characters long.
        bug_title = bug_title.substring(0, 35) + '...';
    }

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
    Y.each(radio_buttons, function(radio_button) {
        var weight = radio_button.get('checked') ? 'bold' : 'normal';
        radio_button.get('parentNode').setStyle('fontWeight', weight);
    });

    return subscribe_form_overlay;
}

/**
 * Reload the +filebug-inline form for the correct product or package.
 */
function reload_filebug_form() {
    var config = {
        on: {
            success: function(transaction_id, response, args) {
                // Hide the filebug form container.
                var filebug_form_container = Y.one(
                    '#filebug-form-container');
                filebug_form_container.setStyle(DISPLAY, NONE);
                Y.log(filebug_form_container);

                // Clear the contents of the search results.
                Y.one('#possible-duplicates').set(INNER_HTML, '');

                // Set up the +filebug form.
                set_up_filebug_form(response.responseText);

                // Change the label on the search button to its default.
                search_button.set('value', 'Next');
            }
        }
    };

    var product_field = Y.one(Y.DOM.byId('field.product'));
    if (Y.Lang.isValue(product_field)) {
        var product = product_field.get('value');
        filebug_form_url =
            filebug_base_url + product + '/+filebug-inline-form';
        search_url_base =
            filebug_base_url + product + '/+filebug-show-similar';
    }

    // Reload the filebug form.
    Y.io(filebug_form_url, config);
}

/**
 * Set up the filebug form.
 */
function set_up_filebug_form(form_contents) {
    var filebug_form_container = Y.one('#filebug-form-container');
    filebug_form_container.set(INNER_HTML, form_contents);

    // Activate the extra options collapsible section on the bug
    // reporting form.
    var bug_reporting_form = Y.one('#bug_reporting_form');
    if (Y.Lang.isValue(bug_reporting_form)) {
        activateCollapsibles();
    }
}

/**
 * Set up the dupe finder, overriding the default behaviour of the
 * +filebug search form.
 */
function set_up_dupe_finder(transaction_id, response, args) {
    // Grab the inline filebug base url and store it.
    filebug_base_url = Y.one('#filebug-base-url').getAttribute('href');

    // Load the +filebug form into its container.
    set_up_filebug_form(response.responseText);

    // Grab the search_url_base value from the page and store it.
    search_url_base = Y.one('#duplicate-search-url').getAttribute('href');

    // Change the name and id of the search field so that it doesn't
    // confuse the view when we submit a bug report.
    search_field = Y.one(Y.DOM.byId('field.title'));
    search_field.set('name', 'field.search');
    search_field.set('id', 'field.search');

    // If there's a product field, hook it up to the
    // reload_filebug_form() function.
    var product_field = Y.one(Y.DOM.byId('field.product'));
    if (Y.Lang.isValue(product_field)) {
        Y.log(product_field);
        product_field.on('change', reload_filebug_form);
    }

    // Update the label on the search button so that it no longer
    // says "Continue".
    search_button = Y.one(Y.DOM.byId('field.actions.search'));
    search_button.set('value', 'Next');

    // Set up the handler for the search form.
    search_form = Y.one('#filebug-search-form');
    search_form.on('submit', function(e) {
        // Prevent the event from propagating; we don't want to reload
        // the page.
        e.halt();
        search_for_and_display_dupes();
    });
}

namespace.setup_dupes = function() {
    bug_already_reported_expanders = Y.all(
        'img.bug-already-reported-expander');
    bug_reporting_form = Y.one('#bug_reporting_form');

    if (bug_already_reported_expanders.size() > 0) {
        // Collapse all the details divs, since we don't want them
        // expanded first up.
        Y.each(Y.all('div.duplicate-details'), function(div) {
            collapse_bug_details(div);
        });

        // Set up the onclick handlers for the expanders.
        Y.each(Y.all('.similar-bug'), function(row) {
            var bug_details_div = row.query('div.duplicate-details');
            var image = row.query('img.bug-already-reported-expander');
            var bug_title_link = row.query('.duplicate-bug-link');
            var view_bug_link = row.query('.view-bug-link');

            // Shut down the default action for the link and mark it
            // as a JS'd link. We do this as it's simpler than
            // trying to find all the bits of the row that we want
            // to make clickable.
            bug_title_link.addClass('js-action');
            bug_title_link.on('click', function(e) {
                e.preventDefault();
            });

            // The "view this bug" link shouldn't trigger the
            // collapsible, so we stop the event from propagating.
            view_bug_link.on('click', function(e) {
                e.stopPropagation();
            });

            // The same is true for the collapsible section. People
            // may want to copy and paste this, which involves
            // clicking, so we stop the onclick event from
            // propagating here, too.
            bug_details_div.on('click', function(e) {
                e.stopPropagation();
            });

            // Set up the on focus handler for the link so that
            // tabbing will expand the different bugs.
            bug_title_link.on('focus', function(e) {
                if (!bug_details_div.hasClass('lazr-opened')) {
                    var anim = Y.lazr.effects.slide_out(bug_details_div);
                    anim.run();

                    image.set(SRC, EXPANDER_EXPANDED);

                    // If the bug reporting form is shown, hide it.
                    if (bug_reporting_form.getStyle(DISPLAY) == BLOCK) {
                        bug_reporting_form.addClass(UNSEEN);
                    }
                }
            });

            row.on('click', function(e) {
                if (bug_details_div.hasClass('lazr-opened')) {
                    collapse_bug_details(image);
                } else {
                    var anim = Y.lazr.effects.slide_out(bug_details_div);
                    anim.run();

                    image.set(SRC, EXPANDER_EXPANDED);
                }
            });
        });

        // Hide the bug reporting form.
        bug_reporting_form.addClass(UNSEEN);
    }

    bug_not_reported_button = Y.one('#bug-not-already-reported');
    if (Y.Lang.isValue(bug_not_reported_button)) {
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
};

namespace.setup_dupe_finder = function() {
    Y.log("In setup_dupe_finder");
    Y.on('domready', function() {
        config = {on: {success: set_up_dupe_finder,
                       failure: function() {}}};

        // Load the filebug form asynchronously. If this fails we
        // degrade to the standard mode for bug filing, clicking through
        // to the second part of the bug filing form.
        var filebug_form_url_element = Y.one(
            '#filebug-form-url');
        if (Y.Lang.isValue(filebug_form_url_element)) {
            filebug_form_url = filebug_form_url_element.getAttribute(
                'href');
            Y.io(filebug_form_url, config);
        }
    });
};

}, "0.1", {"requires": [
    "base", "io", "oop", "node", "event", "lazr.formoverlay", "lazr.effects"]});
