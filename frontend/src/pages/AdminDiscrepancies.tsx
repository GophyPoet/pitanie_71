import { useState, useEffect } from 'react';
import { getDiscrepancies, reviewDiscrepancy } from '../services/api';

export default function AdminDiscrepancies() {
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [filter, setFilter] = useState('');
  const [discs, setDiscs] = useState<any[]>([]);

  useEffect(() => { load(); }, [date, filter]);

  const load = () => {
    const params: any = {};
    if (date) params.meal_date = date;
    if (filter) params.status = filter;
    getDiscrepancies(params).then(r => setDiscs(r.data));
  };

  const handleReview = async (id: number, action: string) => {
    await reviewDiscrepancy(id, action);
    load();
  };

  return (
    <div>
      <h1 className="page-title">Расхождения</h1>

      <div className="card flex gap-12" style={{alignItems: 'end'}}>
        <div className="form-group" style={{marginBottom: 0}}>
          <label>Дата</label>
          <input type="date" value={date} onChange={e => setDate(e.target.value)} />
        </div>
        <div className="form-group" style={{marginBottom: 0}}>
          <label>Статус</label>
          <select value={filter} onChange={e => setFilter(e.target.value)}>
            <option value="">Все</option>
            <option value="new">Новые</option>
            <option value="reviewed">Проверенные</option>
            <option value="dismissed">Отклонённые</option>
          </select>
        </div>
      </div>

      {discs.length === 0 ? (
        <div className="card"><p style={{color: '#888'}}>Расхождений не найдено</p></div>
      ) : (
        discs.map(d => (
          <div className="card" key={d.id}>
            <div className="flex-between mb-8">
              <div>
                <strong>{d.class_name}</strong>
                <span style={{color: '#888', marginLeft: 8}}>
                  {d.meal_date} vs {d.previous_date}
                </span>
              </div>
              <div className="flex gap-8">
                <span className={`badge ${d.status === 'new' ? 'badge-yellow' : d.status === 'reviewed' ? 'badge-green' : 'badge-red'}`}>
                  {d.status === 'new' ? 'Новое' : d.status === 'reviewed' ? 'Проверено' : 'Отклонено'}
                </span>
                {d.status === 'new' && (
                  <>
                    <button className="btn btn-sm btn-success" onClick={() => handleReview(d.id, 'reviewed')}>
                      Проверено
                    </button>
                    <button className="btn btn-sm btn-secondary" onClick={() => handleReview(d.id, 'dismissed')}>
                      Отклонить
                    </button>
                  </>
                )}
              </div>
            </div>
            {d.items.map((item: any) => (
              <div key={item.id} className={`disc-card severity-${item.severity}`}>
                <div>{item.description}</div>
                {item.student_name && <small style={{color: '#888'}}>Ученик: {item.student_name}</small>}
              </div>
            ))}
          </div>
        ))
      )}
    </div>
  );
}
