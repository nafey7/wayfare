# Frontend Internationalization (i18n) Readiness

Notes for future i18n implementation. Not a blocker; document current state and extraction points.

## Current State

- **Landing page**: All section text (headlines, descriptions, testimonials) is hardcoded in component defaults
- **Prop overrides**: Most sections accept optional props to override default text (e.g. `HeroProps.headline`, `FooterProps.brandName`)
- **LandingPage.tsx**: Passes no content props today; all sections use their `DEFAULT_*` values

## Sections with Content Props (Override Points)

| Section | File | Key Override Props |
|---------|------|--------------------|
| Hero | `Hero.tsx` | `calloutText`, `headline`, `subheadline`, `ctaButtonText`, `flightOrigin`, `flightDestination`, `hotelName`, etc. |
| Footer | `Footer.tsx` | `brandName`, `tagline`, `ctaButtonText`, `quickLinksHeading`, `quickLinks`, `legalHeading`, `legalLinks`, `socialLinks` |
| HowItWorksSection | `HowItWorksSection.tsx` | `chipText`, `heading`, `subheadline`, `steps`, `storyCards` |
| WhyVoyaSection | `WhyVoyaSection.tsx` | Heading and card content props |
| WhatVoyaGivesYouSection | `WhatVoyaGivesYouSection.tsx` | Section props |
| ExampleItinerariesSection | `ExampleItinerariesSection.tsx` | `chipLabel`, `title`, `subtitle`, `itineraries`, `planMyOwnTripText`, `planDescription` |
| SignUpCTASection | `SignUpCTASection.tsx` | CTA content props |
| FinalCTASection | `FinalCTASection.tsx` | Primary CTA content |
| IntroTestimonialsSection | `IntroTestimonialsSection.tsx` | Testimonial data |
| Copyright | `Copyright.tsx` | `copyrightYear`, `companyName` |

## Suggested Translation Key Structure

```
landing.hero.headline
landing.hero.subheadline
landing.hero.ctaButtonText
landing.footer.brandName
landing.footer.tagline
landing.howItWorks.heading
landing.howItWorks.subheadline
landing.exampleItineraries.title
landing.exampleItineraries.subtitle
landing.testimonials[0].quote
...
```

## Future i18n Path

1. **Introduce `useTranslations()` or `t()`**: Returns objects keyed by section/field
2. **Replace `DEFAULT_PROPS`**: Use `t('hero.headline')` instead of string literals
3. **Keep prop overrides**: Existing override props stay as runtime overrides (useful for A/B tests, per-tenant content, or CMS-driven content)
4. **Libraries**: Consider `react-i18next`, `formatjs`, or similar when implementing

## Optional: ContentOverrides Config

A future `ContentOverrides` type could map section names to their override props, allowing a single i18n layer to inject translated content:

```ts
interface ContentOverrides {
  hero?: Pick<HeroProps, 'headline' | 'subheadline' | 'ctaButtonText'>;
  footer?: Pick<FooterProps, 'brandName' | 'tagline' | 'ctaButtonText'>;
  // ...
}
```

`LandingPage` would then pass `contentOverrides.hero` into `<Hero {...contentOverrides.hero} />`.
