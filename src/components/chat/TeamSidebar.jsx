const teams = ['개발팀', '인사팀', '마케팅팀', '디자인팀', '기획팀'];

export default function TeamSidebar({
  activeTeam,
  isLauraChat,
  memberTeamIndex,
  onLauraChat,
  onTeamChange,
}) {
  return (
    <aside className="chat-sidebar" aria-label="팀별 채팅 목록">
      <h2 className="chat-sidebar-title">TEAM CHAT</h2>
      <button
        className={`team-chat-button laura-chat-button${isLauraChat ? ' active' : ''}`}
        type="button"
        onClick={onLauraChat}
      >
        <img className="laura-chat-avatar" src="/assets/ai-agent.png" alt="로라" />
        <span>로라<small>AI AGENT · ONLINE</small></span>
      </button>
      <div className="team-chat-divider" aria-hidden="true">TEAM CHANNELS</div>
      {teams.map((team, index) => (
        <button
          className={`team-chat-button${!isLauraChat && index === activeTeam ? ' active' : ''}`}
          type="button"
          key={team}
          disabled={index !== memberTeamIndex}
          title={index !== memberTeamIndex ? '소속 팀 채팅만 참여할 수 있어요.' : undefined}
          onClick={() => onTeamChange(index)}
        >
          {index === memberTeamIndex ? '●' : '🔒'} {team}
        </button>
      ))}
    </aside>
  );
}
