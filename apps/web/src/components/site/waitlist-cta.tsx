"use client";

import { useState } from "react";
import { Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function WaitlistCTA() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    // Persistence follows in a dedicated backend feature (PROJ-18 Beta-Waitlist).
    setSubmitted(true);
  };

  return (
    <section id="waitlist" className="bg-background scroll-mt-20">
      <div className="container pb-24">
        <div className="relative overflow-hidden rounded-2xl bg-primary px-6 py-14 text-center text-primary-foreground sm:px-12">
          <h2 className="font-serif text-4xl leading-tight text-balance sm:text-5xl">
            Beta startet im <span className="italic">Q3 2026.</span>
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-primary-foreground/85">
            Erste 50 Brands erhalten 50 % Rabatt im ersten Jahr und direkten Draht ins
            Produkt-Team.
          </p>

          {submitted ? (
            <div className="mx-auto mt-8 max-w-md rounded-lg border border-primary-foreground/25 bg-primary-foreground/10 p-4 text-sm">
              Danke! Wir melden uns vor dem Launch per E-Mail.
            </div>
          ) : (
            <form
              onSubmit={handleSubmit}
              className="mx-auto mt-8 flex max-w-md flex-col gap-2 sm:flex-row"
            >
              <label htmlFor="waitlist-email" className="sr-only">
                E-Mail-Adresse
              </label>
              <div className="relative flex-1">
                <Mail
                  className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                  aria-hidden
                />
                <Input
                  id="waitlist-email"
                  type="email"
                  required
                  placeholder="email@brand.de"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-background pl-9 text-foreground"
                />
              </div>
              <Button
                type="submit"
                variant="secondary"
                className="bg-background text-foreground hover:bg-background/90"
              >
                Auf Warteliste
              </Button>
            </form>
          )}

          <p className="mx-auto mt-4 max-w-md text-xs text-primary-foreground/70">
            Keine Spam-Mails. Abmeldung jederzeit. Daten werden in Deutschland verarbeitet.
          </p>
        </div>
      </div>
    </section>
  );
}
