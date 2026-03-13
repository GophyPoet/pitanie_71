import { useState } from 'react';
import { exportSummaryByDate, exportSummaryByMonth, downloadSummaryZip, downloadTabelsZip, sendEmail } from '../services/api';

export default function AdminExport() {
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [email, setEmail] = useState('');
  const [emailSubject, setEmailSubject] = useState('');
  const [sendMode, setSendMode] = useState<'date' | 'month'>('date');
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState('');

  const downloadBlob = (data: Blob, filename: string) => {
    const url = URL.createObjectURL(data);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportDate = async () => {
    const res = await exportSummaryByDate(date);
    downloadBlob(res.data, `Заявка_${date}.xlsx`);
  };

  const handleExportMonth = async () => {
    const res = await exportSummaryByMonth(year, month);
    downloadBlob(res.data, `Заявка_${month}_${year}.xlsx`);
  };

  const handleZipSummary = async () => {
    const params = sendMode === 'date' ? { meal_date: date } : { year, month };
    const res = await downloadSummaryZip(params);
    downloadBlob(res.data, `Заявка.zip`);
  };

  const handleZipTabels = async () => {
    const params = sendMode === 'date' ? { meal_date: date } : { year, month };
    const res = await downloadTabelsZip(params);
    downloadBlob(res.data, `Табели.zip`);
  };

  const handleSendEmail = async () => {
    if (!email) { alert('Введите email'); return; }
    setSending(true);
    setResult('');
    try {
      const data: any = { recipient_email: email, subject: emailSubject };
      if (sendMode === 'date') data.meal_date = date;
      else { data.year = year; data.month = month; }
      const res = await sendEmail(data);
      setResult(`Статус: ${res.data.status}${res.data.error ? ' | ' + res.data.error : ''}`);
    } catch (err: any) {
      setResult(`Ошибка: ${err.response?.data?.detail || err.message}`);
    }
    setSending(false);
  };

  const MONTHS = ['', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];

  return (
    <div>
      <h1 className="page-title">Экспорт и отправка</h1>

      <div className="card">
        <h3>Режим</h3>
        <div className="flex gap-8 mb-16">
          <button className={`btn ${sendMode === 'date' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setSendMode('date')}>По дате</button>
          <button className={`btn ${sendMode === 'month' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setSendMode('month')}>За месяц</button>
        </div>
        {sendMode === 'date' ? (
          <div className="form-group">
            <label>Дата</label>
            <input type="date" value={date} onChange={e => setDate(e.target.value)} />
          </div>
        ) : (
          <div className="flex gap-8">
            <div className="form-group">
              <label>Год</label>
              <input type="number" value={year} onChange={e => setYear(+e.target.value)} style={{width: 100}} />
            </div>
            <div className="form-group">
              <label>Месяц</label>
              <select value={month} onChange={e => setMonth(+e.target.value)}>
                {MONTHS.slice(1).map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
              </select>
            </div>
          </div>
        )}
      </div>

      <div className="card">
        <h3>Экспорт Excel</h3>
        <div className="flex gap-8">
          {sendMode === 'date' ? (
            <button className="btn btn-success" onClick={handleExportDate}>Скачать заявку на дату</button>
          ) : (
            <button className="btn btn-success" onClick={handleExportMonth}>Скачать заявку за месяц</button>
          )}
        </div>
      </div>

      <div className="card">
        <h3>ZIP-архивы</h3>
        <p style={{fontSize: 13, color: '#666', marginBottom: 12}}>
          ZIP 1 — сводная заявка | ZIP 2 — все исходные табели учителей
        </p>
        <div className="flex gap-8">
          <button className="btn btn-primary" onClick={handleZipSummary}>Скачать ZIP заявки</button>
          <button className="btn btn-primary" onClick={handleZipTabels}>Скачать ZIP табелей</button>
        </div>
      </div>

      <div className="card">
        <h3>Отправить по email</h3>
        <div className="form-group">
          <label>Email получателя</label>
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="example@school.ru" />
        </div>
        <div className="form-group">
          <label>Тема письма (необязательно)</label>
          <input value={emailSubject} onChange={e => setEmailSubject(e.target.value)} placeholder="Заявка на питание" />
        </div>
        <button className="btn btn-success" onClick={handleSendEmail} disabled={sending}>
          {sending ? 'Отправка...' : 'Отправить email с вложениями'}
        </button>
        {result && <p style={{marginTop: 12, fontWeight: 500}}>{result}</p>}
      </div>
    </div>
  );
}
