// Dashboard JavaScript for Psychosonus
const API_URL = '/api';

// State management
let isSearching = false;
let lastQueueUpdate = 0;
let lastStatusUpdate = 0;

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
    clearQueueButton: null
};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initializeElements();
    setupEventListeners();
    startPolling();
    updateBotStatus('Connecting...', false);
});

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
    
    if (elements.clearQueueButton) {
        elements.clearQueueButton.addEventListener('click', handleClearQueue);
    }
}

function startPolling() {
    // Initial fetch
    fetchStatus();
    fetchQueue();
    
    // Set up polling intervals
    setInterval(fetchStatus, 3000);   // Poll status every 3 seconds
    setInterval(fetchQueue, 5000);    // Poll queue every 5 seconds
}

// Status Management
async function fetchStatus() {
    try {
        const response = await fetch(`${API_URL}/status`);
        const data = await response.json();
        
        if (data.success) {
            updateStatusDisplay(data);
            updateBotStatus('Online', true);
            lastStatusUpdate = Date.now();
        } else {
            showMessage('error', `Status error: ${data.error}`, 'queueMessage');
        }
    } catch (error) {
        console.error('Error fetching status:', error);
        updateBotStatus('Offline', false);
        showMessage('error', 'Connection lost', 'queueMessage');
    }
}

function updateStatusDisplay(data) {
    if (elements.connectedStatus) {
        elements.connectedStatus.textContent = data.connected ? 'Yes' : 'No';
        elements.connectedStatus.style.color = data.connected ? '#00ff88' : '#ff4444';
    }
    
    if (elements.voicePlayingStatus) {
        elements.voicePlayingStatus.textContent = data.playing ? 'Yes' : 'No';
        elements.voicePlayingStatus.style.color = data.playing ? '#00ff88' : '#ff4444';
    }
    
    if (elements.queueSize) {
        elements.queueSize.textContent = data.queue_size || '0';
    }
    
    if (elements.currentTrack) {
        if (data.current_track) {
            elements.currentTrack.innerHTML = `
                <div class="current-track-info">
                    <div class="current-track-title">${escapeHtml(data.current_track.title)}</div>
                    <div class="current-track-artist">${escapeHtml(data.current_track.artist)}</div>
                    <div class="current-track-duration">${escapeHtml(data.current_track.duration)}</div>
                </div>
            `;
        } else {
            elements.currentTrack.textContent = 'Nothing playing';
        }
    }
    
    if (elements.voiceChannel) {
        elements.voiceChannel.textContent = data.voice_channel ? `(${data.voice_channel})` : '';
    }
    
    // Update control button states
    updateControlButtons(data);
}

function updateControlButtons(data) {
    if (elements.playButton) {
        elements.playButton.disabled = !data.connected || data.playing;
        elements.playButton.style.opacity = elements.playButton.disabled ? '0.5' : '1';
    }
    
    if (elements.pauseButton) {
        elements.pauseButton.disabled = !data.playing;
        elements.pauseButton.style.opacity = elements.pauseButton.disabled ? '0.5' : '1';
    }
    
    if (elements.skipButton) {
        elements.skipButton.disabled = !data.playing;
        elements.skipButton.style.opacity = elements.skipButton.disabled ? '0.5' : '1';
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
    if (isSearching) return;
    
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
        elements.searchButton.textContent = '⏳';
    }
    
    try {
        const response = await fetch(`${API_URL}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        
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
            elements.searchButton.disabled = false;
            elements.searchButton.textContent = '🔍';
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
            <button class="add-btn" data-song='${JSON.stringify(track)}'>Add</button>
        `;
        
        const addButton = li.querySelector('.add-btn');
        addButton.addEventListener('click', (e) => {
            const songData = JSON.parse(e.target.getAttribute('data-song'));
            handleAddToQueue(songData, e.target);
        });
        
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
        
        if (!item.current) {
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
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = '...';
    
    try {
        const response = await fetch(`${API_URL}/queue/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ song: song })
        });
        
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
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = '...';
    
    try {
        const response = await fetch(`${API_URL}/queue/remove`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ index: index })
        });
        
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
    try {
        const response = await fetch(`${API_URL}/control/play`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('success', 'Started playing', 'queueMessage');
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
    try {
        const response = await fetch(`${API_URL}/control/pause`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
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

async function handleSkip() {
    try {
        const response = await fetch(`${API_URL}/control/skip`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
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
    if (!confirm('Are you sure you want to clear the entire queue?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/queue/clear`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
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

// Start connection monitoring when page loads
document.addEventListener('DOMContentLoaded', () => {
    startConnectionMonitoring();
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    stopConnectionMonitoring();
});