package com.example.musictransposerapp.network

import com.example.musictransposerapp.data.ProcessingResponse // Import from data package
import okhttp3.MultipartBody
// RequestBody from okhttp3 is used for general request bodies,
// but for @Body with Retrofit and Gson, we pass data classes directly.
// For @Part, if sending simple string data alongside file, RequestBody.create("text/plain", ...) is used.
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*

// Request data class for process_audio endpoint
data class ProcessAudioRequest(
    val file_id: String,
    val target_key: String
)

// Response data class for upload endpoint
// Assuming the backend sends back a file_id and a message.
data class FileUploadResponse(
    val file_id: String, // Ensure this matches the JSON key from backend
    val message: String? // Optional message from backend
)

interface ApiService {
    @Multipart
    @POST("upload") // Endpoint path
    suspend fun uploadAudio(
        @Part audioFile: MultipartBody.Part
    ): Response<FileUploadResponse> // Using specific data class for response

    @POST("process_audio") // Endpoint path
    suspend fun processAudio(
        @Body requestBody: ProcessAudioRequest // Custom data class for the request body
    ): Response<ProcessingResponse> // Using ProcessingResponse from data package
}

object RetrofitClient {
    // =========================================================================================
    // IMPORTANT: BASE_URL Configuration
    // =========================================================================================
    // Replace "http://10.0.2.2:5000/" with the actual IP address or domain of your backend server.
    //
    // - If testing on an Android Emulator against a backend running on the same machine (localhost):
    //   Use "http://10.0.2.2:PORT/" (PORT is usually 5000 for the Python Flask backend).
    //
    // - If testing on a Physical Android Device against a backend on the same machine:
    //   Use "http://YOUR_MACHINE_LOCAL_IP:PORT/"
    //   Find your machine's local IP (e.g., 192.168.1.X) and ensure your device is on the
    //   same Wi-Fi network. The backend server must be configured to listen on 0.0.0.0 or this IP.
    //
    // - If the backend is deployed to a remote server:
    //   Use the server's public URL (e.g., "https://your-api-domain.com/").
    // =========================================================================================
    private const val BASE_URL = "http://10.0.2.2:5000/" // Default for emulator to localhost

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY // Logs request and response bodies, very useful for debugging.
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor) // Add logging interceptor for debugging
        // You can add other configurations like timeouts here if needed:
        // .connectTimeout(30, TimeUnit.SECONDS)
        // .readTimeout(30, TimeUnit.SECONDS)
        .build()

    val instance: ApiService by lazy {
        val retrofit = Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient) // Use the custom OkHttpClient with logging
            .addConverterFactory(GsonConverterFactory.create()) // Gson for JSON parsing
            .build()
        retrofit.create(ApiService::class.java)
    }
}
