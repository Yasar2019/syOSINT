"use client";

import { useMemo, useState } from "react";
import type { PublicTelegramWire } from "@syosint/schemas";
import type { Dictionary, Locale } from "../i18n/types";

const PAGE_SIZE = 25;
type ReportingMode = "all" | "rss" | "telegram";

export function SourceReporting({ wire, locale, dictionary, onModeChange, hideTabs = false, hideFilters = false }: {
  wire: PublicTelegramWire;
  locale: Locale;
  dictionary: Dictionary;
  onModeChange?: (mode: ReportingMode) => void;
  hideTabs?: boolean;
  hideFilters?: boolean;
}) {
  const [mode, setMode] = useState<ReportingMode>("all");
  const [source, setSource] = useState("");
  const [language, setLanguage] = useState<"" | "en" | "ar">("");
  const [count, setCount] = useState(PAGE_SIZE);
  const labels = dictionary.telegramWire;
  const sources = useMemo(() => [...new Set(wire.entries.map((entry) => entry.channel.name))].sort(), [wire.entries]);
  const entries = wire.entries.filter((entry) =>
    (!source || entry.channel.name === source) &&
    (!language || entry.channel.language === language || entry.channel.language === "mixed"),
  );

  return (
    <section className="news-wire telegram-wire" aria-labelledby="telegram-wire-title">
      {!hideTabs && <div role="tablist" aria-label={labels.reportingMode} className="reporting-tabs">
        {(["all", "rss", "telegram"] as const).map((value) => (
          <button key={value} type="button" role="tab" aria-selected={mode === value} onClick={() => {
            setMode(value);
            onModeChange?.(value);
          }}>{labels.modes[value]}</button>
        ))}
      </div>}
      {(hideTabs || mode !== "rss" && (mode === "telegram" || wire.entries.length > 0)) && <div role="tabpanel" aria-label={labels.modes.telegram}>
        <div className="news-wire-heading">
          <div>
            <p className="eyebrow">TELEGRAM</p>
            <h2 id="telegram-wire-title">{labels.title}</h2>
            <strong className="wire-disclosure">{labels.disclosure}</strong>
          </div>
          <div className="wire-refresh"><span>{labels.updated}</span><time dateTime={wire.lastEditorialUpdateAt}>
            {new Date(wire.lastEditorialUpdateAt).toLocaleString(locale === "ar" ? "ar-SY" : "en-GB", { timeZone: "UTC" })} UTC
          </time></div>
        </div>
        <p className="wire-coverage">{labels.window}</p>
        {!hideFilters && <div className="wire-filters">
          <label>{labels.title} · {dictionary.newsWire.sourceFilter}<select value={source} onChange={(event) => { setSource(event.target.value); setCount(PAGE_SIZE); }}>
            <option value="">{dictionary.newsWire.allSources}</option>
            {sources.map((name) => <option value={name} key={name}>{name}</option>)}
          </select></label>
          <label>{labels.title} · {dictionary.newsWire.languageFilter}<select value={language} onChange={(event) => { setLanguage(event.target.value as "" | "en" | "ar"); setCount(PAGE_SIZE); }}>
            <option value="">{dictionary.newsWire.allLanguages}</option>
            <option value="en">{dictionary.newsWire.english}</option>
            <option value="ar">{dictionary.newsWire.arabic}</option>
          </select></label>
        </div>}
        {entries.length === 0 ? <p className="wire-empty">{labels.empty}</p> : <ol className="wire-list">
          {entries.slice(0, count).map((entry) => <li key={entry.id}><article>
            <div className="wire-meta"><span>{entry.channel.name}</span><time dateTime={entry.publishedAt}>
              {new Date(entry.publishedAt).toLocaleString(locale === "ar" ? "ar-SY" : "en-GB", { timeZone: "UTC" })} UTC
            </time></div>
            <p className="telegram-status">{labels.status[entry.status]}</p>
            {entry.status === "withdrawn" ? <p>{labels.withdrawn}</p> :
              <h3 dir={locale === "ar" ? "rtl" : "ltr"} lang={locale}><a href={entry.url} target="_blank" rel="noopener noreferrer" aria-label={`${entry.headline[locale]} — ${dictionary.newsWire.externalLinkContext}`}>{entry.headline[locale]}</a></h3>}
            {entry.revisions.length > 0 && <div className="telegram-revisions"><strong>{labels.history}</strong><ol>{entry.revisions.map((revision, index) => <li key={`${revision.revisedAt}-${index}`}>
              <time dateTime={revision.revisedAt}>{new Date(revision.revisedAt).toLocaleString(locale === "ar" ? "ar-SY" : "en-GB", { timeZone: "UTC" })} UTC</time>
              {revision.previousHeadline && <p>{labels.previous}: <span dir={locale === "ar" ? "rtl" : "ltr"}>{revision.previousHeadline[locale]}</span></p>}
              <p>{revision.reason[locale]}</p>
            </li>)}</ol></div>}
          </article></li>)}
        </ol>}
        {count < entries.length && <button className="wire-more" type="button" onClick={() => setCount((value) => value + PAGE_SIZE)}>{dictionary.newsWire.showMore}</button>}
      </div>}
    </section>
  );
}
