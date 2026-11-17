package com.kr.ship_odms;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

// 테스트는 실행 DB(ship_odms.db)를 건드리지 않고 build/ 아래 임시 DB 를 쓴다.
@SpringBootTest(properties = "spring.datasource.url=jdbc:sqlite:build/test.db")
class ShipOdmsApplicationTests {

	@Test
	void contextLoads() {
	}

}
