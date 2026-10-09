# Полный Gravitino Server — задание

## Цель

Изучить metalake, managed catalog и dynamic provider.

## Prerequisite

Отдельный Full Server 1.2.1, отдельные namespace/warehouse; baseline не менять.

## Команды

```bash
# В отдельном Compose override запустить официальный Full Gravitino Server.
# Через /api/metalakes создать metalake lab, затем managed Iceberg catalog.
# Указать JDBC/S3 properties выбранного каталога.
# Для отдельного REST service:
# gravitino.iceberg-rest.catalog-config-provider=dynamic-config-provider
# gravitino.iceberg-rest.gravitino-metalake=lab
# gravitino.iceberg-rest.gravitino-uri=http://full-server:8090
# Клиентом выбрать catalog selector/prefix по docs 1.2.1.
# CREATE namespace/table → restart обоих серверов → независимое чтение.
```

## Ожидаемое наблюдение

Full Server управляет metalake/catalog, dynamic provider получает от него конфигурацию. Standalone static baseline читает файл и сам предоставляет Iceberg REST API.

## Объяснение

Gravitino governance и Iceberg protocol — разные уровни. Dynamic standalone и auxiliary embedded различаются; access control 1.2.1 поддерживается auxiliary mode. Server warehouse остаётся S3 location, client selector обозначает каталог.

## Вопросы

Где хранится configuration, где pointers, где файлы? Что происходит при недоступности Full Server?

## Вернуть стенд в рабочее состояние

Вернуться к неизменённому compose.yaml/static provider. Не копировать metadata pointers вручную. Это задание, Full Server не входит в обязательный запуск.

