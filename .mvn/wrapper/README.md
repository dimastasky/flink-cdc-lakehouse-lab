Maven Wrapper launcher использует официальный `maven-wrapper-3.3.4.jar` из Maven Central.
SHA-256 JAR и distribution записаны в config/artifacts.lock.json. Maven 3.9.15
проверяется wrapper через distributionSha256Sum. `mvnw` экспортирует versions.env,
чтобы Maven и Docker использовали одну матрицу. JAVA_HOME задайте на JDK17;
компилятор использует --release 17. JVM не поставляется самим wrapper.
