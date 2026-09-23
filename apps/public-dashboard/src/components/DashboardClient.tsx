"use client";

import { useMemo, useState } from "react";
import type {
  ConfidenceLabel,
  IncidentCategory,
  PublicDataset,
} from "@syosint/schemas";
import { getDictionary, getDirection } from "../i18n/get-dictionary";
import type { Locale } from "../i18n/types";
import { EMPTY_FILTERS, filterIncidents } from "../lib/filter-incidents";
import { DemoBanner } from "./DemoBanner";
import { FilterBar } from "./FilterBar";
import { Header } from "./Header";
import { IncidentDetail } from "./IncidentDetail";
import { IncidentFeed } from "./IncidentFeed";
import { SummaryCards } from "./SummaryCards";
import { SyriaMap } from "./SyriaMap";
import { Timeline } from "./Timeline";
import Link from "next/link";

function toggleValue<T>(values: T[], value: T): T[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

export function DashboardClient({ dataset }: { dataset: PublicDataset }) {
  const [locale, setLocale] = useState<Locale>("en");
  const [categories, setCategories] = useState<IncidentCategory[]>([]);
  const [confidence, setConfidence] = useState<ConfidenceLabel[]>([]);
  const [search, setSearch] = useState("");
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const dictionary = getDictionary(locale);
  const incidents = useMemo(
    () => filterIncidents(dataset.incidents, { categories, confidence, search }),
    [dataset.incidents, categories, confidence, search],
  );
  const selectedIncident = dataset.incidents.find((item) => item.id === selectedIncidentId);

  function resetFilters() {
    setCategories(EMPTY_FILTERS.categories);
    setConfidence(EMPTY_FILTERS.confidence);
    setSearch(EMPTY_FILTERS.search);
  }

  return (
    <div
      className="dashboard-root"
      data-testid="dashboard-root"
      dir={getDirection(locale)}
      lang={locale}
    >
      <a className="skip-link" href="#main-content">
        {dictionary.accessibility.skipToContent}
      </a>
      <Header
        locale={locale}
        dictionary={dictionary}
        generatedAt={dataset.generatedAt}
        onLocaleChange={setLocale}
      />
      <DemoBanner dictionary={dictionary} />
      <main id="main-content">
        <SummaryCards incidents={incidents} dictionary={dictionary} />
        <FilterBar
          dictionary={dictionary}
          selectedCategories={categories}
          selectedConfidence={confidence}
          search={search}
          resultCount={incidents.length}
          onCategoryToggle={(category) => setCategories(toggleValue(categories, category))}
          onConfidenceToggle={(label) => setConfidence(toggleValue(confidence, label))}
          onSearchChange={setSearch}
          onReset={resetFilters}
        />
        <div className="situation-grid">
          <SyriaMap
            incidents={incidents}
            locale={locale}
            dictionary={dictionary}
            onSelect={setSelectedIncidentId}
          />
          <Timeline
            incidents={incidents}
            locale={locale}
            dictionary={dictionary}
            onSelect={setSelectedIncidentId}
          />
          <IncidentFeed
            incidents={incidents}
            locale={locale}
            dictionary={dictionary}
            onSelect={setSelectedIncidentId}
          />
        </div>
        {selectedIncident ? (
          <IncidentDetail
            incident={selectedIncident}
            locale={locale}
            dictionary={dictionary}
            onClose={() => setSelectedIncidentId(null)}
          />
        ) : null}
      </main>
      <footer className="site-footer">
        <p>syOSINT · Apache-2.0 · {dictionary.demo.title}</p>
        <nav aria-label={dictionary.navigation.methodology}>
          <Link href="/methodology/">{dictionary.navigation.methodology}</Link>
          <a href="https://github.com/Yasar2019/syOSINT">
            {dictionary.navigation.repository}
          </a>
        </nav>
      </footer>
    </div>
  );
}
