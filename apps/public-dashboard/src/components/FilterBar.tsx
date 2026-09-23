import type { ConfidenceLabel, IncidentCategory } from "@syosint/schemas";
import type { Dictionary } from "../i18n/types";

const categories: IncidentCategory[] = [
  "armed-conflict",
  "political-security",
  "humanitarian",
  "infrastructure",
  "border-crossing",
  "disinformation",
];

const confidenceLabels: ConfidenceLabel[] = [
  "unverified",
  "developing",
  "corroborated",
  "verified",
  "disputed",
  "false",
];

export function FilterBar({
  dictionary,
  selectedCategories,
  selectedConfidence,
  search,
  resultCount,
  onCategoryToggle,
  onConfidenceToggle,
  onSearchChange,
  onReset,
}: {
  dictionary: Dictionary;
  selectedCategories: IncidentCategory[];
  selectedConfidence: ConfidenceLabel[];
  search: string;
  resultCount: number;
  onCategoryToggle: (category: IncidentCategory) => void;
  onConfidenceToggle: (confidence: ConfidenceLabel) => void;
  onSearchChange: (search: string) => void;
  onReset: () => void;
}) {
  return (
    <section className="filter-panel" aria-labelledby="filters-title">
      <div className="filter-heading">
        <h2 id="filters-title">{dictionary.filters.title}</h2>
        <button type="button" onClick={onReset}>
          {dictionary.filters.reset}
        </button>
      </div>
      <label className="search-field">
        <span>{dictionary.filters.searchLabel}</span>
        <input
          type="search"
          value={search}
          placeholder={dictionary.filters.searchPlaceholder}
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </label>
      <fieldset>
        <legend>{dictionary.filters.categories}</legend>
        <div className="filter-options">
          {categories.map((category) => (
            <label key={category}>
              <input
                type="checkbox"
                checked={selectedCategories.includes(category)}
                onChange={() => onCategoryToggle(category)}
              />
              <span>{dictionary.categories[category]}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset>
        <legend>{dictionary.filters.confidence}</legend>
        <div className="filter-options">
          {confidenceLabels.map((confidence) => (
            <label key={confidence}>
              <input
                type="checkbox"
                checked={selectedConfidence.includes(confidence)}
                onChange={() => onConfidenceToggle(confidence)}
              />
              <span>{dictionary.confidence[confidence]}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <p role="status" aria-live="polite">
        {resultCount} {dictionary.filters.results}
      </p>
    </section>
  );
}
