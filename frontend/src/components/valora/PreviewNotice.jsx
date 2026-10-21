import { Info } from 'lucide-react';
/** Keeps the Vantage design while distinguishing its prototype data from estate records. */
export function PreviewNotice({ detail }) {
    return (<aside role="note" className="flex gap-3 rounded-2xl border border-ochre/30 bg-ochre-wash p-4 text-sm text-ink">
      <Info className="mt-0.5 h-5 w-5 shrink-0 text-ochre" aria-hidden="true"/>
      <div><p className="font-semibold">Sample preview</p><p className="mt-1 leading-relaxed text-ink/70">{detail} No changes are saved from this preview.</p></div>
    </aside>);
}
