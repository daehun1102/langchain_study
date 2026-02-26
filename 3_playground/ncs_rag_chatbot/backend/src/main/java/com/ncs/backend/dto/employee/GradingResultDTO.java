package com.ncs.backend.dto.employee;

import lombok.Data;
import java.util.Date;

@Data
public class GradingResultDTO {
    private Long resultId;
    private Long submissionId;
    private String graderId;
    private Double score;
    private String passYn; // Y, N
    private String feedback;
    private Date gradedDate;
}
