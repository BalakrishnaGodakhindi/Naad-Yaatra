# Music Transposer App - Build Instructions

This document provides instructions for setting up the development environment, configuring the backend, and building the Android application.

## Prerequisites

*   **Java Development Kit (JDK):** Version 11 or higher (Android Studio often bundles its own, e.g., JDK 17 or newer).
*   **Android Studio:** Latest stable version recommended (e.g., Android Studio Iguana, Hedgehog, or newer).
*   **Python:** Version 3.8 or higher (for the backend).
*   **Pip:** Python package installer (usually comes with Python).
*   **(Optional) Git:** For cloning the repository.

## Part 1: Backend Setup (Python Flask Server)

The backend server is responsible for audio processing (note detection, key detection, transposition).

1.  **Navigate to Backend Directory:**
    Open a terminal or command prompt. Navigate to the `music_transposer_backend` directory. This directory is assumed to be a sibling to the `MusicTransposerApp` directory or at a known path.
    ```bash
    # Example: If MusicTransposerApp and music_transposer_backend are in the same parent folder
    cd ../music_transposer_backend 
    
    # Or provide the absolute or relative path if it's elsewhere
    # cd /path/to/your/project/music_transposer_backend
    ```

2.  **Create a Virtual Environment (Recommended):**
    It's best practice to use a Python virtual environment to manage dependencies for the backend.
    ```bash
    python3 -m venv venv  # Or "python -m venv venv" on some systems
    ```

3.  **Activate the Virtual Environment:**
    *   **macOS/Linux:**
        ```bash
        source venv/bin/activate
        ```
    *   **Windows (Command Prompt/PowerShell):**
        ```bash
        venv\Scripts\activate
        ```
    Your terminal prompt should change to indicate the virtual environment is active (e.g., `(venv)`).

4.  **Install Dependencies:**
    Once the virtual environment is active, install the required Python packages using the `requirements.txt` file located in the `music_transposer_backend` directory.
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: The initial automated setup for the backend in this project might have used a global pip install due to limitations of the execution environment. For end-users and manual setup, using a virtual environment as described here is strongly recommended.)*

5.  **Run the Backend Server:**
    You can run the Flask development server directly or use a production-grade server like Gunicorn.
    *   **Using Flask's built-in server (for development):**
        ```bash
        flask run --host=0.0.0.0 --port=5000
        ```
        (Ensure `app.py` is your main Flask application file, or set `FLASK_APP=your_app_file.py` environment variable).
    *   **Using Gunicorn (more robust, often used for production/testing):**
        ```bash
        gunicorn --bind 0.0.0.0:5000 app:app 
        # Assumes your Flask app instance is named 'app' in 'app.py'
        ```
    The backend server should now be running and listening on port 5000 on all available network interfaces.

## Part 2: Android App Setup (MusicTransposerApp)

1.  **Open Project in Android Studio:**
    *   Launch Android Studio.
    *   Select "Open" (or "File" > "Open...").
    *   Navigate to the `MusicTransposerApp` directory (the one containing this `BUILD_INSTRUCTIONS.md` file) and select it.
    *   Allow Android Studio to perform Gradle sync and download any necessary dependencies. This might take a few moments.

2.  **Configure Backend URL:**
    The Android app needs to know the network address of your running backend server.
    *   In Android Studio, open the file: `MusicTransposerApp/app/src/main/java/com/example/musictransposerapp/network/ApiService.kt`.
    *   Locate the `RetrofitClient` object and find the `BASE_URL` constant.
    *   **IMPORTANT: Modify `BASE_URL` based on your specific testing environment:**
        *   **Android Emulator (Backend on the same machine):** If the Python backend is running on the same computer as the Android Emulator, the emulator can access your machine's localhost via the special IP address `10.0.2.2`. So, the URL should be `http://10.0.2.2:5000/`. (This is often the default value in the provided source code).
        *   **Physical Android Device (Backend on the same Wi-Fi network):**
            1.  Find the local IP address of the machine running the Python backend (e.g., on Windows use `ipconfig`, on macOS/Linux use `ifconfig` or `ip addr`). It will likely be something like `192.168.1.X` or `10.0.0.X`.
            2.  Ensure your physical Android device is connected to the **same Wi-Fi network** as the backend machine.
            3.  Set `BASE_URL` to `http://YOUR_MACHINE_LOCAL_IP:5000/` (e.g., `http://192.168.43.101:5000/`).
            4.  Ensure your backend server (Flask/Gunicorn) is bound to `0.0.0.0` (as shown in the run commands) so it accepts connections from other devices on the network, and that your firewall is not blocking incoming connections on port 5000.
        *   **Deployed Backend:** If your backend is hosted on a remote server or cloud platform, use its public URL (e.g., `https://your-music-transposer-api.com/`).

    *   Example modification:
        ```kotlin
        // private const val BASE_URL = "http://10.0.2.2:5000/" // Default for emulator
        private const val BASE_URL = "http://192.168.1.123:5000/" // Example for physical device
        ```

