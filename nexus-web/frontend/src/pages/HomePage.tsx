import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './HomePage.css';

export function HomePage() {
  const { user } = useAuth();

  return (
    <div className="home-page">
      <section className="hero">
        <h1>Nexus</h1>
        <p className="tagline">A strategic board game combining Go captures with Tic-Tac-Toe lines</p>
        <div className="hero-buttons">
          <Link to="/play" className="btn btn-large btn-primary">
            Play Now
          </Link>
          <Link to="/rules" className="btn btn-large btn-secondary">
            Learn the Rules
          </Link>
        </div>
      </section>

      <section className="features">
        <div className="feature">
          <h3>Strategic Depth</h3>
          <p>Capture opponent stones like Go, but beware the debt you accumulate. Complete a line to win - if you can afford it!</p>
        </div>
        <div className="feature">
          <h3>Two Game Modes</h3>
          <p>Play real-time games for quick matches, or correspondence for thoughtful, long-form play.</p>
        </div>
        <div className="feature">
          <h3>Simple Rules, Deep Strategy</h3>
          <p>Learn in minutes, master over a lifetime. The debt system creates unique tactical decisions.</p>
        </div>
      </section>

      <section className="quick-start">
        <h2>How Nexus Works</h2>
        <div className="rules-preview">
          <div className="rule">
            <span className="rule-num">1</span>
            <div>
              <strong>Place stones</strong> on the board, forming groups that share liberties
            </div>
          </div>
          <div className="rule">
            <span className="rule-num">2</span>
            <div>
              <strong>Capture opponent groups</strong> by filling all their liberties - but each captured stone adds to your debt
            </div>
          </div>
          <div className="rule">
            <span className="rule-num">3</span>
            <div>
              <strong>Complete a line</strong> (row, column, or diagonal) to trigger an audit - pay your debt by removing your own stones
            </div>
          </div>
          <div className="rule">
            <span className="rule-num">4</span>
            <div>
              <strong>Win by surviving</strong> the audit, or watch your opponent go bankrupt trying!
            </div>
          </div>
        </div>
        <Link to="/rules" className="learn-more">Read the full rules &rarr;</Link>
      </section>

      {!user && (
        <section className="cta">
          <h2>Ready to Play?</h2>
          <p>Create an account to save your games and challenge other players.</p>
          <div className="cta-buttons">
            <Link to="/register" className="btn btn-large btn-primary">Create Account</Link>
            <Link to="/login" className="btn btn-large btn-secondary">Sign In</Link>
          </div>
        </section>
      )}
    </div>
  );
}
