import { useEffect, useRef, useState } from 'react';
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

      <div className="desktop-nav" aria-label="프로그램 메뉴">
        {['File', 'Search', 'Edit', 'View', 'Help'].map((menu) => (
          <span key={menu}>{menu}</span>
        ))}
      </div>

      <time className="desktop-clock">{clock}</time>
    </header>
  );
}

function DesktopShortcuts() {
  return (
    <aside className="desktop-icons" aria-label="바탕화면 바로가기">
      <div className="desktop-shortcut">
        <span className="shortcut-icon" aria-hidden="true">💗</span>
        <span>About me</span>
      </div>
    </aside>
  );
}

function Gallery({ images, isOpen, onClose, onRemove, onUpload }) {
  const inputRef = useRef(null);

  if (!isOpen) return null;

  return (
    <section className="gallery-window" aria-label="사진 갤러리">
      <header className="gallery-titlebar">
        <strong>Gallery</strong>
        <button type="button" aria-label="갤러리 닫기" onClick={onClose}>×</button>
      </header>
      <div className="gallery-toolbar">
        <button type="button" onClick={() => inputRef.current?.click()}>＋ 사진 업로드</button>
        <span>이미지 파일을 여러 장 선택할 수 있습니다.</span>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          multiple
          hidden
          onChange={onUpload}
        />
      </div>
      <div className="gallery-grid">
        {images.length ? images.map((image) => (
          <figure className="gallery-photo" key={image.id}>
            <img src={image.url} alt={image.name} />
            <figcaption title={image.name}>{image.name}</figcaption>
            <button type="button" aria-label={`${image.name} 삭제`} onClick={() => onRemove(image.id)}>×</button>
          </figure>
        )) : (
          <div className="gallery-empty">
            <span aria-hidden="true">▧</span>
            <p>업로드한 사진이 여기에 표시됩니다.</p>
          </div>
        )}
      </div>
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
  const [galleryOpen, setGalleryOpen] = useState(false);
  const [galleryImages, setGalleryImages] = useState([]);
  const imageUrlsRef = useRef(new Set());

  useEffect(() => () => {
    imageUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
  }, []);

  const uploadPhotos = (event) => {
    const photos = Array.from(event.target.files || [])
      .filter((file) => file.type.startsWith('image/'))
      .map((file) => {
        const url = URL.createObjectURL(file);
        imageUrlsRef.current.add(url);
        return {
          id: `${file.name}-${file.lastModified}-${crypto.randomUUID()}`,
          name: file.name,
          url,
        };
      });
    if (photos.length) setGalleryImages((current) => [...current, ...photos]);
    event.target.value = '';
  };

  const removePhoto = (imageId) => {
    setGalleryImages((current) => current.filter((image) => {
      if (image.id !== imageId) return true;
      URL.revokeObjectURL(image.url);
      imageUrlsRef.current.delete(image.url);
      return false;
    }));
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
      <DesktopShortcuts />
      <PlanetWindow windowMode={windowMode} {...windowProps} />
      <Gallery
        images={galleryImages}
        isOpen={galleryOpen}
        onClose={() => setGalleryOpen(false)}
        onRemove={removePhoto}
        onUpload={uploadPhotos}
      />
      <Taskbar
        isOpen={windowMode === 'open' || windowMode === 'maximized'}
        onGalleryOpen={() => setGalleryOpen(true)}
        onOpenPlanet={onOpenPlanet}
        onResetDemo={onResetDemo}
        onShutdown={onShutdown}
      />
    </div>
  );
}
