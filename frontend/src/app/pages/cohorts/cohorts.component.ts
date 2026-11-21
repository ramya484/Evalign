import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CohortService } from '../../services/cohort.service';
import { AIWorkflowService, CohortAnalysisResult, CohortFinding, EmailCitation } from '../../services/ai-workflow.service';
import { Cohort } from '../../models/cohort.model';

@Component({
  selector: 'app-cohorts',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './cohorts.component.html',
  styleUrls: ['./cohorts.component.css']
})
export class CohortsComponent implements OnInit {
  cohorts: Cohort[] = [];
  filteredCohorts: Cohort[] = [];
  searchTerm: string = '';
  statusFilter: string = 'All';
  showModal: boolean = false;
  
  notification: { message: string; type: 'success' | 'error' | 'warning' } | null = null;
  modalError: string = '';
  savingCohort: boolean = false;
  selectedCandidateFile: File | null = null;
  candidateFileName: string = '';

  newCohort: Partial<Cohort> = {
    cohortName: '',
    batchCode: '',
    startDate: new Date().toISOString().substring(0, 10),
    status: 'Active',
    candidateCount: 0
  };

  loading: boolean = false;
  loadingMore: boolean = false;
  hasMore: boolean = false;
  page: number = 0;
  pageSize: number = 10;

  // ---------------------------------------------------------------------------
  // Agent 1 – Training Cohorts & Outlook Communications Intelligence State
  // ---------------------------------------------------------------------------
  agent1Loading: boolean = false;
  agent1Analysis: CohortAnalysisResult | null = null;
  showAgent1Panel: boolean = false;
  selectedCohortForAgent1: Cohort | null = null;
  agent1FilterCategory: string = 'ALL';

  constructor(
    private cohortService: CohortService,
    private router: Router,
    private aiWorkflowService: AIWorkflowService
  ) {}

  ngOnInit(): void {
    this.loadCohorts(true);
  }

  showNotification(message: string, type: 'success' | 'error' | 'warning' = 'success'): void {
    this.notification = { message, type };
    setTimeout(() => {
      this.notification = null;
    }, 4500);
  }

  // ---------------------------------------------------------------------------
  // Agent 1 Actions
  // ---------------------------------------------------------------------------

  triggerAgent1(cohort?: Cohort): void {
    this.agent1Loading = true;
    this.showAgent1Panel = true;
    this.selectedCohortForAgent1 = cohort || null;
    this.agent1Analysis = null;

    const payload = cohort ? { cohort_id: cohort.cohortId, batch_code: cohort.batchCode } : {};

    this.aiWorkflowService.analyzeCohort(payload).subscribe({
      next: (res: CohortAnalysisResult) => {
        this.agent1Analysis = res;
        this.agent1Loading = false;
        const conflictCount = res.findings.filter(f => f.category === 'CONFLICT').length;
        if (conflictCount > 0) {
          this.showNotification(`Agent 1: Analyzed ${res.analyzed_emails_count} Outlook emails. Detected ${conflictCount} potential schedule/leave conflicts.`, 'warning');
        } else {
          this.showNotification(`Agent 1: Analyzed ${res.analyzed_emails_count} Outlook emails successfully.`, 'success');
        }
      },
      error: (err: any) => {
        this.agent1Loading = false;
        const msg = err.error?.detail || err.error?.message || 'Agent 1 failed to analyze Outlook communications.';
        this.showNotification(msg, 'error');
      }
    });
  }

  closeAgent1Panel(): void {
    this.showAgent1Panel = false;
    this.selectedCohortForAgent1 = null;
  }

  getFilteredFindings(): CohortFinding[] {
    if (!this.agent1Analysis || !this.agent1Analysis.findings) return [];
    if (this.agent1FilterCategory === 'ALL') return this.agent1Analysis.findings;
    return this.agent1Analysis.findings.filter(f => f.category === this.agent1FilterCategory);
  }

  getSeverityBadgeClass(severity: string): string {
    switch (severity) {
      case 'CRITICAL': return 'badge-red';
      case 'WARNING': return 'badge-orange';
      case 'INFO': return 'badge-blue';
      default: return 'badge-blue';
    }
  }

  // ---------------------------------------------------------------------------
  // Cohorts Standard CRUD & List Operations
  // ---------------------------------------------------------------------------

  loadCohorts(reset: boolean = true): void {
    if (reset) {
      this.page = 0;
      this.loading = true;
      this.cohorts = [];
      this.filteredCohorts = [];
    } else {
      this.loadingMore = true;
    }

    this.cohortService.getCohorts({
      page: this.page,
      size: this.pageSize,
      search: this.searchTerm ? this.searchTerm.trim() : undefined,
      status: this.statusFilter !== 'All' ? this.statusFilter : undefined
    }).subscribe({
      next: (res) => {
        const batch = res || [];
        if (reset) {
          this.cohorts = batch;
        } else {
          this.cohorts = [...this.cohorts, ...batch];
        }
        this.filteredCohorts = this.cohorts;
        this.hasMore = batch.length === this.pageSize;
        this.loading = false;
        this.loadingMore = false;
      },
      error: (err) => {
        console.error('Failed to load cohorts', err);
        this.loading = false;
        this.loadingMore = false;
      }
    });
  }

