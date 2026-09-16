import { useEffect, useRef } from 'react';
import HomeScreen from './HomeScreen';
import DepartmentSetup from './DepartmentSetup';
import ChatExperience from './ChatExperience';

function WindowChrome({ windowMode, onWindowModeChange }) {
  const isMaximized = windowMode === 'maximized';

  return (
    <>
      <div className="top-bar">
        www.unknownpla.net
        <div className="window-buttons">
          <button className="window-btn" type="button" aria-label="창 최소화" onClick={() => onWindowModeChange('minimized')}>−</button>
          <button
            className="window-btn"
            type="button"
            aria-label={isMaximized ? '창 복원' : '창 최대화'}
            onClick={() => onWindowModeChange(isMaximized ? 'open' : 'maximized')}
          >
            {isMaximized ? '❐' : '□'}
          </button>
          <button className="window-btn" type="button" aria-label="창 닫기" onClick={() => onWindowModeChange('closed')}>×</button>
        </div>
      </div>

      <div className="window-brand" aria-hidden="true">
        <img className="window-logo-image" src="/assets/planet-logo.png" alt="" />
        <span>PLANET<small>NEW COMPANY, NEW START.</small></span>
      </div>

      <div className="circuit top-left" />
      <div className="circuit top-right" />
      <div className="circuit bottom-left" />
      <div className="circuit bottom-right" />
    </>
  );
}

export default function PlanetWindow({
  pageClassName,
  windowMode,
  onWindowModeChange,
  ...screenProps
}) {
  const pageRef = useRef(null);

  useEffect(() => {
    if (screenProps.stage === 'loading' || screenProps.stage === 'chat') {
      pageRef.current?.scrollTo({ top: 0, left: 0 });
    }
  }, [screenProps.stage]);

  const startResize = (event) => {
    const page = pageRef.current;
    if (event.button !== 0 || !page || windowMode === 'maximized') return;

    event.preventDefault();
    const windowRect = page.getBoundingClientRect();
    const startX = event.clientX;
    const startY = event.clientY;
    const startWidth = windowRect.width;
    const startHeight = windowRect.height;
    const minimumWidth = Math.min(620, window.innerWidth - 16);
    const minimumHeight = Math.min(480, window.innerHeight - 60);

    Object.assign(page.style, {
      left: `${windowRect.left}px`,
      top: `${windowRect.top}px`,
      width: `${startWidth}px`,
      height: `${startHeight}px`,
      transform: 'none',
    });

    document.body.classList.add('resizing-window');
    event.currentTarget.setPointerCapture(event.pointerId);

    const resizeWindow = (moveEvent) => {
      const maximumWidth = window.innerWidth - windowRect.left - 8;
      const maximumHeight = window.innerHeight - windowRect.top - 50;
      page.style.width = `${Math.min(maximumWidth, Math.max(minimumWidth, startWidth + moveEvent.clientX - startX))}px`;
      page.style.height = `${Math.min(maximumHeight, Math.max(minimumHeight, startHeight + moveEvent.clientY - startY))}px`;
    };

    const stopResizing = () => {
      document.body.classList.remove('resizing-window');
      window.removeEventListener('pointermove', resizeWindow);
      window.removeEventListener('pointerup', stopResizing);
      window.removeEventListener('pointercancel', stopResizing);
    };

    window.addEventListener('pointermove', resizeWindow);
    window.addEventListener('pointerup', stopResizing);
    window.addEventListener('pointercancel', stopResizing);
  };

  return (
    <div className={pageClassName} ref={pageRef}>
      <WindowChrome windowMode={windowMode} onWindowModeChange={onWindowModeChange} />
      <HomeScreen onStart={() => screenProps.onStageChange('department')} />
      <DepartmentSetup {...screenProps} />
      <ChatExperience {...screenProps} />
      <div className="resize-handle" role="separator" aria-label="창 크기 조절" onPointerDown={startResize} />
    </div>
  );
}
