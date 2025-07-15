// Emergency Dashboard JavaScript

let socket;
let alerts = [];
let currentAlertId = null;
let notificationPermission = false;

// Google Maps variables
let map;
let markers = [];
let infoWindows = [];
let heatmap = null;
let heatmapData = [];
let bounds = null;

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeSocket();
    // Wait for Google Maps to load before initializing
    waitForGoogleMaps().then(() => {
        initializeMap();
    }).catch(error => {
        console.error('Failed to load Google Maps:', error);
    });
    loadData();
    updateTime();
    requestNotificationPermission();
    
    // Set up event listeners
    setupEventListeners();
    
    // Update time every second
    setInterval(updateTime, 1000);
    
    // Auto-refresh data every 30 seconds
    setInterval(loadData, 30000);
});

// Wait for Google Maps API to be fully loaded
function waitForGoogleMaps() {
    return new Promise((resolve, reject) => {
        const maxAttempts = 50; // 5 seconds max wait
        let attempts = 0;
        
        const checkGoogleMaps = () => {
            attempts++;
            
            if (typeof google !== 'undefined' && 
                google.maps && 
                google.maps.LatLngBounds && 
                google.maps.Map) {
                console.log('Google Maps API fully loaded');
                resolve();
            } else if (attempts >= maxAttempts) {
                reject(new Error('Google Maps API failed to load within timeout'));
            } else {
                setTimeout(checkGoogleMaps, 100);
            }
        };
        
        checkGoogleMaps();
    });
}

// Initialize Google Map
function initializeMap() {
    // Default center (Thailand)
    const defaultCenter = { lat: 13.7563, lng: 100.5018 };
    
    // Initialize bounds
    bounds = new google.maps.LatLngBounds();
    
    map = new google.maps.Map(document.getElementById('emergency-map'), {
        zoom: 10,
        center: defaultCenter,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        styles: [
            {
                featureType: 'poi',
                elementType: 'labels',
                stylers: [{ visibility: 'off' }]
            }
        ]
    });
    
    // Add map controls
    addMapControls();
    
    console.log('Google Map initialized');
}

// Add map controls
function addMapControls() {
    // Add legend button
    const legendButton = document.createElement('button');
    legendButton.innerHTML = '<i class="fas fa-info-circle"></i> Legend';
    legendButton.className = 'btn btn-sm btn-outline-secondary';
    legendButton.style.cssText = 'position: absolute; top: 10px; left: 10px; z-index: 1000;';
    legendButton.onclick = showMapLegend;
    
    map.controls[google.maps.ControlPosition.TOP_LEFT].push(legendButton);
}

// Show map legend
function showMapLegend() {
    const modal = new bootstrap.Modal(document.getElementById('mapLegendModal'));
    modal.show();
}

// Initialize WebSocket connection
function initializeSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to Emergency Dashboard');
        updateConnectionStatus(true);
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from Emergency Dashboard');
        updateConnectionStatus(false);
    });
    
    // Listen for all events to debug
    socket.onAny((eventName, ...args) => {
        console.log('WebSocket event received:', eventName, args);
    });
    
    socket.on('new_emergency_alert', function(alert) {
        console.log('New emergency alert received:', alert);
        handleNewAlert(alert);
    });
    
    socket.on('emergency_alert', function(alert) {
        console.log('Emergency alert received:', alert);
        handleNewAlert(alert);
    });
    
    socket.on('alert_processed', function(data) {
        console.log('Alert processed:', data);
        handleAlertProcessed(data);
    });
    
    socket.on('connected', function(data) {
        console.log('Socket connected:', data.data);
        showNotification('Connected to Emergency Dashboard', 'success');
    });
}

// Update connection status
function updateConnectionStatus(connected) {
    const statusIcon = document.getElementById('connection-status');
    const statusText = document.getElementById('connection-text');
    
    if (connected) {
        statusIcon.className = 'fas fa-circle text-success';
        statusText.textContent = 'Connected';
    } else {
        statusIcon.className = 'fas fa-circle text-danger';
        statusText.textContent = 'Disconnected';
    }
}

