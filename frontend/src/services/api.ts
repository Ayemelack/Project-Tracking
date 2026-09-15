import axios from 'axios';
import type {
  Estimate,
  EstimateDetail,
  EstimateListResponse,
  UploadResponse,
  HealthResponse,
  FundReceipt,
  FundReceiptListResponse,
  FundReceiptDetail,
  FundAllocation,
  AllocationListResponse,
  AllocationExpenseListResponse,
  FundingSummary,
  Expense,
  ExpenseDetail,
  ExpenseListResponse,
  Resource,
  ResourceDetail,
  ResourceListResponse,
  ResourceMovement,
  Activity,
  ActivityListResponse,
  ActivitySummary,
  Milestone,
  MilestoneListResponse,
  AuthResponse,
  MeResponse,
  AuthUser,
  UserRole,
  UserListResponse,
  Project,
  ProjectListResponse,
  AssistantReply,
  AssistantBriefing,
  AssistantStreamEvent,
} from '../types';
import {
  clearAuth,
  getToken,
  getStoredUser,
  setStoredUser,
} from './authStore';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API = `${API_BASE}/api/v1`;

const client = axios.create({
  baseURL: API,
  timeout: 120000,
});

client.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401 && getToken()) {
      clearAuth();
      window.dispatchEvent(new Event('auth:session-expired'));
    }
    return Promise.reject(error);
  }
);

