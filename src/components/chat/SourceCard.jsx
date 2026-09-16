export default function SourceCard({ source }) {
  return (
    <article className="source-card" aria-label={`${source.title} 출처`}>
      <span className="source-card-icon" aria-hidden="true">▤</span>
      <span className="source-card-content">
        <b><em>출처 문서명</em>{source.title}</b>
      </span>
    </article>
  );
}