// Load emergency alerts data
async function loadData() {
    try {
        const timeRange = document.getElementById('time-range-filter').value;
        
        // Load alerts
        const alertsResponse = await fetch(`/api/emergency-alerts?hours=${timeRange}`);
        const alertsData = await alertsResponse.json();
        
        if (alertsData.success) {
            const previousAlertIds = new Set(alerts.map(alert => alert._id));
            const newAlerts = alertsData.alerts.filter(alert => !previousAlertIds.has(alert._id));
            
            alerts = alertsData.alerts;
            renderAlertsTable();
            if (map) {
                updateMapMarkers();
            }
            
            // Handle new alerts that weren't received via WebSocket
            newAlerts.forEach(alert => {
                console.log('New alert detected via API:', alert);
                // Only trigger alerts for unprocessed alerts
                if (!alert.processed) {
                    console.log('Unprocessed alert detected via API, showing notifications');
                    handleNewAlert(alert);
                } else {
                    console.log('Processed alert detected via API, skipping notifications');
                }
            });
        }
        
        // Load statistics
        const statsResponse = await fetch('/api/emergency-stats');
        const statsData = await statsResponse.json();
        
        if (statsData.success) {
            updateStatistics(statsData.stats);
        }
        
    } catch (error) {
        console.error('Error loading data:', error);
        showNotification('Error loading data', 'error');
    }
}

// Update map markers
function updateMapMarkers() {
    if (!map) return;
    
    // Clear existing markers
    clearMapMarkers();
    
    // Reset bounds
    bounds = new google.maps.LatLngBounds();
    
    alerts.forEach(alert => {
        const location = alert.alert_data?.location;
        if (location && location.GPS && location.GPS.latitude && location.GPS.longitude) {
            addMapMarker(alert);
        }
    });
    
    // Fit map to bounds if there are markers
    if (markers.length > 0) {
        map.fitBounds(bounds);
    }
    
    // Update heatmap
    updateHeatmap();
}

// Ensure bounds is initialized
function ensureBoundsInitialized() {
    if (!bounds || typeof bounds.extend !== 'function') {
        if (typeof google !== 'undefined' && google.maps && google.maps.LatLngBounds) {
            bounds = new google.maps.LatLngBounds();
            console.log('Bounds initialized');
        } else {
            console.warn('Google Maps not available, cannot initialize bounds');
            return false;
        }
    }
    return true;
}

// Add map marker for an alert
function addMapMarker(alert) {
    const location = alert.alert_data?.location;
    if (!location || !location.GPS) return;
    
    const position = {
        lat: parseFloat(location.GPS.latitude),
        lng: parseFloat(location.GPS.longitude)
    };
    
    // Create custom marker using standard Marker
    const marker = new google.maps.Marker({
        position: position,
        map: map,
        title: `${alert.patient_name} - ${alert.alert_type}`,
        icon: createCustomMarkerIcon(alert)
    });
    
    // Create info window
    const infoWindow = new google.maps.InfoWindow({
        content: createInfoWindowContent(alert)
    });
    
    // Add click listener
    marker.addListener('click', () => {
        // Close all other info windows
        infoWindows.forEach(iw => iw.close());
        infoWindow.open(map, marker);
    });
    
    // Store references
    markers.push(marker);
    infoWindows.push(infoWindow);
    
    // Ensure bounds is initialized and extend it
    if (ensureBoundsInitialized()) {
        bounds.extend(position);
    }
    
    // Add to heatmap data
    heatmapData.push(position);
}

// Create custom marker icon
function createCustomMarkerIcon(alert) {
    const alertType = alert.alert_type;
    const priority = alert.alert_data?.priority || 'MEDIUM';
    
    const colors = {
        'CRITICAL': '#dc3545',
        'HIGH': '#fd7e14',
        'MEDIUM': '#ffc107',
        'LOW': '#28a745'
    };
    
    const icons = {
        'sos': '📞',
        'fall_down': '👤',
        'low_battery': '🔋'
    };
    
    const color = colors[priority] || colors['MEDIUM'];
    const icon = icons[alertType] || icons['sos'];
    
    // Create SVG icon
    const svg = `
        <svg width="30" height="30" xmlns="http://www.w3.org/2000/svg">
            <circle cx="15" cy="15" r="12" fill="${color}" stroke="white" stroke-width="2"/>
            <text x="15" y="18" text-anchor="middle" fill="white" font-size="12" font-weight="bold">${icon}</text>
        </svg>
    `;
    
    return {
        url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg),
        scaledSize: new google.maps.Size(30, 30),
        anchor: new google.maps.Point(15, 15)
    };
}

