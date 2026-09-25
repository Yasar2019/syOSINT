"use client";

import { useEffect, useMemo, useState } from "react";
import type { PublicNewsWire } from "@syosint/schemas";
import type { Dictionary, Locale } from "../i18n/types";
import { filterNewsWire } from "../lib/filter-news-wire";

const PAGE_SIZE = 25;

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
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
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
      [...wire.sourceStates].sort((left, right) =>
        left.label[locale].localeCompare(right.label[locale], locale),
      ),
    [wire.sourceStates, locale],
  );
  const entries = useMemo(
    () =>
      filterNewsWire(wire.entries, {
        sourceIds: sourceId ? [sourceId] : [],
        languages: language ? [language] : [],
      }),
    [wire.entries, sourceId, language],
  );
  const selectedState = wire.sourceStates.find((source) => source.id === sourceId);
  const visibleEntries = entries.slice(0, visibleCount);
  const emptyMessage = selectedState?.status === "delayed"
    ? dictionary.newsWire.sourceDelayed
    : selectedState && selectedState.entryCount === 0
      ? dictionary.newsWire.sourceEmpty
      : selectedState
        ? dictionary.newsWire.empty
        : wire.entries.length === 0 && (stale || wire.sources.delayed > 0)
          ? dictionary.newsWire.emptyDelayed
          : dictionary.newsWire.empty;

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

      <p className="wire-coverage">
        {wire.sources.configured} {dictionary.newsWire.configured} ·{" "}
        {wire.sources.healthy} {dictionary.newsWire.healthy} ·{" "}
        {wire.sources.delayed} {dictionary.newsWire.delayedCount} ·{" "}
        {wire.entries.length}{" "}
        {wire.entries.length === 1
          ? dictionary.newsWire.headline
          : dictionary.newsWire.headlines}
      </p>

      <div className="wire-filters">
        <label>
          {dictionary.newsWire.sourceFilter}
          <select
            value={sourceId}
            onChange={(event) => {
              setSourceId(event.target.value);
              setVisibleCount(PAGE_SIZE);
            }}
          >
            <option value="">{dictionary.newsWire.allSources}</option>
            {sources.map((source) => (
              <option value={source.id} key={source.id}>
                {source.label[locale]}
                {source.status === "delayed"
                  ? ` · ${dictionary.newsWire.delayedCount}`
                  : source.entryCount === 0
                    ? ` · ${dictionary.newsWire.noRecentHeadlines}`
                    : ""}
              </option>
            ))}
          </select>
        </label>
        <label>
          {dictionary.newsWire.languageFilter}
          <select
            value={language}
            onChange={(event) => {
              setLanguage(event.target.value as "" | "en" | "ar");
              setVisibleCount(PAGE_SIZE);
            }}
          >
            <option value="">{dictionary.newsWire.allLanguages}</option>
            <option value="en">{dictionary.newsWire.english}</option>
            <option value="ar">{dictionary.newsWire.arabic}</option>
          </select>
        </label>
      </div>

      {entries.length === 0 ? (
        <div className="wire-empty">
          <p>{emptyMessage}</p>
          {selectedState && (
            <a
              className="wire-attribution"
              href={selectedState.attributionUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              {selectedState.attribution}
            </a>
          )}
        </div>
      ) : (
        <>
          <ol className="wire-list">
            {visibleEntries.map((entry) => {
              const sourceState = wire.sourceStates.find(
                (source) => source.id === entry.sourceId,
              );
              return (
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
                    {sourceState && (
                      <a
                        className="wire-attribution"
                        href={sourceState.attributionUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {sourceState.attribution}
                      </a>
                    )}
                  </article>
                </li>
              );
            })}
          </ol>
          {visibleCount < entries.length && (
            <button
              className="wire-more"
              type="button"
              onClick={() => setVisibleCount((count) => count + PAGE_SIZE)}
            >
              {dictionary.newsWire.showMore}
            </button>
          )}
        </>
      )}
    </section>
  );
}
