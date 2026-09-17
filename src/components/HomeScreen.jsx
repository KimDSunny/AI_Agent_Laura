export default function HomeScreen({ onStart }) {
  return (
    <>
      <main className="content">
        <div className="logo">
          <img className="main-logo-image" src="/assets/planet-logo.png" alt="PLANET 로고" />
        </div>

        <div className="title">
          {'PLANET'.split('').map((letter, index) => <span key={`${letter}-${index}`}>{letter}</span>)}
        </div>

        <div className="subtitle">NEW COMPANY NEW START</div>
        <div className="buttons">
          <button className="btn start" type="button" onClick={onStart}>Start</button>
        </div>
        <div className="links"><span>Safety ⊘ Notice</span></div>
      </main>

      <footer>
        <div className="about-link"><span>What is PLANET?</span></div>
        <div>
          <span>Contact Us</span>&nbsp;|&nbsp;<span>Privacy Notice</span>
        </div>
        <div style={{ marginTop: 7 }}>
          Copyright © UNP. Inc. <span>All rights reserved.</span>
        </div>
      </footer>
    </>
  );
}
