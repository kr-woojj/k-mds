package com.kr.ship_odms.controller;

import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ResponseBody;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

@Controller
public class OpenApiController {
    @GetMapping(value = "/openapi.yaml", produces = "application/x-yaml")
    @ResponseBody
    public ResponseEntity<Resource> openapiYaml() throws IOException {
        Resource resource = new ClassPathResource("openapi.yaml");
        if (!resource.exists()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok().contentType(MediaType.parseMediaType("application/x-yaml")).body(resource);
    }

    @GetMapping("/")
    public String swaggerUiRedirect() {
        return "redirect:/swagger-ui/index.html";
    }
}
