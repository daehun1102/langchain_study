package com.sdi.chatbot.dto;

import lombok.Data;
import java.util.List;

@Data
public class AnalyzeResponse {
    private String sessionId;
    private List<String> hypotheses;
}
