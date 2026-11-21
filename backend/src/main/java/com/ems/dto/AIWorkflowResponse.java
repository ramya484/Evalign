package com.ems.dto;

import lombok.Data;
import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class AIWorkflowResponse {
    private String workflowId;
    private String status;
    private Object result;
    private String errorMessage;
}
