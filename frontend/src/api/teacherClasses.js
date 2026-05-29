import client from './client'

// 班级
export function listClasses(params = {}) {
  return client.get('/teacher/classes/', { params })
}
export function createClass(data) {
  return client.post('/teacher/classes/', data)
}
export function updateClass(id, data) {
  return client.put(`/teacher/classes/${id}/`, data)
}
export function deactivateClass(id) {
  return client.delete(`/teacher/classes/${id}/`)
}
export function listMajorsReadonly() {
  return client.get('/teacher/majors-readonly/')
}

// 专业（教师端管理）
export function listMajors(params = {}) {
  return client.get('/teacher/majors/', { params })
}
export function createMajor(data) {
  return client.post('/teacher/majors/', data)
}
export function updateMajor(id, data) {
  return client.put(`/teacher/majors/${id}/`, data)
}
export function deactivateMajor(id) {
  return client.delete(`/teacher/majors/${id}/`)
}

// 班级下的学生
export function listClassStudents(classId, params = {}) {
  return client.get(`/teacher/classes/${classId}/class-students/`, { params })
}
export function createClassStudent(classId, data) {
  return client.post(`/teacher/classes/${classId}/class-students/`, data)
}
export function importClassStudents(classId, file) {
  const fd = new FormData()
  fd.append('file', file)
  return client.post(`/teacher/classes/${classId}/class-students/import/`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export function downloadCsvTemplateURL() {
  // 让浏览器带 JWT 拿模板比较麻烦——返回纯 URL 由调用方用 axios 下载
  return '/teacher/students-csv-template/'
}

export function updateClassStudent(studentId, data) {
  return client.put(`/teacher/class-students/${studentId}/`, data)
}
export function deactivateClassStudent(studentId) {
  return client.delete(`/teacher/class-students/${studentId}/`)
}
export function resetClassStudentPassword(studentId, newPassword) {
  return client.post(`/teacher/class-students/${studentId}/reset-password/`, {
    new_password: newPassword,
  })
}

export function downloadCsvTemplate() {
  return client.get('/teacher/students-csv-template/', { responseType: 'blob' })
}
