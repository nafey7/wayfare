'use strict';

module.exports = {
  /**
   * An asynchronous register function that runs before
   * your application is initialized.
   * Component schemas under `src/components/` are auto-discovered; use this
   * only for registering plugins or custom Strapi extensions.
   */
  register(/* { strapi } */) {},

  /**
   * An asynchronous bootstrap function that runs before
   * your application gets started.
   */
  bootstrap(/* { strapi } */) {},
};
