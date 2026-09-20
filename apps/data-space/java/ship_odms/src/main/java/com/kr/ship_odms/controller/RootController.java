package com.kr.ship_odms.controller;

import io.swagger.v3.oas.annotations.Hidden;
import org.springdoc.core.service.OpenAPIService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ClassPathResource;
import org.springframework.http.MediaType;
import org.springframework.util.StreamUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.view.RedirectView;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

@RestController
public class RootController {
    @Autowired
    private OpenAPIService openAPIService;

    // '/' 매핑 제거 (OpenApiController와 중복 방지)

    @GetMapping(value = "/openapi.yaml", produces = MediaType.TEXT_PLAIN_VALUE)
    @Hidden
    public String getOpenApiYaml() throws IOException {
        ClassPathResource resource = new ClassPathResource("openapi.yaml");
        return StreamUtils.copyToString(resource.getInputStream(), StandardCharsets.UTF_8);
    }
}