export const api = {
  // --- Stage A: Authentication ---

  async register(payload: {
    username: string;
    full_name: string;
    password: string;
    confirm_password: string;
    admin_registration_secret?: string;
  }): Promise<{ message: string; user: AuthUser }> {
    const { data } = await client.post<{ message: string; user: AuthUser }>(
      '/auth/register',
      payload
    );
    return data;
  },

  async login(username: string, password: string): Promise<AuthResponse> {
    const { data } = await client.post<AuthResponse>('/auth/login', { username, password });
    return data;
  },

  async me(): Promise<MeResponse> {
    const { data } = await client.get<MeResponse>('/auth/me');
    return data;
  },

  async listUsers(): Promise<UserListResponse> {
    const { data } = await client.get<UserListResponse>('/auth/users');
    return data;
  },

  async createUser(payload: {
    username: string;
    full_name: string;
    password: string;
    role: UserRole;
  }): Promise<AuthUser> {
    const { data } = await client.post<AuthUser>('/auth/users', payload);
    return data;
  },

  async updateUser(
    id: string,
    payload: { full_name?: string; password?: string; role?: UserRole; status?: string }
  ): Promise<AuthUser> {
    const { data } = await client.patch<AuthUser>(`/auth/users/${id}`, payload);
    return data;
  },

  async listProjects(): Promise<ProjectListResponse> {
    const { data } = await client.get<ProjectListResponse>('/auth/projects');
    return data;
  },

  async createProject(payload: { name: string; description?: string | null }): Promise<Project> {
    const { data } = await client.post<Project>('/auth/projects', payload);
    return data;
  },

  async addProjectMember(projectId: string, userId: string): Promise<MeResponse> {
    const { data } = await client.post<MeResponse>(
      `/auth/projects/${projectId}/members/${userId}`
    );
    return data;
  },

  async removeProjectMember(projectId: string, userId: string): Promise<MeResponse> {
    const { data } = await client.delete<MeResponse>(
      `/auth/projects/${projectId}/members/${userId}`
    );
    return data;
  },

  async listProjectMembers(projectId: string): Promise<UserListResponse> {
    const { data } = await client.get<UserListResponse>(
      `/auth/projects/${projectId}/members`
    );
    return data;
  },

  async restoreSession(): Promise<AuthUser | null> {
    const stored = getStoredUser();
    if (!stored) return null;
    try {
      const { user } = await api.me();
      setStoredUser(user);
      return user;
    } catch {
      clearAuth();
      return null;
    }
  },

  async health(): Promise<HealthResponse> {
    const { data } = await client.get('/health');
    return data;
  },

  async uploadEstimate(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await client.post('/estimates/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  async listEstimates(skip = 0, limit = 100): Promise<EstimateListResponse> {
    const { data } = await client.get('/estimates', { params: { skip, limit } });
    return data;
  },

  async getEstimate(id: string): Promise<EstimateDetail> {
    const { data } = await client.get(`/estimates/${id}`);
    return data;
  },

  async updateEstimate(id: string, updates: Partial<Estimate>): Promise<Estimate> {
    const { data } = await client.put(`/estimates/${id}`, updates);
    return data;
  },

  async confirmEstimate(id: string): Promise<Estimate> {
    const { data } = await client.post(`/estimates/${id}/confirm`);
    return data;
  },

  async deleteEstimate(id: string): Promise<void> {
    await client.delete(`/estimates/${id}`);
  },

  async updateLineItem(
    estimateId: string,
    itemId: string,
    updates: Record<string, unknown>
  ): Promise<void> {
    await client.put(`/estimates/${estimateId}/items/${itemId}`, updates);
  },

  async addLineItem(
    estimateId: string,
    item: Record<string, unknown>
  ): Promise<void> {
    await client.post(`/estimates/${estimateId}/items`, item);
  },

  async deleteLineItem(estimateId: string, itemId: string): Promise<void> {
    await client.delete(`/estimates/${estimateId}/items/${itemId}`);
  },

  // --- Phase 2: Project Funding & Money Allocation ---

  async listFunds(skip = 0, limit = 100): Promise<FundReceiptListResponse> {
    const { data } = await client.get('/funds', { params: { skip, limit } });
    return data;
  },

  async getFundingSummary(): Promise<FundingSummary> {
    const { data } = await client.get('/funds/summary');
    return data;
  },

  async createFundReceipt(payload: {
    amount: string | number;
    currency: string;
    received_date: string;
    source: string;
    reference?: string | null;
    purpose?: string | null;
    notes?: string | null;
    estimate_id?: string | null;
  }): Promise<FundReceipt> {
    const { data } = await client.post('/funds', payload);
    return data;
  },

  async getFundReceipt(id: string): Promise<FundReceiptDetail> {
    const { data } = await client.get(`/funds/${id}`);
    return data;
  },

  async listAllocations(fundId: string): Promise<AllocationListResponse> {
    const { data } = await client.get(`/funds/${fundId}/allocations`);
    return data;
  },

  async createAllocation(
    fundId: string,
    payload: {
      amount: number;
      estimate_id?: string | null;
      category?: string | null;
      purpose?: string | null;
      responsible_person?: string | null;
      allocation_date?: string | null;
      notes?: string | null;
    }
  ): Promise<FundAllocation> {
    const { data } = await client.post(`/funds/${fundId}/allocations`, payload);
    return data;
  },

  async getAllocation(id: string): Promise<FundAllocation> {
    const { data } = await client.get(`/allocations/${id}`);
    return data;
  },

  async cancelAllocation(id: string, reason?: string): Promise<FundAllocation> {
    const { data } = await client.post(`/allocations/${id}/cancel`, { reason });
    return data;
  },

  async attachReceiptEvidence(id: string, file: File): Promise<FundReceipt> {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await client.post(`/funds/${id}/evidence`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  async removeReceiptEvidence(id: string): Promise<FundReceipt> {
    const { data } = await client.delete(`/funds/${id}/evidence`);
    return data;
  },

  async attachAllocationEvidence(id: string, file: File): Promise<FundAllocation> {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await client.post(`/allocations/${id}/evidence`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  async removeAllocationEvidence(id: string): Promise<FundAllocation> {
    const { data } = await client.delete(`/allocations/${id}/evidence`);
    return data;
  },

  // --- Phase 3: Expense & Purchase Tracking ---

  async listExpenses(skip = 0, limit = 100): Promise<ExpenseListResponse> {
    const { data } = await client.get('/expenses', { params: { skip, limit } });
    return data;
  },

  async createExpense(payload: {
    amount?: string | number | null;
    expense_date: string;
    description: string;
    project?: string | null;
    category?: string | null;
    estimate_id?: string | null;
    estimate_line_item_id?: string | null;
    allocation_id?: string | null;
    supplier?: string | null;
    payment_method?: string | null;
    reference?: string | null;
    purpose?: string | null;
    responsible_person?: string | null;
    notes?: string | null;
    currency?: string;
    quantity?: string | number | null;
    unit?: string | null;
    unit_price?: string | number | null;
    authorized_by?: string | null;
    authorization_reason?: string | null;
  }): Promise<Expense> {
    const { data } = await client.post('/expenses', payload);
    return data;
  },

  async getExpense(id: string): Promise<ExpenseDetail> {
    const { data } = await client.get(`/expenses/${id}`);
    return data;
  },

  async updateExpense(id: string, updates: Record<string, unknown>): Promise<Expense> {
    const { data } = await client.patch(`/expenses/${id}`, updates);
    return data;
  },

  async reverseExpense(id: string, reason?: string): Promise<Expense> {
    const { data } = await client.post(`/expenses/${id}/reverse`, { reason });
    return data;
  },

  async attachExpenseEvidence(id: string, file: File): Promise<Expense> {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await client.post(`/expenses/${id}/evidence`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  async removeExpenseEvidence(id: string): Promise<Expense> {
    const { data } = await client.delete(`/expenses/${id}/evidence`);
    return data;
  },

  async listAllAllocations(): Promise<AllocationExpenseListResponse> {
    const { data } = await client.get('/allocations');
    return data;
  },

  // --- Phase 4: Material & Resource Accountability ---

  async listResources(skip = 0, limit = 100): Promise<ResourceListResponse> {
    const { data } = await client.get('/resources', { params: { skip, limit } });
    return data;
  },

  async getResource(id: string): Promise<ResourceDetail> {
    const { data } = await client.get(`/resources/${id}`);
    return data;
  },

  async createResource(payload: {
    name: string;
    project?: string | null;
    category?: string | null;
    unit?: string | null;
    currency?: string;
    estimate_id?: string | null;
    estimate_line_item_id?: string | null;
    budgeted_quantity?: string | number | null;
    budgeted_cost?: string | number | null;
    notes?: string | null;
  }): Promise<Resource> {
    const { data } = await client.post('/resources', payload);
    return data;
  },

  async recordPurchase(
    resourceId: string,
    payload: {
      quantity: string | number;
      unit_cost: string | number;
      movement_date?: string | null;
      expense_id?: string | null;
      supplier?: string | null;
      reference?: string | null;
      responsible_person?: string | null;
      notes?: string | null;
    }
  ): Promise<ResourceMovement> {
    const { data } = await client.post(`/resources/${resourceId}/purchases`, payload);
    return data;
  },

  async recordDelivery(
    resourceId: string,
    payload: {
      quantity: string | number;
      movement_date?: string | null;
      linked_purchase_movement_id?: string | null;
      supplier?: string | null;
      reference?: string | null;
      receiver?: string | null;
      responsible_person?: string | null;
      notes?: string | null;
    }
  ): Promise<ResourceMovement> {
    const { data } = await client.post(`/resources/${resourceId}/deliveries`, payload);
    return data;
  },

  async recordUsage(
    resourceId: string,
    payload: {
      quantity: string | number;
      movement_date?: string | null;
      project_stage?: string | null;
      activity?: string | null;
      responsible_person?: string | null;
      notes?: string | null;
    }
  ): Promise<ResourceMovement> {
    const { data } = await client.post(`/resources/${resourceId}/usage`, payload);
    return data;
  },

  async recordAdjustment(
    resourceId: string,
    payload: {
      quantity: string | number;
      movement_date?: string | null;
      authorized_by?: string | null;
      authorization_reason?: string | null;
      responsible_person?: string | null;
      notes?: string | null;
    }
  ): Promise<ResourceMovement> {
    const { data } = await client.post(`/resources/${resourceId}/adjustments`, payload);
    return data;
  },

  async attachMovementEvidence(resourceId: string, movementId: string, file: File): Promise<ResourceMovement> {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await client.post(
      `/resources/${resourceId}/movements/${movementId}/evidence`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return data;
  },

  async removeMovementEvidence(resourceId: string, movementId: string): Promise<ResourceMovement> {
    const { data } = await client.delete(`/resources/${resourceId}/movements/${movementId}/evidence`);
    return data;
  },

  // --- Phase 5: Project Schedule, Progress & Delay Tracking ---

  async listActivities(params?: {
    skip?: number;
    limit?: number;
    status?: string;
    project_stage?: string;
    project?: string;
  }): Promise<ActivityListResponse> {
    const { data } = await client.get('/schedule', { params });
    return data;
  },

  async getActivity(id: string): Promise<Activity> {
    const { data } = await client.get(`/schedule/${id}`);
    return data;
  },

  async getActivitySummary(): Promise<ActivitySummary> {
    const { data } = await client.get('/schedule/summary');
    return data;
  },

  async createActivity(payload: {
    name: string;
    project?: string | null;
    description?: string | null;
    project_stage?: string | null;
    estimate_id?: string | null;
    planned_start_date?: string | null;
    planned_end_date?: string | null;
    actual_start_date?: string | null;
    actual_end_date?: string | null;
    status?: string;
    progress_percentage?: number;
    responsible_person?: string | null;
    notes?: string | null;
    delay_reason?: string | null;
    delay_reason_detail?: string | null;
    resource_dependency?: string | null;
  }): Promise<Activity> {
    const { data } = await client.post('/schedule', payload);
    return data;
  },

  async updateActivity(id: string, payload: Record<string, unknown>): Promise<Activity> {
    const { data } = await client.patch(`/schedule/${id}`, payload);
    return data;
  },

  async listMilestones(params?: {
    skip?: number;
    limit?: number;
    status?: string;
    project?: string;
  }): Promise<MilestoneListResponse> {
    const { data } = await client.get('/schedule/milestones', { params });
    return data;
  },

  async createMilestone(payload: {
    name: string;
    project?: string | null;
    estimate_id?: string | null;
    planned_date?: string | null;
    actual_date?: string | null;
    status?: string;
    notes?: string | null;
  }): Promise<Milestone> {
    const { data } = await client.post('/schedule/milestones', payload);
    return data;
  },

  async updateMilestone(id: string, payload: Record<string, unknown>): Promise<Milestone> {
    const { data } = await client.patch(`/schedule/milestones/${id}`, payload);
    return data;
  },

  // --- Stage B: Assistant ---

  async askAssistant(question: string): Promise<AssistantReply> {
    const { data } = await client.post<AssistantReply>('/assistant/ask', { question });
    return data;
  },

  async getBriefing(): Promise<AssistantBriefing> {
    const { data } = await client.get<AssistantBriefing>('/assistant/briefing');
    return data;
  },

  async askAssistantStream(
    question: string,
    onEvent: (event: AssistantStreamEvent) => void
  ): Promise<void> {
    const token = getToken();
    const response = await fetch(`${API}/assistant/ask/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ question }),
    });
    if (!response.ok || !response.body) {
      if (response.status === 401 && token) {
        clearAuth();
        window.dispatchEvent(new Event('auth:session-expired'));
      }
      let detail = `Stream request failed (${response.status})`;
      try {
        const payload = await response.json();
        if (payload?.detail) detail = String(payload.detail);
      } catch {
        // keep the fallback message
      }
      throw new Error(detail);
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split('\n\n');
      buffer = frames.pop() ?? '';
      for (const frame of frames) {
        const line = frame.split('\n').find((l) => l.startsWith('data:'));
        if (!line) continue;
        try {
          onEvent(JSON.parse(line.slice(5).trim()) as AssistantStreamEvent);
        } catch {
          // skip malformed frames
        }
      }
    }
  },
};
