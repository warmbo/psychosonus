// Dashboard JavaScript for Psychosonus with Discord Auth
const API_URL = '/api';

// State management
let isSearching = false;
let lastQueueUpdate = 0;
let lastStatusUpdate = 0;
let trackStartTime = 0;
let trackDuration = 0;
let isPlaying = false;
let isPaused = false;
let isShuffleEnabled = false;
let currentUser = null;
let userHasAccess = false;

// DOM Elements
const elements = {
    // Status elements
    connectedStatus: null,
    voicePlayingStatus: null,
    botPlayingStatus: null,
    queueSize: null,
    currentTrack: null,
    voiceChannel: null,
    botStatusIndicator: null,
    botStatusText: null,
    
    // Search elements
    searchQuery: null,
    searchButton: null,
    searchMessage: null,
    searchResults: null,
    
    // Queue elements
    queueMessage: null,
    queueList: null,
    
    // Control elements
    playButton: null,
    pauseButton: null,
    skipButton: null,
    shuffleButton: null,
    clearQueueButton: null,
    leaveButton: null,
    
    // Progress elements
    currentTime: null,
    totalTime: null,
    progressFill: null,
    
    // Auth elements
    userInfo: null,
    logoutButton: null
};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initializeElements();
    setupEventListeners();
    setupLogoErrorHandling();
    checkAuthentication();
});

function checkAuthentication() {
    fetch('/api/user')
        .then(response => {
            if (response.status === 401) {
                // Not authenticated, redirect to auth
                window.location.href = '/auth';
                return;
            }
            return response.json();
        })
        .then(data => {
            if (data && data.success) {
                currentUser = data.user;
                setupAuthenticatedInterface();
                startPolling();
                updateBotStatus('Connecting...', false);
            } else {
                window.location.href = '/auth';
            }
        })
        .catch(error => {
            console.error('Auth check failed:', error);
            window.location.href = '/auth';
        });
}

function setupAuthenticatedInterface() {
    // Display user info
    if (elements.userInfo) {
        elements.userInfo.innerHTML = `
            <div class="user-profile">
                <span class="username">${escapeHtml(currentUser.username)}</span>
                <button id="logoutBtn" class="logout-btn">Logout</button>
            </div>
        `;
        
        // Setup logout button
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                if (confirm('Are you sure you want to logout?')) {
                    window.location.href = '/auth/logout';
                }
            });
        }
    }
}

function setupLogoErrorHandling() {
    const logoImg = document.getElementById('botLogo');
    if (logoImg) {
        logoImg.addEventListener('error', () => {
            logoImg.classList.add('error');
            console.log('Logo image failed to load, hiding logo');
        });
        
        logoImg.addEventListener('load', () => {
            logoImg.classList.remove('error');
            console.log('Logo image loaded successfully');
        });
    }
}

function initializeElements() {
    // Get all DOM elements
    for (const [key, _] of Object.entries(elements)) {
        const element = document.getElementById(key);
        if (element) {
            elements[key] = element;
        } else {
            console.warn(`Element not found: ${key}`);
        }
    }
}

function setupEventListeners() {
    // Search functionality
    if (elements.searchButton) {
        elements.searchButton.addEventListener('click', handleSearch);
    }
    
    if (elements.searchQuery) {
        elements.searchQuery.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !isSearching) {
                handleSearch();
            }
        });
    }
    
    // Control buttons
    if (elements.playButton) {
        elements.playButton.addEventListener('click', handlePlay);
    }
    
    if (elements.pauseButton) {
        elements.pauseButton.addEventListener('click', handlePause);
    }
    
    if (elements.skipButton) {
        elements.skipButton.addEventListener('click', handleSkip);
    }
    
    if (elements.shuffleButton) {
        elements.shuffleButton.addEventListener('click', handleShuffle);
    }
    
    if (elements.clearQueueButton) {
        elements.clearQueueButton.addEventListener('click', handleClearQueue);
    }
    
    if (elements.leaveButton) {
        elements.leaveButton.addEventListener('click', handleLeave);
    }
}

function startPolling() {
    // Initial fetch
    fetchStatus();
    fetchQueue();
    
    // Set up polling intervals
    setInterval(fetchStatus, 3000);   // Poll status every 3 seconds
    setInterval(fetchQueue, 5000);    // Poll queue every 5 seconds
    setInterval(updateProgress, 1000); // Update progress every second
}

