package com.ncs.backend.model;

import lombok.Data;
import java.util.Date;

@Data
public class Document {
    private String docId;
    private String filename;
    private String mainCategory;
    private String subCategory;
    private int pageCount;
    private Date uploadDate;
    private String status;
}
