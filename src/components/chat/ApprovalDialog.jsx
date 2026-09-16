export default function ApprovalDialog({ action, onApprove, onDecline }) {
  if (action.status === 'approved') return null;

  const isRunning = action.status === 'running';

  return (
    <div className={`approval-dialog ${action.status}`} role="group" aria-label="업무 실행 확인">
      <div className="approval-title">⚠ EXECUTE TOOL</div>
      <strong>{action.title}</strong>
      <p>{action.detail}</p>

      {action.status === 'pending' || isRunning ? (
        <div className="approval-actions">
          <button type="button" onClick={onDecline} disabled={isRunning}>취소</button>
          <button className="approve" type="button" onClick={onApprove} disabled={isRunning}>
            {isRunning ? '실행 중...' : '승인'}
          </button>
        </div>
      ) : (
        <div className="approval-result">
          × 실행 취소
        </div>
      )}
    </div>
  );
}
