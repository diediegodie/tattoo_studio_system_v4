// modal_system_verification.js - Comprehensive verification of all modal fixes
// Run this in browser console to test all modal functionality

function runModalSystemVerification() {
    console.log('🚀 STARTING COMPREHENSIVE MODAL SYSTEM VERIFICATION');
    console.log('==================================================');

    let testResults = {
        passed: 0,
        failed: 0,
        total: 0
    };

    function test(name, condition, details = '') {
        testResults.total++;
        if (condition) {
            console.log(`✅ PASS: ${name}`);
            testResults.passed++;
        } else {
            console.log(`❌ FAIL: ${name}`);
            if (details) console.log(`   Details: ${details}`);
            testResults.failed++;
        }
    }

    // Test 1: Modal system availability
    test('Modal system loaded', typeof window.openModal === 'function' && typeof window.openCustomModal === 'function',
         'openModal and openCustomModal functions should be available globally');

    // Test 2: Confirm button selector consistency
    const modalTemplate = document.querySelector('#unified-modal');
    test('Modal template exists', modalTemplate !== null,
         'Modal template should be injected into DOM');

    if (modalTemplate) {
        const confirmBtn = modalTemplate.querySelector('#modal-confirm-btn');
        test('Confirm button has correct ID', confirmBtn !== null && confirmBtn.id === 'modal-confirm-btn',
             'Confirm button should have ID #modal-confirm-btn');
    }

    // Test 3: No duplicate confirm buttons
    const allConfirmBtns = document.querySelectorAll('#modal-confirm-btn');
    test('Single confirm button', allConfirmBtns.length <= 1,
         `Found ${allConfirmBtns.length} confirm buttons, should be 0 or 1`);

    // Test 4: Debug logging functions exist
    test('Debug logging in handleConfirm', typeof window.handleConfirm === 'function',
         'handleConfirm should be available for debugging');

    // Test 5: confirmAction function exists
    test('confirmAction function available', typeof window.confirmAction === 'function',
         'confirmAction should be available for unified confirmations');

    // Test 6: Test basic modal functionality
    console.log('\n🧪 Testing Basic Modal Functionality...');

    return new Promise((resolve) => {
        if (typeof window.openModal !== 'function') {
            test('Basic modal test', false, 'openModal function not available');
            resolve(testResults);
            return;
        }

        let modalOpened = false;
        let confirmClicked = false;
        let modalClosed = false;

        // Override console.log temporarily to capture debug messages
        const originalLog = console.log;
        const logs = [];
        console.log = (...args) => {
            logs.push(args.join(' '));
            originalLog.apply(console, args);
        };

        window.openModal({
            title: 'Verification Test Modal',
            body: '<p>This is a test modal for verification.</p>',
            onConfirm: function() {
                confirmClicked = true;
                console.log('[TEST] onConfirm callback executed');
            },
            onCancel: function() {
                console.log('[TEST] onCancel callback executed');
            }
        });

        // Check if modal opened
        setTimeout(() => {
            const modal = document.querySelector('#unified-modal');
            modalOpened = modal && modal.style.display === 'flex';

            test('Modal opens correctly', modalOpened, 'Modal should be visible after openModal call');

            if (modalOpened) {
                // Try to click confirm button
                const confirmBtn = modal.querySelector('#modal-confirm-btn');
                if (confirmBtn) {
                    confirmBtn.click();

                    setTimeout(() => {
                        const modalStillOpen = modal.style.display === 'flex';
                        modalClosed = !modalStillOpen;

                        test('Modal closes on confirm', modalClosed, 'Modal should close after confirm button click');
                        test('onConfirm callback executed', confirmClicked, 'onConfirm callback should have been called');

                        // Check debug logs
                        const hasDebugLogs = logs.some(log => log.includes('[DEBUG]'));
                        test('Debug logging active', hasDebugLogs, 'Debug logs should appear in console');

                        // Restore console.log
                        console.log = originalLog;

                        console.log('\n📊 VERIFICATION RESULTS:');
                        console.log(`Total Tests: ${testResults.total}`);
                        console.log(`Passed: ${testResults.passed}`);
                        console.log(`Failed: ${testResults.failed}`);
                        console.log(`Success Rate: ${Math.round((testResults.passed / testResults.total) * 100)}%`);

                        if (testResults.failed === 0) {
                            console.log('🎉 ALL TESTS PASSED! Modal system is working correctly.');
                        } else {
                            console.log('⚠️  Some tests failed. Check the details above.');
                        }

                        resolve(testResults);
                    }, 100);
                } else {
                    test('Confirm button found', false, 'Confirm button should be present in modal');
                    console.log = originalLog;
                    resolve(testResults);
                }
            } else {
                console.log = originalLog;
                resolve(testResults);
            }
        }, 100);
    });
}

// Auto-run verification if this script is loaded directly
if (typeof window !== 'undefined' && window.document) {
    // Wait for DOM and modal system to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(runModalSystemVerification, 500);
        });
    } else {
        setTimeout(runModalSystemVerification, 500);
    }
}

// Export for manual calling
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { runModalSystemVerification };
} else if (typeof window !== 'undefined') {
    window.runModalSystemVerification = runModalSystemVerification;
}