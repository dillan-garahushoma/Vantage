import { Link } from 'react-router-dom';
import { Keyline } from '../components/Brand';
import { EstatePlan } from '../components/EstatePlan';
import { PublicShell } from '../components/PublicShell';
import { IconArrowRight } from '../components/Icons';
import { Card, Chip, LinkButton } from '../components/ui';

const VALUE_CHAIN = [
  {
    step: '01',
    title: 'Residents report what is actually wrong',
    body: 'A burst pipe, a dead streetlight, a gate that will not close. Each complaint is logged with a category, a priority and a timestamp instead of disappearing into a WhatsApp group.',
  },
  {
    step: '02',
    title: 'The HOA resolves it, visibly',
    body: 'Complaints move through a fixed lifecycle — logged, reviewed, assigned, in progress, resolved, rated. Every transition is retained as evidence, so responsiveness is provable rather than claimed.',
  },
  {
    step: '03',
    title: 'Operational data becomes community health',
    body: 'Resolution times, complaint frequency, security incidents, provider performance and resident satisfaction are weighted into one comparable estate-level figure.',
  },
  {
    step: '04',
    title: 'Evidence supports accountable maintenance',
    body: 'The stored record shows what was reported, who acted, how long it took and whether the resident rated the completed repair.',
  },
];

const COMPARISON = [
  ['Which issues need attention now?', 'Scattered messages and emails', 'yes'],
  ['Complaint history and resolution time', 'Emails and meeting minutes', 'yes'],
  ['Maintenance quality and resident ratings', 'Word of mouth', 'yes'],
  ['Security incident frequency', 'Separate incident records', 'yes'],
  ['Resident satisfaction after completed repairs', 'Rarely connected to the repair', 'yes'],
  ['Estate living quality, scored', 'No shared operational measure', 'yes'],
];

function Section({ id, eyebrow, title, intro, children }) {
  return (
    <section id={id} className="mx-auto max-w-[1200px] px-5 py-14">
      <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">{eyebrow}</p>
      <h2 className="mt-3 max-w-2xl font-display text-[27px] leading-[1.12] font-medium sm:text-[33px]">
        {title}
      </h2>
      {intro ? <p className="mt-3 max-w-2xl text-[15px] text-ink-soft">{intro}</p> : null}
      <div className="mt-8">{children}</div>
    </section>
  );
}

