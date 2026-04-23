export type ClaimStatus = "allowed" | "borderline" | "forbidden" | "unclear";

export type DemoClaim = {
  id: string;
  text: string;
  status: ClaimStatus;
  reasoning: string;
  legalBasis: string[];
  rewrite?: string;
};

export const DEMO_INPUT =
  "Unser Magnesium-Komplex unterstützt eine normale Muskelfunktion und sorgt für einen energiegeladenen Tag. Stärkt zusätzlich das Immunsystem und beugt Erkältungen vor.";

export const DEMO_CLAIMS: DemoClaim[] = [
  {
    id: "c-1",
    text: "unterstützt eine normale Muskelfunktion",
    status: "allowed",
    reasoning:
      "Zugelassener Health Claim aus dem EU-Register, sofern die Mindestmenge von 56,25 mg Magnesium pro Tagesdosis erreicht wird.",
    legalBasis: ["VO (EG) 1924/2006", "EU-Register ID 234", "VO (EU) 432/2012"],
  },
  {
    id: "c-2",
    text: "für einen energiegeladenen Tag",
    status: "borderline",
    reasoning:
      "Impliziter gesundheitsbezogener Claim. Zulässig nur als Verweis auf den zugelassenen Energiestoffwechsel-Claim und nur bei nachgewiesener Mindestmenge.",
    legalBasis: ["Art. 10 Abs. 3 HCVO", "BGH I ZR 252/16 (Detox)"],
    rewrite: `„Magnesium trägt zu einem normalen Energiestoffwechsel bei." (zugelassene Wortwahl)`,
  },
  {
    id: "c-3",
    text: "stärkt das Immunsystem und beugt Erkältungen vor",
    status: "forbidden",
    reasoning:
      "Krankheitsbezogene Aussage – nach Art. 7 LMIV und § 12 LFGB für Lebensmittel verboten. Vorbeugung benannter Krankheiten ist ausschließlich Arzneimitteln vorbehalten.",
    legalBasis: ["Art. 7 LMIV", "§ 12 LFGB", "OLG Frankfurt 6 U 109/22"],
    rewrite: `„Trägt zu einer normalen Funktion des Immunsystems bei." (Krankheitsbezug entfernt)`,
  },
];

export const STATUS_META: Record<
  ClaimStatus,
  { label: string; shortLabel: string; description: string }
> = {
  allowed: {
    label: "Konform",
    shortLabel: "Konform",
    description: "Entspricht einem zugelassenen Claim oder der aktuellen Rechtsprechung.",
  },
  borderline: {
    label: "Risiko",
    shortLabel: "Risiko",
    description: "Rechtlich grenzwertig – benötigt Begleitformulierung oder Reformulierung.",
  },
  forbidden: {
    label: "Unzulässig",
    shortLabel: "Unzulässig",
    description: "Widerspricht HCVO, LMIV, LFGB oder gefestigter Rechtsprechung.",
  },
  unclear: {
    label: "Unklar",
    shortLabel: "Unklar",
    description: "Keine eindeutige Rechtsquelle – manuelle Prüfung empfohlen.",
  },
};
