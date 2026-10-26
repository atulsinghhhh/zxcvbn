import { useState } from 'react';

export type SectionId = 'overview' | 'forecast' | 'accuracy' | 'data-sources';

export function useActiveSection(): [SectionId, (section: SectionId) => void] {
  const [active, setActive] = useState<SectionId>('overview');
  return [active, setActive];
}
