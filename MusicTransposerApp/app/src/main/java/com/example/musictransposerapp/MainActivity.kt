package com.example.musictransposerapp

import android.content.Context
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
// import androidx.compose.material.* // Kept for reference, but prefer Material3
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.musictransposerapp.data.Note
import com.example.musictransposerapp.data.ProcessingResponse
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.util.Log
import androidx.compose.material.icons.filled.PlayArrow
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlin.math.pow
import kotlin.math.sin
import com.example.musictransposerapp.network.ProcessAudioRequest
import com.example.musictransposerapp.network.RetrofitClient
import com.example.musictransposerapp.ui.theme.MusicTransposerAppTheme
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.io.OutputStreamWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale


class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MusicTransposerAppTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    MusicTransposerScreen()
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MusicTransposerScreen() {
    var selectedFileUri by remember { mutableStateOf<Uri?>(null) }
    var selectedFileName by remember { mutableStateOf("Selected File: None") }
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var isLoading by remember { mutableStateOf(false) }
    var processingResult by remember { mutableStateOf<ProcessingResponse?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var isPlayingPlayback by remember { mutableStateOf(false) }

    // Update displayed results based on processingResult
    // Update displayed results based on processingResult with improved formatting
    val sourceKeyText = processingResult?.detected_source_key ?: "-"
    val originalNotesFormatted = processingResult?.original_notes?.joinToString("\n") {
        "Time: ${"%.2f".format(it.time)}s, Note: ${it.note_name}, MIDI: ${it.midi_value}"
    } ?: "-"
    val transposedNotesFormatted = processingResult?.transposed_notes?.joinToString("\n") {
        "Time: ${"%.2f".format(it.time)}s, Note: ${it.note_name}, MIDI: ${it.midi_value}"
    } ?: "-"

    val clipboardManager = LocalClipboardManager.current
    val createDocumentLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.CreateDocument("text/plain"),
        onResult = { uri: Uri? ->
            uri?.let { targetUri ->
                val resultsToDownload = """
                    Detected Source Key: $sourceKeyText
                    Target Key: $targetKey
                    
                    Original Notes:
                    $originalNotesFormatted
                    
                    Transposed Notes:
                    $transposedNotesFormatted
                """.trimIndent()
                try {
                    context.contentResolver.openOutputStream(targetUri)?.use { outputStream ->
                        OutputStreamWriter(outputStream).use { writer ->
                            writer.write(resultsToDownload)
                        }
                    }
                    Toast.makeText(context, "Results saved to file", Toast.LENGTH_SHORT).show()
                } catch (e: Exception) {
                    errorMessage = "Failed to save file: ${e.message}"
                    Toast.makeText(context, "Failed to save file: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    )

    val filePickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument(),
        onResult = { uri: Uri? ->
            selectedFileUri = uri
            if (uri != null) {
                try {
                    val cursor = context.contentResolver.query(uri, null, null, null, null)
                    cursor?.use {
                        if (it.moveToFirst()) {
                            val displayNameIndex = it.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                            if (displayNameIndex != -1) {
                                selectedFileName = "Selected File: ${it.getString(displayNameIndex)}"
                            } else {
                                // Fallback if DISPLAY_NAME column is not found
                                selectedFileName = "Selected File: ${uri.lastPathSegment ?: "Unknown"}"
                            }
                        } else {
                            // Fallback if cursor is empty
                            selectedFileName = "Selected File: ${uri.lastPathSegment ?: "Unknown"}"
                        }
                    } ?: run {
                        // Fallback if cursor is null
                        selectedFileName = "Selected File: ${uri.lastPathSegment ?: "Unknown"}"
                    }
                } catch (e: Exception) {
                    // Catch any exception during query (e.g., security exception)
                    selectedFileName = "Selected File: Error getting name (${uri.lastPathSegment ?: "Unknown"})"
                    // Log.e("FilePicker", "Error getting file name", e)
                }
            } else {
                selectedFileName = "Selected File: None"
            }
        }
    )

    val musicalKeys = remember {
        listOf(
            "C Major", "C# Major", "D Major", "D# Major", "E Major", "F Major",
            "F# Major", "G Major", "G# Major", "A Major", "A# Major", "B Major",
            "C Minor", "C# Minor", "D Minor", "D# Minor", "E Minor", "F Minor",
            "F# Minor", "G Minor", "G# Minor", "A Minor", "A# Minor", "B Minor"
        )
    }
    var targetKey by remember { mutableStateOf(musicalKeys.first()) }
    var expanded by remember { mutableStateOf(false) } // For the dropdown

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(10.dp),
        horizontalAlignment = Alignment.CenterHorizontally // Center loading indicator
    ) {
        if (isLoading) {
            CircularProgressIndicator(modifier = Modifier.padding(vertical = 16.dp))
        }

        errorMessage?.let { error ->
            Text(
                text = error,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(vertical = 8.dp)
            )
        }

        Button(
            onClick = {
                filePickerLauncher.launch(arrayOf("audio/mpeg", "audio/wav", "audio/ogg", "audio/x-wav"))
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isLoading && !isPlayingPlayback // Also disable if playing
        ) {
            Text("Select Audio File")
        }

        Text(text = selectedFileName)

        Text("Select Target Key:")

        ExposedDropdownMenuBox(
            expanded = expanded,
            onExpandedChange = { if (!isLoading && !isPlayingPlayback) expanded = !expanded }, // Disable dropdown interaction during loading/playback
            modifier = Modifier.fillMaxWidth()
        ) {
            OutlinedTextField(
                value = targetKey,
                onValueChange = {}, // Not directly changeable by typing
                readOnly = true,
                label = { Text("Target Key") },
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
                modifier = Modifier
                    .menuAnchor() // Important for the dropdown to anchor correctly
                    .fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    disabledTextColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f), // Standard disabled alpha
                    disabledBorderColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.38f),
                    disabledLabelColor = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.38f),
                    focusedTextColor = MaterialTheme.colorScheme.onSurface,
                    unfocusedTextColor = MaterialTheme.colorScheme.onSurface
                ),
                enabled = !isLoading && !isPlayingPlayback // Disable field when loading/playing
            )
            ExposedDropdownMenu(
                expanded = expanded && !isLoading && !isPlayingPlayback, // Prevent opening during loading/playback
                onDismissRequest = { expanded = false }
            ) {
                musicalKeys.forEach { selectionOption ->
                    DropdownMenuItem(
                        text = { Text(selectionOption) },
                        onClick = {
                            targetKey = selectionOption
                            expanded = false
                        },
                        enabled = !isLoading && !isPlayingPlayback // Disable items during loading/playback
                    )
                }
            }
        }

        Button(
            onClick = {
                if (selectedFileUri == null) {
                    errorMessage = "Please select an audio file first." // Main error display
                    Toast.makeText(context, "Please select an audio file first.", Toast.LENGTH_SHORT).show()
                    return@Button
                }
                isLoading = true
                errorMessage = null // Clear previous errors
                processingResult = null // Clear previous results

                scope.launch {
                    try {
                        val filePart: MultipartBody.Part? = selectedFileUri?.let { uri ->
                            context.contentResolver.openInputStream(uri)?.use { inputStream ->
                                val requestFile = inputStream.readBytes()
                                    .toRequestBody("audio/*".toMediaTypeOrNull())
                                MultipartBody.Part.createFormData("audio_file", "audio_file_to_process", requestFile)
                            }
                        }

                        if (filePart == null) {
                            errorMessage = "Could not prepare file for upload. Please try again."
                            isLoading = false
                            return@launch
                        }

                        Log.d("TransposeLogic", "Uploading audio file...")
                        val uploadResponse = RetrofitClient.instance.uploadAudio(filePart)

                        if (uploadResponse.isSuccessful && uploadResponse.body() != null) {
                            val fileId = uploadResponse.body()!!.file_id
                            Log.d("TransposeLogic", "File uploaded successfully. File ID: $fileId")
                            
                            Log.d("TransposeLogic", "Processing audio with target key: $targetKey")
                            val processRequest = ProcessAudioRequest(file_id = fileId, target_key = targetKey)
                            val processResponse = RetrofitClient.instance.processAudio(processRequest)

                            if (processResponse.isSuccessful && processResponse.body() != null) {
                                Log.d("TransposeLogic", "Audio processed successfully.")
                                processingResult = processResponse.body()
                                errorMessage = null // Clear any previous error message on success
                            } else {
                                val errorBody = processResponse.errorBody()?.string() ?: "Unknown error"
                                Log.e("TransposeLogic", "Error processing audio: ${processResponse.code()} - $errorBody")
                                errorMessage = "Error processing audio: ${processResponse.message()} (Code: ${processResponse.code()}). Details: $errorBody"
                            }
                        } else {
                            val errorBody = uploadResponse.errorBody()?.string() ?: "Unknown error"
                            Log.e("TransposeLogic", "Error uploading file: ${uploadResponse.code()} - $errorBody")
                            errorMessage = "Error uploading file: ${uploadResponse.message()} (Code: ${uploadResponse.code()}). Details: $errorBody"
                        }

                    } catch (e: IOException) {
                        Log.e("TransposeLogic", "Network error", e)
                        errorMessage = "Network error: ${e.message}. Please check your connection."
                    } catch (e: Exception) {
                        Log.e("TransposeLogic", "Unexpected error", e)
                        errorMessage = "An unexpected error occurred: ${e.message}"
                    } finally {
                        isLoading = false
                    }
                }
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isLoading && !isPlayingPlayback // Also disable if playing
        ) {
            Text("Transpose Song")
        }

        Divider(modifier = Modifier.padding(vertical = 8.dp))

        Text("Results:", style = MaterialTheme.typography.headlineSmall)

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly, // Adjusted for three buttons
            verticalAlignment = Alignment.CenterVertically
        ) {
            TextButton(
                onClick = {
                    val resultsToCopy = """
                        Detected Source Key: $sourceKeyText
                        Target Key: $targetKey
                        
                        Original Notes:
                        $originalNotesFormatted
                        
                        Transposed Notes:
                        $transposedNotesFormatted
                    """.trimIndent()
                    clipboardManager.setText(AnnotatedString(resultsToCopy))
                    Toast.makeText(context, "Results copied to clipboard", Toast.LENGTH_SHORT).show()
                },
                enabled = processingResult != null && !isLoading && !isPlayingPlayback
            ) {
                Icon(Icons.Filled.ContentCopy, contentDescription = "Copy Results")
                Spacer(Modifier.size(ButtonDefaults.IconSpacing))
                Text("Copy") // Shortened for space
            }

            TextButton(
                onClick = {
                    val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
                    val suggestedFilename = "transposed_notes_$timestamp.txt"
                    createDocumentLauncher.launch(suggestedFilename)
                },
                enabled = processingResult != null && !isLoading && !isPlayingPlayback
            ) {
                Text("Download") // Shortened
            }

            TextButton(
                onClick = {
                    scope.launch {
                        isPlayingPlayback = true
                        val notesToPlay = processingResult?.transposed_notes
                        if (notesToPlay.isNullOrEmpty()) {
                            Toast.makeText(context, "No transposed notes to play.", Toast.LENGTH_SHORT).show()
                            isPlayingPlayback = false
                            return@launch
                        }

                        // Estimate durations
                        val notesWithDurations = mutableListOf<Pair<Note, Float>>()
                        for (i in notesToPlay.indices) {
                            val currentNote = notesToPlay[i]
                            val duration = if (i < notesToPlay.size - 1) {
                                (notesToPlay[i+1].time - currentNote.time).toFloat()
                            } else {
                                0.5f // Default duration for the last note
                            }
                            if (duration > 0.01f) { // Only play notes with positive, audible duration
                                notesWithDurations.add(Pair(currentNote, duration))
                            }
                        }
                        
                        if (notesWithDurations.isEmpty()){
                             Toast.makeText(context, "No valid notes to play after duration estimation.", Toast.LENGTH_SHORT).show()
                             isPlayingPlayback = false
                             return@launch
                        }

                        val sampleRate = 44100
                        val audioFormatEncoding = AudioFormat.ENCODING_PCM_16BIT
                        val channelConfig = AudioFormat.CHANNEL_OUT_MONO
                        
                        var tempErrorMessage: String? = null // For errors inside withContext

                        withContext(Dispatchers.Default) { // Audio processing off the main thread
                            val minBufferSize = AudioTrack.getMinBufferSize(sampleRate, channelConfig, audioFormatEncoding)
                            if (minBufferSize == AudioTrack.ERROR_BAD_VALUE || minBufferSize == AudioTrack.ERROR) {
                                Log.e("AudioPlayback", "Invalid AudioTrack parameters. MinBufferSize: $minBufferSize")
                                tempErrorMessage = "Could not initialize audio playback: Invalid parameters."
                                return@withContext
                            }
                            // Ensure bufferSize is not negative or zero.
                            val bufferSize = if (minBufferSize > 0) minBufferSize * 2 else sampleRate / 2 // Fallback buffer size


                            val audioTrack = try {
                                AudioTrack.Builder()
                                    .setAudioAttributes(
                                        AudioAttributes.Builder()
                                            .setUsage(AudioAttributes.USAGE_MEDIA)
                                            .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                                            .build()
                                    )
                                    .setAudioFormat(
                                        AudioFormat.Builder()
                                            .setEncoding(audioFormatEncoding)
                                            .setSampleRate(sampleRate)
                                            .setChannelMask(channelConfig)
                                            .build()
                                    )
                                    .setBufferSizeInBytes(bufferSize)
                                    .build()
                            } catch (e: Exception) {
                                Log.e("AudioPlayback", "AudioTrack.Builder failed", e)
                                tempErrorMessage = "Failed to create AudioTrack: ${e.message}"
                                null
                            }

                            if (audioTrack == null || audioTrack.state == AudioTrack.STATE_UNINITIALIZED) {
                                Log.e("AudioPlayback", "AudioTrack initialization failed. State: ${audioTrack?.state}")
                                if (tempErrorMessage == null) tempErrorMessage = "AudioTrack uninitialized."
                                return@withContext
                            }
                            
                            try {
                                audioTrack.play()
                                for ((note, durationInSeconds) in notesWithDurations) {
                                    if (!isPlayingPlayback) break 

                                    val freq = 440.0 * 2.0.pow((note.midi_value - 69.0) / 12.0)
                                    val numSamples = (durationInSeconds * sampleRate).toInt()
                                    if (numSamples <= 0) continue

                                    val pcmData = ShortArray(numSamples)
                                    for (i in 0 until numSamples) {
                                        val angle = 2.0 * Math.PI * i.toDouble() / (sampleRate.toDouble() / freq)
                                        pcmData[i] = (sin(angle) * Short.MAX_VALUE).toInt().toShort()
                                    }
                                    audioTrack.write(pcmData, 0, numSamples)
                                }
                            } catch (e: Exception) {
                                Log.e("AudioPlayback", "Error during playback loop", e)
                                tempErrorMessage = "Playback error: ${e.message}"
                            } finally {
                                try {
                                    if (audioTrack.playState == AudioTrack.PLAYSTATE_PLAYING) {
                                        audioTrack.stop()
                                    }
                                    audioTrack.release()
                                } catch (e: Exception) {
                                    Log.e("AudioPlayback", "Error releasing AudioTrack", e)
                                }
                            }
                        } // End of withContext(Dispatchers.Default)
                        
                        if (tempErrorMessage != null) {
                           errorMessage = tempErrorMessage
                           Toast.makeText(context, tempErrorMessage, Toast.LENGTH_LONG).show()
                        }
                        isPlayingPlayback = false
                    }
                },
                enabled = processingResult?.transposed_notes?.isNotEmpty() == true && !isLoading && !isPlayingPlayback
            ) {
                Icon(Icons.Filled.PlayArrow, contentDescription = "Play Transposed Notes")
                Spacer(Modifier.size(ButtonDefaults.IconSpacing))
                Text("Play") // Shortened
            }
        }

        Text("Detected Source Key:")
        Text(text = sourceKeyText, style = MaterialTheme.typography.bodyLarge)

        Spacer(modifier = Modifier.height(8.dp))

        Text("Original Notes:")
        Text(
            text = originalNotesFormatted, // Use formatted text
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 100.dp, max = 200.dp)
                .verticalScroll(rememberScrollState())
                .border(1.dp, MaterialTheme.colorScheme.outlineVariant, MaterialTheme.shapes.small)
                .padding(8.dp),
            style = MaterialTheme.typography.bodyMedium
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text("Transposed Notes:")
        Text(
            text = transposedNotesFormatted, // Use formatted text
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 100.dp, max = 200.dp)
                .verticalScroll(rememberScrollState())
                .border(1.dp, MaterialTheme.colorScheme.outlineVariant, MaterialTheme.shapes.small)
                .padding(8.dp),
            style = MaterialTheme.typography.bodyMedium
        )
    }
}

