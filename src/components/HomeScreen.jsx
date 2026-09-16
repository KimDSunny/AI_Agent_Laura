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
        <div className="links"><a href="#">Safety ⊘ Notice</a></div>
      </main>

      <footer>
        <div className="about-link"><a href="#">What is PLANET?</a></div>
        <div>
          <a href="#">Contact Us</a>&nbsp;|&nbsp;<a href="#">Privacy Notice</a>
        </div>
        <div style={{ marginTop: 7 }}>
          Copyright © UNP. Inc. <a href="#">All rights reserved.</a>
        </div>
      </footer>
    </>
  );
}
