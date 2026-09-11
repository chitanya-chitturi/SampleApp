package com.example.sampleapp;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/**
 * Injected only by the self-healing CI demo (flaky-test scenario). Asserts a
 * millisecond-scale latency budget on a shared CI runner, which is inherently
 * timing-dependent and fails intermittently under load rather than reliably.
 */
@SpringBootTest
@AutoConfigureMockMvc
class FlakyExampleTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void respondsWithinTightLatencyBudget() throws Exception {
        long start = System.nanoTime();
        mockMvc.perform(get("/hello"));
        long elapsedMs = (System.nanoTime() - start) / 1_000_000;

        assertTrue(elapsedMs < 5,
                "Expected /hello to respond within 5ms but took " + elapsedMs + "ms");
    }

}
