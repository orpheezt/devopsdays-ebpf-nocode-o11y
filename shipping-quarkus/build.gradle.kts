plugins {
    java
    id("io.quarkus")
}

repositories {
    mavenCentral()
    mavenLocal()
}

val quarkusPlatformGroupId: String = project.property("quarkusPlatformGroupId") as String
val quarkusPlatformArtifactId: String = project.property("quarkusPlatformArtifactId") as String
val quarkusPlatformVersion: String = project.property("quarkusPlatformVersion") as String


dependencies {
    implementation(enforcedPlatform("${quarkusPlatformGroupId}:${quarkusPlatformArtifactId}:${quarkusPlatformVersion}"))
    implementation("io.quarkus:quarkus-arc")
    implementation("io.quarkus:quarkus-rest")
    testImplementation("io.quarkus:quarkus-junit")
    testImplementation("io.rest-assured:rest-assured")
}

group = "org.acme"
version = "1.0.0-SNAPSHOT"

java {
    sourceCompatibility = JavaVersion.VERSION_25
    targetCompatibility = JavaVersion.VERSION_25
}

tasks.withType<JavaCompile> {
    options.encoding = "UTF-8"
    options.compilerArgs.add("-parameters")
}

tasks.withType<io.quarkus.gradle.tasks.QuarkusDev> {
    setJvmArgs(listOf("--enable-native-access=ALL-UNNAMED"))
}

