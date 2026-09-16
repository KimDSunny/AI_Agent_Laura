import { useEffect, useState } from 'react';
import PlanetWindow from './PlanetWindow';

function DesktopMenu() {
  const [clock, setClock] = useState('');

  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      const day = now.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase();
      const time = now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      });
      setClock(`${day} ${time}`);
    };

    updateClock();
    const timer = window.setInterval(updateClock, 30000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <header className="desktop-menu">
      <div className="desktop-brand">
        <img className="brand-logo-image" src="/assets/planet-logo.png" alt="" />
        <span>PLANET</span>
      </div>

      <nav className="desktop-nav" aria-label="프로그램 메뉴">
        {['File', 'Search', 'Edit', 'View', 'Help'].map((menu) => (
          <a href="#" key={menu}>{menu}</a>
        ))}
      </nav>

      <time className="desktop-clock">{clock}</time>
    </header>
  );
}

function DesktopShortcuts() {
  return (
    <aside className="desktop-icons" aria-label="바탕화면 바로가기">
      <div className="desktop-shortcut">
        <span className="shortcut-icon" aria-hidden="true">🌐</span>
        <span>이 별로부터</span>
      </div>
      <div className="desktop-shortcut">
        <span className="shortcut-icon" aria-hidden="true">💗</span>
        <span>Dear my crazy<br />soulmate</span>
      </div>
    </aside>
  );
}

function Taskbar({ isOpen, onOpenPlanet }) {
  return (
    <nav className="desktop-taskbar" aria-label="작업 표시줄">
      <button className="task-start" type="button">START</button>
      <button className="task-item" type="button" aria-pressed={isOpen} onClick={onOpenPlanet}>➜ Planet</button>
      <button className="task-item" type="button">➜ Gallery</button>
      <div className="task-tray" aria-hidden="true" />
    </nav>
  );
}

export default function Desktop({ windowMode, onOpenPlanet, ...windowProps }) {
  return (
    <div className="desktop">
      <DesktopMenu />
      <DesktopShortcuts />
      <PlanetWindow windowMode={windowMode} {...windowProps} />
      <Taskbar isOpen={windowMode === 'open' || windowMode === 'maximized'} onOpenPlanet={onOpenPlanet} />
    </div>
  );
}