export function Landing() {
  return (
    <PublicShell>
      {/* ------------------------------------------------------------ hero */}
      <section className="border-b border-ink/15 bg-surface">
        <div className="mx-auto grid max-w-[1200px] gap-10 px-5 py-14 lg:grid-cols-[1.18fr_0.82fr] lg:items-center lg:py-20">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip tone="progress" glyph="◆">
                South African private estates
              </Chip>
              <Chip glyph="◷">MVP — pilot deployment</Chip>
            </div>

            <h1 className="mt-5 font-display text-[36px] leading-[1.04] font-normal tracking-[-0.012em] sm:text-[50px]">
              Know what your estate needs.
              <br />
              <span className="text-accent-ink italic">See what changes.</span>
            </h1>

            <p className="mt-5 max-w-xl text-[16px] text-ink-soft">
              Track the maintenance and management work that makes an apartment complex run: how
              quickly issues are resolved, whether the perimeter holds, and whether residents are
              heard. VALORA turns that operational record into estate intelligence, inside its own
              estate boundary.
            </p>

            <div className="mt-7 flex flex-wrap items-center gap-4">
              <LinkButton to="/register" variant="primary" className="px-6 py-2.5">
                Get started as a resident
                <IconArrowRight size={17}/>
              </LinkButton>
              <Link to="/login" className="text-[13.5px] font-medium text-ink-soft transition-colors hover:text-ink hover:underline">
                Already have an account? Sign in →
              </Link>
            </div>

            <dl className="mt-9 grid max-w-lg grid-cols-3 gap-4 border-t border-ink/15 pt-5">
              {[
                ['30%', 'Resolution time weight'],
                ['90 days', 'Rolling score window'],
                ['5', 'Weighted health factors'],
              ].map(([value, label]) => (
                <div key={label}>
                  <dt className="num text-[20px] font-semibold text-ink">{value}</dt>
                  <dd className="mt-0.5 text-[12px] text-ink-muted">{label}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="hairline rounded-xs bg-paper p-4">
            <div className="flex items-center justify-between">
              <p className="num text-[11px] tracking-wider text-ink-muted uppercase">
                Ridge Close Estate · Model
              </p>
              <p className="num text-[11px] text-ink-muted">scale 1:1000 · rev 03</p>
            </div>
            <div className="relative mt-3 overflow-hidden rounded-xs border border-ink/15">
              <img
                src="/estate-hero.jpg"
                alt="Ridge Close Estate community render"
                className="h-44 w-full object-cover transition-transform duration-500 hover:scale-[1.02]"
              />
              <div className="absolute bottom-2 left-2 flex items-center gap-1.5 rounded-full bg-black/65 px-2.5 py-0.5 text-[10px] font-medium text-white backdrop-blur-xs">
                <span className="h-1.5 w-1.5 rounded-full bg-mint" />
                Live operational deployment
              </div>
            </div>
            <EstatePlan className="mt-3 w-full text-ink" />
            <div className="mt-3 grid grid-cols-3 gap-3 border-t border-ink/15 pt-3">
              {[
                ['Perimeter', 'monitored'],
                ['Units', 'operational'],
                ['Gate', 'single entry'],
              ].map(([term, value]) => (
                <div key={term}>
                  <p className="text-[11px] tracking-wider text-ink-muted uppercase">{term}</p>
                  <p className="num mt-0.5 text-[12.5px]">{value}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------ value chain */}
      <Section
        id="how"
        eyebrow="How the operational record works"
        title="Every feature supports the next maintenance decision"
        intro="VALORA is a management system: what happens in a community becomes measurable health, then evidence for better maintenance decisions."
      >
        <ol className="grid gap-4 md:grid-cols-2">
          {VALUE_CHAIN.map((link) => (
            <li key={link.step}>
              <Card className="h-full p-5">
                <div className="flex items-center gap-3">
                  <span className="num text-[13px] font-semibold text-accent-ink">{link.step}</span>
                  <span className="h-px flex-1 bg-ink/15" />
                </div>
                <h3 className="mt-3 text-[16px] font-semibold">{link.title}</h3>
                <p className="mt-2 text-[13.5px] text-ink-soft">{link.body}</p>
              </Card>
            </li>
          ))}
        </ol>
      </Section>

      {/* ------ living score teaser ------ */}
      <section className="border-y border-ink/15 bg-surface">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-6 px-5 py-8">
          <div>
            <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
              Estate intelligence
            </p>
            <h2 className="mt-2 font-display text-[24px] leading-snug font-medium">
              Every score shows its working
            </h2>
            <p className="mt-1.5 max-w-xl text-[14px] text-ink-soft">
              The Living Score is a weighted composite from 0–100, built from five operational pillars over a rolling 90-day window. The formula is fixed and inspectable.
            </p>
          </div>
          <Link
            to="/methodology"
            className="inline-flex shrink-0 items-center gap-2 rounded-xs border border-line bg-surface px-4 py-2.5 text-[13.5px] font-medium text-ink-soft transition-colors hover:border-accent hover:text-accent-ink"
          >
            Read the methodology
            <IconArrowRight size={15}/>
          </Link>
        </div>
      </section>

      {/* ------ who it is for: role stories ------ */}
      <Section
        eyebrow="Who uses VALORA"
        title="Built for everyone with a stake in the estate"
      >
        <div className="grid gap-4 sm:grid-cols-3">
          {[
            {
              role: 'Residents',
              tagline: 'Report an issue and watch it move.',
              body: 'Log a maintenance request once. Track it through review, assignment, repair and resident rating — all from one screen.',
              cta: 'Get started as a resident',
              to: '/register',
              primary: true,
            },
            {
              role: 'HOA Administrators',
              tagline: 'One command view for everything.',
              body: 'Complaints, work orders, contractors, announcements and estate health — all managed inside one estate-scoped workspace.',
              cta: 'Contact your estate admin',
              to: '/contact',
              primary: false,
            },
            {
              role: 'Service Providers',
              tagline: 'See your work. Log progress. Get rated.',
              body: 'Assigned jobs arrive in your portal. Upload completion evidence and build your verified provider record inside the estate.',
              cta: 'Contact your estate admin',
              to: '/contact',
              primary: false,
            },
          ].map((item) => (
            <Card key={item.role} className="flex flex-col p-5">
              <p className="num text-[11px] tracking-[0.16em] text-accent-ink uppercase">
                {item.role}
              </p>
              <h3 className="mt-2 text-[16px] font-semibold">{item.tagline}</h3>
              <p className="mt-2 flex-1 text-[13px] text-ink-soft">{item.body}</p>
              <Link
                to={item.to}
                className={
                  item.primary
                    ? 'mt-4 inline-flex items-center gap-1.5 text-[13px] font-semibold text-accent-ink hover:underline'
                    : 'mt-4 inline-flex items-center gap-1.5 text-[13px] text-ink-muted hover:text-ink'
                }
              >
                {item.cta}
                <IconArrowRight size={14}/>
              </Link>
            </Card>
          ))}
        </div>
      </Section>

      {/* ------------------------------------------------------- why different */}
      <section className="border-t border-ink/15 bg-surface">
        <div className="mx-auto max-w-[1200px] px-5 py-14">
          <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
            More than a unit register
          </p>
          <h2 className="mt-3 max-w-2xl font-display text-[27px] leading-[1.12] font-medium sm:text-[33px]">
            The operational record exists inside the community that runs on it
          </h2>

          <div className="mt-8 hairline overflow-hidden rounded-xs bg-surface">
            <table className="w-full border-collapse text-left text-[13px]">
              <thead>
                <tr>
                  <th className="border-b border-ink/15 bg-paper px-4 py-2.5 text-[11px] font-medium tracking-wider text-ink-muted uppercase">
                    Operational question
                  </th>
                  <th className="border-b border-ink/15 bg-paper px-4 py-2.5 text-[11px] font-medium tracking-wider text-ink-muted uppercase">
                    Without a shared system
                  </th>
                  <th className="border-b border-ink/15 bg-paper px-4 py-2.5 text-right text-[11px] font-medium tracking-wider text-ink-muted uppercase">
                    On VALORA
                  </th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON.map(([question, today, answer]) => (
                  <tr key={question}>
                    <td className="border-b border-ink/10 px-4 py-3">{question}</td>
                    <td className="border-b border-ink/10 px-4 py-3 text-ink-muted">{today}</td>
                    <td className="border-b border-ink/10 px-4 py-3 text-right">
                      {answer === 'yes' ? (
                        <Chip tone="good" glyph="✓">
                          Visible
                        </Chip>
                      ) : (
                        <Chip tone="alert" glyph="✕">
                          Not visible
                        </Chip>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* -------------------------------------------------------------- close */}
      <section className="bg-ink text-paper">
        <div className="mx-auto max-w-[1200px] px-5 py-14">
          <Keyline className="opacity-40" />
          <h2 className="mt-6 max-w-2xl font-display text-[28px] leading-[1.1] font-medium text-paper sm:text-[34px]">
            Ready to see your estate's real operational data?
          </h2>
          <p className="mt-3 max-w-2xl text-[14.5px] text-paper/75">
            Public registration always creates a resident — privileged estate roles are granted
            through an existing membership, never self-selected. If your estate has not been
            provisioned yet, your account will show that it is awaiting approval.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <LinkButton to="/register" variant="primary" className="px-5 py-2.5">
              Get started as a resident
              <IconArrowRight size={17}/>
            </LinkButton>
            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-xs border border-paper/30 px-5 py-2.5 text-sm font-medium text-paper transition-colors hover:bg-paper/10"
            >
              Sign in
            </Link>
          </div>
        </div>
      </section>
    </PublicShell>
  );
}
