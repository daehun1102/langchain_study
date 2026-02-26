package com.ncs.backend.dto.employee;

import lombok.Data;
import java.util.Date;

@Data
public class EducationHistoryDTO {
    private Long historyId;
    private String courseName;
    private String ncsCode;
    private Date startDate;
    private Date completionDate;
    private String status; // 완료, 진행중, 미이수
    private Double score;
}