// Create info window content
function createInfoWindowContent(alert) {
    const timestamp = new Date(alert.timestamp).toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZoneName: 'short'
    });
    const location = alert.alert_data?.location;
    
    let locationText = 'No location data';
    let speedText = '';
    let headingText = '';
    let accuracyText = '';
    
    if (location && location.GPS) {
        const lat = location.GPS.latitude?.toFixed(6) || 'N/A';
        const lng = location.GPS.longitude?.toFixed(6) || 'N/A';
        locationText = `${lat}, ${lng}`;
        
        if (location.GPS.speed !== undefined && location.GPS.speed !== null) {
            speedText = `<div class="location-detail"><i class="fas fa-tachometer-alt"></i> Speed: ${location.GPS.speed} km/h</div>`;
        }
        
        if (location.GPS.header !== undefined && location.GPS.header !== null) {
            headingText = `<div class="location-detail"><i class="fas fa-compass"></i> Heading: ${location.GPS.header}°</div>`;
        }
        
        if (location.GPS.accuracy !== undefined && location.GPS.accuracy !== null) {
            accuracyText = `<div class="location-detail"><i class="fas fa-crosshairs"></i> Accuracy: ${location.GPS.accuracy}m</div>`;
        }
    }
    
    const priority = alert.alert_data?.priority || 'MEDIUM';
    const priorityColors = {
        'CRITICAL': '#dc3545',
        'HIGH': '#fd7e14',
        'MEDIUM': '#ffc107',
        'LOW': '#28a745'
    };
    const priorityColor = priorityColors[priority] || '#ffc107';
    
    return `
        <div class="info-window" style="max-width: 350px;">
            <div class="info-header" style="background-color: ${priorityColor}; color: white; padding: 10px; margin: -10px -10px 10px -10px; border-radius: 5px 5px 0 0;">
                <h6 style="margin: 0; font-weight: bold;">
                    <i class="fas fa-exclamation-triangle"></i> ${alert.alert_type.toUpperCase()} ALERT
                </h6>
                <div style="font-size: 0.9em; opacity: 0.9;">${priority} Priority</div>
            </div>
            
            <div class="patient-section" style="margin-bottom: 15px;">
                <div style="font-weight: bold; color: #333; font-size: 1.1em;">
                    <i class="fas fa-user"></i> ${alert.patient_name}
                </div>
                <div style="color: #666; font-size: 0.9em;">
                    <i class="fas fa-id-card"></i> Patient ID: ${alert.patient_id}
                </div>
            </div>
            
            <div class="alert-section" style="margin-bottom: 15px;">
                <div style="font-weight: bold; color: #333; margin-bottom: 5px;">
                    <i class="fas fa-clock"></i> Alert Time
                </div>
                <div style="color: #666; font-size: 0.9em;">${timestamp}</div>
            </div>
            
            <div class="location-section" style="margin-bottom: 15px;">
                <div style="font-weight: bold; color: #333; margin-bottom: 5px;">
                    <i class="fas fa-map-marker-alt"></i> Location Details
                </div>
                <div style="color: #666; font-size: 0.9em;">
                    <div class="location-coords">📍 ${locationText}</div>
                    ${speedText}
                    ${headingText}
                    ${accuracyText}
                </div>
            </div>
            
            <div class="device-section" style="margin-bottom: 15px;">
                <div style="font-weight: bold; color: #333; margin-bottom: 5px;">
                    <i class="fas fa-mobile-alt"></i> Device Information
                </div>
                <div style="color: #666; font-size: 0.9em;">
                    <div><i class="fas fa-fingerprint"></i> IMEI: ${alert.alert_data?.imei || 'N/A'}</div>
                    <div><i class="fas fa-signal"></i> Source: ${alert.source}</div>
                </div>
            </div>
            
            <div class="status-section" style="margin-bottom: 15px;">
                <div style="font-weight: bold; color: #333; margin-bottom: 5px;">
                    <i class="fas fa-info-circle"></i> Status
                </div>
                <div style="color: #666; font-size: 0.9em;">
                    ${alert.processed ? 
                        '<span style="color: #28a745;"><i class="fas fa-check-circle"></i> Processed</span>' : 
                        '<span style="color: #fd7e14;"><i class="fas fa-clock"></i> Active - Requires Attention</span>'
                    }
                </div>
            </div>
            
            <div class="actions" style="text-align: center; border-top: 1px solid #eee; padding-top: 10px;">
                <button class="btn btn-sm btn-primary" onclick="viewAlertDetails('${alert._id}')" style="margin-right: 5px;">
                    <i class="fas fa-eye"></i> View Details
                </button>
                ${!alert.processed ? `
                    <button class="btn btn-sm btn-success" onclick="markAlertProcessed('${alert._id}')">
                        <i class="fas fa-check"></i> Mark Processed
                    </button>
                ` : ''}
            </div>
        </div>
    `;
}

