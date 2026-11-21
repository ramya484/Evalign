import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface WorkflowStartRequest {
  cohortId: number;
  roundType: string;
  attempt?: number;
  interviewFrom?: string;
  interviewTo?: string;
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

@Injectable({ providedIn: 'root' })
export class AIWorkflowService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  /** Start the AI-powered evaluator mapping workflow */
  startWorkflow(request: WorkflowStartRequest): Observable<WorkflowResponse> {
    return this.http.post<WorkflowResponse>(`${this.apiUrl}/api/ai/workflow/start`, request);
  }

  /** Submit human approval or rejection */
  approveWorkflow(workflowId: string, approved: boolean, feedback?: string): Observable<WorkflowResponse> {
    let params = new HttpParams()
      .set('workflowId', workflowId)
      .set('approved', String(approved));
    if (feedback) params = params.set('feedback', feedback);
    return this.http.post<WorkflowResponse>(`${this.apiUrl}/api/ai/workflow/approve`, null, { params });
  }

  /** Poll workflow status */
  getWorkflowStatus(workflowId: string): Observable<WorkflowResponse> {
    return this.http.get<WorkflowResponse>(`${this.apiUrl}/api/ai/workflow/${workflowId}/status`);
  }

  /** Check if AI service is reachable */
  checkHealth(): Observable<{ status: string; ai_service_url: string }> {
    return this.http.get<any>(`${this.apiUrl}/api/ai/health`);
  }
}
