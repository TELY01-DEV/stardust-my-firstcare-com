// MQTT Monitor Web Application
class MQTTMonitorApp {
    constructor() {
        this.socket = null;
        this.messages = [];
        this.maxMessages = 100;
        this.stats = {
            totalMessages: 0,
            ava4Count: 0,
            katiCount: 0,
            qubeCount: 0,
            ava4Active: 0,
            katiActive: 0,
            qubeActive: 0,
            processingRate: 0
        };
        this.devices = {
            ava4: [],
            kati: [],
            qube: []
        };
        this.patients = [];
        this.userProfile = null;
        this.currentTab = 'dashboard';
        
        // Redis real-time data properties
        this.redisEvents = [];
        this.redisStats = {};
        this.redisUpdateInterval = null;
        
        this.init();
    }
    
    init() {
        this.loadUserProfile();
        this.connectWebSocket();
        this.loadInitialData();
        this.setupEventListeners();
        this.setupNavigation();
        this.startRedisRealTimeUpdates();
    }
    
    setupNavigation() {
        // Navigation is now handled by separate pages
        // This method is kept for compatibility but simplified
    }
    
    async loadUserProfile() {
        try {
            const response = await fetch('/api/user/profile');
            if (response.ok) {
                const data = await response.json();
                this.userProfile = data.data;
                this.updateUserDisplay();
            }
        } catch (error) {
            console.error('Error loading user profile:', error);
        }
    }
    
    updateUserDisplay() {
        const userNameElement = document.getElementById('user-name');
        if (this.userProfile && userNameElement) {
            userNameElement.textContent = this.userProfile.username || this.userProfile.name || 'User';
        }
    }
    
    connectWebSocket() {
        // Connect to web panel using Socket.IO
        let socketUrl = window.location.origin;
        console.log('[DEBUG] Attempting Socket.IO connection to:', socketUrl);
        this.socket = io(socketUrl);

        this.socket.on('connect', () => {
            console.log('[DEBUG] Connected to web panel via Socket.IO');
            this.updateConnectionStatus('connected');
        });
        
        this.socket.on('disconnect', () => {
            console.log('[DEBUG] Disconnected from web panel');
            this.updateConnectionStatus('disconnected');
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('[DEBUG] Socket.IO connection error:', error);
            this.updateConnectionStatus('disconnected');
        });
        
        this.socket.on('mqtt_message', (data) => {
            console.log('📡 MQTT message received via Socket.IO:', data);
            this.handleMQTTMessage(data);
        });
        
        this.socket.on('data_flow_update', (data) => {
            console.log('🎯 DATA FLOW UPDATE RECEIVED via Socket.IO:', data);
            this.handleDataFlowUpdate(data);
        });
        
        this.socket.on('statistics', (data) => {
            console.log('📊 Statistics received via Socket.IO:', data);
            this.updateStatistics(data);
        });
        
        this.socket.on('initial_data', (data) => {
            console.log('📊 Initial data received via Socket.IO:', data);
            this.handleInitialData(data);
        });
    }
    
    handleInitialData(data) {
        console.log('📊 Initial data received:', data);
        if (data.statistics) {
            this.updateStatistics(data.statistics);
        }
        if (data.devices) {
            this.devices = data.devices;
            this.updateDevicesDisplay();
        }
        if (data.patients) {
            this.patients = data.patients;
            this.updatePatientsDisplay();
        }
        
        // Handle MQTT messages for dashboard
        if (data.message_history && data.message_history.length > 0) {
            console.log('📊 Loading MQTT message history:', data.message_history.length, 'messages');
            // Clear existing messages
            this.messages = [];
            // Add historical MQTT messages
            data.message_history.forEach(message => {
                this.messages.push(message);
                this.addMessageToDisplay(message);
            });
            // Update statistics
            this.stats.totalMessages = this.messages.length;
            this.updateStatisticsDisplay();
        }
        
        // Handle data flow events for data flow pages
        if (data.flow_events && data.flow_events.length > 0) {
            console.log('📊 Loading data flow events:', data.flow_events.length, 'events');
            // Add historical flow events to data flow display
            data.flow_events.forEach(event => {
                this.updateDataFlowDisplay(event);
            });
        }
    }
    
    handleMQTTMessage(message) {
        // Add message to list for statistics
        this.messages.unshift(message);
        if (this.messages.length > this.maxMessages) {
            this.messages.pop();
        }
        
        // Update statistics
        this.stats.totalMessages++;
        this.updateStatisticsDisplay();
        
        // Update message display on dashboard
        this.addMessageToDisplay(message);
    }
    
    handleDataFlowUpdate(flowEvent) {
        console.log('🔄 handleDataFlowUpdate called with:', flowEvent);
        
        try {
            // Extract the actual event data from the wrapper
            const eventData = flowEvent.event || flowEvent;
            console.log('📊 Extracted event data:', eventData);
            
            // Update real-time data flow display
            console.log('🔄 About to call updateDataFlowDisplay...');
            this.updateDataFlowDisplay(eventData);
            console.log('✅ updateDataFlowDisplay completed');
            
            // Update step-by-step processing display
            console.log('🔄 About to call updateStepByStepProcessing...');
            this.updateStepByStepProcessing(eventData);
            console.log('✅ updateStepByStepProcessing completed');
            
            // Update statistics
            console.log('🔄 About to call updateDataFlowStatistics...');
            this.updateDataFlowStatistics(eventData);
            console.log('✅ updateDataFlowStatistics completed');
            
        } catch (error) {
            console.error('❌ Error in handleDataFlowUpdate:', error);
        }
    }
    
    updateDataFlowDisplay(flowEvent) {
        console.log('🔄 updateDataFlowDisplay called with:', flowEvent);
        
        const container = document.getElementById('data-flow-container');
        console.log('🔍 Container found:', container);
        
        if (!container) {
            // This is expected behavior on pages without data-flow-container
            console.log('ℹ️  data-flow-container not found (expected on non-data-flow pages)');
            return;
        }
        
        // Remove loading message if present
        const loadingMessage = container.querySelector('.text-center.text-muted');
        if (loadingMessage) {
            loadingMessage.remove();
        }
        
        // Create flow event element
        console.log('🛠️ Creating data flow element...');
        const eventElement = this.createDataFlowElement(flowEvent);
        console.log('✅ Event element created:', eventElement);
        
        container.insertBefore(eventElement, container.firstChild);
        console.log('✅ Event element added to container');
        
        // Limit displayed events
        const eventElements = container.querySelectorAll('.flow-step');
        if (eventElements.length > 20) {
            eventElements[eventElements.length - 1].remove();
        }
    }
    
