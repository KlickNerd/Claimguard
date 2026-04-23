import Link from "next/link";
import { notFound } from "next/navigation";
import {
  Calendar,
  ChevronLeft,
  Download,
  MoreHorizontal,
  RefreshCcw,
  Share2,
  Tag,
  User,
} from "lucide-react";
import { AppHeader } from "@/components/app/app-header";
import { ClaimCard } from "@/components/site/claim-card";
import { StatusPill } from "@/components/site/status-pill";
import {
  ClaimCountTile,
  ComplianceScore,
} from "@/components/app/compliance-score";
import { MarkedText } from "@/components/app/marked-text";
import { Button } from "@/components/ui/button";
import { MOCK_DETAILS, type AnalysisDetail } from "@/lib/mock-analyses";

export default async function ReportDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const analysis = MOCK_DETAILS[id] as AnalysisDetail | undefined;
  if (!analysis) notFound();

  const { counts } = analysis;
  const highestStatus =
    counts.forbidden > 0
      ? "forbidden"
      : counts.borderline > 0
      ? "borderline"
      : counts.unclear > 0
      ? "unclear"
      : "allowed";

  return (
    <>
      <AppHeader
        crumbs={[
          { label: "Workspace" },
          { label: "Verlauf" },
          { label: "Detail" },
        ]}
      />

      <div className="flex-1 px-6 py-8 lg:px-10">
        <div className="flex flex-col gap-6">
          {/* Back link + actions */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/app/history">
                <ChevronLeft className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                Verlauf
              </Link>
            </Button>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm">
                <RefreshCcw className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                Erneut prüfen
              </Button>
              <Button variant="outline" size="sm">
                <Share2 className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                Teilen
              </Button>
              <Button size="sm">
                <Download className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                PDF-Report
              </Button>
              <button
                type="button"
                aria-label="Weitere Optionen"
                className="grid h-9 w-9 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-muted"
              >
                <MoreHorizontal className="h-4 w-4" aria-hidden />
              </button>
            </div>
          </div>

          {/* Title block */}
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-3">
              <span className="font-mono text-[11px] text-muted-foreground">
                {analysis.shortId}
              </span>
              <StatusPill status={highestStatus} size="sm" />
            </div>
            <h1 className="font-serif text-3xl leading-tight tracking-tight">
              {analysis.title}
            </h1>
            <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5" aria-hidden />
                {analysis.displayDate}
              </span>
              <span className="inline-flex items-center gap-1.5">
                <User className="h-3.5 w-3.5" aria-hidden />
                {analysis.editor.name}
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Tag className="h-3.5 w-3.5" aria-hidden />
                {analysis.category}
              </span>
              {analysis.sourceReference && (
                <span>Quelle: {analysis.sourceReference}</span>
              )}
            </div>
          </div>

          {/* Summary tiles */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <ComplianceScore score={analysis.score} sublabel="Risiko" />
            <ClaimCountTile
              count={counts.allowed}
              status="allowed"
              label="Konforme Claims"
            />
            <ClaimCountTile
              count={counts.borderline}
              status="borderline"
              label="Risiko-Claims"
            />
            <ClaimCountTile
              count={counts.forbidden}
              status="forbidden"
              label="Unzulässige Claims"
            />
          </div>

          {/* Two-column: Text + Claim-Cards */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <section
              aria-label="Originaltext"
              className="rounded-xl border border-border/70 bg-card p-6 shadow-sm"
            >
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-sm font-medium">Originaltext</h2>
                <span className="text-[11px] text-muted-foreground">
                  {analysis.claims.length} Claims markiert
                </span>
              </div>

              <MarkedText
                text={analysis.inputText}
                claims={analysis.claims}
              />

              <div className="mt-6 rounded-lg bg-muted/40 p-4">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Auf einen Blick
                </div>
                <ul className="mt-2 space-y-1.5 text-sm text-foreground/90">
                  {analysis.summary.map((s, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="mt-2 inline-block h-1 w-1 shrink-0 rounded-full bg-primary" />
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </section>

            <section aria-label="Bewertete Claims" className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-medium">Bewertete Claims</h2>
                <button
                  type="button"
                  className="inline-flex items-center gap-1 rounded-md bg-muted/60 px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
                >
                  Sortiert nach Risiko
                  <svg
                    viewBox="0 0 20 20"
                    className="h-3 w-3"
                    fill="currentColor"
                    aria-hidden
                  >
                    <path d="M5 8l5 5 5-5z" />
                  </svg>
                </button>
              </div>
              {analysis.claims.map((claim) => (
                <ClaimCard key={claim.id} claim={claim} />
              ))}
            </section>
          </div>

          <p className="max-w-3xl text-xs text-muted-foreground">
            ClaimGuard ist ein Assistenzsystem zur Compliance-Einschätzung und{" "}
            <strong className="font-semibold text-foreground">
              ersetzt keine Rechtsberatung
            </strong>
            . Im Zweifelsfall einen Fachanwalt für Wettbewerbsrecht konsultieren.
          </p>
        </div>
      </div>
    </>
  );
}