  viewMore(): void {
    if (!this.hasMore || this.loading || this.loadingMore) return;
    this.page++;
    this.loadCohorts(false);
  }

  applyFilter(): void {
    this.loadCohorts(true);
  }

  normalizeStatus(status?: string): string {
    const s = (status || '').trim().toLowerCase().replace(/_/g, ' ');
    if (s === 'active') return 'active';
    if (s.includes('progress')) return 'mapping in progress';
    if (s === 'completed') return 'completed';
    if (s.includes('not started') || s === 'not_started') return 'not started';
    return s;
  }

  openMapping(cohortId: number): void {
    this.router.navigate(['/mapping', cohortId]);
  }

  onStatusChange(cohort: Cohort, newStatus: string): void {
    if (!cohort.cohortId || cohort.status === newStatus || this.loading) return;

    const oldStatus = cohort.status;
    cohort.status = newStatus;
    this.loading = true;

    this.cohortService.updateCohort(cohort.cohortId, {
      cohortId: cohort.cohortId,
      cohortName: cohort.cohortName,
      batchCode: cohort.batchCode,
      startDate: cohort.startDate,
      status: newStatus,
      candidateCount: cohort.candidateCount
    }).subscribe({
      next: (updated) => {
        cohort.status = updated.status || newStatus;
        this.loading = false;
        this.showNotification(`Status updated to '${cohort.status}' for ${cohort.cohortName}`);
      },
      error: (err) => {
        cohort.status = oldStatus;
        this.loading = false;
        this.showNotification(`Failed to update status: ${err.error?.message || 'Server error'}`, 'error');
      }
    });
  }

  deleteCohort(cohort: Cohort): void {
    if (!cohort.cohortId || this.loading) return;

    const confirmed = window.confirm('Delete this cohort? This will remove its candidates, shortlist entries, and mappings.');
    if (!confirmed) return;

    this.loading = true;
    this.cohortService.deleteCohort(cohort.cohortId).subscribe({
      next: () => {
        this.loading = false;
        this.showNotification(`Cohort '${cohort.cohortName}' deleted successfully.`);
        this.loadCohorts(true);
      },
      error: (err) => {
        this.loading = false;
        this.showNotification(`Failed to delete cohort: ${err.error?.message || 'Server error'}`, 'error');
      }
    });
  }

  openNewCohortModal(): void {
    this.showModal = true;
    this.modalError = '';
    this.selectedCandidateFile = null;
    this.candidateFileName = '';
  }

  closeModal(): void {
    this.showModal = false;
    this.modalError = '';
    this.selectedCandidateFile = null;
    this.candidateFileName = '';
    this.newCohort = {
      cohortName: '',
      batchCode: '',
      startDate: new Date().toISOString().substring(0, 10),
      status: 'Active',
      candidateCount: 0
    };
  }

  onCandidateFileSelected(event: any): void {
    const file = event.target.files[0];
    if (file) {
      this.selectedCandidateFile = file;
      this.candidateFileName = file.name;
    }
  }

  removeSelectedFile(): void {
    this.selectedCandidateFile = null;
    this.candidateFileName = '';
  }

  saveCohort(): void {
    if (!this.newCohort.cohortName || !this.newCohort.batchCode) {
      this.modalError = 'Cohort name and batch code are required';
      return;
    }

    this.savingCohort = true;
    this.modalError = '';

    this.cohortService.createCohort(this.newCohort).subscribe({
      next: (createdCohort) => {
        if (this.selectedCandidateFile && createdCohort.cohortId) {
          this.cohortService.uploadCandidateExcel(createdCohort.cohortId, this.selectedCandidateFile).subscribe({
            next: (uploadRes) => {
              this.savingCohort = false;
              this.showNotification(`Cohort '${createdCohort.cohortName}' created and candidates imported successfully!`);
              this.loadCohorts();
              this.closeModal();
            },
            error: (uploadErr) => {
              this.savingCohort = false;
              this.showNotification(`Cohort created, but candidate import had an issue: ${uploadErr.error?.message || 'Invalid file'}`, 'error');
              this.loadCohorts();
              this.closeModal();
            }
          });
        } else {
          this.savingCohort = false;
          this.showNotification(`Cohort '${createdCohort.cohortName}' created successfully!`);
          this.loadCohorts();
          this.closeModal();
        }
      },
      error: (err) => {
        this.savingCohort = false;
        this.modalError = err.error?.message || 'Failed to create cohort batch';
      }
    });
  }

  getStatusClass(status: string): string {
    const s = this.normalizeStatus(status);
    switch(s) {
      case 'active': return 'badge-green';
      case 'completed': return 'badge-blue';
      case 'mapping in progress': return 'badge-orange';
      case 'not started': return 'badge-red';
      default: return 'badge-blue';
    }
  }
}