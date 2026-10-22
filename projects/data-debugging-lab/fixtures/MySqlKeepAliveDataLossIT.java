/*
 * Copyright Debezium Authors.
 *
 * Licensed under the Apache Software License version 2.0, available at http://www.apache.org/licenses/LICENSE-2.0
 */
package io.debezium.connector.mysql;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Path;
import java.sql.Statement;
import java.time.Duration;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import org.apache.kafka.connect.data.Struct;
import org.apache.kafka.connect.source.SourceRecord;
import org.awaitility.Awaitility;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import io.debezium.config.Configuration;
import io.debezium.connector.binlog.AbstractBinlogConnectorIT;
import io.debezium.connector.binlog.BinlogConnectorConfig;
import io.debezium.connector.binlog.util.BinlogTestConnection;
import io.debezium.connector.binlog.util.TestHelper;
import io.debezium.connector.binlog.util.UniqueDatabase;
import io.debezium.data.Envelope;
import io.debezium.jdbc.JdbcConnection;
import io.debezium.util.Testing;

public class MySqlKeepAliveDataLossIT extends AbstractBinlogConnectorIT<MySqlConnector> implements MySqlCommon {

    private static final Path SCHEMA_HISTORY_PATH = Testing.Files.createTestingPath("file-schema-history-keepalive.txt").toAbsolutePath();
    private static final String TABLE_NAME = "keepalive_repro";
    private static final int QUEUE_SIZE = 20;
    private static final int TRANSACTION_COUNT = 30;
    private static final int ROWS_PER_TRANSACTION = 500;
    private static final long FIRST_ID = 1_000_001L;
    private static final long SENTINEL_ID = FIRST_ID + (long) TRANSACTION_COUNT * ROWS_PER_TRANSACTION;

    private final UniqueDatabase database = TestHelper.getUniqueDatabase("keepalive_server", "connector_test_ro")
            .withDbHistoryPath(SCHEMA_HISTORY_PATH);

    @BeforeEach
    void beforeEach() throws Exception {
        stopConnector();
        database.createAndInitialize();
        initializeConnectorTestFramework();
        Testing.Files.delete(SCHEMA_HISTORY_PATH);
    }

    @AfterEach
    void afterEach() {
        try {
            stopConnector();
        }
        finally {
            Testing.Files.delete(SCHEMA_HISTORY_PATH);
        }
    }

    @Override
    protected int getMaximumEnqueuedRecordCount() {
        return QUEUE_SIZE;
    }

    @Test
    void shouldNotLoseRowsWhenKeepAliveReconnectsWithFullQueue() throws Exception {
        final Configuration config = database.defaultConfig()
                .with(BinlogConnectorConfig.USER, "cloud")
                .with(BinlogConnectorConfig.PASSWORD, "cloudpass")
                .with(BinlogConnectorConfig.INCLUDE_SCHEMA_CHANGES, false)
                .with(BinlogConnectorConfig.INCLUDE_SQL_QUERY, false)
                .with(BinlogConnectorConfig.SNAPSHOT_MODE, BinlogConnectorConfig.SnapshotMode.NO_DATA)
                .with(BinlogConnectorConfig.BUFFER_SIZE_FOR_BINLOG_READER, 0)
                .with(BinlogConnectorConfig.MAX_QUEUE_SIZE, QUEUE_SIZE)
                .with(BinlogConnectorConfig.MAX_BATCH_SIZE, 10)
                .with(BinlogConnectorConfig.KEEP_ALIVE_INTERVAL_MS, 1_000)
                .with(BinlogConnectorConfig.TABLE_INCLUDE_LIST, database.qualifiedTableName(TABLE_NAME))
                .build();

        start(getConnectorClass(), config);
        waitForStreamingRunning(getConnectorName(), database.getServerName());

        try (BinlogTestConnection db = getTestDatabaseConnection(database.getDatabaseName());
                JdbcConnection connection = db.connect();
                Statement statement = connection.connection().createStatement()) {
            statement.executeUpdate("CREATE TABLE " + TABLE_NAME
                    + " (id BIGINT NOT NULL PRIMARY KEY, payload TEXT) ENGINE=InnoDB");

            for (int batch = 0; batch < TRANSACTION_COUNT; batch++) {
                final long batchStart = FIRST_ID + (long) batch * ROWS_PER_TRANSACTION;
                statement.execute("SET @n = " + (batchStart - 1));
                final int insertedRows = statement.executeUpdate("INSERT INTO " + TABLE_NAME
                        + " SELECT @n := @n + 1, REPEAT('M', 8192)"
                        + " FROM information_schema.columns LIMIT " + ROWS_PER_TRANSACTION);
                assertThat(insertedRows).isEqualTo(ROWS_PER_TRANSACTION);
                if (batch + 1 < TRANSACTION_COUNT) {
                    TimeUnit.MILLISECONDS.sleep(200);
                }
            }
            statement.executeUpdate("INSERT INTO " + TABLE_NAME + " VALUES (" + SENTINEL_ID + ", 'sentinel')");
        }

        Awaitility.await()
                .alias("Keepalive did not disconnect the stalled binlog connection")
                .pollInterval(Duration.ofMillis(100))
                .atMost(Duration.ofSeconds(30))
                .until(() -> !isStreamingRunning(getConnectorName(), database.getServerName()));

        final SourceRecords records = consumeRecordsByTopicUntil((count, record) -> record.topic().equals(database.topicForTable(TABLE_NAME))
                && extractId(record) == SENTINEL_ID);
        final Set<Long> actualIds = new HashSet<>();
        records.forEachInTopic(database.topicForTable(TABLE_NAME), record -> actualIds.add(extractId(record)));
        assertThat(actualIds).contains(SENTINEL_ID);

        int missingCount = 0;
        long firstMissingId = -1;
        long lastMissingId = -1;
        for (long id = FIRST_ID; id <= SENTINEL_ID; id++) {
            if (!actualIds.contains(id)) {
                if (missingCount == 0) {
                    firstMissingId = id;
                }
                lastMissingId = id;
                missingCount++;
            }
        }
        assertThat(missingCount)
                .as("Missing IDs from " + firstMissingId + " through " + lastMissingId
                        + "; captured " + actualIds.size() + " records")
                .isEqualTo(0);
    }

    private long extractId(SourceRecord record) {
        final Struct value = (Struct) record.value();
        final Struct after = value.getStruct(Envelope.FieldName.AFTER);
        return after.getInt64("id");
    }
}
