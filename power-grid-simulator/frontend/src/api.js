const BASE_URL = '/api';

async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `HTTP error ${response.status}`);
  }
  return data;
}

export const api = {
  getNetwork: () => request('/network'),
  
  addElement: (element) => request('/elements', {
    method: 'POST',
    body: JSON.stringify(element)
  }),
  
  updateElement: (id, updates) => request(`/elements/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(updates)
  }),
  
  deleteElement: (id) => request(`/elements/${id}`, {
    method: 'DELETE'
  }),
  
  addConnection: (connection) => request('/connections', {
    method: 'POST',
    body: JSON.stringify(connection)
  }),
  
  updateConnection: (id, updates) => request(`/connections/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(updates)
  }),
  
  deleteConnection: (id) => request(`/connections/${id}`, {
    method: 'DELETE'
  }),
  
  optimize: () => request('/simulate/optimize', {
    method: 'POST'
  }),
  
  triggerFailure: (id, type) => request('/simulate/failure', {
    method: 'POST',
    body: JSON.stringify({ id, type })
  }),
  
  triggerRestore: (id, type) => request('/simulate/restore', {
    method: 'POST',
    body: JSON.stringify({ id, type })
  }),
  
  reset: () => request('/simulate/reset', {
    method: 'POST'
  }),
  
  getMST: () => request('/mst')
};
