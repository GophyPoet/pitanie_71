import { useState, useEffect } from 'react';
import { getUsers, createUser, toggleUserActive, resetUserPassword, getClasses, updateUserClasses } from '../services/api';

export default function AdminUsers() {
  const [users, setUsers] = useState<any[]>([]);
  const [classes, setClasses] = useState<any[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ username: '', full_name: '', password: '', role: 'teacher', class_ids: [] as number[] });
  const [editClasses, setEditClasses] = useState<{ userId: number; classIds: number[] } | null>(null);

  useEffect(() => {
    loadUsers();
    getClasses().then(r => setClasses(r.data));
  }, []);

  const loadUsers = () => { getUsers().then(r => setUsers(r.data)); };

  const handleCreate = async () => {
    try {
      await createUser(form);
      setShowCreate(false);
      setForm({ username: '', full_name: '', password: '', role: 'teacher', class_ids: [] });
      loadUsers();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Ошибка');
    }
  };

  const handleToggle = async (id: number) => {
    await toggleUserActive(id);
    loadUsers();
  };

  const handleReset = async (id: number) => {
    if (!confirm('Сбросить пароль на 123456?')) return;
    await resetUserPassword(id);
    alert('Пароль сброшен на 123456');
  };

  const handleSaveClasses = async () => {
    if (!editClasses) return;
    await updateUserClasses(editClasses.userId, editClasses.classIds);
    setEditClasses(null);
    loadUsers();
  };

  return (
    <div>
      <div className="flex-between mb-16">
        <h1 className="page-title" style={{marginBottom: 0}}>Управление учителями</h1>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>Добавить учителя</button>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Логин</th><th>ФИО</th><th>Роль</th><th>Активен</th><th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id}>
                <td>{u.username}</td>
                <td>{u.full_name}</td>
                <td><span className={`badge ${u.role === 'admin' ? 'badge-blue' : 'badge-green'}`}>{u.role === 'admin' ? 'Админ' : 'Учитель'}</span></td>
                <td>{u.is_active ? <span className="status-submitted">Да</span> : <span className="status-not-submitted">Нет</span>}</td>
                <td>
                  <div className="flex gap-8">
                    <button className="btn btn-sm btn-secondary" onClick={() => handleToggle(u.id)}>
                      {u.is_active ? 'Деактив.' : 'Активир.'}
                    </button>
                    <button className="btn btn-sm btn-secondary" onClick={() => handleReset(u.id)}>Сброс пароля</button>
                    <button className="btn btn-sm btn-primary" onClick={() => setEditClasses({ userId: u.id, classIds: [] })}>Классы</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Новый учитель</h3>
            <div className="form-group">
              <label>Логин</label>
              <input value={form.username} onChange={e => setForm({...form, username: e.target.value})} />
            </div>
            <div className="form-group">
              <label>ФИО</label>
              <input value={form.full_name} onChange={e => setForm({...form, full_name: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Пароль</label>
              <input value={form.password} onChange={e => setForm({...form, password: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Классы</label>
              <div style={{display: 'flex', flexWrap: 'wrap', gap: 4}}>
                {classes.map(c => (
                  <label key={c.id} style={{fontSize: 13, cursor: 'pointer'}}>
                    <input type="checkbox" checked={form.class_ids.includes(c.id)}
                      onChange={e => {
                        if (e.target.checked) setForm({...form, class_ids: [...form.class_ids, c.id]});
                        else setForm({...form, class_ids: form.class_ids.filter(id => id !== c.id)});
                      }} /> {c.name}
                  </label>
                ))}
              </div>
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowCreate(false)}>Отмена</button>
              <button className="btn btn-primary" onClick={handleCreate}>Создать</button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Classes Modal */}
      {editClasses && (
        <div className="modal-overlay" onClick={() => setEditClasses(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Назначить классы</h3>
            <div style={{display: 'flex', flexWrap: 'wrap', gap: 8}}>
              {classes.map(c => (
                <label key={c.id} style={{fontSize: 13, cursor: 'pointer', padding: '4px 8px', background: editClasses.classIds.includes(c.id) ? '#dbeafe' : '#f3f4f6', borderRadius: 6}}>
                  <input type="checkbox" checked={editClasses.classIds.includes(c.id)}
                    onChange={e => {
                      if (e.target.checked) setEditClasses({...editClasses, classIds: [...editClasses.classIds, c.id]});
                      else setEditClasses({...editClasses, classIds: editClasses.classIds.filter(id => id !== c.id)});
                    }} /> {c.name}
                </label>
              ))}
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setEditClasses(null)}>Отмена</button>
              <button className="btn btn-primary" onClick={handleSaveClasses}>Сохранить</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
