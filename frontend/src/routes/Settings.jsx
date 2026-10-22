import { RequireEstate } from '../components/RequireEstate';
import { Card, LinkButton, SectionTitle } from '../components/ui';
import { useEstateScope } from '../context/EstateContext';

function SettingsContent() {
    const { estate } = useEstateScope();
    return (<div className="space-y-6">
      <header>
        <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">Administration</p>
        <h1 className="mt-2 text-[26px] leading-tight font-semibold">Estate settings</h1>
        <p className="mt-1 max-w-2xl text-[13.5px] text-ink-muted">
          Administration for {estate?.estate_name ?? 'the selected estate'}, using only records that are available to this account.
        </p>
      </header>

      <Card className="p-5">
        <SectionTitle title="Estate record" hint="Edit the published estate profile, unit register and photographs through the operational setup flow."/>
        <LinkButton to="/admin/setup">Open estate setup</LinkButton>
      </Card>

      <Card className="p-5">
        <SectionTitle title="Account notifications" hint="Notifications and delivery preferences are personal to the signed-in account, rather than a shared estate setting."/>
        <LinkButton to="/app/notifications">Open notifications</LinkButton>
      </Card>

      <Card className="p-5">
        <SectionTitle title="Living Score" hint="The score is calculated and stored by the backend. Review the current result and recorded pillars in Estate health."/>
        <LinkButton to="/app/health">Open estate health</LinkButton>
      </Card>
    </div>);
}
export function Settings() {
    return (<RequireEstate>
      <SettingsContent />
    </RequireEstate>);
}
export default Settings;
