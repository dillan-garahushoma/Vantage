import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Contact } from './Contact';
import { BoardReportDialog } from '../components/valora/BoardReportDialog';
import { PreviewNotice } from '../components/valora/PreviewNotice';
import { scoreMethodology } from '../lib/estateMockData';
const mocks = vi.hoisted(() => ({ contact: vi.fn() }));
vi.mock('../lib/api', () => ({
    api: { contact: mocks.contact },
    ApiError: class ApiError extends Error {
        status = 0;
    },
}));
vi.mock('../context/AuthContext', () => ({
    useAuth: () => ({ user: { role: 'resident' } }),
}));
vi.mock('../context/EstateContext', () => ({
    useEstate: () => ({ loading: false, awaitingProvisioning: false, error: null }),
    useEstateScope: () => ({ estate: { estate_name: 'Current estate' }, estateId: 1 }),
}));
beforeEach(() => mocks.contact.mockReset());
describe('combined Vantage workspace', () => {
    it('sends the legacy contact journey through the current API and waits for success', async () => {
        mocks.contact.mockResolvedValue({ id: 12 });
        render(<MemoryRouter><Contact /></MemoryRouter>);
        fireEvent.change(screen.getByLabelText('Your name'), { target: { value: '  Resident Name  ' } });
        fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'resident@example.com' } });
        fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'Please contact me about joining the estate.' } });
        fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
        await waitFor(() => expect(mocks.contact).toHaveBeenCalledWith({
            name: 'Resident Name', email: 'resident@example.com', phone: null, subject: null,
            message: 'Please contact me about joining the estate.',
        }));
        expect(await screen.findByRole('status')).toHaveTextContent('Message received');
    });
    it('refuses invalid contact data without calling the backend', () => {
        render(<MemoryRouter><Contact /></MemoryRouter>);
        fireEvent.change(screen.getByLabelText('Your name'), { target: { value: 'R' } });
        fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'resident@example.com' } });
        fireEvent.submit(screen.getByRole('button', { name: 'Send message' }).closest('form'));
        expect(screen.getByRole('alert')).toHaveTextContent('Enter your name');
        expect(mocks.contact).not.toHaveBeenCalled();
    });
    it('labels the Vantage prototype data and the lack of persistence explicitly', () => {
        render(<PreviewNotice detail="Financial figures and approvals are samples."/>);
        expect(screen.getByRole('note')).toHaveTextContent('Sample preview');
        expect(screen.getByRole('note')).toHaveTextContent('No changes are saved');
    });
    it('describes the same five pillars as the backend engine', () => {
        const text = scoreMethodology.map((entry) => entry.body).join(' ');
        for (const pillar of ['Resolution (30%)', 'Frequency (25%)', 'Security (20%)', 'Satisfaction (15%)', 'Infrastructure (10%)']) {
            expect(text).toContain(pillar);
        }
        expect(text).not.toContain('Financial & Reserve Stewardship (20%)');
    });
    it('does not present sample reports as measured records of the selected estate', () => {
        render(<BoardReportDialog open onOpenChange={() => { }} summary={{ headline: 'Sample figures', points: [] }} period="90 days" estateName="Current estate"/>);
        expect(screen.getByText(/SAMPLE — NOT AN ESTATE RECORD/)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Export sample summary' })).toBeInTheDocument();
        expect(screen.queryByText(/Every figure in this summary traces back to measured signals/)).not.toBeInTheDocument();
    });
});
