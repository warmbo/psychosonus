@echo off
title Sonus Bot - Installation
color 0b
cls

echo.
echo  ███████╗ ██████╗ ███╗   ██╗██╗   ██╗███████╗    ██████╗  ██████╗ ████████╗
echo  ██╔════╝██╔═══██╗████╗  ██║██║   ██║██╔════╝    ██╔══██╗██╔═══██╗╚══██╔══╝
echo  ███████╗██║   ██║██╔██╗ ██║██║   ██║███████╗    ██████╔╝██║   ██║   ██║   
echo  ╚════██║██║   ██║██║╚██╗██║██║   ██║╚════██║    ██╔══██╗██║   ██║   ██║   
echo  ███████║╚██████╔╝██║ ╚████║╚██████╔╝███████║    ██████╔╝╚██████╔╝   ██║   
echo  ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚══════╝    ╚═════╝  ╚═════╝    ╚═╝   
echo.
echo                      🎵 INSTALLATION SCRIPT
echo                      ====================
echo.

REM Check if Python is installed
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed!
    echo.
    echo Please install Python 3.8+ from: https://python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% found

REM Upgrade pip
echo.
echo [2/5] Upgrading pip...
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo ⚠️  Warning: Could not upgrade pip
) else (
    echo ✅ pip upgraded successfully
)

REM Install Python packages
echo.
echo [3/5] Installing Python packages...
echo This may take a few minutes...

python -m pip install discord.py>=2.3.0 --quiet
if errorlevel 1 (
    echo ❌ Failed to install discord.py
    goto error
)
echo ✅ discord.py installed

python -m pip install spotipy>=2.22.1 --quiet
if errorlevel 1 (
    echo ❌ Failed to install spotipy
    goto error
)
echo ✅ spotipy installed

python -m pip install flask>=2.3.0 --quiet
if errorlevel 1 (
    echo ❌ Failed to install flask
    goto error
)
echo ✅ flask installed

python -m pip install yt-dlp>=2023.7.6 --quiet
if errorlevel 1 (
    echo ❌ Failed to install yt-dlp
    goto error
)
echo ✅ yt-dlp installed

python -m pip install requests>=2.31.0 --quiet
if errorlevel 1 (
    echo ❌ Failed to install requests
    goto error
)
echo ✅ requests installed

python -m pip install PyNaCl>=1.5.0 --quiet
if errorlevel 1 (
    echo ❌ Failed to install PyNaCl
    goto error
)
echo ✅ PyNaCl installed

REM Check FFmpeg
echo.
echo [4/5] Checking FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  FFmpeg not found. Installing...
    
    REM Try winget first
    winget install FFmpeg --accept-source-agreements >nul 2>&1
    if errorlevel 1 (
        echo ❌ Could not install FFmpeg automatically
        echo.
        echo Please install FFmpeg manually:
        echo 1. Download from: https://ffmpeg.org/download.html
        echo 2. Add to system PATH
        echo.
        echo The bot will still work, but audio playback may not function.
        echo.
        set /p continue="Continue anyway? [Y/N]: "
        if /i not "%continue%"=="Y" (
            echo Installation cancelled.
            pause
            exit /b 1
        )
    ) else (
        echo ✅ FFmpeg installed via winget
    )
) else (
    echo ✅ FFmpeg already installed
)

REM Create config file if it doesn't exist
echo.
echo [5/5] Creating configuration file...
if not exist config.json (
    echo {> config.json
    echo   "discord_token": "",>> config.json
    echo   "spotify_client_id": "",>> config.json
    echo   "spotify_client_secret": "",>> config.json
    echo   "web_port": 8888>> config.json
    echo }>> config.json
    echo ✅ config.json created
) else (
    echo ✅ config.json already exists
)

REM Create run script
echo.
echo Creating run script...
echo @echo off> run.bat
echo title Sonus Bot>> run.bat
echo python bot.py>> run.bat
echo pause>> run.bat
echo ✅ run.bat created

echo.
echo 🎉 INSTALLATION COMPLETE!
echo ========================
echo.
echo Next steps:
echo 1. Edit config.json with your Discord bot token
echo 2. (Optional) Add Spotify credentials to config.json
echo 3. Run 'run.bat' or 'python bot.py' to start the bot
echo.
echo 📋 Setup guides:
echo   Discord: https://discord.com/developers/applications
echo   Spotify: https://developer.spotify.com/dashboard
echo.
echo 🌐 Web interface will be available at: http://localhost:8888
echo.
pause
exit /b 0

:error
echo.
echo ❌ Installation failed!
echo Please check your internet connection and try again.
echo.
pause
exit /b 1