import client from './client'

// 教师 CRUD
export function listTeachers(params = {}) {
  return client.get('/admin/teachers/', { params })
}
export function createTeacher(data) {
  return client.post('/admin/teachers/', data)
}
export function updateTeacher(id, data) {
  return client.put(`/admin/teachers/${id}/`, data)
}
export function deactivateTeacher(id) {
  return client.delete(`/admin/teachers/${id}/`)
}
export function resetTeacherPassword(id, newPassword) {
  return client.post(`/admin/teachers/${id}/reset-password/`, { new_password: newPassword })
}
