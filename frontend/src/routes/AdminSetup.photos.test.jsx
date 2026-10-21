/**
 * The estate's photograph uploader.
 *
 * An administrator arrives with a folder of photographs, not one, so the picker
 * takes many and the interesting cases are all about batches: sending one
 * request per photograph, deciding each *file* on its own merits rather than
 * failing the batch together, never queueing more than the estate can hold, not
 * sending the same photograph twice, and — the easy thing to leak — giving back
 * the object URL behind every preview that goes away.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../lib/api';
import { MAX_ESTATE_PHOTOS, MAX_UPLOAD_BYTES } from '../lib/estateAdmin';
import { PhotoUploader } from './AdminSetup';
const mocks = vi.hoisted(() => ({ upload: vi.fn() }));
vi.mock('../lib/estateAdmin', async () => {
    const actual = await vi.importActual('../lib/estateAdmin');
    return { ...actual, uploadEstatePhoto: mocks.upload };
});
let created = [];
let revoked = [];
function photo(name, type = 'image/jpeg', bytes = 2048) {
    return new File([new Uint8Array(bytes)], name, { type });
}
function renderUploader(existingCount = 0) {
    const onChanged = vi.fn();
    render(<PhotoUploader estateId={7} existingCount={existingCount} onChanged={onChanged}/>);
    return { onChanged };
}
/** The file input is sr-only, which is how the project's pickers are driven. */
function picker() {
    return screen.getByLabelText(/choose photographs to upload/i);
}
beforeEach(() => {
    mocks.upload.mockReset();
    mocks.upload.mockResolvedValue({ photo_id: 1 });
    created = [];
    revoked = [];
    let count = 0;
    const url = URL;
    url.createObjectURL = (file) => {
        count += 1;
        const value = `blob:${file.name}-${count}`;
        created.push(value);
        return value;
    };
    url.revokeObjectURL = (value) => {
        revoked.push(value);
    };
});
describe('PhotoUploader — taking more than one at a time', () => {
    it('queues every photograph chosen in a single selection, with a preview each', async () => {
        const user = userEvent.setup();
        renderUploader();
        // One picker operation, three files — the whole request.
        await user.upload(picker(), [
            photo('pool.jpg'),
            photo('gate.png', 'image/png'),
            photo('court.webp', 'image/webp'),
        ]);
        expect(screen.getByText('pool.jpg')).toBeVisible();
        expect(screen.getByText('gate.png')).toBeVisible();
        expect(screen.getByText('court.webp')).toBeVisible();
        // The count shares its line with the estate's remaining capacity.
        expect(screen.getByText(/3 photographs queued/)).toBeVisible();
        // A preview per row. Decorative, because the row already names the file.
        expect(screen.getAllByRole('presentation')).toHaveLength(3);
        expect(screen.getByRole('button', { name: 'Upload 3 photographs' })).toBeEnabled();
    });
    it('adds a second selection without losing the first', async () => {
        const user = userEvent.setup();
        renderUploader();
        await user.upload(picker(), [photo('pool.jpg')]);
        await user.upload(picker(), [photo('gate.png', 'image/png'), photo('court.webp', 'image/webp')]);
        expect(screen.getByText('pool.jpg')).toBeVisible();
        expect(screen.getByText('gate.png')).toBeVisible();
        expect(screen.getByText(/3 photographs queued/)).toBeVisible();
    });
    it('sends one request per photograph, each with its own caption', async () => {
        const user = userEvent.setup();
        const { onChanged } = renderUploader();
        await user.upload(picker(), [photo('pool.jpg'), photo('gate.png', 'image/png')]);
        await user.type(screen.getByLabelText('Caption for pool.jpg'), 'The pool at dusk');
        await user.type(screen.getByLabelText('Caption for gate.png'), 'The north gate');
        await user.click(screen.getByRole('button', { name: 'Upload 2 photographs' }));
        await waitFor(() => expect(mocks.upload).toHaveBeenCalledTimes(2));
        const [first, second] = mocks.upload.mock.calls;
        expect(first[0]).toBe(7);
        expect(first[1].name).toBe('pool.jpg');
        expect(first[2]).toMatchObject({ caption: 'The pool at dusk' });
        expect(second[1].name).toBe('gate.png');
        expect(second[2]).toMatchObject({ caption: 'The north gate' });
        // The uploaded rows leave the queue and the estate is re-read.
        await waitFor(() => expect(onChanged).toHaveBeenCalled());
        expect(screen.queryByText('pool.jpg')).toBeNull();
        expect(screen.getByText('2 photographs uploaded.')).toBeVisible();
    });
    it('judges each file on its own, so one bad file does not sink the batch', async () => {
        // The control's `accept` would otherwise filter the text file out before the
        // component ever sees it, and this test is about the component's own
        // decision — which has to hold for a file that reaches it anyway, from a
        // drag-and-drop or a renamed extension.
        const user = userEvent.setup({ applyAccept: false });
        renderUploader();
        await user.upload(picker(), [
            photo('notes.txt', 'text/plain'),
            photo('huge.jpg', 'image/jpeg', MAX_UPLOAD_BYTES + 1),
            photo('pool.jpg'),
        ]);
        // Both refusals name the file and the reason, and neither is sent.
        expect(screen.getByText(/cannot be sent: not jpeg, png, webp/i)).toBeVisible();
        expect(screen.getByText(/cannot be sent: larger than 5 mb/i)).toBeVisible();
        expect(screen.getByRole('button', { name: 'Upload 1 photograph' })).toBeEnabled();
        await user.click(screen.getByRole('button', { name: 'Upload 1 photograph' }));
        await waitFor(() => expect(mocks.upload).toHaveBeenCalledTimes(1));
        expect(mocks.upload.mock.calls[0][1].name).toBe('pool.jpg');
    });
    it('never queues more than the estate has places for', async () => {
        const user = userEvent.setup();
        // Ten already stored: two places left.
        renderUploader(MAX_ESTATE_PHOTOS - 2);
        await user.upload(picker(), [
            photo('a.jpg'),
            photo('b.jpg'),
            photo('c.jpg'),
            photo('d.jpg'),
        ]);
        expect(screen.getByText(/2 photographs queued/)).toBeVisible();
        expect(screen.getByText(/only 2 of those 4 added/i)).toBeVisible();
        expect(screen.queryByText('c.jpg')).toBeNull();
        expect(screen.getByText(/2 of 12 places left in the estate/)).toBeVisible();
    });
    it('refuses a full estate outright, and says how to make room', async () => {
        const user = userEvent.setup();
        renderUploader(MAX_ESTATE_PHOTOS);
        await user.upload(picker(), [photo('a.jpg')]);
        expect(screen.getByText(/nothing added/i)).toBeVisible();
        expect(screen.getByText(/delete one first/i)).toBeVisible();
        expect(screen.queryByRole('button', { name: /^upload/i })).toBeNull();
    });
    it('ignores a photograph that is already queued', async () => {
        const user = userEvent.setup();
        renderUploader();
        // The same file, chosen twice — which is what a person does when they are
        // unsure whether the first selection took.
        const pool = photo('pool.jpg');
        await user.upload(picker(), [pool]);
        await user.upload(picker(), [pool]);
        expect(screen.getAllByText('pool.jpg')).toHaveLength(1);
        expect(screen.getByText('1 file was already in the list.')).toBeVisible();
    });
});
describe('PhotoUploader — the queue as memory', () => {
    it('gives back the preview of a row that is removed', async () => {
        const user = userEvent.setup();
        renderUploader();
        await user.upload(picker(), [photo('pool.jpg'), photo('gate.png', 'image/png')]);
        const poolUrl = created[0];
        await user.click(screen.getByRole('button', { name: 'Remove pool.jpg from the queue' }));
        expect(screen.queryByText('pool.jpg')).toBeNull();
        expect(revoked).toContain(poolUrl);
        expect(screen.getByText(/1 photograph queued/)).toBeVisible();
    });
    it('gives back every remaining preview when the screen goes away', async () => {
        const user = userEvent.setup();
        const { unmount } = render(<PhotoUploader estateId={7} existingCount={0} onChanged={vi.fn()}/>);
        await user.upload(picker(), [photo('pool.jpg'), photo('gate.png', 'image/png')]);
        unmount();
        expect(revoked.sort()).toEqual([...created].sort());
    });
    it('clears the queue on request, previews and all', async () => {
        const user = userEvent.setup();
        renderUploader();
        await user.upload(picker(), [photo('pool.jpg'), photo('gate.png', 'image/png')]);
        await user.click(screen.getByRole('button', { name: 'Clear' }));
        expect(screen.queryByText(/queued/)).toBeNull();
        expect(revoked.sort()).toEqual([...created].sort());
        expect(mocks.upload).not.toHaveBeenCalled();
    });
    it('keeps a rejected photograph in the queue with the server’s own words', async () => {
        mocks.upload.mockRejectedValueOnce(new ApiError(413, 'That image is larger than the 5 MB limit.', 'PAYLOAD_TOO_LARGE', 'req-413'));
        const user = userEvent.setup();
        renderUploader();
        await user.upload(picker(), [photo('pool.jpg')]);
        await user.click(screen.getByRole('button', { name: 'Upload 1 photograph' }));
        await waitFor(() => expect(screen.getByText(/larger than the 5 MB limit/i)).toBeVisible());
        expect(screen.getByText(/ref req-413/)).toBeVisible();
        // Still there, so it can be retried or removed rather than silently vanishing.
        expect(screen.getByText('pool.jpg')).toBeVisible();
    });
});
