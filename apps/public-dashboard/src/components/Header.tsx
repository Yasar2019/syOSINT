import Link from "next/link";
import type { Dictionary, Locale } from "../i18n/types";

export function Header({
  locale,
  dictionary,
  generatedAt,
  onLocaleChange,
}: {
  locale: Locale;
  dictionary: Dictionary;
  generatedAt: string;
  onLocaleChange: (locale: Locale) => void;
}) {
  const timestamp = new Intl.DateTimeFormat(locale === "ar" ? "ar" : "en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(generatedAt));

  return (
    <header className="site-header">
      <div>
        <p className="eyebrow">{dictionary.brand.eyebrow}</p>
        <h1>{dictionary.brand.title}</h1>
        <p className="subtitle">{dictionary.brand.subtitle}</p>
        <p className="updated-at">
          {dictionary.brand.lastUpdated}: {timestamp} UTC
        </p>
      </div>
      <div className="header-actions">
        <div className="locale-switcher" aria-label="Language / اللغة">
          <button
            type="button"
            aria-pressed={locale === "en"}
            onClick={() => onLocaleChange("en")}
          >
            English
          </button>
          <button
            type="button"
            aria-pressed={locale === "ar"}
            onClick={() => onLocaleChange("ar")}
          >
            العربية
          </button>
        </div>
        <nav aria-label={dictionary.navigation.methodology}>
          <Link href="/methodology/">{dictionary.navigation.methodology}</Link>
          <a
            href="https://github.com/Yasar2019/syOSINT"
            target="_blank"
            rel="noopener noreferrer"
          >
            {dictionary.navigation.repository}
          </a>
        </nav>
      </div>
    </header>
  );
}
