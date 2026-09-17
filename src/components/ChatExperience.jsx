import { useEffect, useState } from 'react';
import ChatRoom from './chat/ChatRoom';
import TeamSidebar from './chat/TeamSidebar';

function ProjectAnswer() {
  return (
    <div className="demo-answer project-result" aria-label="프로젝트 흐름도 답변 예시">
      <div className="demo-answer-label">로라의 답변</div>
      <div className="project-result-title">CURRENT PROJECT FLOW</div>
      <div className="project-result-track">
        <span><b>01</b> Laura 사내 QA</span><i />
        <span><b>02</b> 고객 파일럿</span><i />
        <span><b>03</b> 안정화</span><i />
        <span><b>04</b> 11월 출시</span>
      </div>
    </div>
  );
}

function HistoryAnswer() {
  return (
    <div className="demo-answer history-result" aria-label="회사 연혁 답변 예시">
      <div className="demo-answer-label">로라의 답변</div>
      <p><b>2012</b> 협업 소프트웨어 스튜디오 PLANET 설립</p>
      <p><b>2021</b> Employee Experience 플랫폼으로 전환</p>
      <p><b>2024</b> AI Agent 사업부 및 Laura 개발 시작</p>
    </div>
  );
}

function ScheduleAnswer() {
  return (
    <div className="demo-answer schedule-result" aria-label="Google Calendar 일정 등록 결과 예시">
      <div className="demo-answer-label">로라의 답변</div>
      <div className="schedule-result-status">✓ GOOGLE CALENDAR 등록 완료</div>
      <dl>
        <div><dt>일정</dt><dd>팀 미팅</dd></div>
        <div><dt>시간</dt><dd>오늘 오후 3:00</dd></div>
        <div><dt>캘린더</dt><dd>내 기본 캘린더</dd></div>
      </dl>
    </div>
  );
}

function MultiAgentAnswer() {
  return (
    <div className="multi-agent-result" aria-label="로라에 연결된 팀별 Agent 창">
      <div className="agent-org-connector" aria-hidden="true" />
      <div className="team-agent-org" aria-label="로라에 연결된 팀별 Agent 조직도">
        {[
          ['개발팀', false],
          ['인사팀', false],
          ['마케팅팀', true],
          ['디자인팀', true],
          ['기획팀', false],
        ].map(([team, targeted]) => (
          <section className={`team-agent-node${targeted ? ' targeted' : ''}`} key={team}>
            <span>{team}</span>
            <b>AI AGENT</b>
            <small>{targeted ? '● 명령 수신' : '○ STANDBY'}</small>
          </section>
        ))}
      </div>
    </div>
  );
}

function FeatureDemo({
  active,
  demoId,
  question,
  buttonLabel,
  onPlayButtonSound,
  onStartKeyboard,
  onStopKeyboard,
  externalResult = false,
  children,
}) {
  const [cycle, setCycle] = useState(0);
  const [typedText, setTypedText] = useState('');
  const [phase, setPhase] = useState('idle');

  useEffect(() => {
    if (!active) {
      setTypedText('');
      setPhase('idle');
      onStopKeyboard(demoId);
      return undefined;
    }

    let characterIndex = 0;
    let typingTimer;
    const timers = [];
    const later = (callback, delay) => {
      const timer = window.setTimeout(callback, delay);
      timers.push(timer);
      return timer;
    };

    setTypedText('');
    setPhase('animate');

    later(() => {
      setPhase('typing');
      onStartKeyboard(demoId);

      typingTimer = window.setInterval(() => {
        characterIndex += 1;
        setTypedText(question.slice(0, characterIndex));

        if (characterIndex >= question.length) {
          window.clearInterval(typingTimer);
          onStopKeyboard(demoId);

          later(() => {
            if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
              setPhase('clicked');
              if (!externalResult) later(() => setCycle((value) => value + 1), 2400);
              return;
            }
            setPhase('cursor-active');
          }, 180);
        }
      }, 96);
    }, 420);

    return () => {
      timers.forEach(window.clearTimeout);
      window.clearInterval(typingTimer);
      onStopKeyboard(demoId);
    };
  }, [active, cycle, demoId, externalResult, onStartKeyboard, onStopKeyboard, question]);

  const finishCursorClick = (event) => {
    if (event.animationName !== 'demo-cursor-click' || !active) return;
    onPlayButtonSound();
    setPhase('clicked');
    if (!externalResult) window.setTimeout(() => setCycle((value) => value + 1), 2400);
  };

  const demoClassName = [
    'feature-demo',
    active ? 'animate' : '',
    phase === 'cursor-active' ? 'cursor-active' : '',
    phase === 'clicked' ? 'clicked' : '',
  ].filter(Boolean).join(' ');

  const chatWindow = (
    <section className={demoClassName}>
      <header className="demo-chat-header">
        <img src="/assets/ai-agent.png" alt="" />
        <span>{externalResult ? '로라 · ORCHESTRATOR' : '로라 · AI agent'}</span>
        <small>● ONLINE</small>
      </header>

      {!externalResult && children}

      <div className="demo-composer">
        <span className={`demo-typing${phase === 'typing' ? ' typing' : ''}`}>{typedText}</span>
        <button className="demo-send" type="button" tabIndex="-1">{buttonLabel}</button>
        <span className="demo-cursor" aria-hidden="true" onAnimationEnd={finishCursorClick}>➤</span>
      </div>
    </section>
  );

  if (!externalResult) return chatWindow;

  return (
    <div className={`orchestration-demo ${phase === 'clicked' ? 'clicked' : ''}`}>
      {chatWindow}
      {children}
    </div>
  );
}

