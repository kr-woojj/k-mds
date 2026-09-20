// API 클라이언트: openapi.yaml 기반 fetch 래퍼
const API_BASE_URL = 'http://localhost:8000/api';

export async function apiRequest(path, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || response.statusText);
    }
    // 204 No Content
    if (response.status === 204) return null;
    return await response.json();
  } catch (err) {
    // 네트워크 또는 서버 에러
    throw err;
  }
}
