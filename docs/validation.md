# Реально выполненные проверки

Дата: **2026-10-03**, macOS arm64. Docker Desktop 24.0.7, Compose 2.23.3; Docker VM: 4 CPU, 6 223 220 736 bytes RAM (около 5.8 GiB). Это параметры реальной проверки, не рекомендуемый минимум.

**Полный CDC E2E пока НЕ прошёл.** Код, SQL, образы и тесты созданы; результаты ниже нельзя читать как заявление «всё работает».

## Успешно выполнено

| Проверка | Результат / evidence |
|---|---|
| Официальная документация и метаданные релизов | `docs/sources.md`, `versions.env`; Flink 1.20.5/CDC 3.5.0, PG14 по явной матрице |
| 14 downloads с SHA-256 | Все скачаны и повторно пересчитаны; `config/artifacts.lock.json`, `docs/artifacts.md` |
| Gravitino standalone tar | SHA-512 Apache совпал, используется серверный AWS bundle 1.2.1 |
| Base image manifests | Теги/index digest для PostgreSQL/Flink/Trino/Maven/Java/Go/Python разрешены; amd64/arm64 объявлены |
| `./mvnw -B -ntp package` | BUILD SUCCESS, оба Java-модуля |
| Multi-stage Docker build | Все 6 образов собраны: Flink, generator, submitter, Gravitino, MinIO, MC |
| `MAVEN_ARGS=-o make test-unit` | **5 JUnit + 4 Python tests passed**, `.runtime/final-unit.log` |
| Python syntax, shell syntax, Compose config | `py_compile`, `bash -n`, `docker compose config --quiet` проходят |
| PostgreSQL/MinIO/Gravitino/Flink/Trino startup | Все сервисы доходили до healthy; TaskManager регистрировался после исправления адреса JM |
| Реальный S3 write/read | MC проверяет три bucket с pipeline credentials; Java `StorageProbe` проверил Flink filesystem в checkpoints/savepoints |
| Реальный Gravitino REST/JDBC bootstrap | Namespace и Iceberg-таблицы созданы клиентом через `/iceberg`, не JdbcCatalog в клиенте |
| Небольшой Iceberg v2 CRUD через Trino | INSERT → UPDATE → DELETE, итог `(id=1, amount=42.37)` проверен; это ещё НЕ доказательство Flink equality deletes |
| Java seed | Реально создано 100 customers, 200 accounts, 10 000 payments, транзакция закрыта |

## Исправления, выявленные реальным запуском

1. Psql PostgreSQL 14 не имеет `\getenv`: заменено на поддерживаемое получение env внутри psql. Проверено последующим bootstrap.
2. Официальный entrypoint Flink переопределяет RPC address: явно задан `JOB_MANAGER_RPC_ADDRESS=flink-jobmanager`. Проверена регистрация TaskManager.
3. Iceberg Flink CatalogFactory требует Hadoop Configuration API даже для REST: добавлены hadoop-client-api/runtime 3.4.1 и commons-logging 1.3.5. Последующий bootstrap и S3 probe прошли.
4. Полная замена Flink config.yaml убрала стандартные Java 17 module options. Первый CDC submit завершался HTTP 400 / `InaccessibleObjectException: java.base does not opens java.util`. В template внесён полный набор options из официального **release-1.20.5** config.yaml; последующий запуск ещё требуется.

## Журнал E2E-попыток

Все — настоящий Compose; runner сохраняет logs/XML и удаляет только volumes своего временного проекта.

| Run в `.runtime/e2e/` | Фактический результат |
|---|---|
| `20261003T173924-26145` | setup остановился на psql `\getenv`; 11 setup errors |
| `20261003T174216-26820` | deadline регистрации slots; 11 setup errors |
| `20261003T175021-28347` | bootstrap: missing Hadoop Configuration; 1 setup error, остальные не запускались (`-x`) |
| `20261003T175439-29316` | submit HTTP 400; тест A/G не прошёл, остальные не запускались |
| `20261003T175931-30637` | конкретизирован Java 17 module-access error; тест A/G не прошёл, остальные не запускались |

После исправления JVM options автоматическая проверка разрешений дважды завершилась по таймауту до запуска `make test-e2e`. Это не результат выполнения исправленного pipeline. Запрос подтверждения повторного запуска передан пользователю.

## Что ещё не подтверждено

- Initial snapshot + WAL до Iceberg и полная сверка всех полей; реальные Flink equality deletes и time travel после DELETE.
- Изменения во время snapshot; rollback, повторные версии, multi-table transaction в end-to-end потоке.
- Recovery после SIGKILL TaskManager, stop-savepoint/restore, restart каталога с сохранением таблиц, краткие outages, конкурентный повторный submit.
- Полный `make demo`; `make doctor` как одна команда (его отдельные проверки Docker/resources/ports/manifests выполнялись частично).
- Runtime на amd64, stress-профиль, ручные упражнения по schema migration и расширения 11–14.

Эти сценарии **реализованы** в `tests/e2e/test_pipeline.py`, но наличие тестового кода не означает прохождение. Для продолжения: `make test-e2e`, затем при успехе `make demo`. Все опубликованные порты — localhost; основные persistent volumes при E2E не удаляются.

## Границы проекта

Standalone session cluster без HA; один MinIO volume — не DR; commit трёх Iceberg mirrors не атомарен. SQL restore поддерживается только для идентичного artifact/плана и доступного WAL/state. Старое Flink state нельзя откатывать на продвинувшийся sink без анализа. Advanced labs 11–14 описаны, отдельные дополнительные сервисы/jobs не реализованы.
