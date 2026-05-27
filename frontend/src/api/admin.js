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

// 专业 CRUD
export function listMajors(params = {}) {
  return client.get('/admin/majors/', { params })
}
export function createMajor(data) {
  return client.post('/admin/majors/', data)
}
export function updateMajor(id, data) {
  return client.put(`/admin/majors/${id}/`, data)
}
export function deactivateMajor(id) {
  return client.delete(`/admin/majors/${id}/`)
}
