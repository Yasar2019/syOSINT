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
        <IncidentFeed
          incidents={incidents}
          locale={locale}
          dictionary={dictionary}
          onSelect={setSelectedIncidentId}
        />
        {selectedIncident ? (
          <IncidentDetail
            incident={selectedIncident}
            locale={locale}
            dictionary={dictionary}
            onClose={() => setSelectedIncidentId(null)}
          />
        ) : null}
      </main>
    </div>
  );
}
