import { SiteHeader } from "@/components/site/site-header";
import { SiteFooter } from "@/components/site/site-footer";
import { Hero } from "@/components/site/hero";
import { FeatureGrid } from "@/components/site/feature-grid";
import { HowItWorks } from "@/components/site/how-it-works";
import { LegalSources } from "@/components/site/legal-sources";
import { Pricing } from "@/components/site/pricing";
import { WaitlistCTA } from "@/components/site/waitlist-cta";

export default function HomePage() {
  return (
    <>
      <SiteHeader />
      <main>
        <Hero />
        <FeatureGrid />
        <HowItWorks />
        <LegalSources />
        <Pricing />
        <WaitlistCTA />
      </main>
      <SiteFooter />
    </>
  );
}
