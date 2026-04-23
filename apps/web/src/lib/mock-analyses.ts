import type { ClaimStatus, DemoClaim } from "@/lib/demo-data";
import { DEMO_CLAIMS, DEMO_INPUT } from "@/lib/demo-data";

export type AnalysisSource = "text" | "url" | "pdf";

export type AnalysisListItem = {
  id: string;
  shortId: string;
  title: string;
  category: "Supplement" | "Marketing" | "Functional Drink" | "Naturkosmetik";
  source: AnalysisSource;
  sourceReference?: string;
  counts: Record<ClaimStatus, number>;
  score: number;
  editor: { name: string; initials: string };
  createdAt: string;
  displayDate: string;
};

export type AnalysisDetail = AnalysisListItem & {
  inputText: string;
  claims: DemoClaim[];
  summary: string[];
};

export const MOCK_ANALYSES: AnalysisListItem[] = [
  {
    id: "chk_2k9f3a",
    shortId: "chk_2k9f3a",
    title: "Magnesium-Komplex 400 – Produktseite",
    category: "Supplement",
    source: "url",
    sourceReference: "shop.apothera.de/products/magnesium-komplex",
    counts: { allowed: 1, borderline: 1, forbidden: 1, unclear: 0 },
    score: 54,
    editor: { name: "Julia M.", initials: "JM" },
    createdAt: "2026-04-24T14:32:00Z",
    displayDate: "Heute, 14:32",
  },
  {
    id: "chk_2k9f2b",
    shortId: "chk_2k9f2b",
    title: `Newsletter „Spring Detox" Q2`,
    category: "Marketing",
    source: "text",
    counts: { allowed: 0, borderline: 2, forbidden: 3, unclear: 0 },
    score: 22,
    editor: { name: "Julia M.", initials: "JM" },
    createdAt: "2026-04-24T11:08:00Z",
    displayDate: "Heute, 11:08",
  },
  {
    id: "chk_2k9f1c",
    shortId: "chk_2k9f1c",
    title: "Vitamin-D3-Tropfen Etikett v4.pdf",
    category: "Supplement",
    source: "pdf",
    sourceReference: "Vitamin-D3-Tropfen Etikett v4.pdf",
    counts: { allowed: 4, borderline: 1, forbidden: 0, unclear: 0 },
    score: 88,
    editor: { name: "Tim B.", initials: "TB" },
    createdAt: "2026-04-23T16:50:00Z",
    displayDate: "Gestern, 16:50",
  },
  {
    id: "chk_2k9eze",
    shortId: "chk_2k9eze",
    title: "Naturkosmetik Serum – Landing",
    category: "Naturkosmetik",
    source: "url",
    counts: { allowed: 3, borderline: 2, forbidden: 1, unclear: 0 },
    score: 67,
    editor: { name: "Tim B.", initials: "TB" },
    createdAt: "2026-04-23T09:14:00Z",
    displayDate: "Gestern, 09:14",
  },
  {
    id: "chk_2k9eyf",
    shortId: "chk_2k9eyf",
    title: "Kollagen-Drink Werbeclaim Test",
    category: "Functional Drink",
    source: "text",
    counts: { allowed: 2, borderline: 0, forbidden: 0, unclear: 0 },
    score: 100,
    editor: { name: "Julia M.", initials: "JM" },
    createdAt: "2026-04-12T10:00:00Z",
    displayDate: "12.04.2026",
  },
  {
    id: "chk_2k9exg",
    shortId: "chk_2k9exg",
    title: "Adaptogen-Mix v2 – Amazon-Listing",
    category: "Supplement",
    source: "url",
    counts: { allowed: 1, borderline: 3, forbidden: 2, unclear: 0 },
    score: 41,
    editor: { name: "Julia M.", initials: "JM" },
    createdAt: "2026-04-11T10:00:00Z",
    displayDate: "11.04.2026",
  },
  {
    id: "chk_2k9esh",
    shortId: "chk_2k9esh",
    title: "Probiotika-Kapseln Faltblatt.pdf",
    category: "Supplement",
    source: "pdf",
    sourceReference: "Probiotika-Kapseln Faltblatt.pdf",
    counts: { allowed: 5, borderline: 0, forbidden: 0, unclear: 0 },
    score: 100,
    editor: { name: "Tim B.", initials: "TB" },
    createdAt: "2026-04-10T10:00:00Z",
    displayDate: "10.04.2026",
  },
];

export const MOCK_DETAILS: Record<string, AnalysisDetail> = {
  chk_2k9f3a: {
    ...MOCK_ANALYSES[0],
    inputText: DEMO_INPUT,
    claims: DEMO_CLAIMS,
    summary: [
      "1 Aussage entspricht direkt einem zugelassenen EU-Register-Claim.",
      "1 implizite Aussage benötigt Begleitformulierung nach Art. 10 Abs. 3 HCVO.",
      "1 krankheitsbezogene Aussage – sofortige Reformulierung empfohlen.",
    ],
  },
};

export const WORKSPACE = {
  name: "Apothera GmbH",
  plan: "Studio",
  members: 2,
  initials: "AP",
  usage: { used: 412, limit: 1000 },
};

export const KPIS = {
  analysesThisMonth: { value: 412, delta: "+12 %" },
  averageScore: { value: 78, delta: "+4 pp" },
  preventedRisks: { value: 94, window: "letzten 30 Tage" },
};

export const LEGAL_SOURCES_APP = [
  {
    title: "EU-Register zugelassener Health Claims",
    subtitle: "2.417 Einträge · aktualisiert 19.04.2026",
    items: 2417,
    badge: "wöchentlich",
  },
  {
    title: "VO (EG) 1924/2006 (HCVO)",
    subtitle: "konsolidierte Fassung",
    items: 29,
    badge: "Verordnung",
  },
  {
    title: "VO (EU) 432/2012",
    subtitle: "Liste zugelassener Claims",
    items: 222,
    badge: "Verordnung",
  },
  {
    title: "LMIV & LFGB",
    subtitle: "Art. 7 LMIV, § 12 LFGB u. a.",
    items: 18,
    badge: "Verordnung",
  },
  {
    title: "Paraphrasierte Urteile",
    subtitle: "BGH, OLG, LG",
    items: 34,
    badge: "redaktionell",
  },
  {
    title: "EFSA Scientific Opinions",
    subtitle: "Botanicals, On-Hold-Liste",
    items: 156,
    badge: "Wissenschaft",
  },
];
