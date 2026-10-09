# Матрица версий

Проверено 2026-10-03. Единственный файл переменных: `versions.env`.
Точные теги и multi-architecture index digest записаны там; сборка использует digest.
Полные URL, SHA-256 и назначение скачанных JAR/архивов: `config/artifacts.lock.json`.
Maven coordinates соответствуют пути Central: groupId = путь до artifactId, заменяя `/` на `.`.

| Компонент | Версия/линия | Основание и статус |
|---|---|---|
| Java job / generator | release 17 | Flink Java 17; локальный javac может быть новее, bytecode release=17 |
| Maven / wrapper | 3.9.15 / 3.3.4 | фиксированная distribution + SHA-256 |
| PostgreSQL OLTP/catalog | 14.24-bookworm | CDC 3.5 docs явно перечисляют PG14; artifact-resolved |
| Flink | 1.20.5, Scala 2.12, Java 17 | актуальный patch линии в Central; artifact-resolved |
| CDC SQL bundle | 3.5.0 | матрица 3.5 ↔ 1.20; artifact-resolved |
| Iceberg client | 1.10.2 runtime-1.20 + aws-bundle | один runtime в lib, API Flink provided; artifact-resolved |
| Flink S3 filesystem | 1.20.5 hadoop plugin | только plugins/s3-fs-hadoop; отдельный classloader |
| Hadoop client API/runtime | 3.4.1 + commons-logging 1.3.5 | Iceberg Flink CatalogFactory требует Configuration даже для REST; shaded client runtime, не второй S3 SDK |
| Gravitino | 1.2.1 standalone distribution | официальный tar, SHA-512 Apache; Docker Hub final tag 404 |
| Gravitino Iceberg | 1.10.1 | исходный gradle/libs.versions.toml тега v1.2.1; bundles сервера не заменяем |
| JDBC | 42.7.10 | явно добавлен в libs Gravitino; generator shaded JDBC |
| Trino | 476 | REST + native S3 + v2 deletes; собственная Java внутри образа |
| MinIO | RELEASE.2025-09-07T16-13-09Z | официальный source tag, сборка Go 1.24.13 |
| MC | RELEASE.2025-08-13T08-35-41Z | официальный source tag, отдельная сборка |
| Builder | Maven 3.9.15 / Go 1.24.13 | digest в versions.env, amd64 и arm64 в manifest |
| Test/runtime utility | Python 3.12.10 slim-bookworm | digest в versions.env; stdlib runner, зависимости E2E зафиксированы отдельно |

Для PostgreSQL, Flink, Trino, Maven, Python, Java и Go Docker Hub manifests подтвердили linux/amd64 и linux/arm64. MinIO/MC собираются нативно для TARGETARCH; Gravitino tar содержит Java bytecode. Наличие manifests не равняется успешному запуску на обеих архитектурах. Фактическая машина проверки — Apple arm64.

Gravitino 1.2.1 использует REST `/iceberg/v1/config`. Static provider без client warehouse selector выбирает default backend. Server warehouse — `s3://warehouse/`; не передаём этот путь как Trino warehouse selector. JDBC driver проверяется в libs. S3 библиотеки сервера проверяются отдельно при bootstrap write/read.

Источник CDC — SQL connector, не YAML Pipeline API. `scan.incremental.snapshot.enabled=true` — experimental в документации CDC 3.5. Чтение snapshot затем pgoutput; периодического SELECT по updated_at в pipeline нет.

Статусы: **documentation-only** = проверена документация; **artifact-resolved** = артефакт скачан или manifest разрешён; **built** = сборка выполнена; **integration-tested** = реальный стенд и данные. Итоговые реально достигнутые статусы, команды и ограничения — в [validation.md](validation.md); здесь не предполагается успех интеграции заранее.

Документация именно выбранных версий перечислена в [sources.md](sources.md). Сторонние latest/nightly/SNAPSHOT образы не используются. `nightlies.apache.org/...release-...` — адрес опубликованной versioned документации, не версия загружаемого ПО.

Фактически достигнуто: Java-модули и все собственные образы — **built**; MinIO, Gravitino REST/JDBC bootstrap и Trino v2 CRUD — **integration-tested** в узком объёме из validation.md. Полный CDC/sink/recovery — пока **не integration-tested**. Наличие образов amd64 проверено через manifest, запуск выполнялся только arm64.
