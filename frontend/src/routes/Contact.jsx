import { useState } from 'react';
import { Mail, ArrowRight } from 'lucide-react';
import { PublicShell } from '../components/PublicShell';
import { Surface } from '../components/valora/Surface';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { api } from '../lib/api';
export function Contact() {
    const [form, setForm] = useState({ name: '', email: '', phone: '', subject: '', message: '' });
    const [sending, setSending] = useState(false);
    const [received, setReceived] = useState(false);
    const [error, setError] = useState(null);
    function update(key, value) {
        setForm((previous) => ({ ...previous, [key]: value }));
        setReceived(false);
    }
    async function submit(event) {
        event.preventDefault();
        if (sending)
            return;
        setError(null);
        setReceived(false);
        if (form.name.trim().length < 2 || form.message.trim().length < 10) {
            setError('Enter your name and a message of at least 10 characters.');
            return;
        }
        setSending(true);
        try {
            await api.contact({
                name: form.name.trim(), email: form.email.trim(), phone: form.phone.trim() || null,
                subject: form.subject.trim() || null, message: form.message.trim(),
            });
            setReceived(true);
            setForm({ name: '', email: '', phone: '', subject: '', message: '' });
        }
        catch (cause) {
            setError(cause instanceof Error ? cause.message : 'The message could not be sent. Please try again.');
        }
        finally {
            setSending(false);
        }
    }
    const control = 'mt-2 w-full rounded-xl border-line bg-surface';
    return (<PublicShell>
      <section className="mx-auto max-w-[1100px] px-5 py-12 sm:py-20">
        <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr]">
          <div>
            <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-wash text-brand"><Mail size={21}/></span>
            <p className="mt-6 text-xs font-semibold tracking-[0.18em] text-brand uppercase">Contact VALORA</p>
            <h1 className="mt-3 font-heading text-4xl font-extrabold tracking-tight text-ink">Let's talk about your estate.</h1>
            <p className="mt-5 max-w-md leading-relaxed text-ink-muted">Ask about the platform, onboarding or a technical issue. Your message goes to the VALORA team.</p>
            <p className="mt-5 text-sm leading-relaxed text-ink-muted">For a maintenance issue at your estate, sign in and use Maintenance & complaints so your HOA can track it. This form does not create a complaint or send a notification email.</p>
          </div>
          <Surface className="p-6 sm:p-8">
            {received ? <div role="status" className="mb-5 rounded-xl bg-mint-wash p-4 text-sm text-ink">Message received. Your enquiry has been recorded.</div> : null}
            {error ? <div role="alert" className="mb-5 rounded-xl border border-signal/30 p-4 text-sm text-signal-ink">{error}</div> : null}
            <form onSubmit={(event) => void submit(event)} className="space-y-5">
              <div className="grid gap-5 sm:grid-cols-2">
                <div><label className="text-sm font-medium text-ink" htmlFor="contact-name">Your name</label><Input className={control} id="contact-name" autoComplete="name" required minLength={2} maxLength={100} value={form.name} onChange={(event) => update('name', event.target.value)}/></div>
                <div><label className="text-sm font-medium text-ink" htmlFor="contact-email">Email address</label><Input className={control} id="contact-email" type="email" autoComplete="email" required value={form.email} onChange={(event) => update('email', event.target.value)}/></div>
              </div>
              <div><label className="block text-sm font-medium text-ink" htmlFor="contact-phone">Phone (optional)</label><Input className={control} id="contact-phone" type="tel" autoComplete="tel" value={form.phone} onChange={(event) => update('phone', event.target.value)}/></div>
              <div><label className="block text-sm font-medium text-ink" htmlFor="contact-subject">Subject (optional)</label><Input className={control} id="contact-subject" maxLength={150} value={form.subject} onChange={(event) => update('subject', event.target.value)}/></div>
              <div><label className="block text-sm font-medium text-ink" htmlFor="contact-message">Message</label><Textarea className={`${control} min-h-36`} id="contact-message" required minLength={10} maxLength={5000} value={form.message} onChange={(event) => update('message', event.target.value)}/></div>
              <Button type="submit" disabled={sending} className="h-11 rounded-full bg-ink px-6 text-white hover:bg-brand">{sending ? 'Sending…' : 'Send message'}<ArrowRight className="ml-2 h-4 w-4"/></Button>
            </form>
          </Surface>
        </div>
      </section>
    </PublicShell>);
}
