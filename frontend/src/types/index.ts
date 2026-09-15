export interface EstimateLineItem {
  id: string;
  estimate_id: string;
  item_number: string | null;
  category: string | null;
  description: string;
  quantity: number | null;
  unit: string | null;
  unit_cost: number | null;
  total_cost: number | null;
  source_page: number | null;
  section_total_type: string | null;
  created_at: string;
  updated_at: string;
}

export interface Estimate {
  id: string;
  title: string;
  project_name: string | null;
  reference_number: string | null;
  contractor: string | null;
  client: string | null;
  currency: string;
  original_filename: string;
  status: string;
  total_estimated_amount: number | null;
  created_at: string;
  updated_at: string;
}

export interface EstimateDetail extends Estimate {
  line_items: EstimateLineItem[];
}

export interface EstimateListResponse {
  estimates: Estimate[];
  total: number;
}

export interface UploadResponse {
  id: string;
  filename: string;
  status: string;
  message: string;
}

export interface HealthResponse {
  status: string;
  version: string;
}

export interface FundingSummary {
  approved_estimated_amount: string;
  total_received: string;
  total_allocated: string;
  total_unallocated: string;
  funding_coverage_percentage: number | null;
}

export interface FundingEvidence {
  evidence_filename: string | null;
  evidence_original_filename: string | null;
  evidence_mime_type: string | null;
  evidence_size: number | null;
}

