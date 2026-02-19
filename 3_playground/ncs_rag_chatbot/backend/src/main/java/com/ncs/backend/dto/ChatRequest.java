package com.ncs.backend.dto;

import lombok.Data;

@Data
public class ChatRequest {
    private String query;
    private String mainCategory;
    private String subCategory;
}
