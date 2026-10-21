import { Link } from 'react-router-dom';
import { ArrowRight, Building2 } from 'lucide-react';
import { RequireEstate } from '../components/RequireEstate';
import { Surface } from '../components/valora/Surface';
import { useAuth } from '../context/AuthContext';
import { useEstateScope } from '../context/EstateContext';
import { propertyWorkflows } from '../lib/propertyWorkflows';
function Workflows() {
    const { user } = useAuth();
    const { estate } = useEstateScope();
    const workflows = propertyWorkflows.filter((workflow) => user && workflow.roles.includes(user.role));
    return (<div className="space-y-6">
      <div className="max-w-3xl">
        <p className="text-xs font-semibold tracking-[0.18em] text-brand uppercase">Property & investment</p>
        <h1 className="mt-2 font-heading text-3xl font-extrabold tracking-tight text-ink">Your property workspace</h1>
        <p className="mt-3 leading-relaxed text-ink-muted">Property journeys for {estate?.estate_name ?? 'your estate'}, together with the operational workspace. Available features open below; the remaining journeys show exactly what is still needed.</p>
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        {workflows.map((workflow) => (<Surface key={workflow.id} className="scroll-mt-24 p-6">
            <div id={workflow.id} className="flex items-start justify-between gap-3">
              <Building2 className="h-5 w-5 shrink-0 text-brand" aria-hidden="true"/>
              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${workflow.status === 'Available' ? 'bg-mint-wash text-mint' : 'bg-ochre-wash text-ink'}`}>{workflow.status}</span>
            </div>
            <h2 className="mt-4 font-heading text-lg font-bold text-ink">{workflow.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-ink-muted">{workflow.description}</p>
            {workflow.needs ? <p className="mt-4 rounded-xl bg-canvas p-4 text-sm leading-relaxed text-ink/70"><strong>Still needed: </strong>{workflow.needs}</p> : null}
            {workflow.to ? <Link to={workflow.to} className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-brand hover:underline">{workflow.linkLabel}<ArrowRight size={16}/></Link> : null}
          </Surface>))}
      </div>
      {workflows.length === 0 ? <p className="rounded-2xl border border-line bg-surface p-6 text-sm text-ink-muted">This workspace is for residents, investors, agents and estate administrators. Your provider jobs remain in My work.</p> : null}
    </div>);
}
export function PropertyWorkflows() {
    return <RequireEstate><Workflows /></RequireEstate>;
}
