import { useState, useEffect } from 'react';
import { getSummaryByDate, updateSummaryRow } from '../services/api';

export default function AdminSummary() {
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [rows, setRows] = useState<any[]>([]);
  const [editRow, setEditRow] = useState<any>(null);
  const [editForm, setEditForm] = useState<any>({});
  const [comment, setComment] = useState('');

  useEffect(() => { load(); }, [date]);

  const load = () => {
    getSummaryByDate(date).then(r => setRows(r.data));
  };

  const openEdit = (row: any) => {
    setEditRow(row);
    setEditForm({ ...row });
    setComment('');
  };

  const saveEdit = async () => {
    if (!editRow) return;
    try {
      await updateSummaryRow(editRow.id, { ...editForm, comment });
      setEditRow(null);
      load();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Ошибка');
    }
  };

  const elementaryRows = rows.filter(r => {
    const grade = parseInt(r.class_name);
    return grade >= 1 && grade <= 4;
  });
  const middleRows = rows.filter(r => {
    const grade = parseInt(r.class_name);
    return grade >= 5;
  });

  const sumField = (arr: any[], field: string) => arr.reduce((s, r) => s + (r[field] || 0), 0);

  const renderSection = (title: string, sectionRows: any[]) => (
    <>
      <tr><td colSpan={23} style={{background: '#f0f2f5', fontWeight: 700, fontSize: 13}}>{title} ({sectionRows.length} кл.)</td></tr>
      {sectionRows.map(r => (
        <tr key={r.id} style={{cursor: 'pointer'}} onClick={() => openEdit(r)}>
          <td>{r.class_name}</td>
          <td>{r.teacher_name}</td>
          <td className="text-center">{r.student_count}</td>
          <td className="text-center">{r.eating_count}</td>
          <td className="text-center">{r.parent_breakfast || ''}</td>
          <td className="text-center">{r.parent_lunch || ''}</td>
          <td className="text-center">{r.parent_lunch_shved || ''}</td>
          <td className="text-center">{r.benefit_breakfast || ''}</td>
          <td className="text-center">{r.benefit_lunch || ''}</td>
          <td className="text-center">{r.free_breakfast || ''}</td>
          <td className="text-center">{r.free_lunch || ''}</td>
          <td className="text-center">{r.multichild_breakfast || ''}</td>
          <td className="text-center">{r.sozvezdie_breakfast || ''}</td>
          <td className="text-center">{r.mobilized_breakfast_lunch || ''}</td>
          <td className="text-center">{r.mobilized_count || ''}</td>
          <td className="text-center">{r.ovz_breakfast_lunch || ''}</td>
          <td className="text-center">{r.ovz_count || ''}</td>
          <td className="text-center">{r.sozvezdie_ovz_breakfast_lunch || ''}</td>
          <td className="text-center">{r.sozvezdie_ovz_count || ''}</td>
          <td className="text-center" style={{fontWeight: 600}}>{r.total_breakfasts}</td>
          <td className="text-center" style={{fontWeight: 600}}>{r.total_lunches}</td>
          <td>{r.notes || ''}</td>
          <td><span className={`badge ${r.source === 'manual' ? 'badge-yellow' : 'badge-blue'}`}>{r.source}</span></td>
        </tr>
      ))}
      <tr style={{background: '#d9e1f2', fontWeight: 700}}>
        <td colSpan={2}>ИТОГО</td>
        <td className="text-center">{sumField(sectionRows, 'student_count')}</td>
        <td className="text-center">{sumField(sectionRows, 'eating_count')}</td>
        <td className="text-center">{sumField(sectionRows, 'parent_breakfast')}</td>
        <td className="text-center">{sumField(sectionRows, 'parent_lunch')}</td>
        <td className="text-center">{sumField(sectionRows, 'parent_lunch_shved')}</td>
        <td className="text-center">{sumField(sectionRows, 'benefit_breakfast')}</td>
        <td className="text-center">{sumField(sectionRows, 'benefit_lunch')}</td>
        <td className="text-center">{sumField(sectionRows, 'free_breakfast')}</td>
        <td className="text-center">{sumField(sectionRows, 'free_lunch')}</td>
        <td className="text-center">{sumField(sectionRows, 'multichild_breakfast')}</td>
        <td className="text-center">{sumField(sectionRows, 'sozvezdie_breakfast')}</td>
        <td className="text-center">{sumField(sectionRows, 'mobilized_breakfast_lunch')}</td>
        <td className="text-center">{sumField(sectionRows, 'mobilized_count')}</td>
        <td className="text-center">{sumField(sectionRows, 'ovz_breakfast_lunch')}</td>
        <td className="text-center">{sumField(sectionRows, 'ovz_count')}</td>
        <td className="text-center">{sumField(sectionRows, 'sozvezdie_ovz_breakfast_lunch')}</td>
        <td className="text-center">{sumField(sectionRows, 'sozvezdie_ovz_count')}</td>
        <td className="text-center">{sumField(sectionRows, 'total_breakfasts')}</td>
        <td className="text-center">{sumField(sectionRows, 'total_lunches')}</td>
        <td colSpan={2}></td>
      </tr>
    </>
  );

  return (
    <div>
      <div className="flex-between mb-16">
        <h1 className="page-title" style={{marginBottom: 0}}>Сводная заявка на питание</h1>
        <input type="date" value={date} onChange={e => setDate(e.target.value)} style={{padding: '6px 12px', borderRadius: 6, border: '1px solid #d1d5db'}} />
      </div>

      {rows.length === 0 ? (
        <div className="card"><p style={{color: '#888'}}>Нет данных на выбранную дату</p></div>
      ) : (
        <div className="card" style={{overflowX: 'auto'}}>
          <table>
            <thead>
              <tr>
                <th>Класс</th><th>ФИО учителя</th>
                <th>Детей</th><th>Питаются</th>
                <th>Род. завтр.</th><th>Род. обед</th><th>Род. обед/шв</th>
                <th>Льг. завтр.</th><th>Льг. обед</th>
                <th>Бесп. завтр.</th><th>Бесп. обед</th>
                <th>Мног.</th><th>Созв.</th>
                <th>Мобил.</th><th>Мобил. кол.</th>
                <th>ОВЗ</th><th>ОВЗ кол.</th>
                <th>Созв. ОВЗ</th><th>Созв. ОВЗ кол.</th>
                <th>Завтр.</th><th>Обедов</th>
                <th>Прим.</th><th>Источник</th>
              </tr>
            </thead>
            <tbody>
              {elementaryRows.length > 0 && renderSection('Начальная школа (1-4)', elementaryRows)}
              {middleRows.length > 0 && renderSection('Основная и старшая школа (5-11)', middleRows)}
            </tbody>
          </table>
        </div>
      )}

      {/* Edit Modal */}
      {editRow && (
        <div className="modal-overlay" onClick={() => setEditRow(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Редактирование: {editRow.class_name} от {editRow.meal_date}</h3>
            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8}}>
              {[
                ['student_count', 'Детей в классе'],
                ['eating_count', 'Питающихся'],
                ['parent_breakfast', 'Род. завтрак'],
                ['parent_lunch', 'Род. обед'],
                ['parent_lunch_shved', 'Род. обед/шв'],
                ['free_breakfast', 'Бесп. завтрак'],
                ['free_lunch', 'Бесп. обед'],
                ['multichild_breakfast', 'Многодетные'],
                ['mobilized_breakfast_lunch', 'Мобилизованные'],
                ['mobilized_count', 'Мобил. кол-во'],
                ['ovz_breakfast_lunch', 'ОВЗ'],
                ['ovz_count', 'ОВЗ кол-во'],
                ['total_breakfasts', 'Итого завтраков'],
                ['total_lunches', 'Итого обедов'],
              ].map(([field, label]) => (
                <div className="form-group" key={field}>
                  <label>{label}</label>
                  <input type="number" value={editForm[field] || 0}
                    onChange={e => setEditForm({...editForm, [field]: parseInt(e.target.value) || 0})} />
                </div>
              ))}
            </div>
            <div className="form-group">
              <label>Примечание</label>
              <input value={editForm.notes || ''} onChange={e => setEditForm({...editForm, notes: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Комментарий к правке</label>
              <input value={comment} onChange={e => setComment(e.target.value)} placeholder="Причина изменения" />
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setEditRow(null)}>Отмена</button>
              <button className="btn btn-primary" onClick={saveEdit}>Сохранить</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
