import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { AiAnswerRenderer } from './AiAnswerRenderer';

describe('AiAnswerRenderer', () => {
  it('turns common markdown into semantic reading structure without exposing markers', () => {
    render(<AiAnswerRenderer content={'## Immediate action\n\n**Escalate** the gate repair.\n\n- Review the work order\n- Confirm the due date'} />);
    expect(screen.getByRole('heading', { name: 'Immediate action' })).toBeVisible();
    expect(screen.getByText('Escalate').tagName).toBe('STRONG');
    expect(screen.getByRole('list')).toHaveTextContent('Review the work order');
    expect(screen.queryByText(/\*\*/)).not.toBeInTheDocument();
  });

  it('renders model-supplied HTML as text rather than executing it', () => {
    render(<AiAnswerRenderer content={'<script>alert(1)</script>\n\nPlain answer.'} />);
    expect(screen.getByText('<script>alert(1)</script>')).toBeVisible();
    expect(document.querySelector('script')).toBeNull();
  });

  it('turns links, tables and stray markdown markers into readable content', () => {
    render(
      <AiAnswerRenderer
        content={'**Priority\n\n| Record | State |\n| --- | --- |\n| Gate motor | In progress |\n\nRead [the work order](https://example.test/work-order).'}
      />,
    );
    expect(screen.getByText('Priority')).toBeVisible();
    expect(screen.getByRole('table')).toHaveTextContent('Gate motor');
    expect(screen.getByRole('link', { name: 'the work order' })).toHaveAttribute(
      'href',
      'https://example.test/work-order',
    );
    expect(screen.queryByText(/\*\*Priority/)).not.toBeInTheDocument();
  });

  it('renders structured responses with takeaway, citation chips, action card and follow-ups', async () => {
    const handleFollowUp = vi.fn();
    const user = userEvent.setup();

    render(
      <AiAnswerRenderer
        content={{
          summary: 'Gate motor replacement is scheduled for tomorrow.',
          evidence: ['WO-0042 (In Progress)', 'Complaint #12 (Sensor fault)'],
          recommendation: 'Verify gate access for the technician at 08:00.',
          related: ['Which open issues are driving this?', 'Compare with last 30 days'],
        }}
        onFollowUp={handleFollowUp}
      />
    );

    // Key takeaway
    expect(screen.getByText('Gate motor replacement is scheduled for tomorrow.')).toBeVisible();
    // Evidence chips
    expect(screen.getByText('WO-0042 (In Progress)')).toBeVisible();
    expect(screen.getByText('Complaint #12 (Sensor fault)')).toBeVisible();
    // Recommended action card
    expect(screen.getByText(/Recommended next action/i)).toBeVisible();
    expect(screen.getByText('Verify gate access for the technician at 08:00.')).toBeVisible();
    // Contextual follow-up chips
    const followUpBtn = screen.getByRole('button', { name: /Which open issues are driving this\?/i });
    expect(followUpBtn).toBeVisible();
    await user.click(followUpBtn);
    expect(handleFollowUp).toHaveBeenCalledWith('Which open issues are driving this?');
  });
});
