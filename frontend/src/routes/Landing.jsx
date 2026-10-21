import { Link } from 'react-router-dom';
import { Keyline } from '../components/Brand';
import { EstatePlan } from '../components/EstatePlan';
import { LivingScoreFactors } from '../components/LivingScore';
import { PublicShell } from '../components/PublicShell';
import { IconArrowRight, IconChart, IconPin, IconShield, IconSparkle, IconUsers } from '../components/Icons';
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
        title: 'Community health informs property intelligence',
        body: 'Buyers and investors see not only what a property costs, but how well the community is run — the signal no listing platform has.',
    },
];
const AUDIENCE = [
    {
        icon: <IconUsers size={18}/>,
        who: 'Residents',
        line: 'Report issues once, watch them move, and see what good management is worth to your home.',
    },
    {
        icon: <IconChart size={18}/>,
        who: 'Investors',
        line: 'Read the estate’s operational record before committing capital — resolution times and complaint trends, not rumours.',
    },
    {
        icon: <IconShield size={18}/>,
        who: 'HOA administrators',
        line: 'One dashboard for complaints, work orders, verified providers and announcements. Prove governance quality with data.',
    },
    {
        icon: <IconPin size={18}/>,
        who: 'Estate agents',
        line: 'Market a property with an operational track record attached — nothing a competitor can match.',
    },
];
const COMPARISON = [
    ['Bedrooms, bathrooms, price', 'Everything a listing shows', 'yes'],
    ['Complaint history and resolution time', 'Hidden in emails and minutes', 'no'],
    ['Maintenance quality and provider ratings', 'Word of mouth', 'no'],
    ['Security incident frequency', 'Facebook groups', 'no'],
    ['Resident satisfaction', 'Nowhere — unmeasured', 'no'],
    ['Estate living quality, scored', 'Does not exist', 'no'],
];
function Section({ id, eyebrow, title, intro, children, }) {
    return (<section id={id} className="mx-auto max-w-[1200px] px-5 py-14">
      <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">{eyebrow}</p>
      <h2 className="mt-3 max-w-2xl text-[26px] leading-tight font-semibold sm:text-[32px]">
        {title}
      </h2>
      {intro ? <p className="mt-3 max-w-2xl text-[15px] text-ink-soft">{intro}</p> : null}
      <div className="mt-8">{children}</div>
    </section>);
}
export function Landing() {
    return (<PublicShell>
      {/* ------------------------------------------------------------ hero */}
      <section className="border-b border-ink/15 bg-surface">
        <div className="mx-auto grid max-w-[1200px] gap-10 px-5 py-14 lg:grid-cols-[1.05fr_1fr] lg:items-center lg:py-20">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip tone="progress" glyph="◆">
                South African private estates
              </Chip>
              <Chip glyph="◷">MVP — pilot deployment</Chip>
            </div>

            <h1 className="mt-5 text-[38px] leading-[1.05] font-semibold tracking-tight sm:text-[52px]">
              Know what a property costs.
              <br />
              <span className="text-accent-ink">Know why it’s worth it.</span>
            </h1>

            <p className="mt-5 max-w-xl text-[16px] text-ink-soft">
              A property’s value is not only bedrooms and bathrooms. It is how fast the estate fixes
              a sewage leak, whether the perimeter holds, and whether the HOA answers. VALORA turns
              that operational reality into intelligence — for one private residential community at
              a time, inside its own estate boundary.
            </p>

            <div className="mt-7 flex flex-wrap items-center gap-3">
              <LinkButton to="/register" variant="primary" className="px-5 py-2.5">
                Create an account
                <IconArrowRight size={17}/>
              </LinkButton>
              <LinkButton to="/login" variant="secondary" className="px-5 py-2.5">
                Sign in to an estate
              </LinkButton>
              <LinkButton to="/estates" variant="ghost" className="px-5 py-2.5">
                Browse published complexes
                <IconArrowRight size={17}/>
              </LinkButton>
            </div>

            <dl className="mt-9 grid max-w-lg grid-cols-3 gap-4 border-t border-ink/15 pt-5">
              {[
            ['30%', 'Resolution time weight'],
            ['90 days', 'Rolling score window'],
            ['5', 'Weighted health factors'],
        ].map(([value, label]) => (<div key={label}>
                  <dt className="num text-[20px] font-semibold text-ink">{value}</dt>
                  <dd className="mt-0.5 text-[12px] text-ink-muted">{label}</dd>
                </div>))}
            </dl>
          </div>

          <div className="hairline rounded-xs bg-paper p-4">
            <div className="flex items-center justify-between">
              <p className="num text-[11px] tracking-wider text-ink-muted uppercase">
                Estate plan · rev 03
              </p>
              <p className="num text-[11px] text-ink-muted">scale 1:1000</p>
            </div>
            <EstatePlan className="mt-3 w-full text-ink"/>
            <div className="mt-3 grid grid-cols-3 gap-3 border-t border-ink/15 pt-3">
              {[
            ['Perimeter', 'monitored'],
            ['Units', 'operational'],
            ['Gate', 'single entry'],
        ].map(([term, value]) => (<div key={term}>
                  <p className="text-[11px] tracking-wider text-ink-muted uppercase">{term}</p>
                  <p className="num mt-0.5 text-[12.5px]">{value}</p>
                </div>))}
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------ value chain */}
      <Section id="how" eyebrow="How the value chain works" title="Every feature exists because it feeds the next link" intro="VALORA is not a complaint tool with a valuation bolted on. It is a single chain: what happens in a community becomes measurable health, and measurable health becomes investment intelligence.">
        <ol className="grid gap-4 md:grid-cols-2">
          {VALUE_CHAIN.map((link) => (<li key={link.step}>
              <Card className="h-full p-5">
                <div className="flex items-center gap-3">
                  <span className="num text-[13px] font-semibold text-accent-ink">{link.step}</span>
                  <span className="h-px flex-1 bg-ink/15"/>
                </div>
                <h3 className="mt-3 text-[16px] font-semibold">{link.title}</h3>
                <p className="mt-2 text-[13.5px] text-ink-soft">{link.body}</p>
              </Card>
            </li>))}
        </ol>
      </Section>

      {/* ----------------------------------------------------- living score */}
      <section className="border-y border-ink/15 bg-surface">
        <div className="mx-auto grid max-w-[1200px] gap-10 px-5 py-14 lg:grid-cols-[1fr_1.15fr]">
          <div>
            <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
              The differentiator
            </p>
            <h2 className="mt-3 text-[26px] leading-tight font-semibold sm:text-[32px]">
              A score that shows its working
            </h2>
            <p className="mt-3 text-[15px] text-ink-soft">
              The Living Score is a weighted composite index from 0 to 100, calculated per estate
              over a rolling 90-day window. It is deliberately explainable: a number without its
              contributing factors is marketing, not intelligence.
            </p>
            <div className="mt-6 flex items-start gap-3 border-l-2 border-l-accent bg-accent-wash px-4 py-3">
              <IconSparkle size={18} className="mt-0.5 shrink-0 text-accent-ink"/>
              <p className="text-[13px] text-ink-soft">
                The Property Health Engine is the next build. Until it publishes a score for an
                estate, VALORA shows the real operational data underneath and states plainly that the
                score is pending — it never invents one.
              </p>
            </div>
            <Link to="/register" className="mt-6 inline-flex items-center gap-2 text-[13.5px] font-medium text-accent-ink hover:underline">
              Create an account to see your estate’s data
              <IconArrowRight size={16}/>
            </Link>
          </div>

          <Card className="p-6">
            <div className="flex items-baseline justify-between">
              <h3 className="text-[15px] font-semibold">Published factor weights</h3>
              <span className="num text-[11px] text-ink-muted">PRD §8.1</span>
            </div>
            <p className="mt-1.5 text-[12.5px] text-ink-muted">
              The formula is fixed and inspectable before any machine learning is introduced.
            </p>
            <LivingScoreFactors />
          </Card>
        </div>
      </section>

      {/* -------------------------------------------------------- who it's for */}
      <Section eyebrow="Who it is for" title="Everyone with a long-term stake in the estate" intro="Access is estate-scoped. A client never proves which estate it belongs to by supplying an identifier — membership is resolved on the server, and anything outside your estate is not there.">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {AUDIENCE.map((person) => (<Card key={person.who} className="p-5">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-xs bg-accent-wash text-accent-ink">
                {person.icon}
              </span>
              <h3 className="mt-3 text-[15px] font-semibold">{person.who}</h3>
              <p className="mt-1.5 text-[13px] text-ink-soft">{person.line}</p>
            </Card>))}
        </div>
      </Section>

      {/* ------------------------------------------------------- why different */}
      <section className="border-t border-ink/15 bg-surface">
        <div className="mx-auto max-w-[1200px] px-5 py-14">
          <p className="num text-[11px] tracking-[0.18em] text-accent-ink uppercase">
            What a listing cannot tell you
          </p>
          <h2 className="mt-3 max-w-2xl text-[26px] leading-tight font-semibold sm:text-[32px]">
            The data only exists inside the communities that run on it
          </h2>

          <div className="mt-8 hairline overflow-hidden rounded-xs bg-surface">
            <table className="w-full border-collapse text-left text-[13px]">
              <thead>
                <tr>
                  <th className="border-b border-ink/15 bg-paper px-4 py-2.5 text-[11px] font-medium tracking-wider text-ink-muted uppercase">
                    Question a buyer actually asks
                  </th>
                  <th className="border-b border-ink/15 bg-paper px-4 py-2.5 text-[11px] font-medium tracking-wider text-ink-muted uppercase">
                    Where it lives today
                  </th>
                  <th className="border-b border-ink/15 bg-paper px-4 py-2.5 text-right text-[11px] font-medium tracking-wider text-ink-muted uppercase">
                    On VALORA
                  </th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON.map(([question, today, answer]) => (<tr key={question}>
                    <td className="border-b border-ink/10 px-4 py-3">{question}</td>
                    <td className="border-b border-ink/10 px-4 py-3 text-ink-muted">{today}</td>
                    <td className="border-b border-ink/10 px-4 py-3 text-right">
                      {answer === 'yes' ? (<Chip tone="good" glyph="✓">
                          Visible
                        </Chip>) : (<Chip tone="alert" glyph="✕">
                          Not visible
                        </Chip>)}
                    </td>
                  </tr>))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* -------------------------------------------------------------- close */}
      <section className="bg-ink text-paper">
        <div className="mx-auto max-w-[1200px] px-5 py-14">
          <Keyline className="opacity-40"/>
          <h2 className="mt-6 max-w-2xl text-[26px] leading-tight font-semibold sm:text-[30px]">
            Residents register themselves. Estates are provisioned by their HOA.
          </h2>
          <p className="mt-3 max-w-2xl text-[14.5px] text-paper/75">
            Public registration always creates a resident — privileged estate roles are granted
            through an existing membership, never self-selected. If your estate has not been
            provisioned yet, your account will show that it is awaiting approval.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <LinkButton to="/register" variant="primary" className="px-5 py-2.5">
              Create a resident account
              <IconArrowRight size={17}/>
            </LinkButton>
            <Link to="/login" className="inline-flex items-center gap-2 rounded-xs border border-paper/30 px-5 py-2.5 text-sm font-medium text-paper transition-colors hover:bg-paper/10">
              Sign in
            </Link>
          </div>
        </div>
      </section>
    </PublicShell>);
}
