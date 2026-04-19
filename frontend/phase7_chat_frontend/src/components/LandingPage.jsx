import "./LandingPage.css";
import founderImg from "../assets/founder.jpg";

export default function LandingPage({ onStartChat }) {
  return (
    <div className="landing-container">
      {/* Header / Navbar */}
      <nav className="navbar">
        <div className="navbar-logo">
          <div className="logo-icon">🌿</div>
          <div className="logo-text">
            <span className="brand-name">Laxmi Chit Funds</span>
            <span className="brand-tagline">MUTUAL FUND DISTRIBUTOR</span>
          </div>
        </div>
        <div className="navbar-links">
          <a href="#funds">Funds</a>
          <a href="#why-us">Why us</a>
          <a href="#process">Process</a>
          <button className="nav-schedule-btn" onClick={onStartChat}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            Schedule
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="hero">
        <div className="hero-left">
          <div className="badge">AMFI REGISTERED DISTRIBUTOR</div>
          <h1 className="hero-title">
            Wealth that <br />
            <span className="accent-italic">compounds</span>, <br />
            advice you <span className="accent-italic">trust.</span>
          </h1>
          <p className="hero-description">
            Laxmi Chit Funds curates mutual fund portfolios tailored to your goals — whether that's retirement, your child's education, or simply growing what you've earned.
          </p>
          <div className="hero-buttons">
            <button className="btn-primary" onClick={onStartChat}>
              Schedule an appointment <span>→</span>
            </button>
            <button className="btn-outline">Explore funds</button>
          </div>
          <div className="hero-stats">
            <div className="stat-item">
              <span className="stat-value">₹240Cr+</span>
              <span className="stat-label">AUM ADVISED</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">1,800+</span>
              <span className="stat-label">FAMILIES SERVED</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">12 yrs</span>
              <span className="stat-label">IN THE MARKET</span>
            </div>
          </div>
        </div>

        <div className="hero-right">
          <div className="portfolio-card glass-card">
            <div className="card-top">
              <span className="card-label">PORTFOLIO • BALANCED</span>
              <div className="growth-badge">+14.6%</div>
            </div>
            <div className="portfolio-value">₹ 18,42,560</div>
            <div className="graph-container">
              <svg className="growth-graph" viewBox="0 0 400 150">
                <path d="M0,130 C50,120 100,100 150,90 C250,70 300,60 400,40" fill="none" stroke="var(--accent)" strokeWidth="3" />
                <path d="M0,130 C50,120 100,100 150,90 C250,70 300,60 400,40 V150 H0 Z" fill="url(#graph-gradient)" />
                <defs>
                  <linearGradient id="graph-gradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.3" />
                    <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <div className="asset-allocation">
              <div className="allocation-item">
                <span className="dot teal"></span> Equity • Large Cap <span className="value">42%</span>
              </div>
              <div className="allocation-item">
                <span className="dot teal-light"></span> Debt • Short Duration <span className="value">28%</span>
              </div>
              <div className="allocation-item">
                <span className="dot mint"></span> Hybrid • Aggressive <span className="value">20%</span>
              </div>
              <div className="allocation-item">
                <span className="dot gray"></span> Gold ETF <span className="value">10%</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Why Laxmi */}
      <section id="why-us" className="why-laxmi">
        <div className="section-label">— WHY LAXMI</div>
        <h2 className="section-title">Boutique advisory,<br /> institutional rigor.</h2>
        <div className="values-grid">
          <div className="value-card glass-card">
            <div className="icon-circle">🛡️</div>
            <h3>Goal-first planning</h3>
            <p>Every recommendation maps to a specific life goal — not a sales target.</p>
          </div>
          <div className="value-card glass-card">
            <div className="icon-circle">📈</div>
            <h3>Curated funds</h3>
            <p>We screen 1,500+ schemes down to a shortlist that's actually worth your money.</p>
          </div>
          <div className="value-card glass-card">
            <div className="icon-circle">👥</div>
            <h3>Family-grade service</h3>
            <p>A dedicated relationship manager who picks up the phone — every time.</p>
          </div>
        </div>
      </section>

      {/* Categories */}
      <section id="funds" className="categories">
        <div className="section-label">— CATEGORIES WE COVER</div>
        <div className="section-header">
          <h2 className="section-title">From safe to spirited.</h2>
          <p className="header-hint">We help you build across the full risk spectrum — diversified the way it should be.</p>
        </div>
        <div className="categories-grid">
          <div className="cat-card glass-card">
            <div className="cat-info">
               <span className="cat-type">LOW RISK</span>
               <h3>Liquid & Debt</h3>
               <p>Park cash, earn better than savings</p>
            </div>
          </div>
          <div className="cat-card glass-card">
            <div className="cat-info">
               <span className="cat-type">MODERATE</span>
               <h3>Hybrid Funds</h3>
               <p>Balanced equity-debt mix</p>
            </div>
          </div>
          <div className="cat-card glass-card">
            <div className="cat-info">
               <span className="cat-type">GROWTH</span>
               <h3>Equity Funds</h3>
               <p>Large, mid & flexicap strategies</p>
            </div>
          </div>
          <div className="cat-card glass-card">
            <div className="cat-info">
               <span className="cat-type">3YR LOCK</span>
               <h3>ELSS / Tax</h3>
               <p>Save tax under section 80C</p>
            </div>
          </div>
        </div>
      </section>

      {/* Process */}
      <section id="process" className="process">
        <div className="section-label">— HOW IT WORKS</div>
        <div className="process-split">
          <div className="process-left">
            <h2 className="section-title">Three steps to a <br /> portfolio that fits.</h2>
            <p className="section-subtitle">No jargon, no pressure. Start with a 30-minute conversation.</p>
            <button className="btn-primary" onClick={onStartChat}>
              Schedule an appointment <span>→</span>
            </button>
          </div>
          <div className="process-right">
            <div className="step-card glass-card">
              <span className="step-num">01</span>
              <div>
                 <h4>Discovery call</h4>
                 <p>We understand your goals, timeline and risk appetite.</p>
              </div>
            </div>
            <div className="step-card glass-card">
              <span className="step-num">02</span>
              <div>
                 <h4>Custom proposal</h4>
                 <p>A shortlist of funds with clear reasoning behind each pick.</p>
              </div>
            </div>
            <div className="step-card glass-card">
              <span className="step-num">03</span>
              <div>
                 <h4>Onboard & review</h4>
                 <p>Paperless onboarding, then quarterly reviews to stay on track.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Founder Message Section */}
      <section className="founder-message">
        <div className="section-label">— MESSAGE FROM THE FOUNDER</div>
        <div className="founder-content">
          <div className="founder-visual">
            <div className="founder-photo-glow">
              <img src={founderImg} alt="Laxmi Kant Pal" />
            </div>
            <h4 className="founder-name">Laxmi Kant Pal</h4>
            <p className="founder-title">FOUNDER • LAXMI CHIT FUNDS</p>
          </div>
          <div className="founder-text">
            <h2 className="quote-header">
              "Your money deserves more than <br />
              <span className="accent-italic">good intentions.</span>"
            </h2>
            <div className="message-paragraphs">
              <p>Long before Laxmi Chit Funds existed, I was the person my peers and colleagues came to for money advice. From helping a junior colleague pick their first SIP to guiding senior friends through retirement planning, those conversations consistently helped people grow their wealth steadily and avoid costly mistakes.</p>
              <p>Word spread quickly — what began as casual lunch-table chats turned into detailed portfolio reviews for dozens of families. That track record of giving genuinely good, unbiased investment advice is what made starting Laxmi Chit Funds a natural next step for me.</p>
              <p>Today, the same principle drives the firm: a distributor's job is not to sell, it's to <span className="bold-white">simplify</span>. Whether you're starting with a ₹5,000 SIP or planning a multi-crore retirement corpus, you get the same care, clarity, and the same person on the other end of the phone — me.</p>
            </div>
            <p className="signature">— L.K. PAL</p>
          </div>
        </div>
      </section>

      {/* Bottom CTA Card */}
      <section className="bottom-cta">
        <div className="cta-banner-card">
          <h2>Let's plan the next ten years of <br /> your money.</h2>
          <p>Book a free 30-minute consultation. No commitment, no spam.</p>
          <button className="btn-primary" onClick={onStartChat}>
            Schedule an appointment <span className="arrow">→</span>
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-left">
          © 2026 Laxmi Chit Funds • AMFI Registered Mutual Fund Distributor
        </div>
        <div className="footer-right">
          MUTUAL FUND INVESTMENTS ARE SUBJECT TO MARKET RISKS
        </div>
      </footer>
    </div>
  );
}
