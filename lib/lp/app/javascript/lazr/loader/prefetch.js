/* Copyright (c) 2010, Canonical Ltd. All rights reserved. */

/**
 * Prefetch a set of files, deferring calls to 'use' until the
 * preloaded files are finished loading.
 *
 * @public
 */

YUI.prototype.prefetch = function prefetch() {
    var Y = this,
        deferred = [],
        preload = arguments,
        pending = arguments.length;

    var YArray_each = Y.Array.each,
        YGet_script = Y.Get.script;

    /**
     * Wrap the native 'use' function to add some smarts around
     * our custom loading of the rolled-up minified files so that
     * we delay the loader from firing until the rolled-up files
     * are finished loading, in order to avoid loading the
     * modules twice.
     */
    var native_use = Y.use;

    /* Now replace the original 'use' function with our own. */
    Y.use = function use() {
        /**
         * If all external dependencies have been loaded, just
         * call the native 'use' function directly.
         */
        if (!pending) {
            native_use.apply(Y, arguments);
        } else {
            /**
             * If there are things still loading, queue calls to 'use'
             *  until they are finished.
             */
            var ridx = arguments.length,
            args = [];
            /* Make a copy of the original arguments. */
            while (--ridx >= 0) {
                args[ridx] = arguments[ridx];
            }

            /* Push copied arguments into the queue. */
            deferred.push(args);
        }
    };

    /**
     * For each item to be preloaded, use the Y.Get utility to
     * fetch the script (which might fetch them in parallel). When
     * all the scripts are finished loading, we'll process the
     * deferred calls to use with the native 'use' function.
     */
    YArray_each(preload, function(value) {
        YGet_script(value, {onEnd: function() {
            /**
             * Once an item has finished preloading, we decrement
             * the pending variable. Once it reaches zero, we
             * know all preload items have finished loading.
             */
            pending--;

            /**
             * Once we're done, restore the original 'use'
             * function and call all of the deferred callbacks in
             * their original order.
             */
            if (!pending) {
                Y.use = native_use;

                /**
                 * Attach the 'loader' module, which *should* be
                 * already loaded by now.
                 */
                Y._attach(["loader"]);
                YArray_each(deferred, function(value) {
                    native_use.apply(this, value);
                });
            }
        }, attributes: {defer: "defer"}});
    });
};
