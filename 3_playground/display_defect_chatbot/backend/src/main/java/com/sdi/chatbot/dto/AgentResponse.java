package com.sdi.chatbot.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class AgentResponse {
    private String action;
    // start
    private List<HypothesisItem> hypotheses;
    // select_hypothesis
    private Map<String, Object> agentResults;
    private String longTermTaskId;
    // resume_long_term
    private String finalActionPlan;
    // chat
    private String reply;

    @Data
    public static class HypothesisItem {
        private String text;
        @JsonProperty("recommended_agents")
        private List<String> recommendedAgents;
    }
}
