/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Setup for managing subscribers list for questions.
 *
 * @module answers
 * @submodule subscribers
 */

YUI.add('lp.answers.subscribers', function(Y) {

var namespace = Y.namespace('lp.answers.subscribers');

/**
 * Possible subscriber levels with descriptive headers for
 * sections that will hold them.
 */
var subscriber_levels = {
    'Direct': 'Direct subscribers',
    'Indirect': 'Also notified'
};

/**
 * Order of subscribers sections.
 */
var subscriber_level_order = ['Direct', 'Indirect'];


/**
 * Create the SubscribersLoader instance which will load subscribers for
 * a question and put them in the web page.
 *
 * @param config {Object} Defines `container_box' CSS selector for the
 *     SubscribersList container box, `context' holding context metadata (at
 *     least with `web_link') and `subscribers_details_view' holding
 *     a relative URI to load subscribers' details from.
 */
function createQuestionSubscribersLoader(config) {
    config.subscriber_levels = subscriber_levels;
    config.subscriber_level_order = subscriber_level_order;
    config.context = config.question;
    config.subscribe_someone_else_level = 'Direct';
    config.default_subscriber_level = 'Indirect';
    var module = Y.lp.app.subscribers.subscribers_list;
    return new module.SubscribersLoader(config);
}
namespace.createQuestionSubscribersLoader = createQuestionSubscribersLoader;

}, "0.1", {"requires": ["lp.app.subscribers.subscribers_list"]});
