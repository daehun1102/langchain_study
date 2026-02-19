package com.ncs.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import java.util.List;

@Data
@AllArgsConstructor
public class InternalChatRequest {
    private String query;

    @JsonProperty("doc_ids")
    private List<String> docIds;
}
