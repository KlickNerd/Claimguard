import { Users } from "lucide-react";
import { AppHeader } from "@/components/app/app-header";
import { Button } from "@/components/ui/button";

export default function TeamPage() {
  return (
    <>
      <AppHeader crumbs={[{ label: "Workspace" }, { label: "Team" }]} />

      <div className="flex-1 px-6 py-8 lg:px-10">
        <div className="flex flex-col gap-6">
          <div>
            <h1 className="font-serif text-3xl leading-tight tracking-tight">
              Team
            </h1>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              Team-Features sind für Version 1.1 geplant – Einladungen, Rollen und
              Multi-Workspace folgen direkt nach dem MVP-Launch.
            </p>
          </div>

          <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-border/70 bg-card/60 p-16 text-center">
            <span className="grid h-12 w-12 place-items-center rounded-full bg-accent text-accent-foreground">
              <Users className="h-5 w-5" aria-hidden />
            </span>
            <div>
              <span className="inline-flex items-center rounded-full bg-accent px-2.5 py-0.5 text-[11px] font-medium text-accent-foreground">
                V1.1 · In Entwicklung
              </span>
              <h2 className="mt-3 font-serif text-xl font-semibold tracking-tight">
                Gemeinsam prüfen.
              </h2>
              <p className="mt-2 max-w-md text-sm text-muted-foreground">
                Lade bis zu 10 Team-Mitglieder ein, vergib Rollen (Editor /
                Reviewer / Admin) und teile Reports workspace-weit.
              </p>
            </div>
            <Button variant="outline" size="sm">
              Auf V1.1 aufmerksam machen
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}
