import type { Dictionary } from "../i18n/types";

export function DemoBanner({ dictionary }: { dictionary: Dictionary }) {
  return (
    <section className="demo-banner" aria-labelledby="demo-banner-title">
      <strong id="demo-banner-title">{dictionary.demo.title}</strong>
      <span>{dictionary.demo.body}</span>
    </section>
  );
}
