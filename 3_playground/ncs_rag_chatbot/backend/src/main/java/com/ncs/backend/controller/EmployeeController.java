package com.ncs.backend.controller;

import com.ncs.backend.dto.employee.EmployeeHistoryResponseDTO;
import com.ncs.backend.service.EmployeeService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import lombok.extern.slf4j.Slf4j;

@Slf4j
@RestController
@RequestMapping("/internal/v1/employee")
@RequiredArgsConstructor
public class EmployeeController {

    private final EmployeeService employeeService;

    @GetMapping("/history")
    public ResponseEntity<?> getEmployeeHistory(@RequestParam("identifier") String identifier) {
        log.info("Requested employee history for identifier: [{}]", identifier);
        long startTime = System.currentTimeMillis();
        try {
            EmployeeHistoryResponseDTO response = employeeService.getEmployeeHistory(identifier);
            long endTime = System.currentTimeMillis();
            log.info("Employee history response for [{}] took {} ms", identifier, (endTime - startTime));
            return ResponseEntity.ok(response);
        } catch (IllegalArgumentException e) {
            long endTime = System.currentTimeMillis();
            log.info("Employee history not found for [{}] took {} ms", identifier, (endTime - startTime));
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body("{\"error\": \"" + e.getMessage() + "\"}");
        } catch (Exception e) {
            long endTime = System.currentTimeMillis();
            log.error("Employee history failure for [{}] took {} ms", identifier, (endTime - startTime));
            e.printStackTrace();
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body("{\"error\": \"" + e.getMessage() + "\"}");
        }
    }
}
