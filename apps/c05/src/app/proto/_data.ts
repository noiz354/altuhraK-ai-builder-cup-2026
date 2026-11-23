// Synthetic demo data for the UI prototype. Every name is fictional.

export type QuadrantKey = "Q1" | "Q2" | "Q3" | "Q4";
export type QuadrantState = "complete" | "short" | "unsure";
export type Confidence = "Yakin" | "Cukup yakin" | "Ragu";

export const MENU_TODAY = {
  date: "Senin, 23 Nov 2026",
  kitchen: "SPPG Cempaka Putih",
  batch: "B-1123-02",
  school: "SDN Cempaka 03",
  quadrants: [
    { key: "Q1" as QuadrantKey, name: "Nasi", item: "Nasi putih" },
    { key: "Q2" as QuadrantKey, name: "Lauk", item: "Ayam bumbu kecap" },
    { key: "Q3" as QuadrantKey, name: "Sayur", item: "Sayur bening bayam" },
    { key: "Q4" as QuadrantKey, name: "Buah", item: "Pisang" },
  ],
};

export const BEFORE_RESULT: {
  key: QuadrantKey;
  state: QuadrantState;
  note: string;
}[] = [
  { key: "Q1", state: "complete", note: "Porsi sesuai manifest" },
  { key: "Q2", state: "complete", note: "1 potong ayam terlihat" },
  { key: "Q3", state: "short", note: "Kompartemen sayur kosong" },
  { key: "Q4", state: "complete", note: "1 buah pisang" },
];

export const AFTER_RESULT: { key: QuadrantKey; left: number; confidence: Confidence }[] = [
  { key: "Q1", left: 18, confidence: "Yakin" },
  { key: "Q2", left: 6, confidence: "Yakin" },
  { key: "Q3", left: 70, confidence: "Cukup yakin" },
  { key: "Q4", left: 12, confidence: "Yakin" },
];

export const CLASSES = ["1A", "2B", "3A", "4C", "5B", "6A"];

export const KPI = {
  waste: 27,
  wasteDelta: -11,
  menusToReview: 3,
  eaten: 73,
  cartridges: 1240,
  schools: 8,
};

export type MenuRow = {
  menu: string;
  waste: number;
  trend: "naik" | "turun" | "stabil";
  schools: { name: string; waste: number }[];
};

export const MENU_WASTE: MenuRow[] = [
  {
    menu: "Sayur bening bayam",
    waste: 68,
    trend: "naik",
    schools: [
      { name: "SDN Cempaka 03", waste: 74 },
      { name: "SDN Rawasari 01", waste: 69 },
      { name: "SMPN 41", waste: 52 },
    ],
  },
  {
    menu: "Tumis labu siam",
    waste: 54,
    trend: "stabil",
    schools: [
      { name: "SDN Cempaka 03", waste: 58 },
      { name: "SDN Rawasari 01", waste: 55 },
      { name: "SMPN 41", waste: 44 },
    ],
  },
  {
    menu: "Ikan pindang",
    waste: 41,
    trend: "turun",
    schools: [
      { name: "SDN Cempaka 03", waste: 45 },
      { name: "SDN Rawasari 01", waste: 40 },
      { name: "SMPN 41", waste: 36 },
    ],
  },
  {
    menu: "Ayam bumbu kecap",
    waste: 9,
    trend: "stabil",
    schools: [
      { name: "SDN Cempaka 03", waste: 8 },
      { name: "SDN Rawasari 01", waste: 11 },
      { name: "SMPN 41", waste: 7 },
    ],
  },
  {
    menu: "Nasi putih",
    waste: 16,
    trend: "turun",
    schools: [
      { name: "SDN Cempaka 03", waste: 18 },
      { name: "SDN Rawasari 01", waste: 15 },
      { name: "SMPN 41", waste: 14 },
    ],
  },
];

