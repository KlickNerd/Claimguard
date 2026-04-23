import { AppHeader } from "@/components/app/app-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const SECTIONS = [
  {
    title: "Profil",
    description: "Name und E-Mail-Adresse.",
    fields: [
      { label: "Name", id: "name", value: "Julia Müller" },
      { label: "E-Mail", id: "email", value: "julia@apothera.de" },
    ],
  },
  {
    title: "Workspace",
    description: "Anzeige- und Rechnungsinformationen des Workspace.",
    fields: [
      { label: "Workspace-Name", id: "ws-name", value: "Apothera GmbH" },
      { label: "Umsatzsteuer-ID", id: "vatid", value: "DE123456789" },
    ],
  },
];

export default function SettingsPage() {
  return (
    <>
      <AppHeader crumbs={[{ label: "Workspace" }, { label: "Einstellungen" }]} />

      <div className="flex-1 px-6 py-8 lg:px-10">
        <div className="max-w-3xl">
          <h1 className="font-serif text-3xl leading-tight tracking-tight">
            Einstellungen
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Profil, Workspace und Abrechnungsoptionen.
          </p>

          <div className="mt-8 space-y-6">
            {SECTIONS.map((section) => (
              <section
                key={section.title}
                className="rounded-xl border border-border/70 bg-card p-6"
              >
                <h2 className="font-serif text-lg font-semibold tracking-tight">
                  {section.title}
                </h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  {section.description}
                </p>

                <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {section.fields.map((f) => (
                    <div key={f.id} className="flex flex-col gap-1.5">
                      <Label htmlFor={f.id} className="text-xs">
                        {f.label}
                      </Label>
                      <Input
                        id={f.id}
                        defaultValue={f.value}
                        className="h-9"
                      />
                    </div>
                  ))}
                </div>

                <div className="mt-5 flex items-center justify-end gap-2">
                  <Button variant="outline" size="sm">
                    Verwerfen
                  </Button>
                  <Button size="sm">Speichern</Button>
                </div>
              </section>
            ))}

            <section className="rounded-xl border border-border/70 bg-card p-6">
              <h2 className="font-serif text-lg font-semibold tracking-tight">
                Daten & Datenschutz
              </h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Exportiere alle eigenen Daten oder lösche den Account vollständig
                (Hard-Delete nach 30 Tagen).
              </p>
              <div className="mt-5 flex flex-wrap items-center gap-2">
                <Button variant="outline" size="sm">
                  Daten exportieren
                </Button>
                <Button variant="outline" size="sm">
                  Account löschen
                </Button>
              </div>
            </section>
          </div>
        </div>
      </div>
    </>
  );
}
