/**
 * FD Forensics API client.
 * All backend communication goes through this module.
 * Base URL: relative (uses Vite proxy in dev) or VITE_API_BASE_URL env.
 */

import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000,
});

function normalizeError(err) {
  if (err.code === 'ERR_NETWORK') {
    return 'Backend unavailable. Ensure the API is running.';
  }
  if (err.code === 'ECONNABORTED') {
    return 'Request timed out.';
  }
  return err.response?.data?.detail || err.message || 'Request failed';
}

/**
 * GET /processes
 * @returns {Promise<Array<{pid: number, name: string, user: string, fd_count: number}>>}
 */
export async function fetchProcesses() {
  const { data } = await api.get('/processes');
  return data;
}

/**
 * GET /process/{pid}/analysis
 * @param {number} pid
 * @returns {Promise<ProcessAnalysisResponse>}
 */
export async function fetchProcessAnalysis(pid) {
  const { data } = await api.get(`/process/${pid}/analysis`);
  return data;
}

/**
 * POST /analyze/code
 * @param {File} file - Python or C source file
 * @returns {Promise<CodeAnalysisResponse>}
 */
export async function analyzeCode(file) {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/analyze/code', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 90000,
  });
  return data;
}

/**
 * GET /process/{pid}/analysis/pdf
 * @param {number} pid
 * @returns {Promise<Blob>} PDF blob
 */
export async function fetchProcessAnalysisPdf(pid) {
  const { data } = await api.get(`/process/${pid}/analysis/pdf`, {
    responseType: 'blob',
    timeout: 30000,
  });
  return data;
}

/**
 * POST /analyze/code/pdf
 * @param {File} file - Python or C source file
 * @returns {Promise<Blob>} PDF blob
 */
export async function analyzeCodePdf(file) {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/analyze/code/pdf', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
    timeout: 90000,
  });
  return data;
}

export { normalizeError };

export default api;
