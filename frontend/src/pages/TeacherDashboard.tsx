import { useState, useEffect, useRef } from 'react';
import { getMyClasses, getUploads, uploadTabel, getUploadRecords, getDiscrepancies } from '../services/api';

export default function TeacherDashboard() {
  const [classes, setClasses] = useState<any[]>([]);
  const [uploads, setUploads] = useState<any[]>([]);
  const [selectedClass, setSelectedClass] = useState('');
  const [mealDate, setMealDate] = useState(new Date().toISOString().split('T')[0]);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<{type: string, text: string} | null>(null);
  const [records, setRecords] = useState<any[] | null>(null);
  const [discrepancies, setDiscrepancies] = useState<any[]>([]);
  const [showDiscModal, setShowDiscModal] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getMyClasses().then(r => {
      setClasses(r.data);
      if (r.data.length === 1) setSelectedClass(r.data[0].id);
    });
    loadUploads();
  }, []);

  const loadUploads = () => {
    getUploads().then(r => setUploads(r.data));
  };

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file || !selectedClass || !mealDate) {
      setMessage({ type: 'error', text: 'Заполните все поля и выберите файл' });
      return;
    }
    setUploading(true);
    setMessage(null);
    const fd = new FormData();
    fd.append('file', file);
    fd.append('class_id', selectedClass);
    fd.append('meal_date', mealDate);
    try {
      const res = await uploadTabel(fd);
      setMessage({ type: 'success', text: `Файл загружен! Статус: ${res.data.status}. Учеников: ${res.data.parsed_class_name || ''}` });
      loadUploads();
      // Load records for preview
      getUploadRecords(res.data.id).then(r => setRecords(r.data));
      // Load discrepancies
      getDiscrepancies({ class_id: selectedClass, meal_date: mealDate }).then(r => {
        setDiscrepancies(r.data);
        if (r.data.length > 0) setShowDiscModal(true);
      });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Ошибка загрузки' });
    }
    setUploading(false);
  };

  return (
    <div>
      <h1 className="page-title">Кабинет учителя</h1>

      <div className="card">
        <h3>Загрузка табеля питания</h3>
        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 16}}>
          <div className="form-group">
            <label>Класс</label>
            <select value={selectedClass} onChange={e => setSelectedClass(e.target.value)}>
              <option value="">Выберите класс</option>
              {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Дата</label>
            <input type="date" value={mealDate} onChange={e => setMealDate(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Файл (.xls / .xlsx)</label>
            <input type="file" ref={fileRef} accept=".xls,.xlsx" />
          </div>
        </div>
        <button className="btn btn-primary" onClick={handleUpload} disabled={uploading}>
          {uploading ? 'Загрузка...' : 'Загрузить табель'}
        </button>
      </div>

      {message && (
        <div className={`card ${message.type === 'error' ? 'disc-card severity-error' : ''}`}
             style={message.type === 'success' ? {background: '#dcfce7', borderLeft: '4px solid #16a34a'} : {}}>
          {message.text}
        </div>
      )}

      {/* Parsed records preview */}
      {records && records.length > 0 && (
        <div className="card">
          <h3>Распарсенные данные ({records.length} учеников)</h3>
          <div style={{overflowX: 'auto'}}>
            <table>
              <thead>
                <tr>
                  <th>ФИО</th>
                  <th>Льгота</th>
                  <th>Аванг. завтр.</th>
                  <th>Аванг. обед</th>
                  <th>Аванг. ШВ</th>
                  <th>Люб. завтр.</th>
                  <th>Люб. обед</th>
                  <th>Люб. ШВ</th>
                  <th>Итого завтр.</th>
                  <th>Итого обед</th>
                  <th>Итого ШВ</th>
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
          </div>
        </div>
      )}

      {/* Upload history */}
      <div className="card">
        <h3>История загрузок</h3>
        {uploads.length === 0 ? <p style={{color: '#888'}}>Пока нет загрузок</p> : (
          <table>
            <thead>
              <tr>
                <th>Дата</th>
                <th>Класс</th>
                <th>Файл</th>
                <th>Версия</th>
                <th>Статус</th>
                <th>Загружен</th>
              </tr>
            </thead>
            <tbody>
              {uploads.map((u: any) => (
                <tr key={u.id}>
                  <td>{u.meal_date}</td>
                  <td>{u.class_name}</td>
                  <td>{u.original_filename}</td>
                  <td className="text-center">{u.version}</td>
                  <td>
                    <span className={`badge ${u.status === 'success' ? 'badge-green' : u.status === 'error' ? 'badge-red' : 'badge-yellow'}`}>
                      {u.status === 'success' ? 'Обработан' : u.status === 'error' ? 'Ошибка' : 'Обработка...'}
                    </span>
                  </td>
                  <td>{new Date(u.created_at).toLocaleString('ru')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Discrepancies Modal */}
      {showDiscModal && discrepancies.length > 0 && (
        <div className="modal-overlay" onClick={() => setShowDiscModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Обнаружены расхождения с предыдущим днём</h3>
            {discrepancies.map((d: any) => (
              <div key={d.id} style={{marginBottom: 16}}>
                <p style={{fontWeight: 600, marginBottom: 8}}>
                  {d.class_name} | {d.meal_date} vs {d.previous_date}
                </p>
                {d.items.map((item: any) => (
                  <div key={item.id} className={`disc-card severity-${item.severity}`}>
                    {item.description}
                  </div>
                ))}
              </div>
            ))}
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowDiscModal(false)}>Закрыть</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
