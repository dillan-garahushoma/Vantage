import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Field, PasswordInput } from '../ui';

describe('PasswordInput', () => {
  it('starts masked and reveals on request without losing its label', async () => {
    const user = userEvent.setup();
    render(
      <Field label="Password">
        <PasswordInput defaultValue="aGoodPassword1" />
      </Field>,
    );

    const field = screen.getByLabelText('Password');
    expect(field).toHaveAttribute('type', 'password');

    const reveal = screen.getByRole('button', { name: 'Show password' });
    expect(reveal).toHaveAttribute('aria-pressed', 'false');

    await user.click(reveal);

    expect(field).toHaveAttribute('type', 'text');
    expect(field).toHaveValue('aGoodPassword1');
    expect(screen.getByRole('button', { name: 'Hide password' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('keeps the reveal control out of the field name, so getByLabel stays unique', () => {
    render(
      <Field label="New password">
        <PasswordInput />
      </Field>,
    );

    expect(screen.getByLabelText('New password')).toBeInTheDocument();
    expect(screen.getAllByLabelText(/password/i)).toHaveLength(1);
  });
});
