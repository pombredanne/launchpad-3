/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Library for code review javascript.
 *
 * @module CodeReview
 * @requires base, lazr.anim, lazr.formoverlay
 */

YUI.add('code.codereview', function(Y) {

Y.codereview = Y.namespace('code.codereview');

var reviewer_picker; // The "Request a review" overlay
var lp_client;

Y.codereview.connect_links = function() {

    var link = Y.get('#request-review');
    link.addClass('js-action');
    link.on('click', show_request_review_form);

};

function show_request_review_form(e) {

    e.preventDefault();
    var config = {
        header: 'Request a review',
        step_title: 'Search',
    };

    reviewer_picker = Y.lp.picker.create(
        'ValidPersonOrTeam',
        function(result) {
            var review_type = Y.get("[id=field.review_type]").get('value');
            request_reviewer(result, review_type);
        },
        config);
    reviewer_picker.set('footer_slot', Y.Node.create([
        '<div>',
        '<div style="float: left; padding-right: 9px;">',
        '<label for="field.review_type">Review type:</label><br />',
        '<span class="fieldRequired">(Optional)</span>',
        '</div>',
        '<input class="textType" id="field.review_type" ',
        'name="field.review_type" size="14" type="text" value=""  /></div>',
        ].join(' ')));
    reviewer_picker.on('save', function() {})
    reviewer_picker.on('cancel', function() {})
    reviewer_picker.show()

}

function request_reviewer(person, reviewtype) {

    // Add the temp "Requesting review..." text
    var table_row = Y.Node.create([
        '<tr><td colspan="4">',
        '<img src="/@@/spinner" />',
        'Requesting review...',
        '</td></tr>'].join(""));
    var last_element = Y.get('#email-review');
    var reviewer_table = last_element.get('parentNode');
    reviewer_table.insertBefore(table_row, last_element);


    var context = LP.client.cache['context'];
    if (lp_client === undefined) {
        lp_client = new LP.client.Launchpad();
    }

    var config = {
        parameters: {
            reviewer: LP.client.get_absolute_uri(person['api_uri']),
            review_type: reviewtype
        },
        on: {
            success: add_reviewer_html,
            failure: function(result) {
                alert('An error has occurred. Unable to request review.');
                Y.log(result);
            }
        }
    };
    lp_client.named_post(context['self_link'],
        'nominateReviewer', config);
}


function add_reviewer_html(result) {

    var VOTES_TABLE_PATH = '+votes-table-fragment';
    Y.io(VOTES_TABLE_PATH, {
        on: {
            success: function() {},
            failure: function() {}
        }
    };
}


}, '0.1', {requires: ['base', 'lazr.anim', 'lazr.formoverlay', 'lp.picker']});
