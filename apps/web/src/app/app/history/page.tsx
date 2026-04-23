import Link from "next/link";
import {
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  Link2,
  ListFilter,
  Plus,
  Search,
} from "lucide-react";
import { AppHeader } from "@/components/app/app-header";
import { AmpelBar } from "@/components/app/ampel-bar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { MOCK_ANALYSES, type AnalysisSource } from "@/lib/mock-analyses";

const SOURCE_ICON: Record<AnalysisSource, typeof Link2> = {
  text: FileText,
  url: Link2,
  pdf: FileText,
};

function scoreTone(score: number): string {
  if (score >= 85) return "text-status-allowed";
  if (score >= 60) return "text-status-borderline";
  return "text-status-forbidden";
}

const FILTERS = [
  { label: "Alle Quellen" },
  { label: "Alle Kategorien" },
  { label: "Alle Nutzer" },
  { label: "Letzte 30 Tage" },
];

export default function HistoryPage() {
  return (
    <>
      <AppHeader crumbs={[{ label: "Workspace" }, { label: "Verlauf" }]} />

      <div className="flex-1 px-6 py-8 lg:px-10">
        <div className="flex flex-col gap-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="font-serif text-3xl leading-tight tracking-tight">
                Verlauf
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                248 Prüfungen · letzte Aktivität vor 14 Minuten
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm">
                <Download className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                Export CSV
              </Button>
              <Button size="sm" asChild>
                <Link href="/app">
                  <Plus className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                  Neue Prüfung
                </Link>
              </Button>
            </div>
          </div>

          {/* Filter bar */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative flex-1 min-w-[260px]">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
                aria-hidden
              />
              <Input
                type="search"
                placeholder="Nach Titel, ID oder Claim suchen…"
                className="h-9 pl-8"
              />
            </div>
            {FILTERS.map((f) => (
              <Button key={f.label} variant="outline" size="sm">
                <ListFilter className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                {f.label}
              </Button>
            ))}
          </div>

          {/* Table */}
          <div className="overflow-hidden rounded-xl border border-border/70 bg-card">
            <table className="w-full text-sm">
              <thead className="border-b border-border/60 bg-muted/40 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-5 py-3">Prüfung</th>
                  <th className="px-5 py-3">Kategorie</th>
                  <th className="px-5 py-3">Ampel</th>
                  <th className="px-5 py-3">Score</th>
                  <th className="px-5 py-3">Bearbeitet von</th>
                  <th className="px-5 py-3">Datum</th>
                  <th className="w-8 px-3 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {MOCK_ANALYSES.map((a) => {
                  const Icon = SOURCE_ICON[a.source];
                  const isLinked = a.id === "chk_2k9f3a";
                  return (
                    <tr
                      key={a.id}
                      className={cn(
                        "group border-b border-border/40 transition-colors last:border-0",
                        isLinked
                          ? "cursor-pointer hover:bg-muted/40"
                          : "cursor-not-allowed opacity-95",
                      )}
                    >
                      <td className="px-5 py-4">
                        <MaybeLink
                          isLinked={isLinked}
                          href={`/app/history/${a.id}`}
                          className="flex items-center gap-3"
                        >
                          <span className="grid h-8 w-8 place-items-center rounded-md bg-accent text-accent-foreground">
                            <Icon className="h-3.5 w-3.5" aria-hidden />
                          </span>
                          <span className="min-w-0">
                            <span className="block truncate font-medium text-foreground">
                              {a.title}
                            </span>
                            <span className="block font-mono text-[11px] text-muted-foreground">
                              {a.shortId}
                            </span>
                          </span>
                        </MaybeLink>
                      </td>
                      <td className="px-5 py-4">
                        <span className="inline-flex items-center rounded-md bg-muted/60 px-2 py-0.5 text-xs text-foreground/80">
                          {a.category}
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        <AmpelBar counts={a.counts} className="w-32" />
                      </td>
                      <td className="px-5 py-4">
                        <span
                          className={cn(
                            "font-serif text-base font-semibold tabular-nums",
                            scoreTone(a.score),
                          )}
                        >
                          {a.score}
                        </span>
                        <span className="text-xs text-muted-foreground"> / 100</span>
                      </td>
                      <td className="px-5 py-4">
                        <span className="inline-flex items-center gap-2">
                          <span className="grid h-6 w-6 place-items-center rounded-full bg-primary text-[10px] font-semibold text-primary-foreground">
                            {a.editor.initials}
                          </span>
                          <span className="text-foreground/80">{a.editor.name}</span>
                        </span>
                      </td>
                      <td className="px-5 py-4 text-muted-foreground">
                        {a.displayDate}
                      </td>
                      <td className="px-3 py-4 text-muted-foreground">
                        {isLinked ? (
                          <ChevronRight className="h-4 w-4 opacity-70 group-hover:opacity-100" aria-hidden />
                        ) : (
                          <span className="font-mono text-[10px]">Mock</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Zeige 1–7 von 248</span>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" disabled className="h-7 w-7 p-0">
                <ChevronLeft className="h-3.5 w-3.5" aria-hidden />
              </Button>
              <Button size="sm" className="h-7 min-w-7 px-2">1</Button>
              <Button variant="ghost" size="sm" className="h-7 min-w-7 px-2">2</Button>
              <Button variant="ghost" size="sm" className="h-7 min-w-7 px-2">3</Button>
              <span className="px-1 text-muted-foreground">…</span>
              <Button variant="ghost" size="sm" className="h-7 min-w-7 px-2">36</Button>
              <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
                <ChevronRight className="h-3.5 w-3.5" aria-hidden />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function MaybeLink({
  isLinked,
  href,
  className,
  children,
}: {
  isLinked: boolean;
  href: string;
  className?: string;
  children: React.ReactNode;
}) {
  return isLinked ? (
    <Link href={href} className={className}>
      {children}
    </Link>
  ) : (
    <span className={className}>{children}</span>
  );
}
