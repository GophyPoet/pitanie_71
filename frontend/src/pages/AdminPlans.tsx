import { useState, useEffect } from 'react';
import { getPlans, createPlan, getPlan, removePlanDay, addPlanDay, getSubmissionStatus } from '../services/api';

const MONTHS = ['', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];

export default function AdminPlans() {
  const [plans, setPlans] = useState<any[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<any>(null);
  const [newYear, setNewYear] = useState(new Date().getFullYear());
  const [newMonth, setNewMonth] = useState(new Date().getMonth() + 1);
  const [dayStatuses, setDayStatuses] = useState<Record<string, any[]>>({});
  const [addDate, setAddDate] = useState('');

  useEffect(() => { loadPlans(); }, []);

  const loadPlans = () => { getPlans().then(r => setPlans(r.data)); };

  const handleCreate = async () => {
    try {
      await createPlan(newYear, newMonth);
      loadPlans();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Ошибка');
    }
  };

  const selectPlan = async (plan: any) => {
    const res = await getPlan(plan.id);
    setSelectedPlan(res.data);
    // Load submission status for each school day
    const statMap: Record<string, any[]> = {};
    for (const day of res.data.days) {
      if (day.is_school_day) {
        try {
          const st = await getSubmissionStatus(day.date);
          statMap[day.date] = st.data;
        } catch { /* ignore */ }
      }
    }
    setDayStatuses(statMap);
  };

  const handleRemoveDay = async (dayId: number) => {
    if (!selectedPlan) return;
    await removePlanDay(selectedPlan.id, dayId);
    selectPlan(selectedPlan);
  };

  const handleAddDay = async () => {
    if (!selectedPlan || !addDate) return;
    try {
      await addPlanDay(selectedPlan.id, addDate);
      setAddDate('');
      selectPlan(selectedPlan);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Ошибка');
    }
  };

  return (
    <div>
      <h1 className="page-title">Месячное планирование</h1>

      <div className="card">
        <h3>Создать план на месяц</h3>
        <div className="flex gap-8" style={{alignItems: 'end'}}>
          <div className="form-group" style={{marginBottom: 0}}>
            <label>Год</label>
            <input type="number" value={newYear} onChange={e => setNewYear(+e.target.value)} style={{width: 100}} />
          </div>
          <div className="form-group" style={{marginBottom: 0}}>
            <label>Месяц</label>
            <select value={newMonth} onChange={e => setNewMonth(+e.target.value)}>
              {MONTHS.slice(1).map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
            </select>
          </div>
          <button className="btn btn-primary" onClick={handleCreate}>Создать</button>
        </div>
      </div>

      <div className="card">
        <h3>Существующие планы</h3>
        <div className="flex gap-8" style={{flexWrap: 'wrap'}}>
          {plans.map(p => (
            <button key={p.id}
              className={`btn ${selectedPlan?.id === p.id ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => selectPlan(p)}>
              {MONTHS[p.month]} {p.year}
            </button>
          ))}
        </div>
      </div>

      {selectedPlan && (
        <div className="card">
          <div className="flex-between mb-8">
            <h3>{MONTHS[selectedPlan.month]} {selectedPlan.year} ({selectedPlan.days.length} дней)</h3>
            <div className="flex gap-8" style={{alignItems: 'center'}}>
              <input type="date" value={addDate} onChange={e => setAddDate(e.target.value)} style={{padding: '4px 8px', borderRadius: 6, border: '1px solid #d1d5db'}} />
              <button className="btn btn-sm btn-success" onClick={handleAddDay}>Добавить дату</button>
            </div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Дата</th>
                <th>День недели</th>
                <th>Учебный</th>
                <th>Прислали</th>
                <th>Не прислали</th>
                <th>Действие</th>
              </tr>
            </thead>
            <tbody>
              {selectedPlan.days.map((day: any) => {
                const d = new Date(day.date);
                const dayName = d.toLocaleDateString('ru', { weekday: 'long' });
                const stats = dayStatuses[day.date] || [];
                const submitted = stats.filter((s: any) => s.is_submitted).length;
                const notSubmitted = stats.filter((s: any) => !s.is_submitted).length;
                return (
                  <tr key={day.id} style={{opacity: day.is_school_day ? 1 : 0.5}}>
                    <td style={{fontWeight: 600}}>{day.date}</td>
                    <td>{dayName}</td>
                    <td className="text-center">{day.is_school_day ? 'Да' : 'Нет'}</td>
                    <td className="text-center">
                      {day.is_school_day && stats.length > 0 && (
                        <span className="badge badge-green">{submitted}</span>
                      )}
                    </td>
                    <td className="text-center">
                      {day.is_school_day && stats.length > 0 && notSubmitted > 0 && (
                        <span className="badge badge-red">{notSubmitted}</span>
                      )}
                    </td>
                    <td>
                      <button className="btn btn-sm btn-danger" onClick={() => handleRemoveDay(day.id)}>
                        Удалить
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
