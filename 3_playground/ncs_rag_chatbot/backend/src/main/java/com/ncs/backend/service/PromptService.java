package com.ncs.backend.service;

import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class PromptService {

    private static final String PREFIX = "prompt:";

    private final StringRedisTemplate redisTemplate;

    public String get(String key) {
        return redisTemplate.opsForValue().get(PREFIX + key);
    }

    public void set(String key, String value) {
        redisTemplate.opsForValue().set(PREFIX + key, value);
    }

    public void delete(String key) {
        redisTemplate.delete(PREFIX + key);
    }

    public Map<String, String> getAll() {
        Set<String> keys = redisTemplate.keys(PREFIX + "*");
        if (keys == null || keys.isEmpty()) return Map.of();
        return keys.stream().collect(Collectors.toMap(
            k -> k.substring(PREFIX.length()),
            k -> {
                String v = redisTemplate.opsForValue().get(k);
                return v != null ? v : "";
            }
        ));
    }
}
