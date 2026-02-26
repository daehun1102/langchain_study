package com.ncs.backend.mapper;

import com.ncs.backend.dto.employee.AssignmentSubmissionDTO;
import com.ncs.backend.dto.employee.EducationHistoryDTO;
import com.ncs.backend.dto.employee.EmployeeInfoDTO;
import com.ncs.backend.dto.employee.GradingResultDTO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Optional;

@Mapper
public interface EmployeeMapper {

    Optional<EmployeeInfoDTO> findByEmployeeIdOrName(@Param("identifier") String identifier);

    List<EducationHistoryDTO> findEducationHistoryByEmployeeId(@Param("employeeId") String employeeId);

    List<AssignmentSubmissionDTO> findAssignmentSubmissionsByEmployeeId(@Param("employeeId") String employeeId);

    List<GradingResultDTO> findGradingResultsByEmployeeId(@Param("employeeId") String employeeId);
}
