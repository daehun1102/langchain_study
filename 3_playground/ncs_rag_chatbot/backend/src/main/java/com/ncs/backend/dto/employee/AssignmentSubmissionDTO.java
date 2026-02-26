package com.ncs.backend.dto.employee;

import lombok.Data;
import java.util.Date;

@Data
public class AssignmentSubmissionDTO {
    private Long submissionId;
    private String courseName;
    private String assignmentName;
    private Date submitDate;
    private String status; // 제출, 미제출, 반려
    private String content;
}
