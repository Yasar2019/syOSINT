import { DashboardClient } from "../components/DashboardClient";
import { loadPublicDataset } from "../lib/load-public-dataset";
import { loadPublicNewsWire } from "../lib/load-public-news-wire";

export default function HomePage() {
  return <DashboardClient dataset={loadPublicDataset()} newsWire={loadPublicNewsWire()} />;
}
