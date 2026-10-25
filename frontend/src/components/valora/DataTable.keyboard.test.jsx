import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { DataTable } from './DataTable';

it('opens a desktop record with Enter or Space from keyboard focus', async () => {
  const user = userEvent.setup();
  const open = vi.fn();
  const row = { id: 1, issue: 'Repair the gate' };
  render(<DataTable columns={[{ key: 'issue', header: 'Issue' }]} rows={[row]} rowKey={(record) => record.id} onRowClick={open} />);
  await user.tab();
  expect(screen.getByRole('row', { name: 'Repair the gate' })).toHaveFocus();
  await user.keyboard('{Enter}');
  await user.keyboard(' ');
  expect(open).toHaveBeenCalledTimes(2);
  expect(open).toHaveBeenLastCalledWith(row);
});

it('sorts a column through its keyboard-accessible header button', async () => {
  const user = userEvent.setup();
  render(<DataTable columns={[{ key: 'issue', header: 'Issue', sortable: true }]} rows={[{ id: 1, issue: 'Z repair' }, { id: 2, issue: 'A repair' }]} rowKey={(row) => row.id} />);
  await user.tab();
  expect(screen.getByRole('button', { name: 'Sort by Issue' })).toHaveFocus();
  await user.keyboard('{Enter}');
  expect(screen.getAllByRole('row')[1]).toHaveTextContent('A repair');
  await user.keyboard('{Enter}');
  expect(screen.getAllByRole('row')[1]).toHaveTextContent('Z repair');
});