// Status Management
async function fetchStatus() {
    try {
        const response = await fetch(`${API_URL}/status`);
        
        if (response.status === 401) {
            window.location.href = '/auth';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            updateStatusDisplay(data);
            updateBotStatus('Online', true);
            lastStatusUpdate = Date.now();
            userHasAccess = data.user_has_access;
            updateControlsAccess();
        } else {
            showMessage('error', `Status error: ${data.error}`, 'queueMessage');
        }
    } catch (error) {
        console.error('Error fetching status:', error);
        updateBotStatus('Offline', false);
        showMessage('error', 'Connection lost', 'queueMessage');
    }
}

function updateControlsAccess() {
    // Disable/enable controls based on user access
    const controlButtons = [
        elements.searchButton,
        elements.playButton,
        elements.pauseButton,
        elements.skipButton,
        elements.shuffleButton,
        elements.clearQueueButton,
        elements.leaveButton
    ];
    
    controlButtons.forEach(btn => {
        if (btn) {
            if (!userHasAccess) {
                btn.disabled = true;
                btn.title = 'You do not have access to control this server';
                btn.style.opacity = '0.3';
            }
        }
    });
    
    // Also disable search input
    if (elements.searchQuery && !userHasAccess) {
        elements.searchQuery.disabled = true;
        elements.searchQuery.placeholder = 'No access to this server';
    }
    
    // Show access message
    if (!userHasAccess) {
        showMessage('error', 'You do not have access to control this server. Bot must be in a server you\'re a member of.', 'queueMessage');
    }
}

function updateStatusDisplay(data) {
    if (elements.connectedStatus) {
        elements.connectedStatus.textContent = data.connected ? 'Yes' : 'No';
        elements.connectedStatus.style.color = data.connected ? '#00ff88' : '#ff4444';
    }

    if (elements.voicePlayingStatus) {
        const statusText = data.paused ? 'Paused' : (data.playing ? 'Yes' : 'No');
        elements.voicePlayingStatus.textContent = statusText;
        elements.voicePlayingStatus.style.color = data.playing ? '#00ff88' : (data.paused ? '#ffaa00' : '#ff4444');
    }

    if (elements.queueSize) {
        elements.queueSize.textContent = data.queue_size || '0';
    }

    // Update global state
    isPlaying = data.playing;
    isPaused = data.paused;

    // Update track info and progress
    if (data.current_track) {
        if (elements.currentTrack) {
            elements.currentTrack.innerHTML = `
                <div class="current-track-info">
                    <div class="current-track-title">${escapeHtml(data.current_track.title)}</div>
                    <div class="current-track-artist">${escapeHtml(data.current_track.artist)}</div>
                    <div class="current-track-duration">${escapeHtml(data.current_track.duration)}</div>
                </div>
            `;
        }

        // Parse duration and set track info
        const duration = data.current_track.duration;
        if (duration && duration.includes(':')) {
            const [mins, secs] = duration.split(':').map(Number);
            trackDuration = (mins * 60) + secs;
        }

        // Reset start time if track changed
        if (data.track_changed || trackStartTime === 0) {
            trackStartTime = Date.now() / 1000;
        }
    } else {
        if (elements.currentTrack) {
            elements.currentTrack.textContent = 'Nothing playing';
        }
        trackDuration = 0;
        trackStartTime = 0;
    }

    if (elements.voiceChannel) {
        const channelText = data.voice_channel ? `(${data.voice_channel})` : '';
        const guildText = data.guild_name ? ` - ${data.guild_name}` : '';
        elements.voiceChannel.textContent = channelText + guildText;
    }

    // ...removed server selection UI...

    // Update control button states
    updateControlButtons(data);
}

