import os
import librosa
import crepe
import numpy as np
from music21 import stream, note, analysis, key, interval

def detect_notes(audio_path, confidence_threshold=0.8):
    """
    Detects musical notes from an audio file using CREPE.

    Args:
        audio_path (str): Path to the audio file.
        confidence_threshold (float): Minimum confidence level (0 to 1) for a note to be detected.

    Returns:
        list: A list of dictionaries, where each dictionary represents a detected note
              with 'time', 'midi_value', and 'note_name'.
    """
    try:
        # Load audio file with a 16kHz sample rate, mono
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
    except Exception as e:
        # Handle file loading errors (e.g., file not found, corrupted file)
        print(f"Error loading audio file: {e}")
        return []

    # Get time, frequency, confidence, and activation using CREPE
    # Using 'tiny' model for faster processing
    time, frequency, confidence, activation = crepe.predict(
        audio, 
        sr=16000, 
        viterbi=True, 
        model_capacity='tiny'
    )

    detected_notes = []
    last_added_midi_value = None

    for i in range(len(time)):
        if confidence[i] > confidence_threshold:
            if frequency[i] > 0:  # Check for valid frequency
                midi_note = librosa.hz_to_midi(frequency[i])
                
                # Check if midi_note is valid (not NaN or Inf)
                if np.isfinite(midi_note):
                    midi_value_rounded = int(round(midi_note))
                    
                    # Refined approach: Add note if different from the last added note's MIDI value
                    if midi_value_rounded != last_added_midi_value:
                        note_name = librosa.midi_to_note(midi_value_rounded)
                        detected_notes.append({
                            'time': float(time[i]),
                            'midi_value': midi_value_rounded,
                            'note_name': note_name
                        })
                        last_added_midi_value = midi_value_rounded
                        
    return detected_notes

def detect_key(notes_list):
    """
    Detects the musical key from a list of notes using music21.

    Args:
        notes_list (list): A list of dictionaries, where each dictionary represents a detected note
                           with 'time', 'midi_value', and 'note_name'.

    Returns:
        str: The detected key (e.g., "C major", "a minor") or a message if the key cannot be determined.
    """
    if not notes_list:
        return "Could not determine key: No notes provided."

    s = stream.Score()

    for note_info in notes_list:
        # Using midi_value directly to create a music21.note.Note object
        n = note.Note(midi=note_info['midi_value'])
        s.append(n)

    if not s.notes: # Check if the stream actually contains notes after processing
        return "Could not determine key: Stream is empty after processing notes."

    try:
        # Analyze the stream to find the key
        k = analysis.discrete.analyzeStream(s, 'key')
    except Exception as e:
        # Catch potential errors during analysis (e.g., if the stream is too sparse)
        print(f"Error during key analysis: {e}")
        return f"Could not determine key: Error during analysis ({e})."

    if k:
        return k.name
    else:
        return "Could not determine key: Analysis did not return a key."

def transpose_notes(notes_list, source_key_str, target_key_str):
    """
    Transposes a list of notes from a source key to a target key.

    Args:
        notes_list (list): List of note dictionaries (containing 'time', 'midi_value', 'note_name').
        source_key_str (str): The source key (e.g., "C major", "a minor").
        target_key_str (str): The target key (e.g., "G major", "e minor").

    Returns:
        list: A new list of transposed note dictionaries, or the original list if transposition fails.
    """
    if not notes_list:
        print("Transpose: No notes provided to transpose.")
        return notes_list

    if not source_key_str or not target_key_str:
        print("Transpose: Source or target key string is missing.")
        return notes_list

    try:
        source_key_obj = key.Key(source_key_str)
        target_key_obj = key.Key(target_key_str)
    except Exception as e:
        print(f"Transpose: Invalid key string provided: {e}. Returning original notes.")
        return notes_list

    try:
        # Calculate the interval between the tonics of the source and target keys
        transposition_interval = interval.Interval(source_key_obj.tonic, target_key_obj.tonic)
    except Exception as e:
        print(f"Transpose: Could not calculate transposition interval: {e}. Returning original notes.")
        return notes_list

    transposed_notes_list = []
    for note_data in notes_list:
        try:
            original_m21_note = note.Note(midi=note_data['midi_value'])
            transposed_m21_note = original_m21_note.transpose(transposition_interval)
            
            transposed_notes_list.append({
                'time': note_data['time'],
                'midi_value': int(transposed_m21_note.pitch.midi),
                'note_name': transposed_m21_note.nameWithOctave 
            })
        except Exception as e:
            # Log error for this specific note and potentially skip it or add original
            print(f"Error transposing note MIDI {note_data.get('midi_value', 'N/A')}: {e}")
            # Optionally, add the original note if transposition fails for it
            # transposed_notes_list.append(note_data) 
            
    return transposed_notes_list

