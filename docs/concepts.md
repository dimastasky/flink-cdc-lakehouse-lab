# Понятия на примере проекта

**OLTP и OLAP.** `sql/postgres/bootstrap.sql` описывает строки, FK, ограничения и короткие транзакции приложения. Trino выполняет аналитический join и группирует суммы по валютам (`sql/trino/analytics.sql`). Учебная модель не проводит балансировочные записи ledger.

**CDC и ETL.** Initial snapshot — ограниченное чтение исходных таблиц; затем поток pgoutput из WAL не ограничен во времени. В `sql/flink/*-source.sql` включён incremental snapshot (experimental в CDC 3.5). Генератор изменяет PostgreSQL, job не опрашивает updated_at. E2E намеренно делает изменения при заблокированном snapshot reader.

**Changelog.** +I — новая строка, -U — прежняя версия UPDATE, +U — новая версия, -D — удаление. RowKind передаётся SQL runtime в Iceberg sink, не превращается в INSERT. `event_time` — время бизнес-события; оно может быть старым. Нельзя добавлять NOW() или случайные значения к retract-строкам: до/после перестанут описывать одно изменение. Нет stateful joins или HTTP enrichment в baseline.

**FULL и upsert.** REPLICA IDENTITY FULL пишет старый образ всей строки в WAL, увеличивая объём WAL, network и deserialization. Он полезен здесь для наблюдения полного changelog. Альтернатива с PK и `changelog-mode=upsert` требует отдельной проверки коннектора, sink и nullable/non-key колонок; FULL не является универсальной рекомендацией production.

**Четыре слоя.** MinIO хранит объекты. Parquet кодирует columnar data files и delete files; JSON metadata и Avro manifests не становятся Parquet. Iceberg связывает файлы со snapshot и schema, применяет equality deletes. Gravitino предоставляет REST-каталог, а его JDBC backend сохраняет указатели на актуальные metadata. Поэтому `glob('*.parquet')` не является чтением текущей таблицы. Сумма физических record_count не равна числу логических строк после deletes.

**Current state и история.** payments_current содержит последнюю версию каждого ключа, но не журнал всех CDC-событий. Старый Iceberg snapshot позволяет time travel до expiration. `PRIMARY KEY NOT ENFORCED` — обещание planner/sink, а не проверка уникальности runtime: источник и hash-routing всё равно должны быть корректны. В sink upsert=true создаёт equality deletes по identifier field; один writer обрабатывает последовательность изменений ключа.

**State и checkpoint storage.** HashMapStateBackend отвечает за рабочее состояние внутри TaskManager. `s3://checkpoints/` — сериализованные согласованные снимки состояния. Iceberg S3FileIO и Flink filesystem plugin — разные classloaders и настройки. Bootstrap проверяет filesystem write/read; успешные Iceberg commits отдельно проверяются Trino. S3FileIO в сервере Gravitino имеет собственный bundle и JDBC driver.

**Checkpoint и savepoint.** Checkpoint нужен регулярному recovery и запускает commit sink. Savepoint нужен запланированной остановке и управляемому restore. SQL UID генерируются, поэтому изменение SQL может нарушить совместимость. Одинаковый jar/план проверяется в E2E; произвольное изменение плана не обещается. Детали — `docs/recovery.md`.

**Время и деньги.** NUMERIC(18,2) ↔ DECIMAL(18,2), Java BigDecimal. Все хранимые значения времени кратны миллисекунде: timestamptz(3) ↔ TIMESTAMP_LTZ(3) ↔ Iceberg timestamptz ↔ Trino timestamp(6) with time zone. Последний тип имеет больше ёмкости точности, но значения должны оставаться миллисекундными. `scripts/verify.py` отвергает потерю timezone и sub-ms значения. `country_code` nullable; тесты сравнивают NULL с NULL, а не пустой строкой.

**Eventual consistency.** Между PostgreSQL commit и Trino видимостью проходят CDC, checkpoint и публикация metadata. 10 s checkpoints — учебный компромисс: чаще → меньше задержка, больше commits и мелких файлов; target-file-size не запрещает маленькие файлы при каждом checkpoint. Нет атомарного Iceberg commit сразу для трёх таблиц. Join во время catch-up может видеть промежуточное несогласованное состояние даже для одной исходной PostgreSQL транзакции.

**Exactly-once.** Согласованное восстановление state не означает одно физическое исполнение каждого record: после отказа возможен replay. Успешный checkpoint и успешно опубликованный Iceberg snapshot — связанные, но отдельные наблюдения. E2E проверяет конкретную конфигурацию и набор отказов, не доказывает все случаи mathematically. После остановки нагрузки сверяем полный набор ключей, decimal/time/status/version/NULL, а не только counts/checksum.

**Observability.** Byte lag = разница LSN, event lag = отставание событий/offset progression, E2E latency = длительность от подтверждённого source commit до видимости контрольной строки в Trino. Эти величины не взаимозаменяемы. Старый event_time не является network latency. При пустом потоке отсутствие новых Iceberg commits само по себе не авария.
