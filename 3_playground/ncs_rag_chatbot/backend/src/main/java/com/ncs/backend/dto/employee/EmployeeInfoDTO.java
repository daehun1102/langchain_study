package com.ncs.backend.dto.employee;

import lombok.Data;
import java.util.Date;

@Data
public class EmployeeInfoDTO {
    private String employeeId;
    private String name;
    private String department;
    private String position;
    private Date joinDate;
    private String email;
}
