import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { RecommendationCard } from './RecommendationCard';

it('does not turn missing confidence and cost evidence into numeric claims', () => {
  render(<RecommendationCard recommendation={{ id: 'overdue_work_order-12', kind: 'EMERGING SERVICE RISK', title: 'Overdue work order #12', summary: 'Review the overdue repair.', evidence: [], confidence: 'High', confidenceValue: null, savingsZar: null, impact: 'No financial estimate.' }} />);
  expect(screen.queryByText(/% confidence/)).not.toBeInTheDocument();
  expect(screen.queryByText('R0')).not.toBeInTheDocument();
  expect(screen.getByText('No financial estimate.')).toBeVisible();
  expect(screen.getByRole('button', { name: 'View work orders' })).toBeVisible();
});
