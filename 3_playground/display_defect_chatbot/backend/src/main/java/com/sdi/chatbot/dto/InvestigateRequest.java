package com.sdi.chatbot.dto;

import lombok.Data;

@Data
public class InvestigateRequest {
    private String sessionId;
    private String company;
    private String defectDescription;
    private String productId;
    private String selectedHypothesis;
}
