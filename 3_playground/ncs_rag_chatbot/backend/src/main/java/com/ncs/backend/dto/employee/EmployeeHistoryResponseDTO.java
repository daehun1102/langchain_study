package com.ncs.backend.dto.employee;

import lombok.Data;
import java.util.List;

@Data
public class EmployeeHistoryResponseDTO {
    private EmployeeInfoDTO employee;
    private List<EducationHistoryDTO> educationHistory;
    private List<AssignmentSubmissionDTO> assignmentSubmissions;
    private List<GradingResultDTO> gradingResults;
}