    updateStepByStepProcessing(flowEvent) {
        const container = document.getElementById('step-processing-container');
        if (!container) return;
        
        // Remove loading message if present
        const loadingMessage = container.querySelector('.text-center.text-muted');
        if (loadingMessage) {
            loadingMessage.remove();
        }
        
        // Update or create step element
        this.updateStepElement(flowEvent);
    }
    
    createDataFlowElement(flowEvent) {
        console.log('🛠️ [DEBUG] createDataFlowElement input:', flowEvent);
        console.log('🛠️ [DEBUG] Flow event keys:', Object.keys(flowEvent));
        console.log('🛠️ [DEBUG] Flow event step:', flowEvent.step);
        console.log('🛠️ [DEBUG] Flow event device_type:', flowEvent.device_type);
        console.log('🛠️ [DEBUG] Flow event processed_data:', flowEvent.processed_data);
        console.log('🛠️ [DEBUG] Flow event patient_info:', flowEvent.patient_info);
        
        // Try to parse medical data from this event
        console.log('🛠️ [DEBUG] Attempting to parse medical data from flow event...');
        const medicalDataHtml = this.parseMedicalData(flowEvent);
        console.log('🛠️ [DEBUG] Medical data HTML result:', medicalDataHtml);
        
        const div = document.createElement('div');
        div.className = `flow-step ${flowEvent.status || ''}`;
        
        const timestamp = flowEvent.timestamp ? new Date(flowEvent.timestamp).toLocaleTimeString() : '-';
        const deviceType = flowEvent.device_type || 'Unknown';
        const deviceBadgeClass = this.getDeviceBadgeClass(deviceType);
        const statusClass = this.getStatusClass(flowEvent.status || '');
        const step = flowEvent.step || '?';
        const topic = flowEvent.topic || '-';
        const payload = flowEvent.payload ? JSON.stringify(flowEvent.payload, null, 2) : '-';
        const patientName = flowEvent.patient_info && flowEvent.patient_info.patient_name ? flowEvent.patient_info.patient_name : '-';
        const error = flowEvent.error || '';
        
        // Check if this is a FHIR R5 step
        const isFhirStep = step === '6_fhir_r5_stored' || step === 'fhir_r5_store';
        const fhirCondition = isFhirStep ? `
            <div class="mb-2">
                <span class="badge bg-info text-white me-2">
                    <i class="ti ti-info-circle me-1"></i>
                    Condition: Only for Patient Resource Data
                </span>
            </div>
        ` : '';
        
        div.innerHTML = `
            <div class="d-flex align-items-start">
                <span class="step-indicator ${statusClass}">${this.getStepNumber(step)}</span>
                <div class="flex-grow-1">
                    <div class="d-flex align-items-center mb-2">
                        <span class="badge ${deviceBadgeClass} device-badge me-2">${deviceType}</span>
                        <strong class="me-2">${this.getStepTitle(step)}</strong>
                        <span class="badge ${statusClass} status-badge me-2">${flowEvent.status || '-'}</span>
                        <small class="text-muted">${timestamp}</small>
                    </div>
                    ${fhirCondition}
                    <div class="mb-2">
                        <strong>Topic:</strong> ${topic}
                    </div>
                    ${flowEvent.patient_info ? `
                        <div class="mb-2">
                            <strong>Patient:</strong> ${patientName}
                        </div>
                    ` : ''}
                    ${error ? `
                        <div class="mb-2 text-danger">
                            <strong>Error:</strong> ${error}
                        </div>
                    ` : ''}
                    <div class="mb-2">
                        <strong>Medical Data:</strong>
                        <div class="medical-data-display">
                            ${medicalDataHtml}
                        </div>
                    </div>
                    <div class="payload-display">
                        <strong>Payload:</strong>
                        <pre>${payload}</pre>
                    </div>
                </div>
            </div>
        `;
        
        return div;
    }
    
    updateStepElement(flowEvent) {
        const stepId = `step-${flowEvent.step}`;
        let stepElement = document.getElementById(stepId);
        
        if (!stepElement) {
            stepElement = this.createStepElement(flowEvent);
            const container = document.getElementById('step-processing-container');
            if (container) {
                container.appendChild(stepElement);
            }
        } else {
            this.updateStepContent(stepElement, flowEvent);
        }
    }
    
