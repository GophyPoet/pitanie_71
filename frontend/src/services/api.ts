import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// Auth
export const login = (username: string, password: string) =>
  api.post('/auth/login', { username, password });
export const getMe = () => api.get('/auth/me');
export const changePassword = (old_password: string, new_password: string) =>
  api.post('/auth/change-password', { old_password, new_password });

// Users
export const getUsers = () => api.get('/users/');
export const createUser = (data: any) => api.post('/users/', data);
export const toggleUserActive = (id: number) => api.put(`/users/${id}/toggle-active`);
export const resetUserPassword = (id: number) => api.put(`/users/${id}/reset-password`);
export const updateUserClasses = (id: number, classIds: number[]) =>
  api.put(`/users/${id}/classes`, classIds);

// Classes
export const getClasses = () => api.get('/classes/');
export const getBenefits = () => api.get('/classes/benefits');

// Uploads
export const uploadTabel = (formData: FormData) =>
  api.post('/uploads/', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
export const getUploads = (params?: any) => api.get('/uploads/', { params });
export const getUploadRecords = (id: number) => api.get(`/uploads/${id}/records`);
export const getMyClasses = () => api.get('/uploads/my-classes');

// Summary
export const getSummaryByDate = (meal_date: string) =>
  api.get('/summary/by-date', { params: { meal_date } });
export const updateSummaryRow = (id: number, data: any) => api.put(`/summary/${id}`, data);
export const getSubmissionStatus = (meal_date: string) =>
  api.get('/summary/submission-status', { params: { meal_date } });
export const getDashboard = (meal_date?: string) =>
  api.get('/summary/dashboard', { params: { meal_date } });

// Plans
export const getPlans = () => api.get('/plans/');
export const createPlan = (year: number, month: number) =>
  api.post('/plans/', { year, month });
export const getPlan = (id: number) => api.get(`/plans/${id}`);
export const removePlanDay = (planId: number, dayId: number) =>
  api.delete(`/plans/${planId}/days/${dayId}`);
export const addPlanDay = (planId: number, dayDate: string) =>
  api.post(`/plans/${planId}/days`, null, { params: { day_date: dayDate } });

// Discrepancies
export const getDiscrepancies = (params?: any) => api.get('/discrepancies/', { params });
export const reviewDiscrepancy = (id: number, action: string) =>
  api.put(`/discrepancies/${id}/review`, null, { params: { action } });

// Export
export const exportSummaryByDate = (meal_date: string) =>
  api.get('/export/summary/date', { params: { meal_date }, responseType: 'blob' });
export const exportSummaryByMonth = (year: number, month: number) =>
  api.get('/export/summary/month', { params: { year, month }, responseType: 'blob' });
export const downloadSummaryZip = (params: any) =>
  api.get('/export/zip/summary', { params, responseType: 'blob' });
export const downloadTabelsZip = (params: any) =>
  api.get('/export/zip/tabels', { params, responseType: 'blob' });
export const sendEmail = (data: any) => api.post('/export/send-email', data);

// Roster (teacher student management + interactive tabel)
export const getStudents = (classId: number) => api.get(`/roster/${classId}/students`);
export const addStudent = (classId: number, data: any) =>
  api.post(`/roster/${classId}/students`, data);
export const updateStudent = (classId: number, studentId: number, data: any) =>
  api.put(`/roster/${classId}/students/${studentId}`, data);
export const removeStudent = (classId: number, studentId: number) =>
  api.delete(`/roster/${classId}/students/${studentId}`);
export const getTabel = (classId: number, mealDate: string) =>
  api.get(`/roster/${classId}/tabel/${mealDate}`);
export const saveTabel = (data: any) => api.post('/roster/tabel/save', data);
export const submitTabel = (data: any) => api.post('/roster/tabel/submit', data);
export const exportTabelExcel = (classId: number, mealDate: string) =>
  api.get(`/roster/${classId}/export-tabel/${mealDate}`, { responseType: 'blob' });
