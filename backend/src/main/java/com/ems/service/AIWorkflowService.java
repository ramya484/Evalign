package com.ems.service;

import com.ems.dto.AIWorkflowRequest;
import com.ems.dto.AIWorkflowResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.client.ResourceAccessException;

import java.util.HashMap;
import java.util.Map;

@Service
public class AIWorkflowService {

    @Value("${ai.service.url:http://localhost:8001}")
    private String aiServiceUrl;

    private final RestTemplate restTemplate = new RestTemplate();

    private HttpHeaders jsonHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        return headers;
    }

    public AIWorkflowResponse startWorkflow(AIWorkflowRequest request) {
        try {
            String url = aiServiceUrl + "/api/ai/workflow/start";
            HttpEntity<AIWorkflowRequest> entity = new HttpEntity<>(request, jsonHeaders());
            ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);
            Map body = response.getBody();
            return new AIWorkflowResponse(
                (String) (body != null ? body.get("workflow_id") : null),
                (String) (body != null ? body.get("status") : null),
                body,
                null
            );
        } catch (ResourceAccessException e) {
            return new AIWorkflowResponse(null, "ERROR", null,
                "AI service unreachable. Ensure the Python AI service is running at: " + aiServiceUrl);
        } catch (Exception e) {
            return new AIWorkflowResponse(null, "ERROR", null, e.getMessage());
        }
    }

    public AIWorkflowResponse approveWorkflow(String workflowId, boolean approved, String feedback) {
        try {
            String url = aiServiceUrl + "/api/ai/workflow/approve";
            Map<String, Object> body = new HashMap<>();
            body.put("workflow_id", workflowId);
            body.put("approved", approved);
            if (feedback != null) body.put("feedback", feedback);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, jsonHeaders());
            ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);
            Map respBody = response.getBody();
            return new AIWorkflowResponse(
                workflowId,
                (String) (respBody != null ? respBody.get("status") : null),
                respBody,
                null
            );
        } catch (Exception e) {
            return new AIWorkflowResponse(workflowId, "ERROR", null, e.getMessage());
        }
    }

    public AIWorkflowResponse getWorkflowStatus(String workflowId) {
        try {
            String url = aiServiceUrl + "/api/ai/workflow/" + workflowId + "/status";
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);
            Map body = response.getBody();
            return new AIWorkflowResponse(
                workflowId,
                (String) (body != null ? body.get("current_stage") : null),
                body,
                null
            );
        } catch (Exception e) {
            return new AIWorkflowResponse(workflowId, "ERROR", null, e.getMessage());
        }
    }

    public Map<String, String> checkAIServiceHealth() {
        Map<String, String> result = new HashMap<>();
        try {
            String url = aiServiceUrl + "/api/ai/health";
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);
            result.put("status", "UP");
            result.put("ai_service_url", aiServiceUrl);
        } catch (Exception e) {
            result.put("status", "DOWN");
            result.put("ai_service_url", aiServiceUrl);
            result.put("error", e.getMessage());
        }
        return result;
    }
}
