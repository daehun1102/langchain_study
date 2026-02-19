package com.ncs.backend.service;

import com.ncs.backend.mapper.CategoryMapper;
import com.ncs.backend.model.Category;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
@RequiredArgsConstructor
public class CategoryService {

    private final CategoryMapper categoryMapper;

    public Map<String, List<String>> getCategoriesGrouped() {
        List<Category> categories = categoryMapper.findAll();
        Map<String, List<String>> result = new LinkedHashMap<>();
        for (Category c : categories) {
            result.computeIfAbsent(c.getMainCategory(), k -> new ArrayList<>())
                  .add(c.getSubCategory());
        }
        return result;
    }
}