// Clear map markers
function clearMapMarkers() {
    markers.forEach(marker => marker.setMap(null));
    infoWindows.forEach(infoWindow => infoWindow.close());
    markers = [];
    infoWindows = [];
    heatmapData = [];
}

// Update heatmap
function updateHeatmap() {
    if (!map || !google.maps.visualization) {
        console.log('Heatmap visualization library not available');
        return;
    }
    
    if (heatmap) {
        heatmap.setMap(null);
    }
    
    if (heatmapData.length > 0) {
        try {
            heatmap = new google.maps.visualization.HeatmapLayer({
                data: heatmapData.map(pos => new google.maps.LatLng(pos.lat, pos.lng)),
                map: map,
                radius: 50,
                opacity: 0.6
            });
        } catch (error) {
            console.log('Error creating heatmap:', error);
        }
    }
}

// Toggle heatmap
function toggleHeatmap() {
    const button = event.target.closest('button');
    if (heatmap && google.maps.visualization) {
        if (heatmap.getMap()) {
            heatmap.setMap(null);
            button.classList.remove('heatmap-active');
        } else {
            heatmap.setMap(map);
            button.classList.add('heatmap-active');
        }
    } else {
        showNotification('Heatmap feature not available', 'warning');
    }
}

// Fit map to bounds
function fitMapToBounds() {
    if (markers.length > 0) {
        map.fitBounds(bounds);
    }
}

// Center on active alerts
function centerOnActiveAlerts() {
    const activeAlerts = alerts.filter(alert => !alert.processed);
    if (activeAlerts.length > 0) {
        const activeBounds = new google.maps.LatLngBounds();
        activeAlerts.forEach(alert => {
            const location = alert.alert_data?.location;
            if (location && location.GPS) {
                activeBounds.extend({
                    lat: parseFloat(location.GPS.latitude),
                    lng: parseFloat(location.GPS.longitude)
                });
            }
        });
        map.fitBounds(activeBounds);
    }
}

// Render alerts table
function renderAlertsTable() {
    const tbody = document.getElementById('alerts-table-body');
    const countBadge = document.getElementById('alerts-count');
    
    countBadge.textContent = alerts.length;
    
    if (alerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No emergency alerts found</td></tr>';
        return;
    }
    
    tbody.innerHTML = alerts.map(alert => createAlertRow(alert)).join('');
}

// Create alert row HTML
function createAlertRow(alert) {
    const timestamp = new Date(alert.timestamp).toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short'
    });
    const alertType = getAlertTypeBadge(alert.alert_type);
    const priority = getPriorityBadge(alert.alert_data?.priority || 'MEDIUM');
    const status = getStatusBadge(alert.processed);
    const location = getLocationDisplay(alert.alert_data?.location);
    
    return `
        <tr class="${alert.processed ? '' : 'new-alert'}" data-alert-id="${alert._id}">
            <td class="time-display">${timestamp}</td>
            <td class="patient-info">${alert.patient_name || 'Unknown'}</td>
            <td>${alertType}</td>
            <td>${priority}</td>
            <td>${status}</td>
            <td class="location-info">${location}</td>
            <td>
                <button class="btn btn-sm btn-primary btn-action" onclick="viewAlertDetails('${alert._id}')">
                    <i class="fas fa-eye"></i> View
                </button>
                ${!alert.processed ? `
                    <button class="btn btn-sm btn-success btn-action" onclick="markAlertProcessed('${alert._id}')">
                        <i class="fas fa-check"></i> Process
                    </button>
                ` : ''}
            </td>
        </tr>
    `;
}

// Get alert type badge
function getAlertTypeBadge(type) {
    const icons = {
        'sos': 'fas fa-phone',
        'fall_down': 'fas fa-user-fall',
        'low_battery': 'fas fa-battery-quarter'
    };
    
    const icon = icons[type] || 'fas fa-exclamation-triangle';
    return `<span class="alert-type ${type}"><i class="${icon}"></i> ${type.replace('_', ' ').toUpperCase()}</span>`;
}

