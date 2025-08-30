import axios from 'axios'
import { BASE_URL } from './config'

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120000, // 2 minutes for yt-dlp extraction
})

// (optional) interceptors for errors, etc.
// api.interceptors.response.use(r => r, err => Promise.reject(err))
