import Link from "next/link";

const englishSections = [
  {
    title: "Public sources and human judgment",
    body: "syOSINT is designed for lawfully accessible public reporting. Source items become leads, not facts. A human analyst checks provenance, independence, timing, location consistency, contradictions, and manipulation risk before publication.",
  },
  {
    title: "Confidence, uncertainty, and corrections",
    body: "Confidence labels describe the support for a claim; they are not source reputation scores. Every published record states what remains uncertain. Corrections and withdrawals retain a visible history and stable incident identifier.",
  },
  {
    title: "Safety before speed",
    body: "Locations are delayed, generalized to administrative areas, or withheld when detail could endanger people. The public export excludes raw evidence, private notes, personal identifiers, device metadata, credentials, session data, and operationally sensitive detail.",
  },
  {
    title: "Telegram and platform limits",
    body: "Future collection is limited to approved public channels through the official API. It is read-only, never joins private or invite-only groups, never republishes full posts, and never sends Telegram-derived material to AI or machine-learning systems.",
  },
];

const arabicSections = [
  {
    title: "المصادر العامة والحكم البشري",
    body: "صُمم syOSINT للتقارير العامة المتاحة قانونياً. تُعامل المواد الواردة كمؤشرات لا كحقائق، ويراجع محلل بشري المصدر والاستقلال والتوقيت واتساق الموقع والتناقضات ومخاطر التلاعب قبل النشر.",
  },
  {
    title: "الثقة وعدم اليقين والتصحيحات",
    body: "تصف مستويات الثقة قوة الأدلة على الادعاء ولا تقيّم سمعة المصدر. يوضح كل سجل منشور ما يزال غير مؤكد، وتبقى التصحيحات وعمليات السحب ظاهرة مع معرّف ثابت للحادثة.",
  },
  {
    title: "السلامة قبل السرعة",
    body: "تؤخر المواقع أو تعمم إلى مناطق إدارية أو تحجب عندما قد تعرّض التفاصيل أشخاصاً للخطر. لا يتضمن التصدير العام الأدلة الخام أو الملاحظات الخاصة أو المعرّفات الشخصية أو بيانات الأجهزة أو بيانات الجلسات أو التفاصيل العملياتية الحساسة.",
  },
  {
    title: "تيليغرام وحدود المنصة",
    body: "يقتصر الجمع المستقبلي على القنوات العامة المعتمدة عبر الواجهة الرسمية وبصلاحية القراءة فقط. لا ينضم النظام إلى مجموعات خاصة أو بدعوات، ولا يعيد نشر النصوص الكاملة، ولا يرسل مواد تيليغرام إلى أنظمة الذكاء الاصطناعي أو تعلم الآلة.",
  },
];

export default function MethodologyPage() {
  return (
    <main className="methodology-page">
      <header className="methodology-hero">
        <p className="eyebrow">syOSINT publication standard</p>
        <h1>Methodology / المنهجية</h1>
        <p>
          A transparent, safety-first workflow for turning public reporting into cautious
          situational awareness.
        </p>
        <Link className="back-link" href="/">
          ← Return to situation desk
        </Link>
      </header>

      <div className="methodology-columns">
        <article lang="en">
          <h2>How publication works</h2>
          {englishSections.map((section) => (
            <section key={section.title}>
              <h3>{section.title}</h3>
              <p>{section.body}</p>
            </section>
          ))}
          <section>
            <h3>Map context and demonstration data</h3>
            <p>
              The bundled outline is derived from public-domain Natural Earth data.
              Boundaries provide geographic context and express no position on sovereignty or
              disputed territory. All incidents in this release are fictional synthetic fixtures.
            </p>
          </section>
        </article>

        <article lang="ar" dir="rtl">
          <h2>كيف تتم عملية النشر</h2>
          {arabicSections.map((section) => (
            <section key={section.title}>
              <h3>{section.title}</h3>
              <p>{section.body}</p>
            </section>
          ))}
          <section>
            <h3>سياق الخريطة والبيانات التجريبية</h3>
            <p>
              يعتمد مخطط الخريطة المضمّن على بيانات Natural Earth المتاحة للملكية العامة.
              تُعرض الحدود للسياق الجغرافي فقط ولا تعبّر عن موقف بشأن السيادة أو المناطق
              المتنازع عليها. جميع الحوادث في هذا الإصدار أمثلة اصطناعية خيالية.
            </p>
          </section>
        </article>
      </div>
    </main>
  );
}
