#!/bin/sh
# Maven Wrapper 3.3.4 launcher; distribution and wrapper are checksum-pinned.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
set -a
. "$ROOT/versions.env"
set +a
export MAVEN_USER_HOME="${MAVEN_USER_HOME:-$ROOT/.cache/maven}"
JAR="$ROOT/.mvn/wrapper/maven-wrapper.jar"
if [ ! -f "$JAR" ]; then
  echo 'Missing Maven Wrapper jar; see .mvn/wrapper/README.md' >&2; exit 1
fi
JAVA_CMD=java
if [ -n "${JAVA_HOME:-}" ]; then
  JAVA_CMD="$JAVA_HOME/bin/java"
fi
exec "$JAVA_CMD" "-Dmaven.multiModuleProjectDirectory=$ROOT" -classpath "$JAR" org.apache.maven.wrapper.MavenWrapperMain "$@"
