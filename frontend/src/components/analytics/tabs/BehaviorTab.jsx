import React from 'react';
import { useUnifiedJobContext } from '../../../context/UnifiedJobContext';
import Module6BehaviorAnalytics from '../../module6/Module6BehaviorAnalytics';

export default function BehaviorTab() {
  const { jobId, job, unifiedData } = useUnifiedJobContext();
  const m6Analysis = unifiedData?.behavior || {};

  return (
    <div className="animate-fade-in">
      <Module6BehaviorAnalytics jobId={jobId} job={job} initialData={m6Analysis} />
    </div>
  );
}
