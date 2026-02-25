package com.ncs.backend.dto;

import lombok.Data;

@Data
public class ChatRequest {
    private String query;
    private String mainCategory;
    private String subCategory;
    private String threadId;    // nullable — 없으면 ChatService에서 "default" 사용
}
