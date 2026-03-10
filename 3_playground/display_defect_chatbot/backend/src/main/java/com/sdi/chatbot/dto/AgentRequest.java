package com.sdi.chatbot.dto;

import lombok.Data;
import java.util.List;

@Data
public class AgentRequest {
    private String sessionId;
    private String action;           // "start" | "select_hypothesis" | "resume_long_term" | "chat"
    private String company;
    private String defectDescription;
    private String productId;
    private List<String> enabledAgents;
    // action별 선택 필드
    private String selectedHypothesis;
    private String longTermResult;
    private String userMessage;
    private String notifyEmail;
}
