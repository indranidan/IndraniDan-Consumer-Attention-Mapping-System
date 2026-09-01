import React from 'react';
import { useUnifiedJobContext } from '../../../context/UnifiedJobContext';
import ProductScoringAnalytics from '../ProductScoringAnalytics';

export default function ScoringTab() {
  const { jobId } = useUnifiedJobContext();

  return (
    <div className="animate-fade-in">
      <ProductScoringAnalytics jobId={jobId} />
    </div>
  );
}
