import { NavLink } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout, isAdmin } = useAuth();

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <h2>Школа 71<br/><small style={{fontWeight: 400, fontSize: 12}}>Учёт питания</small></h2>
        <nav>
          {isAdmin ? (
            <>
              <NavLink to="/" end>Дашборд</NavLink>
              <NavLink to="/summary">Сводная заявка</NavLink>
              <NavLink to="/status">Статусы классов</NavLink>
              <NavLink to="/plans">Планирование</NavLink>
              <NavLink to="/discrepancies">Расхождения</NavLink>
              <NavLink to="/users">Учителя</NavLink>
              <NavLink to="/export">Экспорт / Email</NavLink>
            </>
          ) : (
            <NavLink to="/" end>Мой кабинет</NavLink>
          )}
        </nav>
        <div style={{padding: '16px 20px', fontSize: 13, color: '#aaa'}}>
          {user?.full_name}<br/>
          <small>{user?.role === 'admin' ? 'Администратор' : 'Учитель'}</small>
        </div>
        <button className="logout-btn" onClick={logout}>Выйти</button>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}
