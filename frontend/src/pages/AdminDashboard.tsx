import { useState, useEffect } from 'react';
import { getDashboard } from '../services/api';

export default function AdminDashboard() {
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [stats, setStats] = useState<any>(null);

  useEffect(() => { load(); }, [date]);

  const load = () => {
    getDashboard(date).then(r => setStats(r.data));
  };

  if (!stats) return <div>Загрузка...</div>;

  return (
    <div>
      <div className="flex-between mb-16">
        <h1 className="page-title" style={{marginBottom: 0}}>Дашборд</h1>
        <input type="date" value={date} onChange={e => setDate(e.target.value)} style={{padding: '6px 12px', borderRadius: 6, border: '1px solid #d1d5db'}} />
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="value">{stats.total_classes}</div>
          <div className="label">Всего классов</div>
        </div>
        <div className="stat-card">
          <div className="value" style={{color: '#16a34a'}}>{stats.submitted_today}</div>
          <div className="label">Прислали</div>
        </div>
        <div className="stat-card">
          <div className="value" style={{color: '#dc2626'}}>{stats.not_submitted_today}</div>
          <div className="label">Не прислали</div>
        </div>
        <div className="stat-card">
          <div className="value">{stats.total_eating_today}</div>
          <div className="label">Питающихся</div>
        </div>
        <div className="stat-card">
          <div className="value">{stats.total_breakfasts_today}</div>
          <div className="label">Завтраков</div>
        </div>
        <div className="stat-card">
          <div className="value">{stats.total_lunches_today}</div>
          <div className="label">Обедов</div>
        </div>
        <div className="stat-card">
          <div className="value" style={{color: stats.discrepancies_new > 0 ? '#f59e0b' : '#16a34a'}}>
            {stats.discrepancies_new}
          </div>
          <div className="label">Новые расхождения</div>
        </div>
      </div>
    </div>
  );
}