if __name__ == '__main__':
    # This section is for testing the audio_processor.py script independently.
    # You would need an audio file (e.g., 'test_audio.wav') in the same directory 
    # or provide a full path to test this.
    
    # Create a dummy audio file for testing if one doesn't exist
    # This is a very basic sine wave and not representative of real music.
    # For actual testing, use a real audio file.
    test_audio_path = 'test_audio.wav'
    if not os.path.exists(test_audio_path):
        try:
            print(f"Creating dummy audio file: {test_audio_path}")
            sr_test = 16000
            duration_test = 3.0 # seconds
            frequency_test_a4 = 440.0 # A4
            frequency_test_c5 = 523.25 # C5
            
            # Create a sequence of two notes
            t_test = np.linspace(0, duration_test / 2, int(sr_test * duration_test / 2), endpoint=False)
            audio_segment1 = 0.5 * np.sin(2 * np.pi * frequency_test_a4 * t_test)
            audio_segment2 = 0.5 * np.sin(2 * np.pi * frequency_test_c5 * t_test)
            test_signal = np.concatenate((audio_segment1, audio_segment2))
            
            import soundfile as sf
            sf.write(test_audio_path, test_signal, sr_test)
            print(f"Dummy audio file '{test_audio_path}' created successfully.")
        except Exception as e:
            print(f"Could not create dummy audio file: {e}. Please provide a real audio file for testing.")
            test_audio_path = None # Ensure it doesn't try to process if creation failed

    if test_audio_path and os.path.exists(test_audio_path):
        print(f"\nTesting detect_notes with '{test_audio_path}':")
        notes = detect_notes(test_audio_path)
        if notes:
            print("\nDetected notes:")
            for note in notes:
                print(f"Time: {note['time']:.2f}s, MIDI: {note['midi_value']}, Note: {note['note_name']}")
        else:
            print("No notes detected or an error occurred.")
    else:
        print("\nSkipping detect_notes test as no audio file is available.")

    # Example calls
    print("\nTesting key detection:")
    source_key = detect_key(notes) # Renamed for clarity
    print(f"Detected source key: {source_key}")
    
    print("\nTesting note transposition:")
    if notes and isinstance(source_key, str) and "Could not determine key" not in source_key :
        sample_target_key = "G major" # Example target key
        print(f"Target key for transposition: {sample_target_key}")
        
        transposed_notes = transpose_notes(notes, source_key, sample_target_key)
        
        if transposed_notes and transposed_notes != notes: # Check if transposition occurred
            print("\nTransposed notes:")
            for t_note in transposed_notes:
                print(f"Time: {t_note['time']:.2f}s, MIDI: {t_note['midi_value']}, Note: {t_note['note_name']}")
        elif transposed_notes == notes:
             print("Transposition resulted in the same notes (e.g. invalid key or interval).")
        else:
            print("No notes were transposed or an error occurred during transposition.")
    else:
        if not notes:
            print("Skipping transposition test as no notes were detected.")
        else:
            print(f"Skipping transposition test as source key was not reliably determined: {source_key}")