    createStepElement(flowEvent) {
        const div = document.createElement('div');
        div.id = `step-${flowEvent.step}`;
        div.className = `timeline-item ${flowEvent.status}`;
        
        const deviceBadgeClass = this.getDeviceBadgeClass(flowEvent.device_type);
        const statusClass = this.getStatusClass(flowEvent.status);
        
        // Check if this is a FHIR R5 step
        const isFhirStep = flowEvent.step === '6_fhir_r5_stored' || flowEvent.step === 'fhir_r5_store';
        const fhirCondition = isFhirStep ? `
            <div class="mb-2">
                <span class="badge bg-info text-white">
                    <i class="ti ti-info-circle me-1"></i>
                    Condition: Only for Patient Resource Data
                </span>
            </div>
        ` : '';
        
        div.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <div class="d-flex align-items-center">
                        <span class="badge ${deviceBadgeClass} device-badge me-2">${flowEvent.device_type}</span>
                        <h4 class="card-title mb-0">${this.getStepTitle(flowEvent.step)}</h4>
                        <span class="badge ${statusClass} status-badge ms-auto">${flowEvent.status}</span>
                    </div>
                </div>
                <div class="card-body">
                    ${fhirCondition}
                    <div class="mb-2">
                        <strong>Topic:</strong> ${flowEvent.topic}
                    </div>
                    ${flowEvent.patient_info ? `
                        <div class="mb-2">
                            <strong>Patient:</strong> ${flowEvent.patient_info.patient_name || 'Unknown'}
                        </div>
                    ` : ''}
                    ${flowEvent.error ? `
                        <div class="mb-2 text-danger">
                            <strong>Error:</strong> ${flowEvent.error}
                        </div>
                    ` : ''}
                    <div class="payload-display">
                        <strong>Payload:</strong>
                        <pre>${JSON.stringify(flowEvent.payload, null, 2)}</pre>
                    </div>
                </div>
            </div>
        `;
        
        return div;
    }
    
    updateStepContent(stepElement, flowEvent) {
        const statusClass = this.getStatusClass(flowEvent.status);
        const statusBadge = stepElement.querySelector('.status-badge');
        if (statusBadge) {
            statusBadge.className = `badge ${statusClass} status-badge ms-auto`;
            statusBadge.textContent = flowEvent.status;
        }
        
        stepElement.className = `timeline-item ${flowEvent.status}`;
    }
    
    getStepNumber(step) {
        const stepMap = {
            '1_mqtt_received': '1',
            '2_payload_parsed': '2', 
            '3_patient_lookup': '2',
            '4_patient_updated': '3',
            '5_medical_stored': '3',
            '6_fhir_r5_stored': '4',
            'mqtt_payload': '1',
            'parser': '2',
            'database_store': '3',
            'fhir_r5_store': '4'
        };
        return stepMap[step] || '?';
    }
    
    getStepTitle(step) {
        const stepMap = {
            '1_mqtt_received': 'MQTT Payload',
            '2_payload_parsed': 'Parser',
            '3_patient_lookup': 'Parser',
            '4_patient_updated': 'Database Store',
            '5_medical_stored': 'Database Store',
            '6_fhir_r5_stored': 'FHIR R5 Resource Data Store',
            'mqtt_payload': 'MQTT Payload',
            'parser': 'Parser',
            'database_store': 'Database Store',
            'fhir_r5_store': 'FHIR R5 Resource Data Store'
        };
        return stepMap[step] || step;
    }
    
    getStatusClass(status) {
        switch (status) {
            case 'success': return 'step-success';
            case 'error': return 'step-error';
            case 'processing': return 'step-processing';
            default: return 'step-pending';
        }
    }
    
    updateDataFlowStatistics(flowEvent) {
        // Update device-specific statistics
        if (flowEvent.device_type === 'AVA4') {
            this.stats.ava4Count = (this.stats.ava4Count || 0) + 1;
        } else if (flowEvent.device_type === 'Kati') {
            this.stats.katiCount = (this.stats.katiCount || 0) + 1;
        } else if (flowEvent.device_type === 'Qube') {
            this.stats.qubeCount = (this.stats.qubeCount || 0) + 1;
        }
        
        // Update total messages
        this.stats.totalMessages = (this.stats.totalMessages || 0) + 1;
        
        // Update successful/failed flows
        if (flowEvent.status === 'success') {
            this.stats.successfulFlows = (this.stats.successfulFlows || 0) + 1;
        } else if (flowEvent.status === 'error') {
            this.stats.failedFlows = (this.stats.failedFlows || 0) + 1;
        }
        
        this.updateStatisticsDisplay();
    }
    
    addMessageToDisplay(message) {
        const container = document.getElementById('messages-container');
        if (!container) return;
        
        // Remove loading message if present
        const loadingMessage = container.querySelector('.text-center.text-muted');
        if (loadingMessage) {
            loadingMessage.remove();
        }
        
        const messageElement = this.createMessageElement(message);
        container.insertBefore(messageElement, container.firstChild);
        
        // Limit displayed messages
        const messageElements = container.querySelectorAll('.message-card');
        if (messageElements.length > this.maxMessages) {
            messageElements[messageElements.length - 1].remove();
        }
    }
    
    createMessageElement(message) {
        const div = document.createElement('div');
        div.className = 'card message-card mb-2';
        
        const timestamp = new Date(message.timestamp).toLocaleTimeString();
        const deviceType = this.getDeviceType(message.topic);
        const deviceBadgeClass = this.getDeviceBadgeClass(deviceType);
        
        div.innerHTML = `
            <div class="card-body p-3">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="d-flex align-items-center mb-1">
                            <span class="badge ${deviceBadgeClass} device-badge me-2">${deviceType}</span>
                            <strong class="me-2">${message.topic}</strong>
                            <small class="text-muted message-timestamp">${timestamp}</small>
                        </div>
                        <div class="message-content">
                            <pre class="mb-0" style="font-size: 0.875rem; max-height: 100px; overflow-y: auto;">${JSON.stringify(message.payload, null, 2)}</pre>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        return div;
    }
    
    getDeviceType(topic) {
        if (topic.includes('ESP32_BLE_GW_TX') || topic.includes('dusun_sub')) {
            return 'AVA4';
        } else if (topic.includes('iMEDE_watch')) {
            return 'Kati';
        } else if (topic.includes('CM4_BLE_GW_TX')) {
            return 'Qube';
        }
        return 'Unknown';
    }
    
    getDeviceBadgeClass(deviceType) {
        switch (deviceType) {
            case 'AVA4': return 'bg-success';
            case 'Kati': return 'bg-info';
            case 'Qube': return 'bg-warning';
            default: return 'bg-secondary';
        }
    }
    
    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connection-status');
        const textElement = document.getElementById('connection-text');
        
