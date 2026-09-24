"use client";

import { useEffect, useMemo, useState } from "react";
import type { PublicNewsWire } from "@syosint/schemas";
import type { Dictionary, Locale } from "../i18n/types";
import { filterNewsWire } from "../lib/filter-news-wire";

export function NewsWire({
  wire,
  locale,
  dictionary,
}: {
  wire: PublicNewsWire;
  locale: Locale;
  dictionary: Dictionary;
}) {
  const [sourceId, setSourceId] = useState("");
  const [language, setLanguage] = useState<"" | "en" | "ar">("");
  const [stale, setStale] = useState(false);
  useEffect(() => {
    const update = () =>
      setStale(
        Date.now() - Date.parse(wire.lastSuccessfulRefreshAt) > 90 * 60 * 1000,
      );
    update();
    const timer = window.setInterval(update, 60 * 1000);
    return () => window.clearInterval(timer);
  }, [wire.lastSuccessfulRefreshAt]);
  const sources = useMemo(
    () =>
      Array.from(
        new Map(
          wire.entries.map((entry) => [entry.sourceId, entry.sourceLabel]),
        ),
      ).sort((left, right) =>
        left[1][locale].localeCompare(right[1][locale], locale),
      ),
    [wire.entries, locale],
  );
  const entries = useMemo(
    () =>
      filterNewsWire(wire.entries, {
        sourceIds: sourceId ? [sourceId] : [],
        languages: language ? [language] : [],
      }),
    [wire.entries, sourceId, language],
  );

  return (
    <section className="news-wire" aria-labelledby="news-wire-title">
      <div className="news-wire-heading">
        <div>
          <p className="eyebrow">RSS / ATOM</p>
          <h2 id="news-wire-title">{dictionary.newsWire.title}</h2>
          <strong className="wire-disclosure">
            {dictionary.newsWire.disclosure}
          </strong>
        </div>
        <div className="wire-refresh">
          <span>{dictionary.newsWire.refreshed}</span>
          <time dateTime={wire.lastSuccessfulRefreshAt}>
            {new Date(wire.lastSuccessfulRefreshAt).toLocaleString(
              locale === "ar" ? "ar-SY" : "en-GB",
              { timeZone: "UTC" },
            )} UTC
          </time>
          {wire.sources.delayed > 0 && (
            <span role="status" className="wire-delayed">
              {wire.sources.delayed} {dictionary.newsWire.delayed}
            </span>
          )}
          {stale && (
            <span role="alert" className="wire-delayed">
              {dictionary.newsWire.stale}
            </span>
          )}
        </div>
      </div>

      <div className="wire-filters">
        <label>
          {dictionary.newsWire.sourceFilter}
          <select value={sourceId} onChange={(event) => setSourceId(event.target.value)}>
            <option value="">{dictionary.newsWire.allSources}</option>
            {sources.map(([id, label]) => (
              <option value={id} key={id}>{label[locale]}</option>
            ))}
          </select>
        </label>
        <label>
          {dictionary.newsWire.languageFilter}
          <select
            value={language}
            onChange={(event) =>
              setLanguage(event.target.value as "" | "en" | "ar")
            }
          >
            <option value="">{dictionary.newsWire.allLanguages}</option>
            <option value="en">{dictionary.newsWire.english}</option>
            <option value="ar">{dictionary.newsWire.arabic}</option>
          </select>
        </label>
      </div>

      {entries.length === 0 ? (
        <p className="wire-empty">
          {stale || wire.sources.delayed > 0
            ? dictionary.newsWire.emptyDelayed
            : dictionary.newsWire.empty}
        </p>
      ) : (
        <ol className="wire-list">
          {entries.map((entry) => (
            <li key={entry.id}>
              <article>
                <div className="wire-meta">
                  <span>{entry.sourceLabel[locale]}</span>
                  <time dateTime={entry.publishedAt}>
                    {new Date(entry.publishedAt).toLocaleString(
                      locale === "ar" ? "ar-SY" : "en-GB",
                      { timeZone: "UTC" },
                    )} UTC
                  </time>
                </div>
                <h3 lang={entry.language} dir={entry.language === "ar" ? "rtl" : "ltr"}>
                  <a
                    href={entry.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`${entry.headline} — ${dictionary.newsWire.externalLinkContext}`}
                  >
                    {entry.headline}
                  </a>
                </h3>
              </article>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
