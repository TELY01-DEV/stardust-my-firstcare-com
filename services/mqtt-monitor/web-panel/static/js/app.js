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
        
        this.init();
    }
    
    init() {
        this.loadUserProfile();
        this.connectWebSocket();
        this.loadInitialData();
        this.setupEventListeners();
        this.setupNavigation();
    }
    
    setupNavigation() {
        // Handle navigation tabs
        const navLinks = document.querySelectorAll('[data-tab]');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const tabName = link.getAttribute('data-tab');
                this.switchTab(tabName);
            });
        });
        
        // Handle URL hash changes
        window.addEventListener('hashchange', () => {
            const hash = window.location.hash.substring(1);
            if (hash) {
                this.switchTab(hash);
            }
        });
        
        // Handle initial hash
        const hash = window.location.hash.substring(1);
        if (hash) {
            this.switchTab(hash);
        }
    }
    
    switchTab(tabName) {
        // Update navigation
        document.querySelectorAll('[data-tab]').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        // Update tab content
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
        
        // Update page title and description
        this.updatePageHeader(tabName);
        
        // Load tab-specific data
        this.loadTabData(tabName);
        
        this.currentTab = tabName;
    }
    
    updatePageHeader(tabName) {
        const titles = {
            'dashboard': 'Real-time MQTT Monitoring Dashboard',
            'messages': 'MQTT Message Transactions',
            'devices': 'Device Management',
            'patients': 'Patient Management'
        };
        
        const descriptions = {
            'dashboard': 'Monitor device messages, patient mapping, and system statistics',
            'messages': 'View all MQTT message transactions and device communications',
            'devices': 'Manage and monitor AVA4, Kati Watch, and Qube-Vital devices',
            'patients': 'View patient information and device mapping status'
        };
        
        const titleElement = document.getElementById('page-title');
        const descElement = document.getElementById('page-description');
        
        if (titleElement) titleElement.textContent = titles[tabName] || titles['dashboard'];
        if (descElement) descElement.textContent = descriptions[tabName] || descriptions['dashboard'];
    }
    
    loadTabData(tabName) {
        switch (tabName) {
            case 'messages':
                this.updateMessagesTable();
                break;
            case 'devices':
                this.updateDevicesTables();
                break;
            case 'patients':
                this.updatePatientsTable();
                break;
        }
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
        // Connect to WebSocket server
        this.socket = new WebSocket('ws://localhost:8097');
        
        this.socket.onopen = () => {
            console.log('Connected to WebSocket server');
            this.updateConnectionStatus('connected');
        };
        
        this.socket.onclose = () => {
            console.log('Disconnected from WebSocket server');
            this.updateConnectionStatus('disconnected');
            // Attempt to reconnect after 5 seconds
            setTimeout(() => this.connectWebSocket(), 5000);
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus('disconnected');
        };
        
        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
    }
    
    handleWebSocketMessage(data) {
        if (data.type === 'mqtt_message') {
            this.handleMQTTMessage(data.data);
        } else if (data.type === 'statistics') {
            this.updateStatistics(data.data);
        } else if (data.type === 'initial_data') {
            this.handleInitialData(data);
        }
    }
    
    handleMQTTMessage(message) {
        // Add message to list
        this.messages.unshift(message);
        if (this.messages.length > this.maxMessages) {
            this.messages.pop();
        }
        
        // Update statistics
        this.stats.totalMessages++;
        this.updateStatisticsDisplay();
        
        // Update message display
        this.addMessageToDisplay(message);
        
        // Update messages table if on messages tab
        if (this.currentTab === 'messages') {
            this.updateMessagesTable();
        }
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
        // Update statistics cards
        document.getElementById('total-messages').textContent = this.stats.totalMessages || 0;
        document.getElementById('processing-rate').textContent = this.stats.processingRate || 0;
        document.getElementById('ava4-count').textContent = this.stats.ava4Count || 0;
        document.getElementById('ava4-active').textContent = this.stats.ava4Active || 0;
        document.getElementById('kati-count').textContent = this.stats.katiCount || 0;
        document.getElementById('kati-active').textContent = this.stats.katiActive || 0;
        document.getElementById('qube-count').textContent = this.stats.qubeCount || 0;
        document.getElementById('qube-active').textContent = this.stats.qubeActive || 0;
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
        
        const devices = this.devices.qube || [];
        
        if (devices.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="ti ti-hospital-off" style="font-size: 2rem;"></i>
                    <p class="mt-2">No Qube-Vital devices found</p>
                </div>
            `;
            return;
        }
        
        const tableHtml = `
            <div class="table-responsive">
                <table class="table table-vcenter transaction-table">
                    <thead>
                        <tr>
                            <th>Hospital Name</th>
                            <th>MAC Address</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${devices.map(device => `
                            <tr>
                                <td>${device.name || 'Unknown'}</td>
                                <td><code>${device.mac_hv01_box || 'N/A'}</code></td>
                                <td><span class="badge bg-warning">Active</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = tableHtml;
    }
    
    updateMessagesTable() {
        const container = document.getElementById('messages-table-container');
        if (!container) return;
        
        if (this.messages.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="ti ti-message-circle-off" style="font-size: 3rem;"></i>
                    <p class="mt-2">No messages received yet</p>
                </div>
            `;
            return;
        }
        
        const tableHtml = `
            <div class="table-responsive">
                <table class="table table-vcenter transaction-table">
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Device Type</th>
                            <th>Topic</th>
                            <th>Medical Data</th>
                            <th>Health Data</th>
                            <th>Device Data</th>
                            <th>Status</th>
                            <th>Patient Mapping</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.messages.map(message => {
                            const timestamp = new Date(message.timestamp).toLocaleString();
                            const deviceType = this.getDeviceType(message.topic);
                            const statusClass = message.status === 'processed' ? 'bg-success' : 
                                              message.status === 'patient_not_found' ? 'bg-warning' : 'bg-danger';
                            const patientMapping = message.patient_mapping ? 
                                `${message.patient_mapping.patient_name || 'Unknown'} (${message.patient_mapping.patient_id})` : 
                                'Not Mapped';
                            
                            // Parse medical data
                            const medicalData = this.parseMedicalData(message);
                            
                            // Parse health data
                            const healthData = this.parseHealthData(message);
                            
                            // Parse device data
                            const deviceData = this.parseDeviceData(message);
                            
                            return `
                                <tr>
                                    <td>${timestamp}</td>
                                    <td><span class="badge ${this.getDeviceBadgeClass(deviceType)}">${deviceType}</span></td>
                                    <td><code>${message.topic}</code></td>
                                    <td>${medicalData}</td>
                                    <td>${healthData}</td>
                                    <td>${deviceData}</td>
                                    <td><span class="badge ${statusClass}">${message.status}</span></td>
                                    <td>${patientMapping}</td>
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
        console.log('Parsing medical data for message:', message);
        console.log('Medical data:', message.medical_data);
        
        if (!message.medical_data) {
            console.log('No medical data found');
            return '<span class="text-muted">-</span>';
        }
        
        const data = message.medical_data;
        const deviceType = message.device_type;
        
        console.log('Device type:', deviceType);
        console.log('Medical data structure:', data);
        
        if (deviceType === 'AVA4') {
            return this.parseAva4MedicalData(data);
        } else if (deviceType === 'Kati Watch') {
            return this.parseKatiMedicalData(data);
        } else if (deviceType === 'Qube-Vital') {
            return this.parseQubeMedicalData(data);
        }
        
        return '<span class="text-muted">Unknown</span>';
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
}

// Global functions
function refreshData() {
    if (window.mqttApp) {
        window.mqttApp.loadInitialData();
    }
}

function clearMessages() {
    const container = document.getElementById('messages-container');
    if (container) {
        container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="ti ti-message-circle-off" style="font-size: 3rem;"></i>
                <p class="mt-2">Messages cleared</p>
            </div>
        `;
    }
    if (window.mqttApp) {
        window.mqttApp.messages = [];
        window.mqttApp.updateMessagesTable();
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.mqttApp = new MQTTMonitorApp();
}); 