## Part 3: Building and Running the Android App

1.  **Select Build Variant (Optional but Recommended):**
    *   In Android Studio, open the "Build Variants" tool window (usually found on the left sidebar or via "View" > "Tool Windows" > "Build Variants").
    *   For development and testing, select the `debug` build variant. For generating a release APK, you would select `release`.

2.  **Run on Emulator or Physical Device:**
    *   **Ensure a device is ready:**
        *   **Emulator:** Start an Android Virtual Device (AVD) from Android Studio's "Device Manager" (previously AVD Manager).
        *   **Physical Device:** Connect your Android phone/tablet to your computer via USB. Enable "Developer options" and "USB debugging" on your device. You may need to approve the computer for debugging on your device.
    *   **Select the target device:** The connected device or running emulator should appear in the toolbar at the top of Android Studio (next to the "Run 'app'" button).
    *   **Run the app:** Click the "Run 'app'" button (the green play icon ▶️) or select "Run" > "Run 'app'" from the menu. Android Studio will build the app and install it on the selected device/emulator.

3.  **Build Debug APK:**
    If you need a standalone `.apk` file for testing on other devices without installing directly from Android Studio:
    *   Select "Build" > "Build Bundle(s) / APK(s)" > "Build APK(s)".
    *   Android Studio will build the APK. A notification will appear in the "Build" output window when it's complete.
    *   Click the "locate" link in the notification to find the generated APK file. It's typically located in: `MusicTransposerApp/app/build/outputs/apk/debug/app-debug.apk`.

4.  **Build Release APK (Signed):**
    To create an APK for distribution (e.g., manual installation or for app stores that don't use App Bundles directly), you need to sign it.
    *   **Generate a Signing Key (if you don't have one):**
        1.  In Android Studio, select "Build" > "Generate Signed Bundle / APK...".
        2.  Select "APK" and click "Next".
        3.  In the "Key store path" section, click "Create new...".
        4.  Choose a path and filename for your new key store (e.g., `my-release-key.jks` in a secure location).
        5.  Enter and confirm strong passwords for the key store and the key itself.
        6.  For "Key alias", you can use a name like `releasekey`.
        7.  Fill in the certificate information (at least one field is typically required, like "First and Last Name").
        8.  Set the validity period (default is 25 years, which is usually fine).
        9.  Click "OK". **Remember your key store path, passwords, and key alias securely.** Losing this key means you cannot update your app.
    *   **Build the Signed APK:**
        1.  After creating or selecting your existing key store in the "Generate Signed Bundle / APK" dialog:
        2.  Enter the Key store password, Key alias, and Key password.
        3.  (Optional) Check "Export encrypted key for enrolling published apps in Google Play App Signing" if relevant.
        4.  Click "Next".
        5.  Choose "release" as the "Build Variant".
        6.  Select the desired Signature Versions (V1 and V2 are commonly selected for broad compatibility).
        7.  Click "Finish".
    *   The signed release APK will be generated, typically in: `MusicTransposerApp/app/release/app-release.apk` (or a similar path under `MusicTransposerApp/app/build/outputs/apk/release/`).

---

These instructions should help you get the Music Transposer App and its backend running. If you encounter issues, ensure all prerequisites are met and that Android Studio has the latest updates for its components (SDK, build tools).
```
