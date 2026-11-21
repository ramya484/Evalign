package com.ems.controller;

import com.ems.dto.AIWorkflowRequest;
import com.ems.dto.AIWorkflowResponse;
import com.ems.service.AIWorkflowService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * AIWorkflowController - Centralized proxy controller routing requests from Angular
 * to the Python AI Multi-Agent Service.
 *
 * Exposes endpoints for:
 *  - Agent 1: Training Cohorts & Outlook Intelligence Agent (/api/ai/cohort/**)
 *  - Agent 2: Evaluator Mapping Agent + Outlook Integration (/api/ai/workflow/**)
 *  - Agent 3: Shortlisting Agent for Dashboard and Pool (/api/ai/shortlist/**)
 */
@RestController
@RequestMapping("/api/ai")
public class AIWorkflowController {

    @Autowired
    private AIWorkflowService aiWorkflowService;

    // -------------------------------------------------------------------------
    // Agent 1: Training Cohorts Page + Outlook Integration
    // -------------------------------------------------------------------------

    @PostMapping("/cohort/analyze")
    public ResponseEntity<Map> analyzeCohort(@RequestBody(required = false) Map<String, Object> request) {
        return ResponseEntity.ok(aiWorkflowService.analyzeCohort(request));
    }

    @GetMapping("/cohort/{cohortId}/analysis")
    public ResponseEntity<Map> getCohortAnalysis(@PathVariable Long cohortId) {
        return ResponseEntity.ok(aiWorkflowService.getCohortAnalysis(cohortId));
    }

    // -------------------------------------------------------------------------
    // Agent 2: Evaluator Mapping Page + Outlook Integration
    // -------------------------------------------------------------------------

    @PostMapping("/workflow/start")
    public ResponseEntity<AIWorkflowResponse> startWorkflow(@RequestBody AIWorkflowRequest request) {
        return ResponseEntity.ok(aiWorkflowService.startWorkflow(request));
    }

    @PostMapping("/workflow/approve")
    public ResponseEntity<AIWorkflowResponse> approveWorkflow(
            @RequestParam String workflowId,
            @RequestParam boolean approved,
            @RequestParam(required = false) String feedback) {
        return ResponseEntity.ok(aiWorkflowService.approveWorkflow(workflowId, approved, feedback));
    }

    @GetMapping("/workflow/{workflowId}/status")
    public ResponseEntity<AIWorkflowResponse> getWorkflowStatus(@PathVariable String workflowId) {
        return ResponseEntity.ok(aiWorkflowService.getWorkflowStatus(workflowId));
    }

    // -------------------------------------------------------------------------
    // Agent 3: Shortlisting Agent (Shared by Dashboard and Pool)
    // -------------------------------------------------------------------------

    @PostMapping("/shortlist/run")
    public ResponseEntity<Map> runShortlisting(@RequestBody(required = false) Map<String, Object> request) {
        return ResponseEntity.ok(aiWorkflowService.runShortlisting(request));
    }

    @GetMapping("/shortlist/stats")
    public ResponseEntity<Map> getShortlistStats() {
        return ResponseEntity.ok(aiWorkflowService.getShortlistStats());
    }

    @GetMapping("/shortlist/results")
    public ResponseEntity<Map> getShortlistResults() {
        return ResponseEntity.ok(aiWorkflowService.getShortlistResults());
    }

    @PostMapping("/shortlist/decision")
    public ResponseEntity<Map> submitShortlistDecision(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(aiWorkflowService.submitShortlistDecision(request));
    }

    // -------------------------------------------------------------------------
    // Health Check
    // -------------------------------------------------------------------------

    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> healthCheck() {
        return ResponseEntity.ok(aiWorkflowService.checkAIServiceHealth());
    }
}