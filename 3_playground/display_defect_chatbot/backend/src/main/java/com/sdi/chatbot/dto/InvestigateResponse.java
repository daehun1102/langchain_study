package com.sdi.chatbot.dto;

import lombok.Data;
import java.util.List;

@Data
public class InvestigateResponse {
    private String actionPlan;
    private List<Object> processHistory;
    private List<Object> returnHistory;
    private List<Object> testResults;
    private String longTermTaskId;
}