// Portions through the day for the flow ribbon: cooked → delivered → eaten → left.
export const FLOW = [
  { stage: "Dimasak", value: 1240, note: "porsi" },
  { stage: "Dikirim", value: 1228, note: "99% tepat waktu" },
  { stage: "Dimakan", value: 905, note: "73% dari dikirim" },
  { stage: "Sisa", value: 323, note: "27% terbuang" },
];

export const TREND_WEEK = [
  { day: "Sen", waste: 34 },
  { day: "Sel", waste: 31 },
  { day: "Rab", waste: 29 },
  { day: "Kam", waste: 33 },
  { day: "Jum", waste: 27 },
];

export const TREND_MONTH = [
  { day: "M1", waste: 38 },
  { day: "M2", waste: 35 },
  { day: "M3", waste: 31 },
  { day: "M4", waste: 27 },
];

export type Proposal = {
  id: string;
  kind: "remove" | "add";
  menu: string;
  reason: string;
  nutrition: string;
  supplier: string;
  distanceKm: number;
};

export const PROPOSALS: Proposal[] = [
  {
    id: "p1",
    kind: "remove",
    menu: "Sayur bening bayam",
    reason: "Sisa 68% selama 5 hari, paling tinggi di SD.",
    nutrition: "Serat 2,1 g",
    supplier: "Tani Makmur",
    distanceKm: 38,
  },
  {
    id: "p2",
    kind: "remove",
    menu: "Tumis labu siam",
    reason: "Sisa 54%, keluhan rasa hambar dari 3 kelas.",
    nutrition: "Serat 1,7 g",
    supplier: "Tani Makmur",
    distanceKm: 38,
  },
  {
    id: "p3",
    kind: "add",
    menu: "Tumis buncis wortel",
    reason: "Bahan musiman, gizi setara, disukai di uji rasa SD.",
    nutrition: "Serat 2,8 g",
    supplier: "Kebun Sumber Rejeki",
    distanceKm: 12,
  },
];

export type ChainNode = {
  id: string;
  title: string;
  detail: string;
  meta: string;
  hash: string;
};

export const TRACE_MENUS = [
  { id: "t1", menu: "Sayur bening bayam", date: "20 Nov 2026", issue: "Sisa 68%" },
  { id: "t2", menu: "Ayam bumbu kecap", date: "19 Nov 2026", issue: "Laporan mual (3)" },
  { id: "t3", menu: "Ikan pindang", date: "18 Nov 2026", issue: "Sisa 41%" },
];

export const CHAIN: ChainNode[] = [
  {
    id: "n1",
    title: "Supplier",
    detail: "Tani Makmur · Bogor",
    meta: "Terverifikasi dinas sejak Agu 2026",
    hash: "a91f…3c2e",
  },
  {
    id: "n2",
    title: "Lot bahan L-0412",
    detail: "Bayam 40 kg · 38 km · tiba 6,4 °C",
    meta: "Rp 11.500/kg · diterima 05.42",
    hash: "7d0b…e911",
  },
  {
    id: "n3",
    title: "Batch masak B-1120-01",
    detail: "SPPG Cempaka Putih · 1.240 porsi",
    meta: "Selesai 09.10 · 3 kru",
    hash: "c44a…02bd",
  },
  {
    id: "n4",
    title: "Cartridge before",
    detail: "Q3 sayur kosong di 4 cartridge, diperbaiki",
    meta: "Dicek Gemini 09.18 · ditinjau Bu Rina",
    hash: "19ee…8f70",
  },
  {
    id: "n5",
    title: "Sekolah",
    detail: "SDN Cempaka 03 · 214 cartridge diterima",
    meta: "Diterima Pak Joko 11.05",
    hash: "5b7c…a4d1",
  },
  {
    id: "n6",
    title: "Cartridge after",
    detail: "Sayur tersisa 74% (sampel 18 cartridge)",
    meta: "Dicek Gemini 12.40",
    hash: "e2f9…6c13",
  },
];
