"use client";

import { useMemo, useState } from "react";
import { FileText, Link2, Upload, Scan } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ClaimCard } from "@/components/site/claim-card";
import { DEMO_CLAIMS, DEMO_INPUT, STATUS_META } from "@/lib/demo-data";

const TABS = [
  { id: "text", label: "Text", icon: FileText },
  { id: "url", label: "URL", icon: Link2 },
  { id: "pdf", label: "PDF", icon: Upload },
] as const;

export function DemoWidget() {
  const [input] = useState(DEMO_INPUT);
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]["id"]>("text");

  const counts = useMemo(() => {
    const by = { allowed: 0, borderline: 0, forbidden: 0, unclear: 0 };
    for (const c of DEMO_CLAIMS) by[c.status] += 1;
    return by;
  }, []);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* ---------- Eingabe ---------- */}
      <div className="rounded-xl border border-border/80 bg-card shadow-sm">
        <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
            <FileText className="h-3.5 w-3.5" aria-hidden />
            Werbetext
          </span>
          <div className="flex items-center gap-1 rounded-md bg-muted/60 p-0.5">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const active = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium transition-colors",
                    active
                      ? "bg-background text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                  aria-pressed={active}
                >
                  <Icon className="h-3 w-3" aria-hidden />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="p-5">
          {activeTab === "text" && (
            <p className="font-serif text-[15px] leading-relaxed text-foreground">
              {input}
            </p>
          )}
          {activeTab === "url" && (
            <div className="flex h-[108px] flex-col items-center justify-center gap-2 text-center">
              <Link2 className="h-5 w-5 text-muted-foreground" aria-hidden />
              <p className="text-sm text-muted-foreground">
                URL einfügen, wir rendern die Seite und extrahieren den Text.
              </p>
            </div>
          )}
          {activeTab === "pdf" && (
            <div className="flex h-[108px] flex-col items-center justify-center gap-2 text-center">
              <Upload className="h-5 w-5 text-muted-foreground" aria-hidden />
              <p className="text-sm text-muted-foreground">
                PDF hier ablegen oder auswählen. Text wird serverseitig extrahiert.
              </p>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-border/60 px-4 py-3 text-xs text-muted-foreground">
          <span>{input.length} Zeichen · Analyse dauert ≈ 6 s</span>
          <Button size="sm" disabled className="cursor-default">
            <Scan className="mr-1.5 h-3.5 w-3.5" aria-hidden />
            Claims prüfen
          </Button>
        </div>
      </div>

      {/* ---------- Ergebnisse ---------- */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-serif text-lg font-semibold tracking-tight">
            {DEMO_CLAIMS.length} Claims identifiziert
          </h3>
          <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
            <Dot className="bg-status-allowed" /> {counts.allowed}
            <Dot className="bg-status-borderline" /> {counts.borderline}
            <Dot className="bg-status-forbidden" /> {counts.forbidden}
            {counts.unclear > 0 && (
              <>
                <Dot className="bg-status-unclear" /> {counts.unclear}
              </>
            )}
          </div>
        </div>

        <div className="space-y-3">
          {DEMO_CLAIMS.map((claim) => (
            <ClaimCard key={claim.id} claim={claim} />
          ))}
        </div>

        <p className="mt-4 text-[11px] leading-relaxed text-muted-foreground">
          Beispielanalyse. Eine echte Prüfung liefert zusätzlich {" "}
          {STATUS_META.unclear.label.toLowerCase()}-Fallback bei unklarer Rechtslage.
        </p>
      </div>
    </div>
  );
}

function Dot({ className }: { className: string }) {
  return (
    <span
      aria-hidden
      className={cn("inline-block h-1.5 w-1.5 rounded-full", className)}
    />
  );
}
