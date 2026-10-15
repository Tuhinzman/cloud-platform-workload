// Modified from the upstream OpenTelemetry Demo release 2.2.0.
// Change: dependencies are locked in strict mode, so every resolved configuration must match
// the committed gradle.lockfile, the file the source scan reads.
// Change: kafka-clients raised from 4.1.1 to 4.1.2, and jackson (2.21.7) and netty
// (4.2.18.Final) aligned through their BOMs, to clear the HIGH and CRITICAL findings both
// scans reported.
// Change: lz4-java, which kafka-clients 4.1.2 asks for at 1.10.1, constrained to 1.11.4 to
// clear CVE-2026-106451, a HIGH finding both scans reported.

import org.jetbrains.kotlin.gradle.tasks.KotlinCompile
import com.google.protobuf.gradle.*
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    kotlin("jvm") version "2.3.0"
    application
    id("java")
    id("idea")
    id("com.google.protobuf") version "0.9.6"
    id("com.github.johnrengelman.shadow") version "8.1.1"
}

group = "io.opentelemetry"
version = "1.0"


val grpcVersion = "1.78.0"
val protobufVersion = "4.33.2"


repositories {
    mavenCentral()
    gradlePluginPortal()
}

dependencyLocking {
    lockAllConfigurations()
    lockMode.set(LockMode.STRICT)
}



dependencies {
    implementation(platform("com.fasterxml.jackson:jackson-bom:2.21.7"))
    implementation(platform("io.netty:netty-bom:4.2.18.Final"))
    implementation("com.google.protobuf:protobuf-java:${protobufVersion}")
    testImplementation(kotlin("test"))
    implementation(kotlin("script-runtime"))
    implementation("org.apache.kafka:kafka-clients:4.1.2")
    constraints {
        implementation("at.yawk.lz4:lz4-java:1.11.4")
    }
    implementation("com.google.api.grpc:proto-google-common-protos:2.63.2")
    implementation("io.grpc:grpc-protobuf:${grpcVersion}")
    implementation("io.grpc:grpc-stub:${grpcVersion}")
    implementation("io.grpc:grpc-netty:${grpcVersion}")
    implementation("io.grpc:grpc-services:${grpcVersion}")
    implementation("io.opentelemetry:opentelemetry-api:1.57.0")
    implementation("io.opentelemetry:opentelemetry-sdk:1.57.0")
    implementation("io.opentelemetry:opentelemetry-extension-annotations:1.18.0")
    implementation("org.apache.logging.log4j:log4j-core:2.25.3")
    implementation("org.slf4j:slf4j-api:2.0.17")
    implementation("com.google.protobuf:protobuf-kotlin:${protobufVersion}")
    implementation("dev.openfeature:sdk:1.19.2")
    implementation("dev.openfeature.contrib.providers:flagd:0.11.19")

    if (JavaVersion.current().isJava9Compatible) {
        // Workaround for @javax.annotation.Generated
        // see: https://github.com/grpc/grpc-java/issues/3633
        implementation("javax.annotation:javax.annotation-api:1.3.2")
    }
}

tasks {
    shadowJar {
        mergeServiceFiles()
    }
}

tasks.test {
    useJUnitPlatform()
}

kotlin {
  compilerOptions {
    jvmTarget.set(JvmTarget.JVM_17)
  }
}

protobuf {
    protoc {
        artifact = "com.google.protobuf:protoc:${protobufVersion}"
    }
    plugins {

        id("grpc") {
            artifact = "io.grpc:protoc-gen-grpc-java:${grpcVersion}"
        }
    }
    generateProtoTasks {
        ofSourceSet("main").forEach {
            it.plugins {
                // Apply the "grpc" plugin whose spec is defined above, without
                // options. Note the braces cannot be omitted, otherwise the
                // plugin will not be added. This is because of the implicit way
                // NamedDomainObjectContainer binds the methods.
                id("grpc") { }
            }
        }
    }
}

application {
    mainClass.set("frauddetection.MainKt")
}

tasks.jar {
    manifest.attributes["Main-Class"] = "frauddetection.MainKt"
}
