import { DashboardClient } from "../components/DashboardClient";
import { loadPublicDataset } from "../lib/load-public-dataset";

export default function HomePage() {
  return <DashboardClient dataset={loadPublicDataset()} />;
}
