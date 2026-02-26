package com.ncs.backend.service;

import com.ncs.backend.dto.employee.AssignmentSubmissionDTO;
import com.ncs.backend.dto.employee.EducationHistoryDTO;
import com.ncs.backend.dto.employee.EmployeeHistoryResponseDTO;
import com.ncs.backend.dto.employee.EmployeeInfoDTO;
import com.ncs.backend.dto.employee.GradingResultDTO;
import com.ncs.backend.mapper.EmployeeMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class EmployeeService {

    private final EmployeeMapper employeeMapper;

    public EmployeeHistoryResponseDTO getEmployeeHistory(String identifier) {
        // 1. Employee Info 조회
        EmployeeInfoDTO employeeInfo = employeeMapper.findByEmployeeIdOrName(identifier)
                .orElseThrow(() -> new IllegalArgumentException("Employee not found with identifier: " + identifier));

        String employeeId = employeeInfo.getEmployeeId();

        // 2. 이력 데이터 조회
        List<EducationHistoryDTO> educationHistory = employeeMapper.findEducationHistoryByEmployeeId(employeeId);
        List<AssignmentSubmissionDTO> assignmentSubmissions = employeeMapper
                .findAssignmentSubmissionsByEmployeeId(employeeId);
        List<GradingResultDTO> gradingResults = employeeMapper.findGradingResultsByEmployeeId(employeeId);

        // 3. Response DTO 조립
        EmployeeHistoryResponseDTO response = new EmployeeHistoryResponseDTO();
        response.setEmployee(employeeInfo);
        response.setEducationHistory(educationHistory);
        response.setAssignmentSubmissions(assignmentSubmissions);
        response.setGradingResults(gradingResults);

        return response;
    }
}