// Get priority badge
function getPriorityBadge(priority) {
    const priorityClass = `priority-${priority.toLowerCase()}`;
    const icons = {
        'CRITICAL': '🚨',
        'HIGH': '⚠️',
        'MEDIUM': '⚡',
        'LOW': 'ℹ️'
    };
    
    const icon = icons[priority] || '⚡';
    return `<span class="priority-badge ${priorityClass}">${icon} ${priority}</span>`;
}

// Get status badge
function getStatusBadge(processed) {
    if (processed) {
        return '<span class="status-badge status-processed"><i class="fas fa-check"></i> Processed</span>';
    } else {
        return '<span class="status-badge status-active"><i class="fas fa-clock"></i> Active</span>';
    }
}

// Get location display
function getLocationDisplay(location) {
    if (!location) return 'No location data';
    
    if (location.GPS) {
        const lat = location.GPS.latitude?.toFixed(6) || 'N/A';
        const lng = location.GPS.longitude?.toFixed(6) || 'N/A';
        return `<span class="location-gps"><i class="fas fa-map-marker-alt"></i> ${lat}, ${lng}</span>`;
    }
    
    if (location.WiFi) {
        return '<span class="location-info"><i class="fas fa-wifi"></i> WiFi Available</span>';
    }
    
    if (location.LBS) {
        return '<span class="location-info"><i class="fas fa-mobile-alt"></i> Cell Tower</span>';
    }
    
    return 'Location data available';
}

// Update statistics
function updateStatistics(stats) {
    document.getElementById('total-alerts').textContent = stats.total_24h;
    document.getElementById('sos-count').textContent = stats.sos_count;
    document.getElementById('fall-count').textContent = stats.fall_count;
    document.getElementById('active-count').textContent = stats.active_count;
    document.getElementById('critical-count').textContent = stats.critical_count;
    document.getElementById('high-count').textContent = stats.high_count;
}

// Handle new emergency alert
function handleNewAlert(alert) {
    console.log('handleNewAlert called with:', alert);
    
    // Add to alerts array
    alerts.unshift(alert);
    
    // Update display
    renderAlertsTable();
    loadData(); // Refresh statistics
    
    // Add marker to map if it has location and map is available
    if (alert.alert_data?.location?.GPS && map) {
        addMapMarker(alert);
        updateHeatmap();
    } else if (alert.alert_data?.location?.GPS && !map) {
        console.log('Map not available yet, marker will be added when map initializes');
    }
    
    // Only show alerts for unprocessed alerts
    if (!alert.processed) {
        console.log('Alert is unprocessed, showing emergency notifications');
        
        // Show emergency banner
        showEmergencyBanner(alert);
        
        // Play sound
        playEmergencySound();
        
        // Show notification
        const message = `${alert.alert_type.toUpperCase()} Alert for ${alert.patient_name}`;
        showNotification(message, 'emergency');
        
        // Send browser notification
        sendBrowserNotification(alert);
    } else {
        console.log('Alert is already processed, skipping emergency notifications');
    }
}

// Show emergency banner
function showEmergencyBanner(alert) {
    const banner = document.getElementById('emergency-banner');
    const message = document.getElementById('emergency-message');
    
    message.textContent = `${alert.alert_type.toUpperCase()} ALERT - ${alert.patient_name} - ${alert.alert_data?.priority || 'HIGH'} PRIORITY`;
    
    banner.style.display = 'block';
    
    // Hide after 10 seconds
    setTimeout(() => {
        banner.style.display = 'none';
    }, 10000);
}

// Play emergency sound
function playEmergencySound() {
    const audio = document.getElementById('emergency-sound');
    if (audio) {
        audio.play().catch(e => console.log('Audio play failed:', e));
    }
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <i class="fas fa-${getNotificationIcon(type)}"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Get notification icon
function getNotificationIcon(type) {
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'emergency': 'exclamation-triangle',
        'info': 'info-circle'
    };
    
    return icons[type] || 'info-circle';
}

// Send browser notification
function sendBrowserNotification(alert) {
    if (!notificationPermission) return;
    
    const title = `${alert.alert_type.toUpperCase()} Alert`;
    const body = `${alert.patient_name} - ${alert.alert_data?.priority || 'HIGH'} Priority`;
    const icon = '/static/AMY_LOGO.png';
    
    new Notification(title, {
        body: body,
        icon: icon,
        tag: 'emergency-alert',
        requireInteraction: true
    });
}

