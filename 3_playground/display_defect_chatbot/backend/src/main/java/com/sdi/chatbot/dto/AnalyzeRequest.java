package com.sdi.chatbot.dto;

import lombok.Data;

@Data
public class AnalyzeRequest {
    private String sessionId;
    private String company;
    private String defectDescription;
}
