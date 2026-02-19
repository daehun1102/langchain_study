package com.ncs.backend.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import java.util.List;

@Data
@AllArgsConstructor
public class InternalChatRequest {
    private String query;
    private List<String> docIds;
}