// Request notification permission
async function requestNotificationPermission() {
    if ('Notification' in window) {
        const permission = await Notification.requestPermission();
        notificationPermission = permission === 'granted';
    }
}

// View alert details
async function viewAlertDetails(alertId) {
    const alert = alerts.find(a => a._id === alertId);
    if (!alert) return;
    
    currentAlertId = alertId;
    
    const modalBody = document.getElementById('alert-modal-body');
    modalBody.innerHTML = createAlertDetailsHTML(alert);
    
    const modal = new bootstrap.Modal(document.getElementById('alertModal'));
    modal.show();
}

// Create alert details HTML
function createAlertDetailsHTML(alert) {
    const timestamp = new Date(alert.timestamp).toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZoneName: 'short'
    });
    const location = alert.alert_data?.location;
    
    return `
        <div class="alert-details">
            <h6><i class="fas fa-user"></i> Patient Information</h6>
            <p><strong>Name:</strong> ${alert.patient_name}</p>
            <p><strong>Patient ID:</strong> ${alert.patient_id}</p>
        </div>
        
        <div class="alert-details">
            <h6><i class="fas fa-exclamation-triangle"></i> Alert Information</h6>
            <p><strong>Type:</strong> ${getAlertTypeBadge(alert.alert_type)}</p>
            <p><strong>Priority:</strong> ${getPriorityBadge(alert.alert_data?.priority || 'MEDIUM')}</p>
            <p><strong>Status:</strong> ${getStatusBadge(alert.processed)}</p>
            <p><strong>Time:</strong> <span class="timestamp">${timestamp}</span></p>
        </div>
        
        ${location ? `
            <div class="alert-details">
                <h6><i class="fas fa-map-marker-alt"></i> Location Information</h6>
                ${location.GPS ? `
                    <p><strong>GPS:</strong> ${location.GPS.latitude}, ${location.GPS.longitude}</p>
                    <p><strong>Speed:</strong> ${location.GPS.speed || 'N/A'} km/h</p>
                    <p><strong>Heading:</strong> ${location.GPS.header || 'N/A'}°</p>
                ` : ''}
                ${location.WiFi ? `<p><strong>WiFi Networks:</strong> Available</p>` : ''}
                ${location.LBS ? `
                    <p><strong>Cell Tower:</strong> MCC: ${location.LBS.MCC}, MNC: ${location.LBS.MNC}</p>
                    <p><strong>LAC:</strong> ${location.LBS.LAC}, CID: ${location.LBS.CID}</p>
                ` : ''}
            </div>
        ` : ''}
        
        <div class="alert-details">
            <h6><i class="fas fa-mobile-alt"></i> Device Information</h6>
            <p><strong>IMEI:</strong> ${alert.alert_data?.imei || 'N/A'}</p>
            <p><strong>Source:</strong> ${alert.source}</p>
        </div>
    `;
}

