"use client";

import { useMemo, useState } from "react";
import type { PublicNewsWire, PublicTelegramEntry, PublicTelegramWire } from "@syosint/schemas";
import type { Dictionary, Locale } from "../i18n/types";
import { NewsWire } from "./NewsWire";
import { SourceReporting } from "./SourceReporting";

const PAGE_SIZE = 25;
type Mode = "all" | "rss" | "telegram";

export function ReportingHub({ newsWire, telegramWire, locale, dictionary }: {
  newsWire: PublicNewsWire;
  telegramWire: PublicTelegramWire;
  locale: Locale;
  dictionary: Dictionary;
}) {
  const [mode, setMode] = useState<Mode>("all");
  const [source, setSource] = useState("");
  const [language, setLanguage] = useState<"" | "en" | "ar">("");
  const [since, setSince] = useState("");
  const [count, setCount] = useState(PAGE_SIZE);
  const labels = dictionary.telegramWire;
  const dateMatches = (publishedAt: string) => !since || publishedAt.slice(0, 10) >= since;
  const rss = newsWire.entries.filter((entry) =>
    (!source || source === `rss:${entry.sourceId}`) &&
    (!language || entry.language === language) && dateMatches(entry.publishedAt));
  const telegram = telegramWire.entries.filter((entry) =>
    (!source || source === `telegram:${entry.channel.username.toLowerCase()}`) &&
    (!language || entry.channel.language === language || entry.channel.language === "mixed") &&
    dateMatches(entry.publishedAt));
  const sources = useMemo(() => [
    ...newsWire.sourceStates.map((item) => ({ id: `rss:${item.id}`, label: item.label[locale] })),
    ...Array.from(new Map(telegramWire.entries.map((item) => [item.channel.username.toLowerCase(), item.channel.name])).entries(),
      ([username, name]) => ({ id: `telegram:${username}`, label: `${name} · Telegram` })),
  ].sort((a, b) => a.label.localeCompare(b.label, locale)), [newsWire.sourceStates, telegramWire.entries, locale]);
  const combined = [...rss.map((entry) => ({ platform: "rss" as const, entry })),
    ...telegram.map((entry) => ({ platform: "telegram" as const, entry }))]
    .sort((a, b) => Date.parse(b.entry.publishedAt) - Date.parse(a.entry.publishedAt) ||
      a.entry.id.localeCompare(b.entry.id));
  const trimmedNews = { ...newsWire, entries: rss };
  const trimmedTelegram = { ...telegramWire, entries: telegram };
  const date = (timestamp: string) => `${new Date(timestamp).toLocaleString(
    locale === "ar" ? "ar-SY" : "en-GB", { timeZone: "UTC" })} UTC`;

  function selectMode(next: Mode) { setMode(next); setCount(PAGE_SIZE); }
  function updateSource(next: string) { setSource(next); setCount(PAGE_SIZE); }
  function updateLanguage(next: "" | "en" | "ar") { setLanguage(next); setCount(PAGE_SIZE); }
  function updateSince(next: string) { setSince(next); setCount(PAGE_SIZE); }

  function telegramCard(entry: PublicTelegramEntry) {
    return <>
      <div className="wire-meta"><span>{entry.channel.name} · Telegram</span><time dateTime={entry.publishedAt}>{date(entry.publishedAt)}</time></div>
      <p className="telegram-status">{labels.disclosure} · {labels.status[entry.status]}</p>
      {entry.status === "withdrawn" ? <p>{labels.withdrawn}</p> :
        <h3 lang={locale} dir={locale === "ar" ? "rtl" : "ltr"}><a href={entry.url} target="_blank" rel="noopener noreferrer"
          aria-label={`${entry.headline[locale]} — ${dictionary.newsWire.externalLinkContext}`}>{entry.headline[locale]}</a></h3>}
      {entry.revisions.length > 0 && <div className="telegram-revisions"><strong>{labels.history}</strong><ol>
        {entry.revisions.map((revision, index) => <li key={`${revision.revisedAt}-${index}`}>
          <time dateTime={revision.revisedAt}>{date(revision.revisedAt)}</time>
          {revision.previousHeadline && <p>{labels.previous}: <span dir={locale === "ar" ? "rtl" : "ltr"}>{revision.previousHeadline[locale]}</span></p>}
          <p>{revision.reason[locale]}</p>
        </li>)}
      </ol></div>}
    </>;
  }

  return <>
    <section className="reporting-controls" aria-label={labels.reportingMode}>
      <div role="tablist" aria-label={labels.reportingMode} className="reporting-tabs">
        {(["all", "rss", "telegram"] as const).map((value) => <button type="button" role="tab" key={value}
          aria-selected={mode === value} onClick={() => selectMode(value)}>{labels.modes[value]}</button>)}
      </div>
      <div className="wire-filters">
        <label>{dictionary.newsWire.sourceFilter}<select value={source} onChange={(event) => updateSource(event.target.value)}>
          <option value="">{dictionary.newsWire.allSources}</option>
          {sources.map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}
        </select></label>
        <label>{dictionary.newsWire.languageFilter}<select value={language} onChange={(event) => updateLanguage(event.target.value as "" | "en" | "ar")}>
          <option value="">{dictionary.newsWire.allLanguages}</option>
          <option value="en">{dictionary.newsWire.english}</option>
          <option value="ar">{dictionary.newsWire.arabic}</option>
        </select></label>
        <label>{labels.dateFilter}<input type="date" value={since} onChange={(event) => updateSince(event.target.value)} /></label>
      </div>
    </section>
    {mode === "all" && <section className="news-wire" aria-labelledby="news-wire-title">
      <div className="news-wire-heading"><div>
        <p className="eyebrow">RSS / ATOM · TELEGRAM</p>
        <h2 id="news-wire-title">{dictionary.newsWire.title}</h2>
        <strong className="wire-disclosure">{dictionary.newsWire.disclosure}</strong>
      </div><div className="wire-refresh">
        <span>{dictionary.newsWire.refreshed}</span><time dateTime={newsWire.lastSuccessfulRefreshAt}>{date(newsWire.lastSuccessfulRefreshAt)}</time>
        {newsWire.sources.delayed > 0 && <span role="status" className="wire-delayed">{newsWire.sources.delayed} {dictionary.newsWire.delayed}</span>}
        <span>{labels.updated}</span><time dateTime={telegramWire.lastEditorialUpdateAt}>{date(telegramWire.lastEditorialUpdateAt)}</time>
      </div></div>
      <p className="wire-coverage">{newsWire.sources.configured} {dictionary.newsWire.configured} · {newsWire.sources.healthy} {dictionary.newsWire.healthy} · {newsWire.sources.delayed} {dictionary.newsWire.delayedCount} · {newsWire.entries.length} {newsWire.entries.length === 1 ? dictionary.newsWire.headline : dictionary.newsWire.headlines}</p>
      {combined.length === 0 ? <p className="wire-empty">{dictionary.newsWire.empty}</p> : <ol className="wire-list">
        {combined.slice(0, count).map(({ platform, entry }) => <li key={`${platform}:${entry.id}`}><article>
          {platform === "telegram" ? telegramCard(entry) : <>
            <div className="wire-meta"><span>{entry.sourceLabel[locale]} · RSS / Atom</span><time dateTime={entry.publishedAt}>{date(entry.publishedAt)}</time></div>
            <p className="telegram-status">{dictionary.newsWire.disclosure}</p>
            <h3 lang={entry.language} dir={entry.language === "ar" ? "rtl" : "ltr"}><a href={entry.url} target="_blank" rel="noopener noreferrer"
              aria-label={`${entry.headline} — ${dictionary.newsWire.externalLinkContext}`}>{entry.headline}</a></h3>
            {newsWire.sourceStates.find((state) => state.id === entry.sourceId) && <a className="wire-attribution"
              href={newsWire.sourceStates.find((state) => state.id === entry.sourceId)!.attributionUrl}
              target="_blank" rel="noopener noreferrer">{newsWire.sourceStates.find((state) => state.id === entry.sourceId)!.attribution}</a>}
          </>}
        </article></li>)}
      </ol>}
      {count < combined.length && <button className="wire-more" type="button" onClick={() => setCount((value) => value + PAGE_SIZE)}>{dictionary.newsWire.showMore}</button>}
    </section>}
    {mode === "rss" && <NewsWire wire={trimmedNews} locale={locale} dictionary={dictionary} hideFilters />}
    {mode === "telegram" && <SourceReporting wire={trimmedTelegram} locale={locale} dictionary={dictionary} hideTabs hideFilters />}
  </>;
}
