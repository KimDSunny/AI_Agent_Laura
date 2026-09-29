import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import PlanetWindow from './PlanetWindow';

const GALLERY_FOLDERS = [
  {
    id: 'AI_agent',
    label: 'AI_agent',
    files: [
      'KakaoTalk_Photo_2026-09-29-09-20-13 001.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-20-14 002.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-20-14 003.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-20-14 004.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-20-15 005.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-20-15 006.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-20-15 007.jpeg',
    ],
  },
  {
    id: 'GPT-2',
    label: 'GPT-2',
    files: [
      'KakaoTalk_Photo_2026-09-29-09-18-36 001.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-37 002.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-37 003.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-38 004.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-38 005.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-38 006.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-39 007.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-39 008.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-39 009.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-40 010.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-40 011.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-41 012.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-41 013.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-41 014.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-42 015.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-42 016.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-43 017.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-43 018.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-43 019.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-44 020.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-44 021.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-44 022.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-45 023.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-45 024.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-46 025.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-46 026.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-46 027.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-47 028.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-47 029.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-18-47 030.jpeg',
    ],
  },
  {
    id: 'Neural_Network',
    label: 'Neural_Network',
    files: [
      'KakaoTalk_Photo_2026-09-29-09-20-45 001.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-20-45 002.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-20-45 003.jpeg',
    ],
  },
  {
    id: 'rag',
    label: 'rag',
    files: [
      'KakaoTalk_Photo_2026-09-29-09-16-18 001.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-16-19 002.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-16-19 003.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-16-19 004.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-16-20 005.jpeg',
      'KakaoTalk_Photo_2026-09-29-09-16-20 006.jpeg',
    ],
  },
];

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

      <div className="desktop-nav" aria-label="프로그램 메뉴">
        {['File', 'Search', 'Edit', 'View', 'Help'].map((menu) => (
          <span key={menu}>{menu}</span>
        ))}
      </div>

      <time className="desktop-clock">{clock}</time>
    </header>
  );
}

function DesktopShortcuts({ onAboutMeOpen, onGalleryOpen }) {
  return (
    <aside className="desktop-icons" aria-label="바탕화면 바로가기">
      <button className="desktop-shortcut" type="button" onClick={onAboutMeOpen}>
        <span className="shortcut-icon" aria-hidden="true">💗</span>
        <span>About me</span>
      </button>
      <button className="desktop-shortcut" type="button" onClick={onGalleryOpen}>
        <span className="shortcut-icon" aria-hidden="true">🖼️</span>
        <span>Gallery</span>
      </button>
    </aside>
  );
}

function AboutMe({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <section className="about-window" aria-label="About me 영상">
      <header className="about-titlebar">
        <strong>About me</strong>
        <button type="button" aria-label="About me 닫기" onClick={onClose}>×</button>
      </header>
      <div className="about-video-frame">
        <iframe
          src="https://www.youtube.com/embed/I9sDQE5ZdZk?autoplay=1&mute=1&playsinline=1&rel=0"
          title="About me"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          referrerPolicy="strict-origin-when-cross-origin"
          allowFullScreen
        />
      </div>
    </section>
  );
}

function Gallery({ isOpen, onClose }) {
  const [activeFolderId, setActiveFolderId] = useState(null);
  const [selectedImage, setSelectedImage] = useState(null);
  const activeFolder = GALLERY_FOLDERS.find((folder) => folder.id === activeFolderId);

  useEffect(() => {
    if (!isOpen) {
      setActiveFolderId(null);
      setSelectedImage(null);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!selectedImage) return undefined;
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') setSelectedImage(null);
    };
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [selectedImage]);

  if (!isOpen) return null;

  return (
    <section className="gallery-window" aria-label="사진 갤러리">
      <header className="gallery-titlebar">
        <strong>{activeFolder ? `Gallery / ${activeFolder.label}` : 'Gallery'}</strong>
        <button type="button" aria-label="갤러리 닫기" onClick={onClose}>×</button>
      </header>
      {activeFolder ? (
        <>
          <div className="gallery-toolbar">
            <button type="button" onClick={() => setActiveFolderId(null)}>← 폴더로 돌아가기</button>
            <span>{activeFolder.files.length}개 이미지</span>
          </div>
          <div className="gallery-grid">
            {activeFolder.files.map((fileName) => (
              <button
                className="gallery-photo"
                type="button"
                key={fileName}
                aria-label={`${activeFolder.label} 이미지 크게 보기`}
                onClick={() => setSelectedImage({
                  src: encodeURI(`/assets/${activeFolder.id}/${fileName}`),
                  alt: `${activeFolder.label} 이미지`,
                })}
              >
                <img
                  src={encodeURI(`/assets/${activeFolder.id}/${fileName}`)}
                  alt=""
                  loading="lazy"
                />
              </button>
            ))}
          </div>
        </>
      ) : (
        <div className="gallery-folder-grid">
          {GALLERY_FOLDERS.map((folder) => (
            <button
              className="gallery-folder"
              type="button"
              key={folder.id}
              onClick={() => setActiveFolderId(folder.id)}
            >
              <span className="gallery-folder-icon" aria-hidden="true">📁</span>
              <strong>{folder.label}</strong>
              <small>{folder.files.length}개 이미지</small>
            </button>
          ))}
        </div>
      )}
      {selectedImage && createPortal((
        <div
          className="gallery-lightbox"
          role="dialog"
          aria-modal="true"
          aria-label="확대 이미지"
          onClick={() => setSelectedImage(null)}
        >
          <button type="button" aria-label="확대 이미지 닫기" onClick={() => setSelectedImage(null)}>×</button>
          <img
            src={selectedImage.src}
            alt={selectedImage.alt}
            onClick={(event) => event.stopPropagation()}
          />
        </div>
      ), document.body)}
    </section>
  );
}

