plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.example.musictransposerapp"
    compileSdk = 34 // Example SDK, can be adjusted

    defaultConfig {
        applicationId = "com.example.musictransposerapp"
        minSdk = 21
        targetSdk = 34 // Should match compileSdk
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
    kotlinOptions {
        jvmTarget = "1.8"
    }
    buildFeatures {
        compose = true
    }
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.3"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.9.0") // Example versions
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.10.0")
    // implementation("androidx.constraintlayout:constraintlayout:2.1.4") // ConstraintLayout might not be needed if UI is fully Compose

    // Jetpack Compose dependencies
    val composeVersion = "1.6.0"
    implementation("androidx.compose.ui:ui:$composeVersion")
    implementation("androidx.compose.material:material:$composeVersion") // For Material Design components (includes material-icons-core)
    implementation("androidx.compose.ui:ui-tooling-preview:$composeVersion")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0") // Lifecycle runtime for Compose
    implementation("androidx.activity:activity-compose:1.8.2") // For `setContent` in Activity
    //androidTestImplementation("androidx.compose.ui:ui-test-junit4:$composeVersion") // For UI tests
    //debugImplementation("androidx.compose.ui:ui-tooling:$composeVersion") // For UI tooling (like live previews)


    // Retrofit and OkHttp dependencies (preserved)
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.9.3")
    implementation("com.squareup.okhttp3:logging-interceptor:4.9.3")
    // Gson is implicitly included by converter-gson, but can be explicit:
    // implementation("com.google.code.gson:gson:2.8.8") 

    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
}