export interface FundReceipt extends FundingEvidence {
  id: string;
  estimate_id: string | null;
  amount: string;
  currency: string;
  received_date: string;
  source: string;
  reference: string | null;
  purpose: string | null;
  notes: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface FundReceiptSummaryItem extends FundReceipt {
  allocated_amount: string;
  unallocated_amount: string;
}

export interface FundReceiptListResponse {
  receipts: FundReceiptSummaryItem[];
  total: number;
  summary: FundingSummary;
}

export interface FundAllocation extends FundingEvidence {
  id: string;
  fund_receipt_id: string;
  estimate_id: string | null;
  estimate_title: string | null;
  category: string | null;
  amount: string;
  purpose: string | null;
  responsible_person: string | null;
  allocation_date: string;
  notes: string | null;
  status: string;
  currency: string;
  created_at: string;
  updated_at: string;
}

export interface FundReceiptDetail extends FundReceipt {
  allocated_amount: string;
  unallocated_amount: string;
  allocations: FundAllocation[];
}

export interface AllocationListResponse {
  allocations: FundAllocation[];
  total: number;
  allocated_amount: string;
  unallocated_amount: string;
}

export interface Expense {
  id: string;
  project: string | null;
  expense_date: string;
  amount: string;
  description: string;
  category: string | null;
  estimate_id: string | null;
  estimate_line_item_id: string | null;
  allocation_id: string | null;
  supplier: string | null;
  payment_method: string | null;
  reference: string | null;
  purpose: string | null;
  responsible_person: string | null;
  notes: string | null;
  currency: string;
  quantity: string | null;
  unit: string | null;
  unit_price: string | null;
  authorized_by: string | null;
  authorization_reason: string | null;
  status: string;
  evidence_filename: string | null;
  evidence_original_filename: string | null;
  evidence_mime_type: string | null;
  evidence_size: number | null;
  created_at: string;
  updated_at: string;
}

export interface ExpenseDetail extends Expense {
  estimate_title: string | null;
  estimate_item_description: string | null;
  allocation_purpose: string | null;
  allocation_category: string | null;
  allocation_currency: string | null;
  allocation_remaining_amount: string | null;
  allocation_spent_amount: string | null;
}

export interface ExpenseCategoryItem {
  category: string;
  total: string;
}

export interface ExpenseAllocationItem {
  allocation_id: string;
  allocation_purpose: string | null;
  allocation_category: string | null;
  estimate_title: string | null;
  allocated_amount: string;
  spent_amount: string;
  remaining_amount: string;
  currency: string;
}

export interface ExpenseBudgetComparisonItem {
  estimate_id: string;
  estimate_title: string;
  estimated_amount: string;
  actual_expenditure: string;
  variance_amount: string;
  status: string;
  currency: string;
}

export interface ExpenseSummary {
  total_expenses: string;
  total_authorized_excess: string;
  by_category: ExpenseCategoryItem[];
  allocation_breakdown: ExpenseAllocationItem[];
  budget_comparison: ExpenseBudgetComparisonItem[];
}

export interface ExpenseListResponse {
  expenses: Expense[];
  total: number;
  summary: ExpenseSummary;
}

export interface AllocationExpenseListResponse {
  allocations: ExpenseAllocationItem[];
  total: number;
}

export interface Resource {
  id: string;
  project: string | null;
  name: string;
  category: string | null;
  unit: string | null;
  currency: string;
  estimate_id: string | null;
  estimate_title: string | null;
  estimate_line_item_id: string | null;
  estimate_item_description: string | null;
  budgeted_quantity: string | null;
  budgeted_cost: string | null;
  notes: string | null;
  status: string;
  purchased_quantity: string;
  delivered_quantity: string;
  used_quantity: string;
  adjustment_quantity: string;
  remaining_quantity: string;
  pending_delivery_quantity: string;
  total_purchase_cost: string;
  cost_variance: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResourceMovement {
  id: string;
  resource_id: string;
  movement_type: string;
  quantity: string;
  movement_date: string;
  unit_cost: string | null;
  total_cost: string | null;
  expense_id: string | null;
  expense_description: string | null;
  related_purchase_movement_id: string | null;
  supplier: string | null;
  reference: string | null;
  receiver: string | null;
  project_stage: string | null;
  activity: string | null;
  responsible_person: string | null;
  notes: string | null;
  authorized_by: string | null;
  authorization_reason: string | null;
  evidence_filename: string | null;
  evidence_original_filename: string | null;
  evidence_mime_type: string | null;
  evidence_size: number | null;
  created_at: string;
}

export interface ResourceExpenseInfo {
  id: string;
  expense_date: string;
  amount: string;
  description: string;
  reference: string | null;
  currency: string;
}

export interface ResourceDetail extends Resource {
  movements: ResourceMovement[];
  related_expenses: ResourceExpenseInfo[];
}

export interface ResourceListResponse {
  resources: Resource[];
  total: number;
}

export type ActivityStatus =
  | 'not_started'
  | 'in_progress'
  | 'completed'
  | 'delayed'
  | 'blocked'
  | 'cancelled';

export interface Activity {
  id: string;
  project: string | null;
  name: string;
  description: string | null;
  project_stage: string | null;
  estimate_id: string | null;
  estimate_title: string | null;
  planned_start_date: string | null;
  planned_end_date: string | null;
  actual_start_date: string | null;
  actual_end_date: string | null;
  status: ActivityStatus;
  progress_percentage: number;
  responsible_person: string | null;
  notes: string | null;
  delay_reason: string | null;
  delay_reason_detail: string | null;
  resource_dependency: string | null;
  is_delayed: boolean;
  delay_days: number;
  created_at: string;
  updated_at: string;
}

export interface ActivitySummary {
  total_activities: number;
  total_completed: number;
  total_in_progress: number;
  total_delayed: number;
  total_blocked: number;
  total_not_started: number;
  total_cancelled: number;
  overall_progress: number | null;
  progress_calculation: string;
}

export interface ActivityListResponse {
  activities: Activity[];
  total: number;
  summary: ActivitySummary | null;
}

export interface Milestone {
  id: string;
  project: string | null;
  name: string;
  estimate_id: string | null;
  estimate_title: string | null;
  planned_date: string | null;
  actual_date: string | null;
  status: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface MilestoneListResponse {
  milestones: Milestone[];
  total: number;
}

// --- Stage A: Authentication, users, roles and project membership ---

export type UserRole = 'administrator' | 'member' | 'viewer';

export interface AuthUser {
  id: string;
  username: string;
  full_name: string;
  role: UserRole;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface MeResponse {
  user: AuthUser;
  projects: Project[];
}

export interface RegisterResponse {
  message: string;
  user: AuthUser;
}

export interface UserListResponse {
  users: AuthUser[];
  total: number;
}

export interface ProjectListResponse {
  projects: Project[];
  total: number;
}

// --- Stage B: Assistant ---

export interface AssistantReference {
  entity_type:
    | 'estimate'
    | 'fund_receipt'
    | 'fund_allocation'
    | 'expense'
    | 'resource'
    | 'activity'
    | 'milestone';
  entity_id: string;
  label: string;
  href: string;
}

export interface AssistantReply {
  intent:
    | 'overview'
    | 'estimates'
    | 'funding'
    | 'allocations'
    | 'expenses'
    | 'resources'
    | 'schedule'
    | 'delays'
    | 'milestones'
    | 'mutation'
    | 'unclear'
    | 'answer'
    | 'error';
  reply: string;
  references: AssistantReference[];
}

export interface AssistantStreamEvent {
  type: 'status' | 'tool' | 'delta' | 'done' | 'error';
  text?: string | null;
  tool?: string | null;
  intent?: string | null;
  references: AssistantReference[];
}

export interface AssistantAttentionItem {
  kind: string;
  message: string;
  references: AssistantReference[];
}

export interface AssistantBriefing {
  greeting: string;
  project_name?: string | null;
  attention: AssistantAttentionItem[];
  suggestions: string[];
}