@Preview(showBackground = true)
@Composable
fun DefaultPreview() {
    MusicTransposerAppTheme {
        Surface(
            modifier = Modifier.fillMaxSize(),
            color = MaterialTheme.colorScheme.background
        ) {
            MusicTransposerScreen()
        }
    }
}

// Placeholder for the theme if not already created.
// Usually, this would be in a separate file like ui/theme/Theme.kt
// Ensure this is either moved to its own file or properly structured if kept here.
// For this exercise, it's kept here for self-containment.
/*
package com.example.musictransposerapp.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val DarkColorScheme = darkColorScheme(
    primary = Color(0xFFBB86FC), // Purple200
    secondary = Color(0xFF03DAC6), // Teal200
    tertiary = Color(0xFF3700B3), // DeepPurple
    background = Color(0xFF121212),
    surface = Color(0xFF121212),
    onPrimary = Color.Black,
    onSecondary = Color.Black,
    onTertiary = Color.White,
    onBackground = Color.White,
    onSurface = Color.White,
)

private val LightColorScheme = lightColorScheme(
    primary = Color(0xFF6200EE), // Purple500
    secondary = Color(0xFF03DAC6), // Teal200
    tertiary = Color(0xFF3700B3), // DeepPurple
    background = Color(0xFFFFFFFF),
    surface = Color(0xFFFFFFFF),
    onPrimary = Color.White,
    onSecondary = Color.Black,
    onTertiary = Color.White,
    onBackground = Color.Black,
    onSurface = Color.Black,
)

@Composable
fun MusicTransposerAppTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography, // Assuming Typography.kt exists
        content = content
    )
}

// Assuming Typography.kt exists (placeholder if not)
// Usually, this would be in a separate file like ui/theme/Typography.kt
package com.example.musictransposerapp.ui.theme // This redeclares the package, be careful

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

val Typography = Typography(
    bodyLarge = TextStyle(
        fontFamily = FontFamily.Default,
        fontWeight = FontWeight.Normal,
        fontSize = 16.sp,
        lineHeight = 24.sp,
        letterSpacing = 0.5.sp
    ),
    headlineSmall = TextStyle(
        fontFamily = FontFamily.Default,
        fontWeight = FontWeight.Bold,
        fontSize = 24.sp,
        lineHeight = 32.sp,
        letterSpacing = 0.sp
    )
    // Define other text styles as needed
)
*/
// NOTE: The Theme and Typography code was duplicated in the prompt.
// For this tool usage, I'll keep only one copy of these at the end of the file.
// In a real project, these would be in `ui/theme/Theme.kt` and `ui/theme/Typography.kt`.

