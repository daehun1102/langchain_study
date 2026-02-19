package com.ncs.backend.dto;

import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class ChatResponse {
    private String answer;
    private List<Map<String, Object>> sources;
}
