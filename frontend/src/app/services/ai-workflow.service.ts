import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

// -----------------------------------------------------------------------------
// Agent 1 Interfaces (Training Cohorts Page + Outlook Integration)
// -----------------------------------------------------------------------------

export interface EmailCitation {
  email_id: number;
  message_id: string;
  sender: string;
  recipient: string;
  subject: string;
  received_date: string;
  snippet: string;
}

export interface CohortFinding {
  category: 'SCHEDULE' | 'PARTICIPANTS' | 'EVALUATOR_NOMINATION' | 'AVAILABILITY' | 'CONFLICT';
  title: string;
  description: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  source_email?: EmailCitation;
  actionable_recommendation: string;
}

export interface CohortAnalysisResult {
  cohort_id?: number;
  cohort_name: string;
  batch_code: string;
  candidate_count: number;
  analyzed_emails_count: number;
  findings: CohortFinding[];
  email_citations: EmailCitation[];
  summary: string;
  status: 'COMPLETED' | 'WARNING' | 'ERROR';
  last_synced_at?: string;
}

// -----------------------------------------------------------------------------
// Agent 2 Interfaces (Evaluator Mapping Page + Outlook Integration)
// -----------------------------------------------------------------------------

export interface WorkflowStartRequest {
  cohortId: number;
  roundType: string;
  attempt?: number;
  interviewFrom?: string;
  interviewTo?: string;
}

export interface EmailCitationRef {
  email_id: number;
  sender: string;
  subject: string;
  date?: string;
  quote?: string;
}

export interface WorkflowResponse {
  workflowId: string;
  status: string;
  result?: any;
  errorMessage?: string;
  mappingSuggestions?: any;
  validationResults?: any;
  humanApprovalRequested?: boolean;
  executionLog?: string[];
}

// -----------------------------------------------------------------------------
// Agent 3 Interfaces (Shortlisting Agent - Shared by Dashboard & Pool)
// -----------------------------------------------------------------------------

export interface ShortlistingStats {
  total_processed: number;
  shortlisted_count: number;
  recommended_count: number;
  approved_count: number;
  rejected_count: number;
  execution_status: string;
  last_run_timestamp?: string;
  active_cohort_id?: number;
  average_score: number;
}

export interface ShortlistCandidateItem {
  id: number;
  name: string;
  emp_id: string;
  email: string;
  vertical: string;
  domain: string;
  score: number;
  fit_rationale: string;
  recommendation: 'SHORTLIST' | 'WAITLIST' | 'REJECT';
  status: 'RECOMMENDED' | 'APPROVED' | 'REJECTED';
  notes?: string;
  availability_status: string;
}

export interface ShortlistResponse {
  stats: ShortlistingStats;
  recommendations: ShortlistCandidateItem[];
  total: number;
}

@Injectable({ providedIn: 'root' })
export class AIWorkflowService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // ---------------------------------------------------------------------------
  // Agent 1 – Training Cohorts Page + Outlook Integration
  // ---------------------------------------------------------------------------

  /** Trigger Agent 1 to audit Outlook communications for a training cohort or all cohorts */
  analyzeCohort(request?: { cohort_id?: number; batch_code?: string }): Observable<CohortAnalysisResult> {
    return this.http.post<CohortAnalysisResult>(`${this.apiUrl}/api/ai/cohort/analyze`, request || {});
  }

  /** Retrieve the latest Agent 1 analysis for a cohort */
  getCohortAnalysis(cohortId: number): Observable<CohortAnalysisResult> {
    return this.http.get<CohortAnalysisResult>(`${this.apiUrl}/api/ai/cohort/${cohortId}/analysis`);
  }

  // ---------------------------------------------------------------------------
  // Agent 2 – Evaluator Mapping Page + Outlook Integration
  // ---------------------------------------------------------------------------

  /** Start Agent 2 AI workflow */
  startWorkflow(request: WorkflowStartRequest): Observable<WorkflowResponse> {
    return this.http.post<WorkflowResponse>(`${this.apiUrl}/api/ai/workflow/start`, request);
  }

  /** Submit human approval or rejection for Agent 2 suggestions */
  approveWorkflow(workflowId: string, approved: boolean, feedback?: string): Observable<WorkflowResponse> {
    let params = new HttpParams()
      .set('workflowId', workflowId)
      .set('approved', String(approved));
    if (feedback) params = params.set('feedback', feedback);
    return this.http.post<WorkflowResponse>(`${this.apiUrl}/api/ai/workflow/approve`, null, { params });
  }

  /** Poll workflow status for Agent 2 */
  getWorkflowStatus(workflowId: string): Observable<WorkflowResponse> {
    return this.http.get<WorkflowResponse>(`${this.apiUrl}/api/ai/workflow/${workflowId}/status`);
  }

  // ---------------------------------------------------------------------------
  // Agent 3 – Shortlisting Agent (Shared by Dashboard and Pool)
  // ---------------------------------------------------------------------------

  /** Run Agent 3 Shortlisting workflow (accessible from Dashboard and Pool) */
  runShortlisting(params?: { cohort_id?: number; vertical?: string; domain?: string; target_count?: number }): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/api/ai/shortlist/run`, params || {});
  }

  /** Get live shared shortlisting statistics for Dashboard and Pool */
  getShortlistStats(): Observable<ShortlistingStats> {
    return this.http.get<ShortlistingStats>(`${this.apiUrl}/api/ai/shortlist/stats`);
  }

  /** Get detailed recommendations for Pool and Dashboard */
  getShortlistResults(): Observable<ShortlistResponse> {
    return this.http.get<ShortlistResponse>(`${this.apiUrl}/api/ai/shortlist/results`);
  }

  /** Submit user approval or rejection for a shortlisted candidate/evaluator (Pool page) */
  submitShortlistDecision(itemId: number, decision: 'APPROVE' | 'REJECT', notes?: string, cohortId?: number): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/api/ai/shortlist/decision`, {
      item_id: itemId,
      decision,
      notes,
      cohort_id: cohortId
    });
  }

  // ---------------------------------------------------------------------------
  // Health Check
  // ---------------------------------------------------------------------------

  /** Check if AI multi-agent service is reachable */
  checkHealth(): Observable<{ status: string; ai_service_url: string; agents?: any }> {
    return this.http.get<any>(`${this.apiUrl}/api/ai/health`);
  }
}