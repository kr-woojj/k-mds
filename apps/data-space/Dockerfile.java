# ---- Build Stage ----
FROM mcr.microsoft.com/openjdk/jdk:21-ubuntu AS build
WORKDIR /app
COPY java/ship_odms/ .
RUN ./gradlew build --no-daemon

# ---- JRE Extract Stage ----
FROM mcr.microsoft.com/openjdk/jdk:21-ubuntu AS jre-extract
RUN jlink \
    --add-modules java.base,java.sql,java.logging,java.desktop,java.naming,java.management,java.security.jgss,java.instrument,java.compiler \
    --output /javaruntime \
    --strip-debug --compress=2 --no-header-files --no-man-pages

# ---- Runtime Stage ----
FROM ubuntu:22.04
ENV LANG C.UTF-8
ENV JAVA_HOME=/opt/java/openjdk
ENV PATH="$JAVA_HOME/bin:$PATH"
# 환경변수 전달
ENV CODESPACE_NAME="${CODESPACE_NAME}"
ENV GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN="${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"

# JRE 복사
COPY --from=jre-extract /javaruntime $JAVA_HOME

# 앱 복사
WORKDIR /app
COPY --from=build /app/build/libs/*.jar app.jar

# SQLite 설치 및 DB 파일 생성
RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/* \
    && sqlite3 ship_odms.db "VACUUM;"

EXPOSE 8088
CMD ["sh", "-c", "java -jar app.jar"]
