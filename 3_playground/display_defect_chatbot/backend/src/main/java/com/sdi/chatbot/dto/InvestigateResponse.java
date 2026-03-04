package com.sdi.chatbot.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import lombok.Data;
import java.util.List;

@Data
public class InvestigateResponse {
    @JsonAlias("action_plan")
    private String actionPlan;

    @JsonAlias("process_history")
    private List<Object> processHistory;

    @JsonAlias("return_history")
    private List<Object> returnHistory;

    @JsonAlias("test_results")
    private List<Object> testResults;

    @JsonAlias("long_term_task_id")
    private String longTermTaskId;
}
