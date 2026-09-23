import { ar } from "./ar";
import { en } from "./en";
import type { Dictionary, Locale } from "./types";

export function getDictionary(locale: Locale): Dictionary {
  switch (locale) {
    case "ar":
      return ar;
    case "en":
      return en;
  }
}

export function getDirection(locale: Locale): "ltr" | "rtl" {
  return locale === "ar" ? "rtl" : "ltr";
}