function LauraIntroduction({
  featureIndex,
  featureMode,
  lauraArrived,
  onCloseWelcome,
  onFeatureArrived,
  onGoToFeature,
  onGoToFinalFeature,
  onGoToIntroduction,
  onGoToSecondFeature,
  onGoToThirdFeature,
  onStartChat,
  onPlayButtonSound,
  onStartKeyboard,
  onStopKeyboard,
}) {
  const welcomeClassName = [
    'welcome-content',
    featureMode ? 'feature-mode' : '',
    featureIndex === 3 ? 'finale-mode' : '',
    lauraArrived ? 'laura-arrived' : '',
  ].filter(Boolean).join(' ');

  return (
    <div className={welcomeClassName}>
      <button className="welcome-close" type="button" aria-label="소개 창 닫기" onClick={onCloseWelcome}>×</button>

      <div
        className="agent-character-wrap"
        onAnimationEnd={(event) => {
          if (event.animationName === 'laura-to-corner') onFeatureArrived();
        }}
      >
        <img className="agent-character" src="/assets/ai-agent.png" alt="웃고 있는 AI 에이전트 캐릭터" />
      </div>

      <button className="intro-next" type="button" aria-label="다음 소개 보기" onClick={onGoToFeature} />
      <p className="welcome-message welcome-intro-message">
        만나서 반가워요! 저는 신입사원이 입사했을 때 회사를 잘 이해하고 적응할 수 있도록 도와주는 AI Agent 로라입니다!
      </p>

      <div className="feature-content">
        <p className="feature-speech" key={featureIndex}>
          {featureIndex === 0
            ? '로라가 제공하는 핵심 기능 3가지를 소개할게요! 첫 번째는 신입사원이 회사에 처음 들어왔을 때 회사 시스템을 빠르게 이해할 수 있도록 다양한 사내 정보를 제공하는 기능입니다.'
            : featureIndex === 1
              ? '두 번째는 AI Agent 기능입니다. 일정을 등록해 달라고 말하면 Agent가 내용을 확인하고, 사용자 승인 후 실제 일정 등록 작업을 수행합니다.'
              : featureIndex === 2
                ? '마지막은 향후 제공할 멀티 AI Agent 기능입니다. 로라가 최상위 Agent가 되어 여러 팀의 개별 Agent에게 작업을 전달할 수 있습니다.'
                : '그럼 바로 로라랑 대화를 시작해봐요!'}
        </p>

        {featureIndex === 0 ? (
          <div className="feature-demo-grid">
            <FeatureDemo
              active={featureMode && lauraArrived}
              demoId="project"
              question="현재 회사에서 어떤 프로젝트를 진행 중이야?"
              buttonLabel="전송"
              onPlayButtonSound={onPlayButtonSound}
              onStartKeyboard={onStartKeyboard}
              onStopKeyboard={onStopKeyboard}
            >
              <ProjectAnswer />
            </FeatureDemo>
            <FeatureDemo
              active={featureMode && lauraArrived}
              demoId="history"
              question="회사 연혁에 대해서 알려줘"
              buttonLabel="전송"
              onPlayButtonSound={onPlayButtonSound}
              onStartKeyboard={onStartKeyboard}
              onStopKeyboard={onStopKeyboard}
            >
              <HistoryAnswer />
            </FeatureDemo>
          </div>
        ) : featureIndex === 1 ? (
          <div className="feature-demo-grid agent-feature-demo-grid">
            <FeatureDemo
              active={featureMode && lauraArrived}
              demoId="schedule-agent"
              question="오늘 오후 3시에 팀 미팅 등록해줘"
              buttonLabel="전송"
              onPlayButtonSound={onPlayButtonSound}
              onStartKeyboard={onStartKeyboard}
              onStopKeyboard={onStopKeyboard}
            >
              <ScheduleAnswer />
            </FeatureDemo>
          </div>
        ) : featureIndex === 2 ? (
          <div className="feature-demo-grid agent-feature-demo-grid">
            <FeatureDemo
              active={featureMode && lauraArrived}
              demoId="multi-agent"
              question="마케팅팀과 디자인팀에게 오늘 오후 미팅 가능한지 메시지 보내줘"
              buttonLabel="전송"
              onPlayButtonSound={onPlayButtonSound}
              onStartKeyboard={onStartKeyboard}
              onStopKeyboard={onStopKeyboard}
              externalResult
            >
              <MultiAgentAnswer />
            </FeatureDemo>
          </div>
        ) : (
          <div className="feature-finale">
            <button type="button" onClick={onStartChat}>시작하기</button>
          </div>
        )}
      </div>

      <button
        className="feature-nav previous"
        type="button"
        aria-label="이전 소개 보기"
        onClick={
          featureIndex === 0
            ? onGoToIntroduction
            : featureIndex === 1
              ? onGoToFeature
              : featureIndex === 2 ? onGoToSecondFeature : onGoToThirdFeature
        }
      />
      {featureIndex < 3 && (
        <button
          className="feature-nav next"
          type="button"
          aria-label={featureIndex === 0 ? '두 번째 기능 보기' : featureIndex === 1 ? '세 번째 기능 보기' : '로라와 대화 시작 안내 보기'}
          onClick={featureIndex === 0 ? onGoToSecondFeature : featureIndex === 1 ? onGoToThirdFeature : onGoToFinalFeature}
        />
      )}
    </div>
  );
}

