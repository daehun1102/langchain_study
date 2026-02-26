package com.ncs.backend.mapper;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.Optional;

@SpringBootTest
public class EmployeeMapperTest {

    @Autowired
    private EmployeeMapper employeeMapper;

    @Test
    public void testFindEmployee() {
        try {
            System.out.println("=== TEST START ===");
            Optional<?> emp = employeeMapper.findByEmployeeIdOrName("EMP001");
            System.out.println("Result: " + emp);
            System.out.println("=== TEST SUCCESS ===");
        } catch (Exception e) {
            e.printStackTrace();
            throw e;
        }
    }
}