        if (statusElement && textElement) {
            statusElement.className = `connection-indicator connection-${status}`;
            
            switch (status) {
                case 'connected':
                    textElement.textContent = 'Connected';
                    break;
                case 'connecting':
                    textElement.textContent = 'Connecting...';
                    break;
                case 'disconnected':
                    textElement.textContent = 'Disconnected';
                    break;
            }
        }
    }
    
    async loadInitialData() {
        await Promise.all([
            this.loadStatistics(),
            this.loadDevices(),
            this.loadPatients()
        ]);
    }
    
    async loadStatistics() {
        try {
            const response = await fetch('/api/statistics');
            if (response.ok) {
                const data = await response.json();
                this.updateStatistics(data.data);
            }
        } catch (error) {
            console.error('Error loading statistics:', error);
        }
    }
    
    async loadDevices() {
        try {
            const response = await fetch('/api/devices');
            if (response.ok) {
                const data = await response.json();
                this.devices = data.data;
                this.updateDevicesDisplay();
                this.updateDevicesTables();
            }
        } catch (error) {
            console.error('Error loading devices:', error);
        }
    }
    
    async loadPatients() {
        try {
            const response = await fetch('/api/patients');
            if (response.ok) {
                const data = await response.json();
                this.patients = data.data;
                this.updatePatientsDisplay();
                this.updatePatientsTable();
            }
        } catch (error) {
            console.error('Error loading patients:', error);
        }
    }
    
    updateStatistics(stats) {
        this.stats = { ...this.stats, ...stats };
        this.updateStatisticsDisplay();
    }
    
    updateStatisticsDisplay() {
        // Update statistics cards with null checks
        const elements = {
            'total-messages': this.stats.totalMessages || 0,
            'processing-rate': this.stats.processingRate || 0,
            'ava4-count': this.stats.ava4Count || 0,
            'ava4-active': this.stats.ava4Active || 0,
            'kati-count': this.stats.katiCount || 0,
            'kati-active': this.stats.katiActive || 0,
            'qube-count': this.stats.qubeCount || 0,
            'qube-active': this.stats.qubeActive || 0,
            // Data Flow page specific statistics
            'ava4-messages': this.stats.ava4Count || 0,
            'kati-messages': this.stats.katiCount || 0,
            'qube-messages': this.stats.qubeCount || 0,
            'successful-flows': this.stats.successfulFlows || 0,
            'failed-flows': this.stats.failedFlows || 0,
            // Data Flow Monitor page elements
            'total-events': this.stats.totalMessages || 0,
            'processing-rate': this.stats.processingRate || 0,
            'success-rate': this.calculateSuccessRate(),
            'error-rate': this.calculateErrorRate(),
            'active-devices': this.calculateActiveDevices(),
            'last-activity': this.getLastActivity(),
            'avg-processing-time': this.stats.avgProcessingTime || '0ms',
            'peak-time': this.stats.peakProcessingTime || '0ms'
        };
        
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }
    
    calculateSuccessRate() {
        const total = this.stats.totalMessages || 0;
        const successful = this.stats.successfulFlows || 0;
        return total > 0 ? Math.round((successful / total) * 100) + '%' : '0%';
    }
    
    calculateErrorRate() {
        const total = this.stats.totalMessages || 0;
        const failed = this.stats.failedFlows || 0;
        return total > 0 ? Math.round((failed / total) * 100) + '%' : '0%';
    }
    
    calculateActiveDevices() {
        let active = 0;
        if (this.stats.ava4Active) active++;
        if (this.stats.katiActive) active++;
        if (this.stats.qubeActive) active++;
        return active;
    }
    
    getLastActivity() {
        // For now, return a simple timestamp
        return this.stats.lastActivity || 'Never';
    }
    
    updateDevicesDisplay() {
        const container = document.getElementById('devices-container');
        if (!container) return;
        
        const ava4Count = this.devices.ava4?.length || 0;
        const katiCount = this.devices.kati?.length || 0;
        const qubeCount = this.devices.qube?.length || 0;
        
        container.innerHTML = `
            <div class="row">
                <div class="col-md-4">
                    <div class="card bg-success text-white">
                        <div class="card-body text-center">
                            <i class="ti ti-devices mb-2" style="font-size: 2rem;"></i>
                            <h3>${ava4Count}</h3>
                            <div class="text-white-50">AVA4 Devices</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card bg-info text-white">
                        <div class="card-body text-center">
                            <i class="ti ti-watch mb-2" style="font-size: 2rem;"></i>
                            <h3>${katiCount}</h3>
                            <div class="text-white-50">Kati Watches</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card bg-warning text-white">
                        <div class="card-body text-center">
                            <i class="ti ti-hospital mb-2" style="font-size: 2rem;"></i>
                            <h3>${qubeCount}</h3>
                            <div class="text-white-50">Qube-Vital</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    updateDevicesTables() {
        this.updateAva4DevicesTable();
        this.updateKatiDevicesTable();
        this.updateQubeDevicesTable();
    }
    
    updateAva4DevicesTable() {
        const container = document.getElementById('ava4-devices-table');
        if (!container) return;
        
        const devices = this.devices.ava4 || [];
        
        if (devices.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="ti ti-devices-off" style="font-size: 2rem;"></i>
                    <p class="mt-2">No AVA4 devices found</p>
                </div>
            `;
            return;
        }
        
        const tableHtml = `
            <div class="table-responsive">
                <table class="table table-vcenter transaction-table">
                    <thead>
                        <tr>
                            <th>MAC Address</th>
                            <th>Name</th>
                            <th>Patient ID</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${devices.map(device => `
                            <tr>
                                <td><code>${device.mac_address || 'N/A'}</code></td>
                                <td>${device.name || 'Unknown'}</td>
                                <td>${device.patient_id || 'Not Mapped'}</td>
                                <td><span class="badge bg-success">Active</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = tableHtml;
    }
    
    updateKatiDevicesTable() {
        const container = document.getElementById('kati-devices-table');
        if (!container) return;
        
        const devices = this.devices.kati || [];
        
        if (devices.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="ti ti-watch-off" style="font-size: 2rem;"></i>
                    <p class="mt-2">No Kati watches found</p>
                </div>
            `;
            return;
        }
        
        const tableHtml = `
            <div class="table-responsive">
                <table class="table table-vcenter transaction-table">
                    <thead>
                        <tr>
                            <th>IMEI</th>
                            <th>Patient ID</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${devices.map(device => `
                            <tr>
                                <td><code>${device.imei || 'N/A'}</code></td>
                                <td>${device.patient_id || 'Not Mapped'}</td>
                                <td><span class="badge bg-info">Active</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = tableHtml;
    }
    
    updateQubeDevicesTable() {
        const container = document.getElementById('qube-devices-table');
        if (!container) return;
        
        const qubeDevices = this.devices.qube;
        
        if (qubeDevices.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="ti ti-devices-off" style="font-size: 2rem;"></i>
                    <p class="mt-2">No Qube-Vital devices found</p>
                </div>
            `;
            return;
        }
        
        const tableHtml = `
            <div class="table-responsive">
                <table class="table table-vcenter">
                    <thead>
                        <tr>
                            <th>Device ID</th>
                            <th>Topic</th>
                            <th>Last Seen</th>
                            <th>Status</th>
                            <th>Patient</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${qubeDevices.map(device => {
                            const lastSeen = new Date(device.last_seen).toLocaleString();
                            const statusClass = device.status === 'active' ? 'bg-success' : 'bg-secondary';
                            
                            return `
                                <tr>
                                    <td><code>${device.device_id}</code></td>
                                    <td><code>${device.topic}</code></td>
                                    <td>${lastSeen}</td>
                                    <td><span class="badge ${statusClass}">${device.status}</span></td>
                                    <td>${device.patient_name || 'Not Mapped'}</td>
                            </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = tableHtml;
    }
    
    parseMedicalData(message) {
        console.log('🔍 === MEDICAL DATA PARSING DEBUG ===');
        console.log('📋 Full message object:', message);
        console.log('📋 Message keys:', Object.keys(message));
        console.log('📋 Message type:', typeof message);
        
        // Check for medical_data field
        console.log('💊 Medical data field:', message.medical_data);
        console.log('💊 Medical data type:', typeof message.medical_data);
        
        // Check for processed_data field (alternative location)
        console.log('📊 Processed data field:', message.processed_data);
        console.log('📊 Processed data type:', typeof message.processed_data);
        
        // Check for payload field
        console.log('📦 Payload field:', message.payload);
        console.log('📦 Payload type:', typeof message.payload);
        
        // Check for device_type field
        console.log('📱 Device type field:', message.device_type);
        console.log('📱 Device type type:', typeof message.device_type);
        
        // Check for topic field
        console.log('📡 Topic field:', message.topic);
        console.log('📡 Topic type:', typeof message.topic);
        
        // Check for step field
        console.log('🔄 Step field:', message.step);
        console.log('🔄 Step type:', typeof message.step);
        
        // Check for status field
        console.log('✅ Status field:', message.status);
        console.log('✅ Status type:', typeof message.status);
        
        // Check for patient_info field
        console.log('👤 Patient info field:', message.patient_info);
        console.log('👤 Patient info type:', typeof message.patient_info);
        
        // Check for error field
        console.log('❌ Error field:', message.error);
        console.log('❌ Error type:', typeof message.error);
        
        console.log('🔍 === END DEBUG ===');
        
        // Try to find medical data in different possible locations
        let medicalData = null;
        let dataSource = 'unknown';
        
        if (message.medical_data) {
            medicalData = message.medical_data;
            dataSource = 'medical_data';
        } else if (message.processed_data) {
            medicalData = message.processed_data;
            dataSource = 'processed_data';
        } else if (message.payload && typeof message.payload === 'object') {
            // Check if payload contains medical data
            if (message.payload.data) {
                medicalData = message.payload.data;
                dataSource = 'payload.data';
            } else if (message.payload.value) {
                medicalData = message.payload.value;
                dataSource = 'payload.value';
            } else {
                medicalData = message.payload;
                dataSource = 'payload';
            }
        }
        
        console.log(`💊 Found medical data in: ${dataSource}`);
        console.log(`💊 Medical data content:`, medicalData);
        
        if (!medicalData) {
            console.log('❌ No medical data found in any location');
            return '<span class="text-muted">No Data</span>';
        }
        
        const deviceType = message.device_type || this.getDeviceType(message.topic);
        
        console.log('📱 Device type:', deviceType);
        console.log('💊 Medical data structure:', medicalData);
        
        if (deviceType === 'AVA4') {
            return this.parseAva4MedicalData(medicalData);
        } else if (deviceType === 'Kati' || deviceType === 'Kati Watch') {
            return this.parseKatiMedicalData(medicalData);
        } else if (deviceType === 'Qube' || deviceType === 'Qube-Vital') {
            return this.parseQubeMedicalData(medicalData);
        }
        
        console.log('❓ Unknown device type:', deviceType);
        return '<span class="text-muted">Unknown Device Type</span>';
    }
    
    parseAva4MedicalData(data) {
        console.log('Parsing AVA4 medical data:', data);
        
        const attribute = data.attribute;
        const value = data.value;
        
        console.log('AVA4 attribute:', attribute);
        console.log('AVA4 value:', value);
        
        if (!attribute || !value) {
            console.log('No attribute or value found for AVA4');
            return '<span class="text-muted">Status</span>';
        }
        
        const deviceList = value.device_list;
        console.log('AVA4 device list:', deviceList);
        
        if (!deviceList || deviceList.length === 0) {
            console.log('No device list found for AVA4');
            return '<span class="text-muted">No data</span>';
        }
        
        const reading = deviceList[0];
        console.log('AVA4 reading:', reading);
        
        let result = '';
        
        switch (attribute) {
            case 'BP_BIOLIGTH':
                result = `BP: ${reading.bp_high}/${reading.bp_low} mmHg<br>PR: ${reading.PR} bpm`;
                break;
            case 'Contour_Elite':
            case 'AccuChek_Instant':
                result = `Glucose: ${reading.blood_glucose} mg/dL<br>Marker: ${reading.marker || 'N/A'}`;
                break;
            case 'Oximeter JUMPER':
                result = `SpO2: ${reading.spo2}%<br>Pulse: ${reading.pulse} bpm<br>PI: ${reading.pi}`;
                break;
            case 'IR_TEMO_JUMPER':
                result = `Temp: ${reading.temp}°C<br>Mode: ${reading.mode}`;
                break;
            case 'BodyScale_JUMPER':
                result = `Weight: ${reading.weight} kg<br>Resistance: ${reading.resistance}`;
                break;
            case 'MGSS_REF_UA':
                result = `Uric Acid: ${reading.uric_acid} mg/dL`;
                break;
            case 'MGSS_REF_CHOL':
                result = `Cholesterol: ${reading.cholesterol} mg/dL`;
                break;
            default:
                result = `<span class="text-muted">${attribute}</span>`;
        }
        
        console.log('AVA4 parsed result:', result);
        return `<div class="small">${result}</div>`;
    }
    
    parseKatiMedicalData(data) {
        console.log('Parsing Kati medical data:', data);
        
        const dataType = data.data_type;
        console.log('Kati data type:', dataType);
        
        switch (dataType) {
            case 'vital_signs':
                let result = '';
                if (data.heart_rate) result += `HR: ${data.heart_rate} bpm<br>`;
                if (data.blood_pressure) {
                    result += `BP: ${data.blood_pressure.bp_sys}/${data.blood_pressure.bp_dia} mmHg<br>`;
                }
                if (data.spO2) result += `SpO2: ${data.spO2}%<br>`;
                if (data.body_temperature) result += `Temp: ${data.body_temperature}°C`;
                console.log('Kati vital signs result:', result);
                return result || '<span class="text-muted">No vital signs</span>';
                
            case 'batch_vital_signs':
                console.log('Kati batch data:', data);
                return `<span class="badge bg-info">Batch Data (${data.num_datas || 0} readings)</span>`;
                
            case 'emergency_alert':
                const alertType = data.alert_type === 'SOS' ? 'bg-danger' : 'bg-warning';
                return `<span class="badge ${alertType}">${data.alert_type}</span>`;
                
            default:
                console.log('Unknown Kati data type:', dataType);
                return '<span class="text-muted">-</span>';
        }
    }
    
    parseQubeMedicalData(data) {
        const attribute = data.attribute;
        const value = data.value;
        
        if (!attribute || !value) return '<span class="text-muted">Status</span>';
        
        let result = '';
        
        switch (attribute) {
            case 'WBP_JUMPER':
                result = `BP: ${value.bp_high}/${value.bp_low} mmHg<br>PR: ${value.pr} bpm`;
                break;
            case 'CONTOUR':
                result = `Glucose: ${value.blood_glucose} mg/dL<br>Marker: ${value.marker || 'N/A'}`;
                break;
            case 'BodyScale_JUMPER':
                result = `Weight: ${value.weight} kg<br>Resistance: ${value.Resistance}`;
                break;
            case 'TEMO_Jumper':
                result = `Temp: ${value.Temp}°C<br>Mode: ${value.mode}`;
                break;
            case 'Oximeter_JUMPER':
                result = `SpO2: ${value.spo2}%<br>Pulse: ${value.pulse} bpm<br>PI: ${value.pi}`;
                break;
            default:
                result = `<span class="text-muted">${attribute}</span>`;
        }
        
        return `<div class="small">${result}</div>`;
    }
    
    parseHealthData(message) {
        if (!message.medical_data) return '<span class="text-muted">-</span>';
        
        const data = message.medical_data;
        const deviceType = message.device_type;
        
        if (deviceType === 'Kati Watch') {
            return this.parseKatiHealthData(data);
        }
        
        return '<span class="text-muted">-</span>';
    }
    
    parseKatiHealthData(data) {
        const dataType = data.data_type;
        
        switch (dataType) {
            case 'heartbeat':
                let result = '';
                if (data.step !== undefined) result += `Steps: ${data.step}<br>`;
                return result || '<span class="text-muted">No health data</span>';
                
            case 'sleepdata':
                return `<span class="badge bg-secondary">Sleep Data</span>`;
                
            default:
                return '<span class="text-muted">-</span>';
        }
    }
    
    parseDeviceData(message) {
        const deviceType = message.device_type;
        
        if (deviceType === 'Kati Watch') {
            return this.parseKatiDeviceData(message.medical_data, message.raw_payload);
        } else if (deviceType === 'AVA4') {
            return this.parseAva4DeviceData(message);
        } else if (deviceType === 'Qube-Vital') {
            return this.parseQubeDeviceData(message);
        }
        
        return '<span class="text-muted">-</span>';
    }
    
    parseKatiDeviceData(data, rawPayload) {
        let result = '';
        
        // Add IMEI information
        if (rawPayload && rawPayload.IMEI) {
            result += `<div class="small mb-1"><strong>IMEI:</strong> <code>${rawPayload.IMEI}</code></div>`;
        }
        
        // Add device status information
        if (data && data.data_type === 'heartbeat') {
            if (data.battery !== undefined) {
                const batteryClass = data.battery > 50 ? 'bg-success' : data.battery > 20 ? 'bg-warning' : 'bg-danger';
                result += `<span class="badge ${batteryClass}">Battery: ${data.battery}%</span><br>`;
            }
            if (data.signal_gsm !== undefined) {
                const signalClass = data.signal_gsm > 70 ? 'bg-success' : data.signal_gsm > 40 ? 'bg-warning' : 'bg-danger';
                result += `<span class="badge ${signalClass}">Signal: ${data.signal_gsm}%</span><br>`;
            }
            if (data.satellites !== undefined) {
                result += `<span class="badge bg-info">GPS: ${data.satellites} satellites</span>`;
            }
        }
        
        return result || '<span class="text-muted">No device data</span>';
    }
    
    parseAva4DeviceData(message) {
        let result = '';
        
        // Add MAC address information
        if (message.raw_payload && message.raw_payload.mac) {
            result += `<div class="small mb-1"><strong>MAC:</strong> <code>${message.raw_payload.mac}</code></div>`;
        }
        
        // Add IMEI information
        if (message.raw_payload && message.raw_payload.IMEI) {
            result += `<div class="small mb-1"><strong>IMEI:</strong> <code>${message.raw_payload.IMEI}</code></div>`;
        }
        
        // Add device name
        if (message.raw_payload && message.raw_payload.name) {
            result += `<div class="small mb-1"><strong>Name:</strong> ${message.raw_payload.name}</div>`;
        }
        
        // Add online status
        if (message.topic === 'ESP32_BLE_GW_TX') {
            const payload = message.raw_payload;
            if (payload.type === 'HB_Msg' || payload.type === 'reportMsg') {
                result += `<span class="badge bg-success">Online</span>`;
            }
        }
        
        return result || '<span class="text-muted">-</span>';
    }
    
    parseQubeDeviceData(message) {
        let result = '';
        
        // Add MAC address information
        if (message.raw_payload && message.raw_payload.mac) {
            result += `<div class="small mb-1"><strong>MAC:</strong> <code>${message.raw_payload.mac}</code></div>`;
        }
        
        // Add IMEI information
        if (message.raw_payload && message.raw_payload.IMEI) {
            result += `<div class="small mb-1"><strong>IMEI:</strong> <code>${message.raw_payload.IMEI}</code></div>`;
        }
        
        // Add device name
        if (message.raw_payload && message.raw_payload.name) {
            result += `<div class="small mb-1"><strong>Name:</strong> ${message.raw_payload.name}</div>`;
        }
        
        // Add online status
        if (message.message_type === 'HB_Msg') {
            result += `<span class="badge bg-success">Online</span>`;
        }
        
        return result || '<span class="text-muted">-</span>';
    }
    
    updatePatientsDisplay() {
        const container = document.getElementById('patients-container');
        if (!container) return;
        
        const patientCount = this.patients.length;
        const mappedCount = this.patients.filter(p => p.ava_mac_address || p.watch_mac_address).length;
        const successRate = patientCount > 0 ? Math.round((mappedCount / patientCount) * 100) : 0;
        
        container.innerHTML = `
            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-body text-center">
                            <h3>${patientCount}</h3>
                            <div class="text-muted">Total Patients</div>
                        </div>
                    </div>
                </div>
                <div class="col-12 mt-3">
                    <div class="card">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span>Mapping Success Rate</span>
                                <span class="badge bg-success">${successRate}%</span>
                            </div>
                            <div class="progress">
                                <div class="progress-bar bg-success" style="width: ${successRate}%"></div>
                            </div>
                            <small class="text-muted">${mappedCount} of ${patientCount} patients mapped</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    updatePatientsTable() {
        const container = document.getElementById('patients-table-container');
        if (!container) return;
        
        if (this.patients.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="ti ti-users-off" style="font-size: 2rem;"></i>
                    <p class="mt-2">No patients found</p>
                </div>
            `;
            return;
        }
        
        const tableHtml = `
            <div class="table-responsive">
                <table class="table table-vcenter transaction-table">
                    <thead>
                        <tr>
                            <th>Patient Name</th>
                            <th>ID Card</th>
                            <th>AVA4 MAC</th>
                            <th>Watch MAC</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.patients.map(patient => {
                            const fullName = `${patient.first_name || ''} ${patient.last_name || ''}`.trim() || 'Unknown';
                            const hasAva4 = patient.ava_mac_address ? 'bg-success' : 'bg-secondary';
                            const hasWatch = patient.watch_mac_address ? 'bg-info' : 'bg-secondary';
                            
                            return `
                                <tr>
                                    <td>${fullName}</td>
                                    <td><code>${patient.id_card || 'N/A'}</code></td>
                                    <td><span class="badge ${hasAva4}">${patient.ava_mac_address || 'Not Mapped'}</span></td>
                                    <td><span class="badge ${hasWatch}">${patient.watch_mac_address || 'Not Mapped'}</span></td>
                                    <td><span class="badge bg-success">${patient.registration_status || 'Registered'}</span></td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = tableHtml;
    }
    
    setupEventListeners() {
        // Profile link
        const profileLink = document.getElementById('profile-link');
        if (profileLink) {
            profileLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.showUserProfile();
            });
        }
    }
    
    showUserProfile() {
        if (this.userProfile) {
            const profileHtml = `
                <div class="modal fade" id="profileModal" tabindex="-1">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">User Profile</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="d-flex align-items-center mb-3">
                                    <span class="avatar avatar-lg me-3">
                                        <i class="ti ti-user"></i>
                                    </span>
                                    <div>
                                        <h4 class="mb-1">${this.userProfile.username || this.userProfile.name || 'User'}</h4>
                                        <div class="text-muted">${this.userProfile.role || 'User'}</div>
                                    </div>
                                </div>
                                <div class="row">
                                    <div class="col-6">
                                        <strong>Username:</strong><br>
                                        <span class="text-muted">${this.userProfile.username || 'N/A'}</span>
                                    </div>
                                    <div class="col-6">
                                        <strong>Role:</strong><br>
                                        <span class="text-muted">${this.userProfile.role || 'N/A'}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Remove existing modal if any
            const existingModal = document.getElementById('profileModal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // Add new modal
            document.body.insertAdjacentHTML('beforeend', profileHtml);
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('profileModal'));
            modal.show();
        }
    }
    
    // Redis-based real-time data fetching
    async startRedisRealTimeUpdates() {
        console.log('🚀 Starting Redis real-time updates...');
        
        // Load initial Redis data
        await this.loadRedisEvents();
        await this.loadRedisStats();
        
        // Set up periodic updates
        this.redisUpdateInterval = setInterval(async () => {
            await this.loadRedisEvents();
            await this.loadRedisStats();
        }, 2000); // Update every 2 seconds
        
        // Listen for real-time events from Socket.IO
        if (this.socket) {
            this.socket.on('real_time_event', (data) => {
                console.log('📡 Redis real-time event received:', data);
                this.handleRedisRealTimeEvent(data);
            });
        }
    }
    
    async loadRedisEvents() {
        try {
            const response = await fetch('/api/redis/events?limit=50');
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.redisEvents = data.data;
                    this.updateRedisEventsDisplay();
                    // Also update dashboard messages immediately
                    this.updateDashboardMessages();
                }
            }
        } catch (error) {
            console.error('Error loading Redis events:', error);
        }
    }
    
    async loadRedisStats() {
        try {
            const response = await fetch('/api/redis/stats');
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.redisStats = data.data;
                    this.updateRedisStatsDisplay();
                }
            }
        } catch (error) {
            console.error('Error loading Redis stats:', error);
        }
    }
    
    handleRedisRealTimeEvent(eventData) {
        console.log('📡 Handling Redis real-time event:', eventData);
        
        // Add to events list
        this.redisEvents.unshift(eventData.data);
        if (this.redisEvents.length > 100) {
            this.redisEvents.pop();
        }
        
        // Update displays
        this.updateRedisEventsDisplay();
        this.updateRedisStatsDisplay();
        
        // Update real-time event stream
        this.updateRealTimeEventStream(eventData.data);
    }
    
    updateRedisEventsDisplay() {
        const container = document.getElementById('redis-events-container');
        if (!container) return;
        
        // Clear loading message
        const loadingMessage = container.querySelector('.text-center.text-muted');
        if (loadingMessage) {
            loadingMessage.remove();
        }
        
        // Update events list
        container.innerHTML = '';
        this.redisEvents.slice(0, 20).forEach(event => {
            const eventElement = this.createRedisEventElement(event);
            container.appendChild(eventElement);
        });
        
        // Also update the main dashboard messages container
        this.updateDashboardMessages();
    }
    
    updateDashboardMessages() {
        const container = document.getElementById('messages-container');
        if (!container) {
            // Silently return if messages-container doesn't exist (not on dashboard page)
            return;
        }
        
        console.log('🔄 updateDashboardMessages called with', this.redisEvents.length, 'events');
        console.log('✅ messages-container found, updating...');
        
        // Clear loading message
        const loadingMessage = container.querySelector('.text-center.text-muted');
        if (loadingMessage) {
            console.log('🗑️ Removing loading message');
            loadingMessage.remove();
        }
        
        // Update messages list
        container.innerHTML = '';
        console.log('📝 Adding', this.redisEvents.slice(0, 20).length, 'messages to dashboard');
        
        this.redisEvents.slice(0, 20).forEach((event, index) => {
            // Convert data flow event to MQTT message format
            const mqttMessage = this.convertDataFlowToMQTTMessage(event);
            const messageElement = this.createMessageElement(mqttMessage);
            container.appendChild(messageElement);
            console.log(`✅ Added message ${index + 1}:`, mqttMessage.topic, mqttMessage.device_type);
        });
        
        // Update statistics
        this.stats.totalMessages = this.redisEvents.length;
        this.updateStatisticsDisplay();
        
        console.log('✅ Dashboard messages updated successfully');
    }
    
    convertDataFlowToMQTTMessage(event) {
        // Extract MQTT payload from data flow event
        const payload = event.details?.payload || event.details?.raw_payload || {};
        const topic = event.details?.topic || 'unknown';
        const timestamp = event.timestamp || event.server_timestamp;
        
        return {
            timestamp: timestamp,
            topic: topic,
            payload: payload,
            device_type: event.source || 'Unknown',
            message_type: event.event_type || 'unknown',
            status: event.status || 'info',
            message: event.message || 'No message'
        };
    }
    
    updateRedisStatsDisplay() {
        const container = document.getElementById('redis-stats-container');
        if (!container) return;
        
        const stats = this.redisStats;
        
        // Update total events
        const totalElement = container.querySelector('#redis-total-events');
        if (totalElement) {
            totalElement.textContent = stats.total || 0;
        }
        
        // Update source breakdown
        const sourceElement = container.querySelector('#redis-source-breakdown');
        if (sourceElement) {
            sourceElement.innerHTML = '';
            Object.entries(stats.by_source || {}).forEach(([source, count]) => {
                const sourceItem = document.createElement('div');
                sourceItem.className = 'd-flex justify-content-between align-items-center mb-2';
                sourceItem.innerHTML = `
                    <span class="badge bg-primary">${source}</span>
                    <span class="fw-bold">${count}</span>
                `;
                sourceElement.appendChild(sourceItem);
            });
        }
        
        // Update event type breakdown
        const typeElement = container.querySelector('#redis-type-breakdown');
        if (typeElement) {
            typeElement.innerHTML = '';
            Object.entries(stats.by_type || {}).forEach(([type, count]) => {
                const typeItem = document.createElement('div');
                typeItem.className = 'd-flex justify-content-between align-items-center mb-2';
                typeItem.innerHTML = `
                    <span class="badge bg-info">${type}</span>
                    <span class="fw-bold">${count}</span>
                `;
                typeElement.appendChild(typeItem);
            });
        }
    }
    
    createRedisEventElement(event) {
        const eventElement = document.createElement('div');
        eventElement.className = 'card mb-2 border-start border-3 border-primary';
        
        const timestamp = new Date(event.timestamp).toLocaleTimeString();
        const source = event.source || 'unknown';
        const eventType = event.event_type || 'unknown';
        const status = event.status || 'info';
        const message = event.message || 'No message';
        
        eventElement.innerHTML = `
            <div class="card-body py-2">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="d-flex align-items-center mb-1">
                            <span class="badge bg-${this.getStatusColor(status)} me-2">${status.toUpperCase()}</span>
                            <span class="badge bg-secondary me-2">${source}</span>
                            <span class="badge bg-info">${eventType}</span>
                        </div>
                        <p class="mb-1 small">${message}</p>
                        <small class="text-muted">${timestamp}</small>
                    </div>
                </div>
            </div>
        `;
        
        return eventElement;
    }
    
    getStatusColor(status) {
        switch (status.toLowerCase()) {
            case 'success': return 'success';
            case 'error': return 'danger';
            case 'warning': return 'warning';
            case 'info': return 'info';
            default: return 'secondary';
        }
    }
    
    updateRealTimeEventStream(event) {
        const container = document.getElementById('real-time-event-stream');
        if (!container) return;
        
        const streamElement = document.createElement('div');
        streamElement.className = 'alert alert-info alert-dismissible fade show';
        streamElement.innerHTML = `
            <strong>${event.source || 'Unknown'}</strong> - ${event.message || 'Event received'}
            <small class="d-block text-muted">${new Date(event.timestamp).toLocaleTimeString()}</small>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        container.insertBefore(streamElement, container.firstChild);
        
        // Limit to 10 events
        const alerts = container.querySelectorAll('.alert');
        if (alerts.length > 10) {
            alerts[alerts.length - 1].remove();
        }
    }
    
    // Cleanup method
    cleanup() {
        if (this.redisUpdateInterval) {
            clearInterval(this.redisUpdateInterval);
            this.redisUpdateInterval = null;
        }
    }
}

// Global functions
function refreshData() {
    if (window.mqttApp) {
        window.mqttApp.loadInitialData();
    }
}

// Initialize the app globally
document.addEventListener('DOMContentLoaded', function() {
    window.mqttApp = new MQTTMonitorApp();
}); 