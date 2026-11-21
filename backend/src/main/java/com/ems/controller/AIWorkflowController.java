package com.ems.controller;

import com.ems.dto.AIWorkflowRequest;
import com.ems.dto.AIWorkflowResponse;
import com.ems.service.AIWorkflowService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * AIWorkflowController – proxy endpoints that forward requests from the Angular
 * frontend to the Python AI workflow service (FastAPI + LangGraph).
 *
 * All existing EMS endpoints are preserved. This controller only adds NEW paths
 * under /api/ai/** that the frontend's AI Auto-Map feature uses.
 */
@RestController
@RequestMapping("/api/ai")
public class AIWorkflowController {

    @Autowired
    private AIWorkflowService aiWorkflowService;

    /**
     * Start a new AI-powered evaluator mapping workflow.
     * POST /api/ai/workflow/start
     */
    @PostMapping("/workflow/start")
    public ResponseEntity<AIWorkflowResponse> startWorkflow(@RequestBody AIWorkflowRequest request) {
        return ResponseEntity.ok(aiWorkflowService.startWorkflow(request));
    }

    /**
     * Submit human approval or rejection for a paused workflow.
     * POST /api/ai/workflow/approve
     */
    @PostMapping("/workflow/approve")
    public ResponseEntity<AIWorkflowResponse> approveWorkflow(
            @RequestParam String workflowId,
            @RequestParam boolean approved,
            @RequestParam(required = false) String feedback) {
        return ResponseEntity.ok(aiWorkflowService.approveWorkflow(workflowId, approved, feedback));
    }

    /**
     * Get the current status of a running/completed workflow.
     * GET /api/ai/workflow/{workflowId}/status
     */
    @GetMapping("/workflow/{workflowId}/status")
    public ResponseEntity<AIWorkflowResponse> getWorkflowStatus(@PathVariable String workflowId) {
        return ResponseEntity.ok(aiWorkflowService.getWorkflowStatus(workflowId));
    }

    /**
     * Health check – reports whether the Python AI service is reachable.
     * GET /api/ai/health
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> healthCheck() {
        return ResponseEntity.ok(aiWorkflowService.checkAIServiceHealth());
    }
}
