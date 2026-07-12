import type { Schema, Struct } from '@strapi/strapi';

export interface LandingInspirationTripCard extends Struct.ComponentSchema {
  collectionName: 'components_landing_inspiration_trip_cards';
  info: {
    description: 'A trip card for the home page rails. Write chatPrompt without an origin city \u2014 the codebase appends a random popular city automatically.';
    displayName: 'Inspiration Trip Card';
    icon: 'plane';
  };
  attributes: {
    builtInSeconds: Schema.Attribute.Integer &
      Schema.Attribute.Required &
      Schema.Attribute.DefaultTo<45>;
    chatPrompt: Schema.Attribute.Text & Schema.Attribute.Required;
    duration: Schema.Attribute.String & Schema.Attribute.Required;
    flightRoute: Schema.Attribute.String & Schema.Attribute.Required;
    hotelName: Schema.Attribute.String & Schema.Attribute.Required;
    image: Schema.Attribute.Media<'images'>;
    rating: Schema.Attribute.Decimal;
    stops: Schema.Attribute.Integer &
      Schema.Attribute.Required &
      Schema.Attribute.DefaultTo<0>;
    tag: Schema.Attribute.String;
    theme: Schema.Attribute.Enumeration<
      ['lisbon', 'tokyo', 'bali', 'bangkok']
    > &
      Schema.Attribute.Required &
      Schema.Attribute.DefaultTo<'lisbon'>;
    title: Schema.Attribute.String & Schema.Attribute.Required;
    totalPrice: Schema.Attribute.String & Schema.Attribute.Required;
  };
}

declare module '@strapi/strapi' {
  export module Public {
    export interface ComponentSchemas {
      'landing.inspiration-trip-card': LandingInspirationTripCard;
    }
  }
}