function updateControlButtons(data) {
    // Only update if user has access
    if (!userHasAccess) return;
    
    // Play button: Start if stopped, Resume if paused
    if (elements.playButton) {
        const canPlay = data.connected && (!data.playing || data.paused);
        elements.playButton.disabled = !canPlay;
        elements.playButton.style.opacity = elements.playButton.disabled ? '0.3' : '1';
        
        // Change button icon based on state
        if (data.paused) {
            elements.playButton.innerHTML = '<i class="fas fa-play"></i>'; // Resume icon
            elements.playButton.title = 'Resume';
        } else {
            elements.playButton.innerHTML = '<i class="fas fa-play"></i>'; // Play icon
            elements.playButton.title = 'Play';
        }
    }
    
    // Pause button: enabled when playing and not paused
    if (elements.pauseButton) {
        elements.pauseButton.disabled = !data.playing || data.paused;
        elements.pauseButton.style.opacity = elements.pauseButton.disabled ? '0.3' : '1';
    }
    
    // Skip button: enabled when playing (paused or not) or when queue has items
    if (elements.skipButton) {
        elements.skipButton.disabled = !data.connected || (!data.playing && !data.paused && data.queue_size === 0);
        elements.skipButton.style.opacity = elements.skipButton.disabled ? '0.3' : '1';
    }
    
    // Shuffle button: always enabled when connected
    if (elements.shuffleButton) {
        elements.shuffleButton.disabled = !data.connected;
        elements.shuffleButton.style.opacity = elements.shuffleButton.disabled ? '0.3' : '1';
    }
    
    // Clear button: enabled when connected and queue has items
    if (elements.clearQueueButton) {
        elements.clearQueueButton.disabled = !data.connected || data.queue_size === 0;
        elements.clearQueueButton.style.opacity = elements.clearQueueButton.disabled ? '0.3' : '1';
    }
    
    // Leave button: enabled when connected
    if (elements.leaveButton) {
        elements.leaveButton.disabled = !data.connected;
        elements.leaveButton.style.opacity = elements.leaveButton.disabled ? '0.3' : '1';
    }
}

function updateBotStatus(status, isOnline) {
    if (elements.botStatusText) {
        elements.botStatusText.textContent = status;
    }
    
    if (elements.botStatusIndicator) {
        elements.botStatusIndicator.className = `status-indicator ${isOnline ? 'online' : 'offline'}`;
    }
}

// Search functionality
async function handleSearch() {
    if (isSearching || !userHasAccess) return;
    
    const query = elements.searchQuery?.value.trim();
    if (!query) {
        showMessage('error', 'Please enter a search query', 'searchMessage');
        return;
    }
    
    isSearching = true;
    showMessage('info', 'Searching...', 'searchMessage');
    clearSearchResults();
    
    if (elements.searchButton) {
        elements.searchButton.disabled = true;
        elements.searchButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    }
    
    try {
        const response = await fetch(`${API_URL}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        
        if (response.status === 401) {
            window.location.href = '/auth';
            return;
        }
        
        if (response.status === 403) {
            showMessage('error', 'Access denied. You must be a member of the server.', 'searchMessage');
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            displaySearchResults(data.results);
            showMessage('success', `Found ${data.results.length} results`, 'searchMessage');
        } else {
            showMessage('error', `Search error: ${data.error}`, 'searchMessage');
        }
    } catch (error) {
        console.error('Search request failed:', error);
        showMessage('error', 'Search failed. Check connection.', 'searchMessage');
    } finally {
        isSearching = false;
        if (elements.searchButton) {
            elements.searchButton.disabled = !userHasAccess;
            elements.searchButton.innerHTML = '<i class="fas fa-search"></i>';
        }
    }
}

function displaySearchResults(results) {
    if (!elements.searchResults) return;
    
    elements.searchResults.innerHTML = '';
    
    results.forEach(track => {
        const li = document.createElement('li');
        li.className = 'search-result-item';
        
        const sourceIcon = track.source === 'spotify' ? '🎵' : '🎥';
        
        li.innerHTML = `
            <span class="search-result-source">${sourceIcon}</span>
            <div class="search-result-info">
                <div class="search-result-title">${escapeHtml(track.title)}</div>
                <div class="search-result-artist">${escapeHtml(track.artist)}</div>
                <div class="search-result-duration">${escapeHtml(track.duration)}</div>
            </div>
            <button class="add-btn" data-song='${JSON.stringify(track)}' ${!userHasAccess ? 'disabled' : ''}>Add</button>
        `;
        
        const addButton = li.querySelector('.add-btn');
        if (userHasAccess) {
            addButton.addEventListener('click', (e) => {
                const songData = JSON.parse(e.target.getAttribute('data-song'));
                handleAddToQueue(songData, e.target);
            });
        }
        
        elements.searchResults.appendChild(li);
    });
}

function clearSearchResults() {
    if (elements.searchResults) {
        elements.searchResults.innerHTML = '';
    }
}

// Queue Management
async function fetchQueue() {
    try {
        const response = await fetch(`${API_URL}/queue`);
        
        if (response.status === 401) {
            window.location.href = '/auth';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            displayQueue(data.queue);
            lastQueueUpdate = Date.now();
        } else {
            console.error('Queue fetch error:', data.error);
        }
    } catch (error) {
        console.error('Error fetching queue:', error);
    }
}

function displayQueue(queue) {
    if (!elements.queueList) return;
    
    elements.queueList.innerHTML = '';
    
    if (queue.length === 0) {
        const li = document.createElement('li');
        li.className = 'queue-item';
        li.innerHTML = '<div class="queue-item-info">Queue is empty</div>';
        elements.queueList.appendChild(li);
        return;
    }
    
    queue.forEach((item, index) => {
        const li = document.createElement('li');
        li.className = `queue-item ${item.current ? 'current' : ''}`;
        
        const song = item.song;
        const sourceIcon = song.source === 'spotify' ? '🎵' : '🎥';
        const prefix = item.current ? '▶️ ' : `${index}. `;
        
        li.innerHTML = `
            <span class="queue-result-source">${sourceIcon}</span>
            <div class="queue-item-info">
                <div class="queue-item-title">${prefix}${escapeHtml(song.title)}</div>
                <div class="queue-item-artist">${escapeHtml(song.artist)} • ${escapeHtml(song.duration)}</div>
            </div>
        `;
        
        if (!item.current && userHasAccess) {
            const removeButton = document.createElement('button');
            removeButton.className = 'queue-item-remove';
            removeButton.textContent = 'Remove';
            removeButton.addEventListener('click', () => {
                const queueIndex = index - queue.filter(q => q.current).length;
                handleRemoveFromQueue(queueIndex, removeButton);
            });
            li.appendChild(removeButton);
        }
        
        elements.queueList.appendChild(li);
    });
}

async function handleAddToQueue(song, button) {
    if (!userHasAccess) return;
    
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = '...';
    
    try {
        const response = await fetch(`${API_URL}/queue/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ song: song })
        });
        
        if (response.status === 401) {
            window.location.href = '/auth';
            return;
        }
        
        if (response.status === 403) {
            showMessage('error', 'Access denied', 'queueMessage');
            button.textContent = originalText;
            button.disabled = false;
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('success', `Added "${song.title}" to queue`, 'queueMessage');
            fetchQueue();
            fetchStatus();
            button.textContent = '✓';
            setTimeout(() => {
                button.textContent = originalText;
                button.disabled = false;
            }, 1500);
        } else {
            showMessage('error', `Error: ${data.error}`, 'queueMessage');
            button.textContent = originalText;
            button.disabled = false;
        }
    } catch (error) {
        console.error('Add to queue failed:', error);
        showMessage('error', 'Failed to add song', 'queueMessage');
        button.textContent = originalText;
        button.disabled = false;
    }
}

