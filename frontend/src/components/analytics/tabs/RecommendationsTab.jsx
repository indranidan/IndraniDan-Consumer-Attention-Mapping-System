import React from "react";
import { useUnifiedJobContext } from "../../../context/UnifiedJobContext";
import RecommendationsDashboard from "../../recommendations/RecommendationsDashboard";

export default function RecommendationsTab() {
  const { jobId, job } = useUnifiedJobContext();

  return (
    <div className="animate-fade-in">
      <RecommendationsDashboard jobId={jobId} storeId={job?.store_id} />
    </div>
  );
}