// Mark alert as processed
async function markAlertProcessed(alertId) {
    try {
        const response = await fetch(`/api/mark-processed/${alertId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Alert marked as processed', 'success');
            loadData(); // Refresh data
        } else {
            showNotification('Error marking alert as processed', 'error');
        }
    } catch (error) {
        console.error('Error marking alert as processed:', error);
        showNotification('Error marking alert as processed', 'error');
    }
}

// Handle alert processed event
function handleAlertProcessed(data) {
    const row = document.querySelector(`tr[data-alert-id="${data.alert_id}"]`);
    if (row) {
        row.classList.remove('new-alert');
        row.querySelector('td:nth-child(5)').innerHTML = getStatusBadge(true);
        
        // Remove process button
        const processBtn = row.querySelector('.btn-success');
        if (processBtn) {
            processBtn.remove();
        }
    }
    
    // Update marker animation
    const markerIndex = markers.findIndex((_, index) => {
        const alert = alerts[index];
        return alert && alert._id === data.alert_id;
    });
    
    if (markerIndex !== -1) {
        // The AdvancedMarkerElement does not have a direct setAnimation method
        // This part of the logic needs to be re-evaluated or removed if not applicable
        // For now, we'll keep it as is, but it might not have the intended effect
        // with AdvancedMarkerElement.
    }
}

// Mark all alerts as processed
async function markAllProcessed() {
    if (!confirm('Mark all active alerts as processed?')) return;
    
    const activeAlerts = alerts.filter(alert => !alert.processed);
    
    for (const alert of activeAlerts) {
        await markAlertProcessed(alert._id);
    }
    
    showNotification(`Marked ${activeAlerts.length} alerts as processed`, 'success');
}

// Refresh data
function refreshData() {
    loadData();
    showNotification('Data refreshed', 'success');
}

// Export alerts
function exportAlerts() {
    const csvContent = generateCSV(alerts);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `emergency_alerts_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Generate CSV
function generateCSV(alerts) {
    const headers = ['Time', 'Patient Name', 'Alert Type', 'Priority', 'Status', 'Latitude', 'Longitude', 'IMEI'];
    const rows = alerts.map(alert => [
        new Date(alert.timestamp).toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            timeZoneName: 'short'
        }),
        alert.patient_name,
        alert.alert_type,
        alert.alert_data?.priority || 'MEDIUM',
        alert.processed ? 'Processed' : 'Active',
        alert.alert_data?.location?.GPS?.latitude || '',
        alert.alert_data?.location?.GPS?.longitude || '',
        alert.alert_data?.imei || ''
    ]);
    
    return [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
}

// Toggle table view
function toggleTable() {
    const container = document.getElementById('alerts-table-container');
    container.classList.toggle('table-collapsed');
}

// Update current time
function updateTime() {
    const timeElement = document.getElementById('current-time');
    timeElement.textContent = new Date().toLocaleString();
}

// Setup event listeners
function setupEventListeners() {
    // Filter event listeners
    document.getElementById('alert-type-filter').addEventListener('change', filterAlerts);
    document.getElementById('priority-filter').addEventListener('change', filterAlerts);
    document.getElementById('status-filter').addEventListener('change', filterAlerts);
    document.getElementById('time-range-filter').addEventListener('change', loadData);
    
    // Mark processed button in modal
    document.getElementById('mark-processed-btn').addEventListener('click', function() {
        if (currentAlertId) {
            markAlertProcessed(currentAlertId);
            bootstrap.Modal.getInstance(document.getElementById('alertModal')).hide();
        }
    });
}

// Filter alerts
function filterAlerts() {
    const typeFilter = document.getElementById('alert-type-filter').value;
    const priorityFilter = document.getElementById('priority-filter').value;
    const statusFilter = document.getElementById('status-filter').value;
    
    const filteredAlerts = alerts.filter(alert => {
        const typeMatch = !typeFilter || alert.alert_type === typeFilter;
        const priorityMatch = !priorityFilter || alert.alert_data?.priority === priorityFilter;
        const statusMatch = !statusFilter || 
            (statusFilter === 'active' && !alert.processed) ||
            (statusFilter === 'processed' && alert.processed);
        
        return typeMatch && priorityMatch && statusMatch;
    });
    
    renderFilteredAlerts(filteredAlerts);
    updateMapMarkersForFilteredAlerts(filteredAlerts);
}

// Render filtered alerts
function renderFilteredAlerts(filteredAlerts) {
    const tbody = document.getElementById('alerts-table-body');
    const countBadge = document.getElementById('alerts-count');
    
    countBadge.textContent = filteredAlerts.length;
    
    if (filteredAlerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No alerts match the selected filters</td></tr>';
        return;
    }
    
    tbody.innerHTML = filteredAlerts.map(alert => createAlertRow(alert)).join('');
}

// Update map markers for filtered alerts
function updateMapMarkersForFilteredAlerts(filteredAlerts) {
    // Clear existing markers
    clearMapMarkers();
    
    // Reset bounds
    bounds = new google.maps.LatLngBounds();
    
    // Add markers for filtered alerts
    filteredAlerts.forEach(alert => {
        const location = alert.alert_data?.location;
        if (location && location.GPS && location.GPS.latitude && location.GPS.longitude) {
            addMapMarker(alert);
        }
    });
    
    // Fit map to bounds if there are markers
    if (markers.length > 0) {
        map.fitBounds(bounds);
    }
    
    // Update heatmap
    updateHeatmap();
}

// Export functions for global access
window.viewAlertDetails = viewAlertDetails;
window.markAlertProcessed = markAlertProcessed;
window.refreshData = refreshData;
window.markAllProcessed = markAllProcessed;
window.exportAlerts = exportAlerts;
window.toggleTable = toggleTable;
window.fitMapToBounds = fitMapToBounds;
window.centerOnActiveAlerts = centerOnActiveAlerts;
window.toggleHeatmap = toggleHeatmap;
window.showMapLegend = showMapLegend; 