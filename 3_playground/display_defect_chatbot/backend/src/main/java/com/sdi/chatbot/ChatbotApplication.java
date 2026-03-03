// display_defect_chatbot/backend/src/main/java/com/sdi/chatbot/ChatbotApplication.java
package com.sdi.chatbot;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.sdi.chatbot.mapper")
public class ChatbotApplication {
    public static void main(String[] args) {
        SpringApplication.run(ChatbotApplication.class, args);
    }
}
