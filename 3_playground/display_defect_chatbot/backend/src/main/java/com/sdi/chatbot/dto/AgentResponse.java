package com.sdi.chatbot.dto;

import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class AgentResponse {
    private String action;
    // start
    private List<String> hypotheses;
    // select_hypothesis
    private Map<String, Object> agentResults;
    private String longTermTaskId;
    // resume_long_term
    private String finalActionPlan;
    // chat
    private String reply;
}
