package com.example.musictransposerapp.data

data class Note(
    val time: Double,
    val midi_value: Int,
    val note_name: String
)

data class ProcessingResponse(
    val original_notes: List<Note>,
    val detected_source_key: String,
    val transposed_notes: List<Note>,
    val target_key: String
)
