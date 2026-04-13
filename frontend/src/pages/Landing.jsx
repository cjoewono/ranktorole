import { Link } from "react-router-dom";

export default function Landing() {
  return (
    <div className="relative min-h-screen bg-background flex flex-col">
      {/* TOP BAR */}
      <div className="relative z-10 flex items-center justify-between px-6 py-3 bg-surface-container-low border-b border-outline-variant">
        <Link
          to="/"
          className="font-headline font-bold text-primary text-sm hover:opacity-80 transition-opacity"
        >
          ▣ RankToRole
        </Link>
        <nav className="flex items-center gap-6">
          <a
            href="#process"
            className="font-label text-xs tracking-widest uppercase text-on-surface-variant hover:text-on-surface transition-colors"
          >
            Process
          </a>
          <a
            href="#example"
            className="font-label text-xs tracking-widest uppercase text-on-surface-variant hover:text-on-surface transition-colors"
          >
            Example
          </a>
          <Link
            to="/login"
            className="font-label text-xs tracking-widest uppercase text-on-surface-variant hover:text-on-surface transition-colors"
          >
            Sign in
          </Link>
          <Link
            to="/register"
            className="mission-gradient px-4 py-1.5 font-label text-xs tracking-widest uppercase text-on-primary font-semibold"
          >
            Enlist
          </Link>
        </nav>
      </div>

      {/* HERO SECTION */}
      <section className="relative flex flex-col items-center justify-center text-center px-6 py-24 flex-1 overflow-hidden">
        <div className="tactical-grid absolute inset-0" />
        <div className="relative z-10 max-w-2xl mx-auto flex flex-col items-center gap-6">
          {/* Status chip */}
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-secondary inline-block" />
            <span className="font-label text-xs tracking-widest uppercase text-secondary">
              TRANSLATION ENGINE ONLINE
            </span>
          </div>

          {/* Headline */}
          <h1 className="font-headline font-bold text-5xl uppercase text-on-surface leading-tight">
            YOUR SERVICE
            <br />
            <span className="text-primary">TRANSLATED</span>
            <br />
            NOT LOST
          </h1>

          {/* Subtext */}
          <p className="font-body text-base text-on-surface-variant max-w-lg mx-auto">
            Upload your military resume. Paste a job description. Get a tailored
            civilian resume that hiring managers actually understand.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center gap-4 mt-2">
            <Link
              to="/register"
              className="mission-gradient px-6 py-3 font-label font-semibold tracking-widest uppercase text-on-primary text-sm"
            >
              BEGIN TRANSLATION →
            </Link>
            <a
              href="#process"
              className="px-6 py-3 font-label font-semibold tracking-widest uppercase text-on-surface-variant text-sm border border-outline-variant bg-transparent hover:border-outline hover:text-on-surface transition-colors"
            >
              SEE THE PROCESS
            </a>
          </div>
        </div>
      </section>

      {/* PROCESS SECTION */}
      <section id="process" className="px-6 py-20 bg-background">
        <div className="max-w-5xl mx-auto">
          <div className="flex flex-col items-center text-center mb-12 gap-3">
            <span className="font-label text-xs tracking-widest uppercase text-secondary">
              OPERATIONAL SEQUENCE
            </span>
            <h2 className="font-headline font-bold text-2xl uppercase text-on-surface">
              THREE PHASES. ONE MISSION.
            </h2>
            <p className="font-body text-sm text-on-surface-variant max-w-md">
              From raw military resume to tailored civilian application — a
              structured process built for precision.
            </p>
          </div>

          {/* Step cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 border border-outline-variant divide-y md:divide-y-0 md:divide-x divide-outline-variant">
            {[
              {
                num: "01",
                title: "UPLOAD RESUME",
                desc: "Drop your military resume PDF. We extract your experience, rank, MOS, and accomplishments automatically.",
              },
              {
                num: "02",
                title: "SET THE TARGET",
                desc: "Paste the job description you're applying for. Our AI aligns your background to exactly what the employer needs.",
              },
              {
                num: "03",
                title: "DEPLOY RESUME",
                desc: "Review the translated draft, refine with AI-assisted chat, finalize your bullets, and export to PDF.",
              },
            ].map(({ num, title, desc }) => (
              <div
                key={num}
                className="bg-surface-container p-6 flex flex-col gap-3"
              >
                <span className="font-headline font-bold text-3xl text-primary-container">
                  {num}
                </span>
                <h3 className="font-headline font-semibold text-sm uppercase text-on-surface">
                  {title}
                </h3>
                <p className="font-body text-sm text-on-surface-variant">
                  {desc}
                </p>
              </div>
            ))}
          </div>

          {/* Metrics row */}
          <div className="grid grid-cols-1 md:grid-cols-3 border border-t-0 border-outline-variant divide-y md:divide-y-0 md:divide-x divide-outline-variant mt-0">
            {[
              { value: "<2m", label: "TIME TO FIRST DRAFT" },
              { value: "100%", label: "JARGON ELIMINATED" },
              { value: "1:1", label: "TAILORED PER JOB" },
            ].map(({ value, label }) => (
              <div
                key={label}
                className="bg-surface-container p-4 text-center flex flex-col items-center gap-1"
              >
                <span className="font-headline font-bold text-2xl text-primary">
                  {value}
                </span>
                <span className="font-label text-xs tracking-widest uppercase text-outline">
                  {label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* BEFORE / AFTER SECTION */}
      <section id="example" className="px-6 py-20 bg-surface-container-low">
        <div className="max-w-5xl mx-auto">
          <div className="flex flex-col items-center text-center mb-12 gap-3">
            <span className="font-label text-xs tracking-widest uppercase text-secondary">
              BEFORE / AFTER
            </span>
            <h2 className="font-headline font-bold text-2xl uppercase text-on-surface">
              SEE THE TRANSLATION
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] items-start gap-4">
            {/* Before card */}
            <div className="bg-surface-container border border-outline-variant p-6 flex flex-col gap-4">
              <span className="font-label text-xs tracking-widest uppercase text-outline">
                INPUT — MILITARY RESUME
              </span>
              <div>
                <h3 className="font-headline font-semibold uppercase text-on-surface">
                  SSG, E-6, SIGNAL CORPS
                </h3>
                <p className="font-label text-xs text-outline uppercase mt-1">
                  UNITED STATES ARMY · 2016–2024
                </p>
              </div>
              <p className="font-body text-sm text-on-surface-variant">
                Served as NCOIC for battalion-level S6 operations. Managed
                NIPR/SIPR network infrastructure, conducted PACE planning, and
                supervised subordinate Soldiers on comms systems maintenance and
                OPSEC compliance.
              </p>
              <ul className="flex flex-col gap-2">
                {[
                  "Executed COMSEC management for 400+ user base across 3 FOBs",
                  "Led KVM switch and VSAT terminal installation under OPTEMPO",
                  "Supervised PCS/PED cycles and conducted EER counseling",
                ].map((b) => (
                  <li key={b} className="flex items-start gap-2">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-outline-variant shrink-0" />
                    <span className="font-body text-sm text-on-surface-variant">
                      {b}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Arrow */}
            <div className="hidden md:flex items-center justify-center self-center">
              <svg
                className="w-6 h-6 text-outline-variant"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="square"
                  strokeLinejoin="miter"
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </div>

            {/* After card */}
            <div className="bg-surface-container border border-secondary p-6 flex flex-col gap-4">
              <span className="font-label text-xs tracking-widest uppercase text-secondary">
                OUTPUT — CIVILIAN RESUME
              </span>
              <div>
                <h3 className="font-headline font-semibold uppercase text-on-surface">
                  IT INFRASTRUCTURE MANAGER
                </h3>
                <p className="font-label text-xs text-outline uppercase mt-1">
                  TARGETING: SENIOR IT MANAGER ROLES
                </p>
              </div>
              <p className="font-body text-sm text-on-surface-variant">
                IT operations leader with 8 years managing enterprise network
                infrastructure in high-pressure, mission-critical environments.
                Proven track record coordinating distributed teams, securing
                sensitive communications systems, and delivering uptime across
                multiple sites.
              </p>
              <ul className="flex flex-col gap-2">
                {[
                  "Managed network security and communications infrastructure for 400+ users across 3 locations",
                  "Led hardware deployment projects — satellite terminals, server racks — under tight operational timelines",
                  "Supervised and developed direct reports through structured performance review cycles",
                ].map((b) => (
                  <li key={b} className="flex items-start gap-2">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-secondary shrink-0" />
                    <span className="font-body text-sm text-on-surface-variant">
                      {b}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* CTA SECTION */}
      <section className="bg-surface-container-low border-t border-outline-variant text-center py-16 px-6">
        <div className="max-w-xl mx-auto flex flex-col items-center gap-6">
          {/* Status chip */}
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-secondary inline-block" />
            <span className="font-label text-xs tracking-widest uppercase text-secondary">
              TRANSLATION ENGINE ONLINE
            </span>
          </div>

          <h2 className="font-headline font-bold text-3xl uppercase text-on-surface leading-tight">
            YOUR SERVICE HAS VALUE.
            <br />
            MAKE EMPLOYERS SEE IT.
          </h2>

          <p className="font-body text-sm text-on-surface-variant">
            Free to start. No credit card. No jargon left behind.
          </p>

          <Link
            to="/register"
            className="mission-gradient px-8 py-3 font-label font-semibold tracking-widest uppercase text-on-primary text-sm"
          >
            BEGIN TRANSLATION →
          </Link>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="bg-background border-t border-outline-variant py-6 px-6 space-y-4">
        <div className="flex items-center justify-between">
          <span className="font-label text-xs tracking-widest uppercase text-outline">
            RANKTOROLE — BUILT FOR THOSE WHO SERVED
          </span>
          <div className="flex items-center gap-6">
            <Link
              to="/login"
              className="font-label text-xs tracking-widest uppercase text-outline hover:text-on-surface-variant transition-colors"
            >
              SIGN IN
            </Link>
            <Link
              to="/register"
              className="font-label text-xs tracking-widest uppercase text-outline hover:text-on-surface-variant transition-colors"
            >
              REGISTER
            </Link>
          </div>
        </div>
        <div className="flex items-center gap-3 pt-2 border-t border-outline-variant">
          <a
            href="https://services.onetcenter.org/"
            target="_blank"
            rel="noopener noreferrer"
            title="This site incorporates information from O*NET Web Services. Click to learn more."
          >
            <img
              src="https://www.onetcenter.org/image/link/onet-in-it.svg"
              alt="O*NET in-it"
              className="h-8 w-auto opacity-60 hover:opacity-100 transition-opacity"
            />
          </a>
          <p className="font-body text-xs text-outline leading-relaxed">
            This site incorporates information from{" "}
            <a
              href="https://services.onetcenter.org/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-tertiary hover:underline"
            >
              O*NET Web Services
            </a>{" "}
            by the U.S. Department of Labor, Employment and Training
            Administration (USDOL/ETA). O*NET® is a trademark of USDOL/ETA.
          </p>
        </div>
      </footer>
    </div>
  );
}