async function handleRemoveFromQueue(index, button) {
    if (!userHasAccess) return;
    
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = '...';
    
    try {
        const response = await fetch(`${API_URL}/queue/remove`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ index: index })
        });
        
        if (response.status === 401) {
            window.location.href = '/auth';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('success', 'Removed song from queue', 'queueMessage');
            fetchQueue();
        } else {
            showMessage('error', `Error: ${data.error}`, 'queueMessage');
        }
    } catch (error) {
        console.error('Remove from queue failed:', error);
        showMessage('error', 'Failed to remove song', 'queueMessage');
    } finally {
        button.textContent = originalText;
        button.disabled = false;
    }
}

// Control Functions
async function handlePlay() {
    if (!userHasAccess) return;
    
    try {
        // If paused, resume. If stopped, start playing
        const endpoint = isPaused ? '/api/control/resume' : '/api/control/play';
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.status === 401) {
            window.location.href = '/auth';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            const message = isPaused ? 'Resumed playback' : 'Started playing';
            showMessage('success', message, 'queueMessage');
            fetchQueue();
            fetchStatus();
        } else {
            showMessage('error', `Error: ${data.error}`, 'queueMessage');
        }
    } catch (error) {
        console.error('Play request failed:', error);
        showMessage('error', 'Failed to start playback', 'queueMessage');
    }
}

async function handlePause() {
    if (!userHasAccess) return;
    
    try {
        const response = await fetch(`${API_URL}/control/pause`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.status === 401) {
            window.location.href = '/auth';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('success', 'Paused playback', 'queueMessage');
            fetchStatus();
        } else {
            showMessage('error', `Error: ${data.error}`, 'queueMessage');
        }
    } catch (error) {
        console.error('Pause request failed:', error);
        showMessage('error', 'Failed to pause', 'queueMessage');
    }
}

