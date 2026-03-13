import { useState, useEffect } from 'react';
import { getSubmissionStatus, getUploadRecords } from '../services/api';

export default function AdminStatus() {
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [statuses, setStatuses] = useState<any[]>([]);
  const [selectedUpload, setSelectedUpload] = useState<{id: number, className: string} | null>(null);
  const [records, setRecords] = useState<any[]>([]);

  useEffect(() => { load(); }, [date]);

  const load = () => {
    getSubmissionStatus(date).then(r => setStatuses(r.data));
  };

  const viewRecords = (uploadId: number, className: string) => {
    setSelectedUpload({ id: uploadId, className });
    getUploadRecords(uploadId).then(r => setRecords(r.data));
  };

  const submitted = statuses.filter(s => s.is_submitted);
  const notSubmitted = statuses.filter(s => !s.is_submitted);

  return (
    <div>
      <div className="flex-between mb-16">
        <h1 className="page-title" style={{marginBottom: 0}}>Статусы классов</h1>
        <input type="date" value={date} onChange={e => setDate(e.target.value)} style={{padding: '6px 12px', borderRadius: 6, border: '1px solid #d1d5db'}} />
      </div>

      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16}}>
        <div className="stat-card" style={{borderLeft: '4px solid #16a34a'}}>
          <div className="value" style={{color: '#16a34a'}}>{submitted.length}</div>
          <div className="label">Прислали</div>
        </div>
        <div className="stat-card" style={{borderLeft: '4px solid #dc2626'}}>
          <div className="value" style={{color: '#dc2626'}}>{notSubmitted.length}</div>
          <div className="label">Не прислали</div>
        </div>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Класс</th>
              <th>Статус</th>
              <th>Учитель</th>
              <th>Время отправки</th>
              <th>Версия</th>
              <th>Расхождения</th>
              <th>Действие</th>
            </tr>
          </thead>
          <tbody>
            {statuses.map(s => (
              <tr key={s.class_id}>
                <td style={{fontWeight: 600}}>{s.class_name}</td>
                <td>
                  {s.is_submitted
                    ? <span className="status-submitted">&#10003; Прислали</span>
                    : <span className="status-not-submitted">&#10007; Не прислали</span>
                  }
                </td>
                <td>{s.teacher_name || '-'}</td>
                <td>{s.submitted_at ? new Date(s.submitted_at).toLocaleString('ru') : '-'}</td>
                <td className="text-center">{s.version || '-'}</td>
                <td>
                  {s.has_discrepancies && <span className="badge badge-yellow">Есть</span>}
                </td>
                <td>
                  {s.upload_id && (
                    <button className="btn btn-sm btn-secondary" onClick={() => viewRecords(s.upload_id, s.class_name)}>
                      Просмотр
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Records Modal */}
      {selectedUpload && (
        <div className="modal-overlay" onClick={() => setSelectedUpload(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Табель: {selectedUpload.className}</h3>
            {records.length === 0 ? <p>Нет данных</p> : (
              <table>
                <thead>
                  <tr>
                    <th>ФИО</th><th>Льгота</th>
                    <th>Аванг.З</th><th>Аванг.О</th><th>Аванг.ШВ</th>
                    <th>Люб.З</th><th>Люб.О</th><th>Люб.ШВ</th>
                    <th>Итого З</th><th>Итого О</th><th>Итого ШВ</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((r: any) => (
                    <tr key={r.id}>
                      <td>{r.student_name_raw}</td>
                      <td>{r.benefit_raw || '-'}</td>
                      <td className="text-center">{r.avangard_breakfast || ''}</td>
                      <td className="text-center">{r.avangard_lunch || ''}</td>
                      <td className="text-center">{r.avangard_shved || ''}</td>
                      <td className="text-center">{r.lyubava_breakfast || ''}</td>
                      <td className="text-center">{r.lyubava_lunch || ''}</td>
                      <td className="text-center">{r.lyubava_shved || ''}</td>
                      <td className="text-center">{r.total_breakfasts}</td>
                      <td className="text-center">{r.total_lunches}</td>
                      <td className="text-center">{r.total_shved}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setSelectedUpload(null)}>Закрыть</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
