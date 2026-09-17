import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Desktop from './components/Desktop';
import {
  askLauraStream,
  declineAgentAction,
  ensureSession,
  executeAgentAction,
  getConversation,
  getProfile,
  getTeamMessages,
  resetProfile,
  saveProfile,
  sendTeamMessage,
} from './services/agentApi';

const departments = ['개발팀', '인사팀', '마케팅팀', '디자인팀', '기획팀'];
const departmentPlanets = [
  '/assets/blue-planet.png',
  '/assets/planet-hr.png',
  '/assets/planet-marketing.png',
  '/assets/planet-design.png',
  '/assets/planet-planning-v2.png',
];
const initialMessage = {
  id: 'initial-agent-message',
  sender: 'agent',
  text: '궁금한 내용을 입력하면 회사 적응을 도와드릴게요.',
};

export default function App() {
  const [stage, setStage] = useState('home');
  const [windowMode, setWindowMode] = useState('open');
  const [departmentIndex, setDepartmentIndex] = useState(0);
  const [activeTeam, setActiveTeam] = useState(0);
  const [isLauraChat, setIsLauraChat] = useState(true);
  const [welcomeOpen, setWelcomeOpen] = useState(false);
  const [featureMode, setFeatureMode] = useState(false);
  const [featureIndex, setFeatureIndex] = useState(0);
  const [lauraArrived, setLauraArrived] = useState(false);
  const [sessionReady, setSessionReady] = useState(false);
  const [messages, setMessages] = useState([initialMessage]);
  const [isReplying, setIsReplying] = useState(false);
  const [agentActivity, setAgentActivity] = useState(null);
  const [failedRequest, setFailedRequest] = useState(null);
  const buttonSoundRef = useRef(null);
  const completionVoiceRef = useRef(null);
  const keyboardSoundRef = useRef(null);
  const typingDemosRef = useRef(new Set());
  const conversationId = isLauraChat ? 'planet-laura' : 'planet-demo';
  const conversationTeam = departments[isLauraChat ? departmentIndex : activeTeam];

  const playClickSound = useCallback(() => {
    const sound = buttonSoundRef.current;
    if (!sound) return;
    sound.pause();
    sound.currentTime = 0;
    sound.play().catch(() => {});
  }, []);

  useEffect(() => {
    buttonSoundRef.current = new Audio('/assets/99F6EC485F71F3ED03.mp3');
    completionVoiceRef.current = new Audio('/assets/0914(1).MP3');
    keyboardSoundRef.current = new Audio('/assets/keyboard.mp3');
    buttonSoundRef.current.volume = 0.45;
    buttonSoundRef.current.preload = 'auto';
    completionVoiceRef.current.preload = 'auto';
    keyboardSoundRef.current.preload = 'auto';
    keyboardSoundRef.current.volume = 0.34;
    keyboardSoundRef.current.loop = true;

    const playButtonSound = (event) => {
      const button = event.target instanceof Element ? event.target.closest('button') : null;
      if (!button || button.id === 'complete-button' || button.disabled) return;

      playClickSound();
    };

    document.addEventListener('click', playButtonSound);

    departmentPlanets.forEach((source) => {
      const image = new Image();
      image.src = source;
    });

    return () => {
      document.removeEventListener('click', playButtonSound);
      [buttonSoundRef, completionVoiceRef, keyboardSoundRef].forEach((audioRef) => {
        audioRef.current?.pause();
      });
    };
  }, [playClickSound]);

  useEffect(() => {
    let cancelled = false;

    const restoreSession = async () => {
      try {
        await ensureSession();
        const savedProfile = await getProfile();
        if (cancelled) return;
        const savedTeamIndex = savedProfile ? departments.indexOf(savedProfile.team) : -1;
        const restoredTeamIndex = savedTeamIndex >= 0 ? savedTeamIndex : 0;
        setSessionReady(true);
        setStage(savedProfile ? 'chat' : 'home');
        setDepartmentIndex(restoredTeamIndex);
        setActiveTeam(restoredTeamIndex);
        setIsLauraChat(true);
        setWelcomeOpen(false);
        setFeatureMode(false);
        setFeatureIndex(0);
        setLauraArrived(false);
        setMessages([initialMessage]);
        setFailedRequest(null);
      } catch (error) {
        if (!cancelled) setFailedRequest({ message: '', error: error.message });
      }
    };

    restoreSession();
    return () => {
      cancelled = true;
    };
  }, []);

  const resetDemo = async () => {
    const confirmed = window.confirm(
      '온보딩 프로필과 대화 기록을 초기화할까요? Google Calendar 연결은 유지됩니다.',
    );
    if (!confirmed) return;

    try {
      await resetProfile();
      setStage('home');
      setWindowMode('open');
      setDepartmentIndex(0);
      setActiveTeam(0);
      setIsLauraChat(true);
      setWelcomeOpen(false);
      setFeatureMode(false);
      setFeatureIndex(0);
      setLauraArrived(false);
      setMessages([initialMessage]);
      setAgentActivity(null);
      setFailedRequest(null);
    } catch (error) {
      window.alert(error.message || '데모를 초기화하지 못했습니다.');
    }
  };

  useEffect(() => {
    if (stage !== 'chat' || !sessionReady) return undefined;
    let cancelled = false;
    const team = conversationTeam;
    setMessages(isLauraChat ? [initialMessage] : []);
    setFailedRequest(null);

    const loadMessages = () => {
      const request = isLauraChat
        ? getConversation(team, conversationId)
        : getTeamMessages(team);
      request.then((response) => {
        if (cancelled) return;
        if (isLauraChat) {
          setMessages(response.messages.length ? response.messages : [initialMessage]);
          return;
        }
        setMessages(response.messages.map((message) => ({
          id: `team-${message.id}`,
          sender: 'member',
          senderName: message.sender_name,
          text: message.content,
          isOwn: message.is_own,
          createdAt: message.created_at,
        })));
      })
      .catch(() => {
        if (cancelled) return;
        setMessages(isLauraChat ? [initialMessage] : []);
      });
    };

    loadMessages();
    const refreshTimer = isLauraChat ? null : window.setInterval(loadMessages, 3000);

    return () => {
      cancelled = true;
      if (refreshTimer) window.clearInterval(refreshTimer);
    };
  }, [activeTeam, conversationId, conversationTeam, isLauraChat, sessionReady, stage]);

  const startKeyboardSound = useCallback((demoId) => {
    typingDemosRef.current.add(demoId);
    if (typingDemosRef.current.size !== 1) return;
    const sound = keyboardSoundRef.current;
    if (!sound) return;
    sound.currentTime = 0;
    sound.play().catch(() => {});
  }, []);

  const stopKeyboardSound = useCallback((demoId) => {
    typingDemosRef.current.delete(demoId);
    if (typingDemosRef.current.size > 0) return;
    const sound = keyboardSoundRef.current;
    if (!sound) return;
    sound.pause();
    sound.currentTime = 0;
  }, []);

  const finishProfile = async (profile) => {
    await saveProfile({ ...profile, team: departments[departmentIndex] });
    setStage('loading');
    const voice = completionVoiceRef.current;

    const finishLoading = () => {
      setStage('chat');
      setActiveTeam(departmentIndex);
      setWelcomeOpen(true);
    };

    if (!voice) {
      window.setTimeout(finishLoading, 3000);
      return;
    }

    voice.pause();
    voice.currentTime = 0;
    voice.addEventListener('ended', finishLoading, { once: true });
    voice.play().catch(() => window.setTimeout(finishLoading, 3000));
  };

  const closeWelcome = () => {
    setWelcomeOpen(false);
    setFeatureMode(false);
    setFeatureIndex(0);
    setLauraArrived(false);
    typingDemosRef.current.clear();
    if (keyboardSoundRef.current) {
      keyboardSoundRef.current.pause();
      keyboardSoundRef.current.currentTime = 0;
    }
  };

  const goToFeature = () => {
    setFeatureMode(true);
    setFeatureIndex(0);
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setLauraArrived(true);
    }
  };

  const goToSecondFeature = () => {
    setFeatureIndex(1);
  };

  const goToThirdFeature = () => {
    setFeatureIndex(2);
  };

  const goToFinalFeature = () => {
    setFeatureIndex(3);
  };

  const goToIntroduction = () => {
    setFeatureMode(false);
    setFeatureIndex(0);
    setLauraArrived(false);
  };

  const sendMessage = async (text, { showUserMessage = true } = {}) => {
    const value = text.trim();
    if (!value || isReplying) return;

    if (!isLauraChat) {
      setFailedRequest(null);
      setIsReplying(true);
      try {
        const message = await sendTeamMessage(conversationTeam, value);
        setMessages((current) => [
          ...current.filter((item) => item.id !== `team-${message.id}`),
          {
            id: `team-${message.id}`,
            sender: 'member',
            senderName: message.sender_name,
            text: message.content,
            isOwn: message.is_own,
            createdAt: message.created_at,
          },
        ]);
      } catch (error) {
        setFailedRequest({ message: value, error: error.message });
      } finally {
        setIsReplying(false);
      }
      return;
    }

    setFailedRequest(null);
    setIsReplying(true);
    setAgentActivity({ phase: 'thinking', label: '요청 전달 중', tool: null });

    if (showUserMessage) {
      setMessages((current) => [
        ...current,
        { id: Date.now(), sender: 'user', text: value },
      ]);
    }

    const responseMessageId = `agent-${Date.now()}`;
    setMessages((current) => [
      ...current,
      { id: responseMessageId, sender: 'agent', text: '', sources: [] },
    ]);

    try {
      const response = await askLauraStream(
        { message: value, team: conversationTeam, conversationId },
        (delta) => {
          setAgentActivity(null);
          setMessages((current) => current.map((item) => (
            item.id === responseMessageId ? { ...item, text: item.text + delta } : item
          )));
        },
        setAgentActivity,
      );
      setMessages((current) => current.map((item) => (
        item.id === responseMessageId ? { ...item, ...response } : item
      )));
    } catch (error) {
      setMessages((current) => current.filter((item) => item.id !== responseMessageId));
      setFailedRequest({ message: value, error: error.message });
    } finally {
      setIsReplying(false);
      setAgentActivity(null);
    }
  };

  const retryLastRequest = () => {
    if (failedRequest) sendMessage(failedRequest.message, { showUserMessage: false });
  };

  const declineAction = async (messageId) => {
    const target = messages.find((message) => message.id === messageId);
    if (!target?.action?.id) return;

    try {
      await declineAgentAction(target.action.id);
    } catch (error) {
      setMessages((current) => [
        ...current,
        { id: Date.now(), sender: 'agent', text: `업무 취소에 실패했습니다. ${error.message}` },
      ]);
      return;
    }

    setMessages((current) => current.map((message) => (
      message.id === messageId
        ? { ...message, action: { ...message.action, status: 'declined' } }
        : message
    )));
  };

  const approveAction = async (messageId) => {
    const target = messages.find((message) => message.id === messageId);
    if (!target?.action?.id) return;

    setMessages((current) => current.map((message) => (
      message.id === messageId
        ? { ...message, action: { ...message.action, status: 'running' } }
        : message
    )));

    let result;
    try {
      result = await executeAgentAction(target.action.id);
      if (result.status === 'authorization_required' && result.authorization_url) {
        window.location.assign(result.authorization_url);
        return;
      }
    } catch (error) {
      setMessages((current) => current.map((message) => (
        message.id === messageId
          ? { ...message, action: { ...message.action, status: 'pending' } }
          : message
      )));
      setMessages((current) => [
        ...current,
        { id: Date.now(), sender: 'agent', text: `업무 실행에 실패했습니다. ${error.message}` },
      ]);
      return;
    }

    setMessages((current) => [
      ...current.map((message) => (
        message.id === messageId
          ? { ...message, action: { ...message.action, status: 'approved' } }
          : message
      )),
      { id: Date.now(), sender: 'agent', text: result.message },
    ]);

  };

  const openLauraChat = () => {
    if (isReplying) return;
    setFailedRequest(null);
    setIsLauraChat(true);
  };

  const changeTeamChat = (index) => {
    if (isReplying || index !== departmentIndex) return;
    setFailedRequest(null);
    setIsLauraChat(false);
    setActiveTeam(index);
  };

  const pageClassName = useMemo(() => {
    const classes = ['page'];
    if (stage !== 'home') classes.push('naming-active');
    if (stage === 'loading') classes.push('loading-active');
    if (stage === 'chat') classes.push('blank-active');
    if (welcomeOpen) classes.push('welcome-open');
    if (windowMode !== 'open') classes.push(windowMode);
    return classes.join(' ');
  }, [stage, welcomeOpen, windowMode]);

  return (
    <div>
      <Desktop
        activeTeam={activeTeam}
        agentActivity={agentActivity}
        departmentIndex={departmentIndex}
        departments={departments}
        departmentPlanets={departmentPlanets}
        failedRequest={failedRequest}
        featureIndex={featureIndex}
        featureMode={featureMode}
        isReplying={isReplying}
        isLauraChat={isLauraChat}
        lauraArrived={lauraArrived}
        memberTeamIndex={departmentIndex}
        messages={messages}
        pageClassName={pageClassName}
        stage={stage}
        welcomeOpen={welcomeOpen}
        windowMode={windowMode}
        onCloseWelcome={closeWelcome}
        onDepartmentChange={setDepartmentIndex}
        onApproveAction={approveAction}
        onDeclineAction={declineAction}
        onFeatureArrived={() => setLauraArrived(true)}
        onFinishProfile={finishProfile}
        onGoToFeature={goToFeature}
        onGoToFinalFeature={goToFinalFeature}
        onGoToIntroduction={goToIntroduction}
        onGoToSecondFeature={goToSecondFeature}
        onGoToThirdFeature={goToThirdFeature}
        onLauraChat={openLauraChat}
        onOpenPlanet={() => setWindowMode('open')}
        onPlayButtonSound={playClickSound}
        onResetDemo={resetDemo}
        onRetry={retryLastRequest}
        onSendMessage={sendMessage}
        onStageChange={setStage}
        onStartKeyboard={startKeyboardSound}
        onStopKeyboard={stopKeyboardSound}
        onTeamChange={changeTeamChat}
        onWindowModeChange={setWindowMode}
      />
    </div>
  );
}
