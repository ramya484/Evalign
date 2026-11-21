package com.ems.dto;

import lombok.Data;

@Data
public class AIWorkflowRequest {
    private Long cohortId;
    private String roundType;   // INTERIM or FINAL
    private Integer attempt = 1;
    private String interviewFrom; // YYYY-MM-DD
    private String interviewTo;
}