export default function ChatExperience({
  activeTeam,
  agentActivity,
  failedRequest,
  featureIndex,
  featureMode,
  isReplying,
  isLauraChat,
  lauraArrived,
  memberTeamIndex,
  messages,
  onApproveAction,
  onCloseWelcome,
  onDeclineAction,
  onFeatureArrived,
  onGoToFeature,
  onGoToFinalFeature,
  onGoToIntroduction,
  onGoToSecondFeature,
  onGoToThirdFeature,
  onLauraChat,
  onPlayButtonSound,
  onRetry,
  onSendMessage,
  onStartKeyboard,
  onStopKeyboard,
  onTeamChange,
}) {
  return (
    <section className="loading-screen" aria-live="polite" aria-label="로라 온보딩 및 채팅">
      <div className="loading-panel">
        <div className="loading-orbit" aria-hidden="true">
          <img className="loading-planet first" src="/assets/planet-design.png" alt="" />
          <img className="loading-planet second" src="/assets/blue-planet.png" alt="" />
        </div>
        <p className="loading-text">Loading...</p>
      </div>

      <div className="chat-layout">
        <TeamSidebar
          activeTeam={activeTeam}
          isLauraChat={isLauraChat}
          memberTeamIndex={memberTeamIndex}
          onLauraChat={onLauraChat}
          onTeamChange={onTeamChange}
        />
        <ChatRoom
          activeTeam={activeTeam}
          agentActivity={agentActivity}
          failedRequest={failedRequest}
          isReplying={isReplying}
          isLauraChat={isLauraChat}
          messages={messages}
          onApproveAction={onApproveAction}
          onDeclineAction={onDeclineAction}
          onRetry={onRetry}
          onSendMessage={onSendMessage}
        />
      </div>

      <LauraIntroduction
        featureIndex={featureIndex}
        featureMode={featureMode}
        lauraArrived={lauraArrived}
        onCloseWelcome={onCloseWelcome}
        onFeatureArrived={onFeatureArrived}
        onGoToFeature={onGoToFeature}
        onGoToFinalFeature={onGoToFinalFeature}
        onGoToIntroduction={onGoToIntroduction}
        onGoToSecondFeature={onGoToSecondFeature}
        onGoToThirdFeature={onGoToThirdFeature}
        onStartChat={() => {
          onLauraChat();
          onCloseWelcome();
        }}
        onPlayButtonSound={onPlayButtonSound}
        onStartKeyboard={onStartKeyboard}
        onStopKeyboard={onStopKeyboard}
      />
    </section>
  );
}
