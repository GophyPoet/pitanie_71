import { useState, useEffect, useRef } from 'react';
import {
  getMyClasses, getUploads, uploadTabel,
  getDiscrepancies, getStudents, addStudent,
  removeStudent, getTabel, saveTabel, submitTabel,
  exportTabelExcel, getBenefits,
} from '../services/api';

interface StudentRow {
  student_id: number;
  full_name: string;
  benefit_code: string | null;
  notes: string;
  avangard_breakfast: number;
  avangard_lunch: number;
  avangard_shved: number;
  lyubava_breakfast: number;
  lyubava_lunch: number;
  lyubava_shved: number;
}

export default function TeacherDashboard() {
  const [classes, setClasses] = useState<any[]>([]);
  const [selectedClass, setSelectedClass] = useState<number | ''>('');
  const [mealDate, setMealDate] = useState(new Date().toISOString().split('T')[0]);
  const [tab, setTab] = useState<'tabel' | 'upload' | 'history'>('tabel');

  // Interactive tabel
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [benefits, setBenefits] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);
  const [tabelMsg, setTabelMsg] = useState<{ type: string; text: string } | null>(null);

  // Add student
  const [showAddStudent, setShowAddStudent] = useState(false);
  const [newName, setNewName] = useState('');
  const [newBenefit, setNewBenefit] = useState('');

  // Upload
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<{ type: string; text: string } | null>(null);

  // History
  const [uploads, setUploads] = useState<any[]>([]);

  // Discrepancies
  const [discrepancies, setDiscrepancies] = useState<any[]>([]);
  const [showDiscModal, setShowDiscModal] = useState(false);

  useEffect(() => {
    getMyClasses().then(r => {
      setClasses(r.data);
      if (r.data.length === 1) setSelectedClass(r.data[0].id);
    });
    getBenefits().then(r => setBenefits(r.data));
  }, []);

  useEffect(() => {
    if (!selectedClass) return;
    loadStudentsAndTabel();
  }, [selectedClass, mealDate]);

  const loadStudentsAndTabel = async () => {
    if (!selectedClass) return;
    const classId = Number(selectedClass);

    const studRes = await getStudents(classId);
    const roster: any[] = studRes.data;

    const tabelRes = await getTabel(classId, mealDate);
    const savedRecords: any[] = tabelRes.data;

    const recordMap = new Map<number, any>();
    for (const rec of savedRecords) {
      if (rec.student_id) recordMap.set(rec.student_id, rec);
    }

    const merged: StudentRow[] = roster.map((s: any) => {
      const saved = recordMap.get(s.id);
      return {
        student_id: s.id,
        full_name: s.full_name,
        benefit_code: s.benefit_code,
        notes: s.notes || '',
        avangard_breakfast: saved?.avangard_breakfast || 0,
        avangard_lunch: saved?.avangard_lunch || 0,
        avangard_shved: saved?.avangard_shved || 0,
        lyubava_breakfast: saved?.lyubava_breakfast || 0,
        lyubava_lunch: saved?.lyubava_lunch || 0,
        lyubava_shved: saved?.lyubava_shved || 0,
      };
    });

    setStudents(merged);

    try {
      const discRes = await getDiscrepancies({ class_id: classId, meal_date: mealDate });
      setDiscrepancies(discRes.data);
    } catch { /* ignore */ }
  };

  const toggleCell = (idx: number, field: keyof StudentRow) => {
    setStudents(prev => prev.map((s, i) => {
      if (i !== idx) return s;
      const val = s[field] as number;
      return { ...s, [field]: val ? 0 : 1 };
    }));
  };

  const buildRecords = () => students.map(s => ({
    student_id: s.student_id,
    avangard_breakfast: s.avangard_breakfast,
    avangard_lunch: s.avangard_lunch,
    avangard_shved: s.avangard_shved,
    lyubava_breakfast: s.lyubava_breakfast,
    lyubava_lunch: s.lyubava_lunch,
    lyubava_shved: s.lyubava_shved,
  }));

  const handleSaveDraft = async () => {
    if (!selectedClass) return;
    setSaving(true);
    setTabelMsg(null);
    try {
      await saveTabel({ class_id: Number(selectedClass), meal_date: mealDate, records: buildRecords() });
      setTabelMsg({ type: 'success', text: 'Черновик сохранён' });
    } catch (err: any) {
      setTabelMsg({ type: 'error', text: err.response?.data?.detail || 'Ошибка сохранения' });
    }
    setSaving(false);
  };

  const handleSubmitTabel = async () => {
    if (!selectedClass) return;
    setSaving(true);
    setTabelMsg(null);
    try {
      const res = await submitTabel({ class_id: Number(selectedClass), meal_date: mealDate, records: buildRecords() });
      setTabelMsg({ type: 'success', text: res.data.message });
      const discRes = await getDiscrepancies({ class_id: Number(selectedClass), meal_date: mealDate });
      setDiscrepancies(discRes.data);
      if (discRes.data.length > 0) setShowDiscModal(true);
    } catch (err: any) {
      setTabelMsg({ type: 'error', text: err.response?.data?.detail || 'Ошибка отправки' });
    }
    setSaving(false);
  };

  const handleExportExcel = async () => {
    if (!selectedClass) return;
    try {
      await saveTabel({ class_id: Number(selectedClass), meal_date: mealDate, records: buildRecords() });
      const res = await exportTabelExcel(Number(selectedClass), mealDate);
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Табель_${mealDate}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Ошибка экспорта');
    }
  };

  const handleAddStudent = async () => {
    if (!selectedClass || !newName.trim()) return;
    try {
      await addStudent(Number(selectedClass), { full_name: newName.trim(), benefit_code: newBenefit || null });
      setNewName('');
      setNewBenefit('');
      setShowAddStudent(false);
      loadStudentsAndTabel();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Ошибка');
    }
  };

  const handleRemoveStudent = async (studentId: number) => {
    if (!selectedClass || !confirm('Удалить ученика из списка?')) return;
    await removeStudent(Number(selectedClass), studentId);
    loadStudentsAndTabel();
  };

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file || !selectedClass || !mealDate) {
      setUploadMsg({ type: 'error', text: 'Заполните все поля и выберите файл' });
      return;
    }
    setUploading(true);
    setUploadMsg(null);
    const fd = new FormData();
    fd.append('file', file);
    fd.append('class_id', String(selectedClass));
    fd.append('meal_date', mealDate);
    try {
      await uploadTabel(fd);
      setUploadMsg({ type: 'success', text: 'Файл загружен! Данные подгружены в таблицу.' });
      await loadStudentsAndTabel();
      setTab('tabel');
    } catch (err: any) {
      setUploadMsg({ type: 'error', text: err.response?.data?.detail || 'Ошибка загрузки' });
    }
    setUploading(false);
  };

  useEffect(() => {
    if (tab === 'history') getUploads().then(r => setUploads(r.data));
  }, [tab]);

  const sumCol = (field: keyof StudentRow) => students.reduce((s, r) => s + ((r[field] as number) || 0), 0);
  const totalBf = students.reduce((s, r) => s + r.avangard_breakfast + r.lyubava_breakfast, 0);
  const totalLu = students.reduce((s, r) => s + r.avangard_lunch + r.lyubava_lunch, 0);
  const totalShv = students.reduce((s, r) => s + r.avangard_shved + r.lyubava_shved, 0);
  const eatingCount = students.filter(s =>
    s.avangard_breakfast + s.avangard_lunch + s.avangard_shved +
    s.lyubava_breakfast + s.lyubava_lunch + s.lyubava_shved > 0
  ).length;

  return (
    <div>
      <h1 className="page-title">Кабинет учителя</h1>

      {/* Class + Date + Tabs */}
      <div className="card">
        <div style={{ display: 'flex', gap: 12, alignItems: 'end', flexWrap: 'wrap' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Класс</label>
            <select value={selectedClass} onChange={e => setSelectedClass(Number(e.target.value) || '')}>
              <option value="">Выберите класс</option>
              {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Дата</label>
            <input type="date" value={mealDate} onChange={e => setMealDate(e.target.value)} />
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button className={`btn ${tab === 'tabel' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setTab('tabel')}>Табель</button>
            <button className={`btn ${tab === 'upload' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setTab('upload')}>Загрузить Excel</button>
            <button className={`btn ${tab === 'history' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setTab('history')}>История</button>
          </div>
        </div>
      </div>

      {!selectedClass && <div className="card"><p style={{ color: '#888' }}>Выберите класс для начала работы</p></div>}

      {/* ══════ INTERACTIVE TABEL ══════ */}
      {tab === 'tabel' && selectedClass && (
        <>
          <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
            <div className="stat-card"><div className="value">{students.length}</div><div className="label">В списке</div></div>
            <div className="stat-card"><div className="value" style={{ color: '#16a34a' }}>{eatingCount}</div><div className="label">Питаются</div></div>
            <div className="stat-card"><div className="value">{totalBf}</div><div className="label">Завтраков</div></div>
            <div className="stat-card"><div className="value">{totalLu}</div><div className="label">Обедов</div></div>
            <div className="stat-card"><div className="value">{totalShv}</div><div className="label">Шведских</div></div>
          </div>

          {tabelMsg && (
            <div className="card" style={{
              background: tabelMsg.type === 'error' ? '#fef2f2' : '#dcfce7',
              borderLeft: `4px solid ${tabelMsg.type === 'error' ? '#dc2626' : '#16a34a'}`,
            }}>{tabelMsg.text}</div>
          )}

          {discrepancies.length > 0 && (
            <div className="disc-card severity-warning" style={{ cursor: 'pointer' }} onClick={() => setShowDiscModal(true)}>
              <strong>Расхождения с предыдущим днём ({discrepancies.reduce((s: number, d: any) => s + d.items.length, 0)} шт.)</strong>
              <span style={{ marginLeft: 8, fontSize: 12 }}>Нажмите для просмотра</span>
            </div>
          )}

          <div className="card" style={{ overflowX: 'auto' }}>
            <div className="flex-between mb-8">
              <h3 style={{ margin: 0 }}>Табель питания — {mealDate}</h3>
              <button className="btn btn-sm btn-success" onClick={() => setShowAddStudent(true)}>+ Ученик</button>
            </div>
            <table>
              <thead>
                <tr>
                  <th rowSpan={2} style={{ width: 30 }}>#</th>
                  <th rowSpan={2}>ФИО ученика</th>
                  <th rowSpan={2} style={{ width: 60 }}>Льгота</th>
                  <th colSpan={3} style={{ textAlign: 'center', background: '#dbeafe' }}>Авангард</th>
                  <th colSpan={3} style={{ textAlign: 'center', background: '#fef3c7' }}>Любава</th>
                  <th rowSpan={2} style={{ width: 50 }}>Итого З</th>
                  <th rowSpan={2} style={{ width: 50 }}>Итого О</th>
                  <th rowSpan={2} style={{ width: 50 }}>Итого ШВ</th>
                  <th rowSpan={2} style={{ width: 30 }}></th>
                </tr>
                <tr>
                  <th style={{ background: '#dbeafe', width: 50 }}>завтр.</th>
                  <th style={{ background: '#dbeafe', width: 50 }}>обед</th>
                  <th style={{ background: '#dbeafe', width: 50 }}>ШВ.стол</th>
                  <th style={{ background: '#fef3c7', width: 50 }}>завтр.</th>
                  <th style={{ background: '#fef3c7', width: 50 }}>обед</th>
                  <th style={{ background: '#fef3c7', width: 50 }}>ШВ.стол</th>
                </tr>
              </thead>
              <tbody>
                {students.map((s, idx) => {
                  const rowBf = s.avangard_breakfast + s.lyubava_breakfast;
                  const rowLu = s.avangard_lunch + s.lyubava_lunch;
                  const rowShv = s.avangard_shved + s.lyubava_shved;
                  return (
                    <tr key={s.student_id}>
                      <td className="text-center">{idx + 1}</td>
                      <td style={{ fontWeight: 500, whiteSpace: 'nowrap' }}>{s.full_name}</td>
                      <td className="text-center">
                        {s.benefit_code && <span className="badge badge-yellow" style={{ fontSize: 10 }}>{s.benefit_code}</span>}
                      </td>
                      {(['avangard_breakfast', 'avangard_lunch', 'avangard_shved'] as const).map(f => (
                        <td key={f} className="text-center" style={{ background: '#eff6ff', cursor: 'pointer', userSelect: 'none' }}
                            onClick={() => toggleCell(idx, f)}>
                          <span style={{ fontSize: 18, color: s[f] ? '#2563eb' : '#ddd' }}>{s[f] ? '1' : '·'}</span>
                        </td>
                      ))}
                      {(['lyubava_breakfast', 'lyubava_lunch', 'lyubava_shved'] as const).map(f => (
                        <td key={f} className="text-center" style={{ background: '#fffbeb', cursor: 'pointer', userSelect: 'none' }}
                            onClick={() => toggleCell(idx, f)}>
                          <span style={{ fontSize: 18, color: s[f] ? '#d97706' : '#ddd' }}>{s[f] ? '1' : '·'}</span>
                        </td>
                      ))}
                      <td className="text-center" style={{ fontWeight: 600 }}>{rowBf || ''}</td>
                      <td className="text-center" style={{ fontWeight: 600 }}>{rowLu || ''}</td>
                      <td className="text-center" style={{ fontWeight: 600 }}>{rowShv || ''}</td>
                      <td>
                        <button className="btn btn-sm btn-danger" style={{ padding: '2px 6px', fontSize: 10 }}
                                onClick={() => handleRemoveStudent(s.student_id)}>x</button>
                      </td>
                    </tr>
                  );
                })}
                <tr style={{ background: '#e2efda', fontWeight: 700 }}>
                  <td></td>
                  <td>ИТОГО ({eatingCount} питаются)</td>
                  <td></td>
                  <td className="text-center">{sumCol('avangard_breakfast') || ''}</td>
                  <td className="text-center">{sumCol('avangard_lunch') || ''}</td>
                  <td className="text-center">{sumCol('avangard_shved') || ''}</td>
                  <td className="text-center">{sumCol('lyubava_breakfast') || ''}</td>
                  <td className="text-center">{sumCol('lyubava_lunch') || ''}</td>
                  <td className="text-center">{sumCol('lyubava_shved') || ''}</td>
                  <td className="text-center">{totalBf || ''}</td>
                  <td className="text-center">{totalLu || ''}</td>
                  <td className="text-center">{totalShv || ''}</td>
                  <td></td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="card flex gap-8" style={{ flexWrap: 'wrap' }}>
            <button className="btn btn-secondary" onClick={handleSaveDraft} disabled={saving}>
              {saving ? 'Сохранение...' : 'Сохранить черновик'}
            </button>
            <button className="btn btn-primary" onClick={handleSubmitTabel} disabled={saving}>
              {saving ? 'Отправка...' : 'Отправить администратору'}
            </button>
            <button className="btn btn-success" onClick={handleExportExcel}>Экспорт в Excel</button>
          </div>
        </>
      )}

      {/* ══════ UPLOAD EXCEL ══════ */}
      {tab === 'upload' && selectedClass && (
        <div className="card">
          <h3>Загрузка Excel-табеля</h3>
          <p style={{ fontSize: 13, color: '#666', marginBottom: 12 }}>
            Загруженный файл будет распарсен, данные автоматически заполнят интерактивную таблицу.
            Вы сможете проверить и отредактировать их перед отправкой.
          </p>
          <div className="form-group">
            <label>Файл (.xls / .xlsx)</label>
            <input type="file" ref={fileRef} accept=".xls,.xlsx" />
          </div>
          <button className="btn btn-primary" onClick={handleUpload} disabled={uploading}>
            {uploading ? 'Загрузка...' : 'Загрузить и заполнить таблицу'}
          </button>
          {uploadMsg && (
            <div style={{
              marginTop: 12, padding: '8px 12px', borderRadius: 6,
              background: uploadMsg.type === 'error' ? '#fee2e2' : '#dcfce7',
              color: uploadMsg.type === 'error' ? '#991b1b' : '#166534', fontSize: 13,
            }}>{uploadMsg.text}</div>
          )}
        </div>
      )}

      {/* ══════ HISTORY ══════ */}
      {tab === 'history' && (
        <div className="card">
          <h3>История загрузок и отправок</h3>
          {uploads.length === 0 ? <p style={{ color: '#888' }}>Пока нет записей</p> : (
            <table>
              <thead><tr><th>Дата</th><th>Класс</th><th>Источник</th><th>Версия</th><th>Статус</th><th>Создан</th></tr></thead>
              <tbody>
                {uploads.map((u: any) => (
                  <tr key={u.id}>
                    <td>{u.meal_date}</td>
                    <td>{u.class_name}</td>
                    <td>{u.original_filename === 'interactive' ? 'Интерактивный' : u.original_filename}</td>
                    <td className="text-center">{u.version}</td>
                    <td>
                      <span className={`badge ${u.status === 'success' ? 'badge-green' : u.status === 'error' ? 'badge-red' : 'badge-yellow'}`}>
                        {u.status === 'success' ? 'Готов' : u.status === 'error' ? 'Ошибка' : 'Обработка'}
                      </span>
                    </td>
                    <td>{new Date(u.created_at).toLocaleString('ru')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* ══════ ADD STUDENT MODAL ══════ */}
      {showAddStudent && (
        <div className="modal-overlay" onClick={() => setShowAddStudent(false)}>
          <div className="modal" style={{ maxWidth: 400 }} onClick={e => e.stopPropagation()}>
            <h3>Добавить ученика</h3>
            <div className="form-group">
              <label>ФИО</label>
              <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Иванов Иван" autoFocus />
            </div>
            <div className="form-group">
              <label>Льгота (необязательно)</label>
              <select value={newBenefit} onChange={e => setNewBenefit(e.target.value)}>
                <option value="">Нет</option>
                {benefits.map((b: any) => <option key={b.id} value={b.code}>{b.code} — {b.name}</option>)}
              </select>
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowAddStudent(false)}>Отмена</button>
              <button className="btn btn-primary" onClick={handleAddStudent}>Добавить</button>
            </div>
          </div>
        </div>
      )}

      {/* ══════ DISCREPANCIES MODAL ══════ */}
      {showDiscModal && discrepancies.length > 0 && (
        <div className="modal-overlay" onClick={() => setShowDiscModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Расхождения с предыдущим днём</h3>
            {discrepancies.map((d: any) => (
              <div key={d.id} style={{ marginBottom: 16 }}>
                <p style={{ fontWeight: 600, marginBottom: 8 }}>{d.class_name} | {d.meal_date} vs {d.previous_date}</p>
                {d.items.map((item: any) => (
                  <div key={item.id} className={`disc-card severity-${item.severity}`}>{item.description}</div>
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