package com.example.musictransposerapp.ui.theme // Final declaration for theme and typo

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp


private val DarkColorScheme = darkColorScheme(
    primary = Color(0xFFBB86FC), // Purple200
    secondary = Color(0xFF03DAC6), // Teal200
    tertiary = Color(0xFF3700B3), // DeepPurple
    background = Color(0xFF121212),
    surface = Color(0xFF121212),
    onPrimary = Color.Black,
    onSecondary = Color.Black,
    onTertiary = Color.White,
    onBackground = Color.White,
    onSurface = Color.White,
)

private val LightColorScheme = lightColorScheme(
    primary = Color(0xFF6200EE), // Purple500
    secondary = Color(0xFF03DAC6), // Teal200
    tertiary = Color(0xFF3700B3), // DeepPurple
    background = Color(0xFFFFFFFF),
    surface = Color(0xFFFFFFFF),
    onPrimary = Color.White,
    onSecondary = Color.Black,
    onTertiary = Color.White,
    onBackground = Color.Black,
    onSurface = Color.Black,
)

@Composable
fun MusicTransposerAppTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}

val Typography = Typography(
    bodyLarge = TextStyle(
        fontFamily = FontFamily.Default,
        fontWeight = FontWeight.Normal,
        fontSize = 16.sp,
        lineHeight = 24.sp,
        letterSpacing = 0.5.sp
    ),
    headlineSmall = TextStyle(
        fontFamily = FontFamily.Default,
        fontWeight = FontWeight.Bold,
        fontSize = 24.sp,
        lineHeight = 32.sp,
        letterSpacing = 0.sp
    )
)