async function handleShuffle() {
    if (!userHasAccess) return;
    
    try {
        const response = await fetch(`${API_URL}/queue/shuffle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.status === 401) {
            window.location.href = '/auth';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            isShuffleEnabled = !isShuffleEnabled;
            elements.shuffleButton.classList.toggle('active', isShuffleEnabled);
            showMessage('success', `Shuffle ${isShuffleEnabled ? 'enabled' : 'disabled'}`, 'queueMessage');
            fetchQueue();
        } else {
            showMessage('error', `Error: ${data.error}`, 'queueMessage');
        }
    } catch (error) {
        console.error('Shuffle request failed:', error);
        showMessage('error', 'Failed to shuffle', 'queueMessage');
    }
}

async function handleLeave() {
    if (!userHasAccess) return;
    
    if (!confirm('Leave the voice channel? This will stop playback.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/control/leave`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.status === 401) {
            window.location.href = '/auth';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('success', 'Left voice channel', 'queueMessage');
            fetchStatus();
            fetchQueue();
        } else {
            showMessage('error', `Error: ${data.error}`, 'queueMessage');
        }
    } catch (error) {
        console.error('Leave request failed:', error);
        showMessage('error', 'Failed to leave channel', 'queueMessage');
    }
}

async function handleSkip() {
    if (!userHasAccess) return;
    
    try {
        const response = await fetch(`${API_URL}/control/skip`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.status === 401) {
            window.location.href = '/auth';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('success', 'Skipped song', 'queueMessage');
            fetchQueue();
            fetchStatus();
        } else {
            showMessage('error', `Error: ${data.error}`, 'queueMessage');
        }
    } catch (error) {
        console.error('Skip request failed:', error);
        showMessage('error', 'Failed to skip', 'queueMessage');
    }
}

async function handleClearQueue() {
    if (!userHasAccess) return;
    
    if (!confirm('Are you sure you want to clear the entire queue?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/queue/clear`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.status === 401) {
            window.location.href = '/auth';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('success', 'Queue cleared', 'queueMessage');
            fetchQueue();
            fetchStatus();
        } else {
            showMessage('error', `Error: ${data.error}`, 'queueMessage');
        }
    } catch (error) {
        console.error('Clear queue failed:', error);
        showMessage('error', 'Failed to clear queue', 'queueMessage');
    }
}

// Progress tracking
function updateProgress() {
    if (!isPlaying || isPaused || trackDuration === 0) {
        return;
    }
    
    const currentTimeSeconds = Math.floor((Date.now() / 1000) - trackStartTime);
    const progressPercent = Math.min((currentTimeSeconds / trackDuration) * 100, 100);
    
    if (elements.currentTime) {
        elements.currentTime.textContent = formatTime(currentTimeSeconds);
    }
    
    if (elements.totalTime) {
        elements.totalTime.textContent = formatTime(trackDuration);
    }
    
    if (elements.progressFill) {
        elements.progressFill.style.width = `${progressPercent}%`;
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Utility Functions
function showMessage(type, text, elementId) {
    const messageElement = elements[elementId] || document.getElementById(elementId);
    if (!messageElement) return;
    
    messageElement.textContent = text;
    messageElement.className = `message ${type}`;
    
    // Auto-clear messages after 5 seconds
    setTimeout(() => {
        if (messageElement.textContent === text) {
            messageElement.textContent = '';
            messageElement.className = 'message';
        }
    }, 5000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Error handling for unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    showMessage('error', 'An unexpected error occurred', 'queueMessage');
});

// Connection status monitoring
let connectionCheckInterval;

function startConnectionMonitoring() {
    connectionCheckInterval = setInterval(() => {
        const timeSinceLastUpdate = Date.now() - lastStatusUpdate;
        if (timeSinceLastUpdate > 10000) { // 10 seconds without update
            updateBotStatus('Connection Lost', false);
        }
    }, 5000);
}

function stopConnectionMonitoring() {
    if (connectionCheckInterval) {
        clearInterval(connectionCheckInterval);
    }
}

// Start connection monitoring when authenticated
function startPolling() {
    // Initial fetch
    fetchStatus();
    fetchQueue();
    
    // Set up polling intervals
    setInterval(fetchStatus, 3000);   // Poll status every 3 seconds
    setInterval(fetchQueue, 5000);    // Poll queue every 5 seconds
    setInterval(updateProgress, 1000); // Update progress every second
    
    // Start connection monitoring
    startConnectionMonitoring();
}

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    stopConnectionMonitoring();
});