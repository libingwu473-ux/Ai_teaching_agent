import client from './client'

export function login(data) {
  return client.post('/auth/login/', data)
}

export function getProfile() {
  return client.get('/auth/profile/')
}

export function changePassword(data) {
  return client.post('/auth/change-password/', data)
}
