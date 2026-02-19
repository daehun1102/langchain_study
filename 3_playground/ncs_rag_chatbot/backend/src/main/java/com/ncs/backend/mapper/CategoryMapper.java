package com.ncs.backend.mapper;

import com.ncs.backend.model.Category;
import org.apache.ibatis.annotations.Mapper;
import java.util.List;

@Mapper
public interface CategoryMapper {
    List<Category> findAll();
}
