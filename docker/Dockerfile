# syntax=docker/dockerfile:1
ARG MAVEN_IMAGE
ARG FLINK_IMAGE
ARG JAVA_IMAGE
ARG PYTHON_IMAGE
ARG GO_IMAGE
FROM ${MAVEN_IMAGE} AS java-build
WORKDIR /src
COPY versions.env pom.xml mvnw ./
COPY .mvn .mvn
COPY flink-job flink-job
COPY workload-generator workload-generator
COPY sql/flink sql/flink
RUN --mount=type=cache,target=/root/.m2 --mount=type=cache,target=/src/.cache/maven ./mvnw -B -ntp package

FROM ${PYTHON_IMAGE} AS artifacts
WORKDIR /deps
COPY .cache/artifacts/ /deps/
COPY config/artifacts.lock.json /tmp/artifacts.lock.json
RUN python -c 'import json,hashlib,pathlib; items=json.load(open("/tmp/artifacts.lock.json")); [(None if hashlib.sha256(pathlib.Path(x["file"]).read_bytes()).hexdigest()==x["sha256"] else (_ for _ in ()).throw(ValueError(x["file"]))) for x in items]'
RUN mkdir /gravitino && tar xzf gravitino.tar.gz -C /gravitino --strip-components=1

FROM ${GO_IMAGE} AS minio-build
ENV GOTOOLCHAIN=local CGO_ENABLED=0 GOMAXPROCS=2
WORKDIR /src/minio
COPY --from=artifacts /deps/minio.tar.gz /tmp/minio.tar.gz
RUN tar xzf /tmp/minio.tar.gz --strip-components=1 && go build -trimpath -buildvcs=false -ldflags="-s -w -X github.com/minio/minio/cmd.Version=2025-09-07T16:13:09Z -X github.com/minio/minio/cmd.ReleaseTag=RELEASE.2025-09-07T16-13-09Z" -o /out/minio .
WORKDIR /src/mc
COPY --from=artifacts /deps/mc.tar.gz /tmp/mc.tar.gz
RUN tar xzf /tmp/mc.tar.gz --strip-components=1 && go build -trimpath -buildvcs=false -ldflags="-s -w -X github.com/minio/mc/cmd.Version=2025-08-13T08:35:41Z -X github.com/minio/mc/cmd.ReleaseTag=RELEASE.2025-08-13T08-35-41Z" -o /out/mc .

FROM ${PYTHON_IMAGE} AS minio
COPY --from=minio-build /out/minio /usr/local/bin/minio
COPY --from=minio-build /out/mc /usr/local/bin/mc
ENTRYPOINT ["minio"]

FROM minio AS minio-client
COPY docker/minio-init.sh /init.sh
ENTRYPOINT ["/bin/sh","/init.sh"]

FROM ${JAVA_IMAGE} AS gravitino
WORKDIR /opt/gravitino
COPY --from=artifacts /gravitino/ /opt/gravitino/
COPY --from=artifacts /deps/postgresql-*.jar /opt/gravitino/libs/
COPY --from=artifacts /deps/gravitino-iceberg-aws-bundle-*.jar /opt/gravitino/libs/
ENV JAVA_OPTS="-Xms128m -Xmx512m"
ENTRYPOINT ["/bin/bash","/opt/gravitino/bin/gravitino-iceberg-rest-server.sh","run"]

FROM ${FLINK_IMAGE} AS flink
USER root
COPY --from=artifacts /deps/flink-sql-connector-postgres-cdc-*.jar /opt/flink/lib/
COPY --from=artifacts /deps/iceberg-flink-runtime-*.jar /opt/flink/lib/
COPY --from=artifacts /deps/iceberg-aws-bundle-*.jar /opt/flink/lib/
COPY --from=artifacts /deps/hadoop-client-*.jar /opt/flink/lib/
COPY --from=artifacts /deps/commons-logging-*.jar /opt/flink/lib/
COPY --from=artifacts /deps/flink-s3-fs-hadoop-*.jar /opt/flink/plugins/s3-fs-hadoop/
COPY --from=java-build /src/flink-job/target/pipeline.jar /opt/lab/pipeline.jar
COPY docker/flink-entrypoint.sh /opt/lab/flink-entrypoint.sh
ENTRYPOINT ["/bin/bash","/opt/lab/flink-entrypoint.sh"]

FROM ${JAVA_IMAGE} AS generator
WORKDIR /app
COPY --from=java-build /src/workload-generator/target/generator.jar /app/generator.jar
ENTRYPOINT ["java","-Xmx128m","-jar","/app/generator.jar"]

FROM ${PYTHON_IMAGE} AS submitter
WORKDIR /app
COPY --from=java-build /src/flink-job/target/pipeline.jar /app/pipeline.jar
COPY scripts/submit.py /app/submit.py
ENTRYPOINT ["python","/app/submit.py"]
