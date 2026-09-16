import { useMemo, useState } from 'react';

export default function DepartmentSetup({
  stage,
  departmentIndex,
  departments,
  departmentPlanets,
  onDepartmentChange,
  onFinishProfile,
  onStageChange,
}) {
  const [profileMessage, setProfileMessage] = useState('');
  const today = useMemo(() => {
    const date = new Date();
    const pad = (value) => String(value).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  }, []);

  const submitProfile = async (event) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const employeeName = String(data.get('employeeName') || '').trim();
    const hireDate = String(data.get('hireDate') || '');

    if (!employeeName) {
      setProfileMessage('이름을 입력해주세요.');
      event.currentTarget.elements.employeeName.focus();
      return;
    }

    setProfileMessage('');
    try {
      await onFinishProfile({ employeeName, hireDate });
    } catch (error) {
      setProfileMessage(error.message || '입사 정보를 저장하지 못했어.');
    }
  };

  return (
    <section className={`naming-screen${stage !== 'department' ? ' profile-active' : ''}`} aria-labelledby="naming-title">
      <p className="department-name" aria-live="polite">{departments[departmentIndex]}</p>

      <div className="planet-selector">
        <button
          className="department-arrow previous"
          type="button"
          aria-label="이전 부서 보기"
          hidden={departmentIndex === 0}
          onClick={() => onDepartmentChange(departmentIndex - 1)}
        />
        <div className="planet-stage">
          <img
            className={`blue-planet${departmentIndex === 4 ? ' round-cutout' : ''}`}
            src={departmentPlanets[departmentIndex]}
            alt={`${departments[departmentIndex]}의 행성`}
          />
        </div>
        <button
          className="department-arrow"
          type="button"
          aria-label="다음 부서 보기"
          disabled={departmentIndex === departments.length - 1}
          onClick={() => onDepartmentChange(departmentIndex + 1)}
        />
      </div>

      <h1 className="naming-title" id="naming-title">부서를 선택해주세요.</h1>

      <form
        className="department-form"
        onSubmit={(event) => {
          event.preventDefault();
          onStageChange('profile');
        }}
      >
        <button className="next-button" type="submit">다음</button>
        <p className="department-message" aria-live="polite" />
      </form>

      <form className="profile-form" aria-label="입사 정보 입력" onSubmit={submitProfile}>
        <label className="profile-field" htmlFor="hire-date">
          입사일
          <input className="profile-input" id="hire-date" name="hireDate" type="date" max={today} required />
        </label>

        <label className="profile-field" htmlFor="employee-name">
          이름
          <input
            className="profile-input"
            id="employee-name"
            name="employeeName"
            type="text"
            maxLength="20"
            placeholder="이름을 입력하세요"
            autoComplete="name"
            required
          />
        </label>

        <button className="next-button complete-button" id="complete-button" type="submit">완료</button>
        <p className="profile-message" aria-live="polite">{profileMessage}</p>
      </form>
    </section>
  );
}
