# Официальные источники

Дата проверки: **2026-10-03**. Версия страницы указана явно. Код, конфигурации и результаты этого проекта — собственная реализация; ссылки подтверждают API/возможности, а не заменяют integration tests.

| Источник | Что проверено |
|---|---|
| [CDC 3.5 source overview](https://nightlies.apache.org/flink/flink-cdc-docs-release-3.5/docs/connectors/flink-sources/overview/) | матрица 3.5↔1.20, явно перечисленный PG14 |
| [CDC 3.5 PostgreSQL SQL/DataStream](https://nightlies.apache.org/flink/flink-cdc-docs-release-3.5/docs/connectors/flink-sources/postgres-cdc/) | pgoutput, incremental snapshot experimental, SQL options, changelog, slots, metrics |
| [Iceberg 1.10.2 Flink writes](https://iceberg.apache.org/docs/1.10.2/flink-writes/) | v2 upsert, equality fields, hash distribution, checkpoints/commit |
| [Iceberg 1.10.2 Flink configuration](https://iceberg.apache.org/docs/1.10.2/flink-configuration/) | REST catalog, sink properties |
| [Iceberg 1.10.2 AWS](https://iceberg.apache.org/docs/1.10.2/aws/) | S3FileIO и AWS bundle |
| [Gravitino 1.2.1 Iceberg REST](https://gravitino.apache.org/docs/1.2.1/iceberg-rest-service/) | standalone/static provider, JDBC, `/iceberg`, server warehouse, S3 options, server AWS bundle |
| [Gravitino v1.2.1 dependency versions](https://github.com/apache/gravitino/blob/v1.2.1/gradle/libs.versions.toml) | серверный Iceberg 1.10.1 отличается от runtime клиента |
| [Gravitino v1.2.1 AWS bundle build](https://github.com/apache/gravitino/blob/v1.2.1/bundles/iceberg-aws-bundle/build.gradle.kts) | назначение отдельного server bundle |
| [Apache Gravitino 1.2.1 official release](https://archive.apache.org/dist/gravitino/1.2.1/) | официальный standalone tar и SHA-512; финального Docker tag 1.2.1 при проверке не было |
| [Flink 1.20 S3 filesystem](https://nightlies.apache.org/flink/flink-docs-release-1.20/docs/deployment/filesystems/s3/) | plugin directory и собственные S3 settings |
| [Flink 1.20 checkpoints](https://nightlies.apache.org/flink/flink-docs-release-1.20/docs/ops/state/checkpoints/) | storage, externalized retention, recovery |
| [Flink 1.20 savepoints](https://nightlies.apache.org/flink/flink-docs-release-1.20/docs/ops/state/savepoints/) | stop/restore, operator state compatibility |
| [Flink 1.20 REST](https://nightlies.apache.org/flink/flink-docs-release-1.20/docs/ops/rest_api/) | jar run, jobs overview, checkpoints, asynchronous savepoint/stop |
| [Flink 1.20 metrics](https://nightlies.apache.org/flink/flink-docs-release-1.20/docs/ops/metrics/) | checkpoint, I/O, backpressure metric names и scopes |
| [PostgreSQL 14 logical decoding](https://www.postgresql.org/docs/14/logicaldecoding-explanation.html) | slots, WAL retention, restart |
| [PostgreSQL 14 publication](https://www.postgresql.org/docs/14/logical-replication-publication.html) | publication scope, replica identity |
| [Trino 476 Iceberg docs (release source)](https://github.com/trinodb/trino/blob/476/docs/src/main/sphinx/connector/iceberg.md) | v2, metadata tables, SQL/time travel/maintenance |
| [Trino 476 REST catalog](https://github.com/trinodb/trino/blob/476/docs/src/main/sphinx/object-storage/metastores.md) | rest URI/security/warehouse/vended credentials |
| [Trino 476 S3](https://github.com/trinodb/trino/blob/476/docs/src/main/sphinx/object-storage/file-system-s3.md) | fs.native-s3.enabled, endpoint, credentials, path style |
| [Trino 476 Iceberg delete tests](https://github.com/trinodb/trino/blob/476/plugin/trino-iceberg/src/test/java/io/trino/plugin/iceberg/TestIcebergV2.java) | independent support for v2 delete-aware reads; project E2E additionally checks actual equality files |
| [MinIO release](https://github.com/minio/minio/releases/tag/RELEASE.2025-09-07T16-13-09Z) | официальный source release, go.mod |
| [MC release](https://github.com/minio/mc/releases/tag/RELEASE.2025-08-13T08-35-41Z) | официальный client source |
| [Iceberg 1.10.2 maintenance](https://iceberg.apache.org/docs/1.10.2/maintenance/) | compaction, expiration, orphan retention safety |

Артефакты Maven проверялись на `repo.maven.apache.org`, Docker-теги и index digest — Docker Hub API, доступность Quay — `docker buildx imagetools inspect` (MinIO получил HTTP 401, использована сборка source). Полные artifact URLs и SHA-256 сохранены в `config/artifacts.lock.json`.

[Default Flink 1.20.5 config.yaml](https://github.com/apache/flink/blob/release-1.20.5/flink-dist/src/main/resources/config.yaml) подтверждает Java 17 module options, сохранённые в template.
