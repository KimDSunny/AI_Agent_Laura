import { useEffect, useRef, useState } from 'react';
import ApprovalDialog from './ApprovalDialog';
import SourceCard from './SourceCard';

const teams = ['개발팀', '인사팀', '마케팅팀', '디자인팀', '기획팀'];

function AgentMessage({ item, onApproveAction, onDeclineAction }) {
  const sourceDocuments = Array.from(
    new Map((item.sources || []).map((source) => [source.title, source])).values(),
  );

  return (
    <div className="agent-message-group">
      <p className="chat-bubble">{item.text}</p>
      {sourceDocuments.map((source) => <SourceCard source={source} key={`${item.id}-${source.title}`} />)}
      {item.action && (
        <ApprovalDialog
          action={item.action}
          onApprove={() => onApproveAction(item.id)}
          onDecline={() => onDeclineAction(item.id)}
        />
      )}
    </div>
  );
}

function TeamMessage({ item }) {
  return (
    <div className={`team-message${item.isOwn ? ' own' : ''}`}>
      <span className="team-message-sender">{item.senderName}</span>
      <p className="chat-bubble">{item.text}</p>
    </div>
  );
}

export default function ChatRoom({
  activeTeam,
  agentActivity,
  failedRequest,
  isReplying,
  isLauraChat,
  messages,
  onApproveAction,
  onDeclineAction,
  onRetry,
  onSendMessage,
}) {
  const [message, setMessage] = useState('');
  const messagesRef = useRef(null);
  const hasRunningAction = messages.some((item) => item.action?.status === 'running');
  const hasPendingAction = messages.some((item) => item.action?.status === 'pending');
  const statusText = isReplying
    ? agentActivity?.label || '처리 중'
    : hasRunningAction ? '도구 실행 중' : hasPendingAction ? '승인 대기' : 'ONLINE';

  useEffect(() => {
    if (messagesRef.current) messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
  }, [failedRequest, isReplying, messages]);

  const submitMessage = (event) => {
    event.preventDefault();
    if (!message.trim() || isReplying) return;
    onSendMessage(message);
    setMessage('');
  };

  return (
    <section className="chat-main" aria-label={isLauraChat ? 'AI 에이전트 채팅' : '팀 그룹 채팅'}>
      <header className="chat-header">
        <span>{isLauraChat ? '로라 · 1:1 AI agent' : `${teams[activeTeam]} · 그룹 채팅`}</span>
        <span className="chat-header-actions">
          <span className={`agent-status${isReplying || hasRunningAction ? ' busy' : ''}`}>
            ● {isLauraChat ? statusText : 'TEAM ONLINE'}
          </span>
        </span>
      </header>

      <div className="chat-messages" ref={messagesRef} aria-live="polite">
        {!isLauraChat && messages.length === 0 && (
          <p className="team-chat-empty">아직 팀 메시지가 없어. 첫 메시지를 남겨봐.</p>
        )}

        {messages.map((item) => (
          !isLauraChat
            ? <TeamMessage item={item} key={item.id} />
            : item.sender === 'user'
              ? <p className="chat-bubble user" key={item.id}>{item.text}</p>
              : (
              <AgentMessage
                item={item}
                key={item.id}
                onApproveAction={onApproveAction}
                onDeclineAction={onDeclineAction}
              />
            )
        ))}

        {isReplying && isLauraChat && agentActivity && (
          <div className="reply-loading" role="status">
            <img src="/assets/ai-agent.png" alt="" />
            <span>{agentActivity?.label || '로라가 확인 중이야'}</span>
            <i /><i /><i />
          </div>
        )}

        {failedRequest && (
          <div className="chat-error" role="alert">
            <b>CONNECTION ERROR</b>
            <span>{failedRequest.error}</span>
            <button type="button" onClick={onRetry}>다시 시도</button>
          </div>
        )}
      </div>

      <form className="chat-composer" onSubmit={submitMessage}>
        <input
          className="chat-input"
          type="text"
          placeholder={isLauraChat ? '회사 정보를 묻거나 일정을 등록해달라고 해봐...' : '팀원에게 메시지를 보내세요...'}
          autoComplete="off"
          aria-label="메시지"
          value={message}
          disabled={isReplying}
          onChange={(event) => setMessage(event.target.value)}
        />
        <button className="chat-send-button" type="submit" disabled={isReplying || !message.trim()}>전송</button>
      </form>
    </section>
  );
}
