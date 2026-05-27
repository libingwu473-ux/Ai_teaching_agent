import client from './client'

export function register(data) {
  return client.post('/auth/register/', data)
}

export function login(data) {
  return client.post('/auth/login/', data)
}

export function getProfile() {
  return client.get('/auth/profile/')
}