function Taskbar({ isOpen, onGalleryOpen, onOpenPlanet, onResetDemo, onShutdown }) {
  const [startMenuOpen, setStartMenuOpen] = useState(false);
  const startAreaRef = useRef(null);

  useEffect(() => {
    if (!startMenuOpen) return undefined;

    const closeMenu = (event) => {
      if (!startAreaRef.current?.contains(event.target)) setStartMenuOpen(false);
    };
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') setStartMenuOpen(false);
    };
    document.addEventListener('pointerdown', closeMenu);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('pointerdown', closeMenu);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [startMenuOpen]);

  const resetAndClose = () => {
    setStartMenuOpen(false);
    onResetDemo();
  };

  const shutdownAndClose = () => {
    setStartMenuOpen(false);
    onShutdown();
  };

  return (
    <nav className="desktop-taskbar" aria-label="작업 표시줄">
      <div className="start-area" ref={startAreaRef}>
        {startMenuOpen && (
          <div className="start-menu" role="menu">
            <div className="start-menu-brand">PLANET</div>
            <div className="start-menu-actions">
              <button type="button" role="menuitem" onClick={resetAndClose}>↻ 새로 시작</button>
              <button type="button" role="menuitem" onClick={shutdownAndClose}>◼ 종료</button>
            </div>
          </div>
        )}
        <button
          className={`task-start${startMenuOpen ? ' active' : ''}`}
          type="button"
          aria-expanded={startMenuOpen}
          onClick={() => setStartMenuOpen((current) => !current)}
        >
          START
        </button>
      </div>
      <button className="task-item" type="button" aria-pressed={isOpen} onClick={onOpenPlanet}>➜ Planet</button>
      <button className="task-item gallery-task-item" type="button" onClick={onGalleryOpen}>▣ Gallery</button>
      <div className="task-tray" aria-hidden="true" />
    </nav>
  );
}

export default function Desktop({ isShutDown, windowMode, onOpenPlanet, onResetDemo, onShutdown, ...windowProps }) {
  const [aboutMeOpen, setAboutMeOpen] = useState(false);
  const [galleryOpen, setGalleryOpen] = useState(false);

  const minimizePlanet = () => {
    windowProps.onWindowModeChange?.('minimized');
  };

  const openAboutMe = () => {
    setGalleryOpen(false);
    setAboutMeOpen(true);
    minimizePlanet();
  };

  const openDesktopGallery = () => {
    setAboutMeOpen(false);
    setGalleryOpen(true);
    minimizePlanet();
  };

  const openTaskbarGallery = () => {
    setAboutMeOpen(false);
    setGalleryOpen(true);
  };

  const openPlanet = () => {
    setAboutMeOpen(false);
    setGalleryOpen(false);
    onOpenPlanet();
  };

  if (isShutDown) {
    return (
      <main className="shutdown-screen" aria-label="PLANET 종료됨">
        <img src="/assets/planet-logo.png" alt="" />
        <strong>PLANET을 종료했습니다.</strong>
        <span>다시 이용하려면 브라우저를 새로고침해 주세요.</span>
      </main>
    );
  }

  return (
    <div className="desktop">
      <DesktopMenu />
      <DesktopShortcuts
        onAboutMeOpen={openAboutMe}
        onGalleryOpen={openDesktopGallery}
      />
      <PlanetWindow windowMode={windowMode} {...windowProps} />
      <AboutMe isOpen={aboutMeOpen} onClose={() => setAboutMeOpen(false)} />
      <Gallery
        isOpen={galleryOpen}
        onClose={() => setGalleryOpen(false)}
      />
      <Taskbar
        isOpen={windowMode === 'open' || windowMode === 'maximized'}
        onGalleryOpen={openTaskbarGallery}
        onOpenPlanet={openPlanet}
        onResetDemo={onResetDemo}
        onShutdown={onShutdown}
      />
    </div>
  );
}
