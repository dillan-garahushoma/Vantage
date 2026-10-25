import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { RecommendationCard } from './RecommendationCard';

it('does not turn missing confidence and cost evidence into numeric claims', () => {
  render(<MemoryRouter><RecommendationCard canAction={false} sourceAction={{ to: '/app/work-orders', state: { focusWorkOrderId: 12 }, label: 'Open work order' }} recommendation={{ id: 'overdue_work_order-12', kind: 'EMERGING SERVICE RISK', title: 'Overdue work order #12', summary: 'Review the overdue repair.', evidence: [], confidence: 'High', confidenceValue: null, savingsZar: null, impact: 'No financial estimate.' }} /></MemoryRouter>);
  expect(screen.queryByText(/% confidence/)).not.toBeInTheDocument();
  expect(screen.queryByText('R0')).not.toBeInTheDocument();
  expect(screen.getByText('No financial estimate.')).toBeVisible();
  expect(screen.getByRole('link', { name: 'Open work order' })).toHaveAttribute('href', '/app/work-orders');
});
