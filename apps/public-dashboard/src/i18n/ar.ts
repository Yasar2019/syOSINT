import type { Dictionary } from "./types";

export const ar = {
  navigation: {
    methodology: "المنهجية",
    repository: "الشيفرة المصدرية",
  },
  brand: {
    eyebrow: "مراقب مفتوح المصدر للأوضاع",
    title: "غرفة متابعة سوريا",
    subtitle: "تقارير عامة يراجعها البشر مع توضيح مستوى عدم اليقين.",
    lastUpdated: "آخر تحديث للبيانات",
  },
  demo: {
    title: "بيانات توضيحية فقط",
    body: "جميع الحوادث المعروضة في هذه المرحلة خيالية ولا تمثل حدثاً أو شخصاً حقيقياً.",
  },
  filters: {
    title: "تصفية الحوادث",
    searchLabel: "البحث في الحوادث",
    searchPlaceholder: "ابحث في العناوين أو الملخصات أو المواقع",
    categories: "الفئات",
    confidence: "مستوى الثقة",
    reset: "إعادة ضبط عوامل التصفية",
    results: "حادثة ظاهرة",
  },
  categories: {
    "armed-conflict": "نزاع مسلح",
    "political-security": "سياسي وأمني",
    humanitarian: "إنساني",
    infrastructure: "البنية التحتية",
    "border-crossing": "الحدود والمعابر",
    disinformation: "معلومات مضللة",
  },
  confidence: {
    unverified: "غير متحقق",
    developing: "قيد التطور",
    corroborated: "مؤكد بمصادر مستقلة",
    verified: "متحقق",
    disputed: "متنازع عليه",
    false: "زائف",
  },
  status: {
    published: "منشور",
    corrected: "مصحح",
    withdrawn: "مسحوب",
  },
  summary: {
    total: "الحوادث الظاهرة",
    verified: "مؤكدة أو متحققة",
    needsAttention: "متنازع عليها أو غير متحققة",
  },
  feed: {
    title: "موجز الحوادث",
    empty: "لا توجد حوادث تطابق عوامل التصفية الحالية.",
    viewDetails: "عرض التفاصيل",
  },
  detail: {
    title: "تفاصيل الحادثة",
    close: "إغلاق التفاصيل",
    occurred: "وقت الحدوث",
    updated: "آخر مراجعة",
    sources: "المراجع العامة",
    uncertainty: "ما يزال غير مؤكد",
    corrections: "سجل التصحيحات",
    noCorrections: "لا توجد تصحيحات مسجلة.",
  },
  map: {
    title: "خريطة الوضع في سوريا",
    description: "مواقع توضيحية معممة من دون مواقع تكتيكية مباشرة.",
    noLocation: "الموقع محجوب",
  },
  timeline: {
    title: "الخط الزمني للنشاط",
  },
  methodology: {
    title: "المنهجية",
    intro: "كيف يفصل syOSINT بين الجمع والتحقق ومراجعة السلامة والنشر.",
  },
  accessibility: {
    skipToContent: "تخطي إلى المحتوى",
    openIncident: "فتح الحادثة",
    externalLink: "يفتح في علامة تبويب جديدة",
  },
} satisfies Dictionary;
