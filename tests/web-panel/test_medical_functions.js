// Test script for medical monitor functions
console.log('🧪 Testing Medical Monitor Functions...');

// Test getDataType function
function testGetDataType() {
    console.log('\n📋 Testing getDataType function:');
    
    // Test with null event
    try {
        const result1 = getDataType(null);
        console.log('✅ getDataType(null):', result1);
    } catch (error) {
        console.log('❌ getDataType(null) failed:', error.message);
    }
    
    // Test with event without data
    try {
        const result2 = getDataType({ source: 'Kati' });
        console.log('✅ getDataType({source: "Kati"}):', result2);
    } catch (error) {
        console.log('❌ getDataType({source: "Kati"}) failed:', error.message);
    }
    
    // Test with valid Kati data
    try {
        const result3 = getDataType({ 
            source: 'Kati', 
            data: { battery: 85 } 
        });
        console.log('✅ getDataType(Kati with battery):', result3);
    } catch (error) {
        console.log('❌ getDataType(Kati with battery) failed:', error.message);
    }
    
    // Test with valid AVA4 data
    try {
        const result4 = getDataType({ 
            source: 'AVA4', 
            data: { data: { msg: 'Heart rate: 72 bpm' } } 
        });
        console.log('✅ getDataType(AVA4):', result4);
    } catch (error) {
        console.log('❌ getDataType(AVA4) failed:', error.message);
    }
}

// Test getDataValue function
function testGetDataValue() {
    console.log('\n📊 Testing getDataValue function:');
    
    // Test with null event
    try {
        const result1 = getDataValue(null);
        console.log('✅ getDataValue(null):', result1);
    } catch (error) {
        console.log('❌ getDataValue(null) failed:', error.message);
    }
    
    // Test with event without data
    try {
        const result2 = getDataValue({ source: 'Kati' });
        console.log('✅ getDataValue({source: "Kati"}):', result2);
    } catch (error) {
        console.log('❌ getDataValue({source: "Kati"}) failed:', error.message);
    }
    
    // Test with valid Kati data
    try {
        const result3 = getDataValue({ 
            source: 'Kati', 
            data: { battery: 85 } 
        });
        console.log('✅ getDataValue(Kati with battery):', result3);
    } catch (error) {
        console.log('❌ getDataValue(Kati with battery) failed:', error.message);
    }
    
    // Test with valid AVA4 data
    try {
        const result4 = getDataValue({ 
            source: 'AVA4', 
            data: { data: { msg: 'Heart rate: 72 bpm' } } 
        });
        console.log('✅ getDataValue(AVA4):', result4);
    } catch (error) {
        console.log('❌ getDataValue(AVA4) failed:', error.message);
    }
}

// Test getDataStatus function
function testGetDataStatus() {
    console.log('\n📈 Testing getDataStatus function:');
    
    // Test with null event
    try {
        const result1 = getDataStatus(null);
        console.log('✅ getDataStatus(null):', result1);
    } catch (error) {
        console.log('❌ getDataStatus(null) failed:', error.message);
    }
    
    // Test with event without data
    try {
        const result2 = getDataStatus({ source: 'Kati' });
        console.log('✅ getDataStatus({source: "Kati"}):', result2);
    } catch (error) {
        console.log('❌ getDataStatus({source: "Kati"}) failed:', error.message);
    }
    
    // Test with valid Kati data
    try {
        const result3 = getDataStatus({ 
            source: 'Kati', 
            data: { battery: 85 } 
        });
        console.log('✅ getDataStatus(Kati with battery):', result3);
    } catch (error) {
        console.log('❌ getDataStatus(Kati with battery) failed:', error.message);
    }
}

// Test API connectivity
async function testAPI() {
    console.log('\n🌐 Testing API connectivity:');
    
    try {
        const response = await fetch('http://localhost:8098/api/medical-data');
        if (response.ok) {
            const data = await response.json();
            console.log('✅ Medical data API is accessible');
            console.log('📊 Data records:', data.data.length);
            console.log('📋 Sample data:', data.data[0] || 'No data available');
        } else {
            console.log('❌ Medical data API returned status:', response.status);
        }
    } catch (error) {
        console.log('❌ Medical data API test failed:', error.message);
    }
}

// Run all tests
async function runAllTests() {
    console.log('🚀 Starting Medical Monitor Function Tests...');
    console.log('=' .repeat(50));
    
    testGetDataType();
    testGetDataValue();
    testGetDataStatus();
    await testAPI();
    
    console.log('\n' + '=' .repeat(50));
    console.log('✅ All tests completed!');
}

// Export for use in browser console
if (typeof window !== 'undefined') {
    window.testMedicalFunctions = runAllTests;
    console.log('💡 Run testMedicalFunctions() in the browser console to test all functions');
}

// Run tests if this is executed directly
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { runAllTests, testGetDataType, testGetDataValue, testGetDataStatus, testAPI };
} 