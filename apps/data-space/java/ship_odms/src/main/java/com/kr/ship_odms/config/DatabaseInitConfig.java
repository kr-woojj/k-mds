package com.kr.ship_odms.config;

import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import org.springframework.stereotype.Component;

import javax.sql.DataSource;

@Component
public class DatabaseInitConfig {
    @Autowired
    private DataSource dataSource;

    @PostConstruct
    public void init() {
        ResourceDatabasePopulator populator = new ResourceDatabasePopulator();
        populator.addScript(new ClassPathResource("schema.sql"));

        try {
            ClassPathResource dataSql = new ClassPathResource("data.sql");
            if (dataSql.exists() && dataSql.contentLength() > 0) {
                populator.addScript(dataSql);
            }
        } catch (Exception ignored) {}

        populator.execute(dataSource);
    }
}
