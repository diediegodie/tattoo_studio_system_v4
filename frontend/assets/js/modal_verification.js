// modal_verification.js - Verification script for modal system
// Run this in the browser console to test modal functionality

function verifyModalSystem() {
    console.log('=== MODAL SYSTEM VERIFICATION ===');

    // Check if modal instance exists
    const modalInstance = document.getElementById('unified-modal');
    if (!modalInstance) {
        console.error('❌ Modal instance not found!');
        return false;
    }
    console.log('✅ Modal instance found');

    // Check for confirm button
    const confirmBtn = modalInstance.querySelector('#modal-confirm-btn');
    if (!confirmBtn) {
        console.error('❌ Confirm button not found!');
        return false;
    }
    console.log('✅ Confirm button found with ID:', confirmBtn.id);

    // Check for multiple confirm buttons
    const allConfirmBtns = document.querySelectorAll('#modal-confirm-btn');
    if (allConfirmBtns.length > 1) {
        console.error('❌ Multiple confirm buttons found:', allConfirmBtns.length);
        return false;
    }
    console.log('✅ Only one confirm button exists');

    // Check if handleConfirm function exists
    if (typeof window.handleConfirm === 'undefined') {
        console.error('❌ handleConfirm function not found in global scope');
        return false;
    }
    console.log('✅ handleConfirm function available globally');

    // Test modal opening and closing
    console.log('Testing modal open/close...');

    // Open a test modal
    if (typeof window.openModal === 'function') {
        window.openModal({
            title: 'Test Modal',
            body: '<p>This is a test modal for verification.</p>',
            onConfirm: function() {
                console.log('✅ Test onConfirm callback executed');
            },
            onCancel: function() {
                console.log('✅ Test onCancel callback executed');
            }
        });
        console.log('✅ Test modal opened successfully');
    } else {
        console.error('❌ openModal function not found');
        return false;
    }

    // Check if modal is visible
    if (modalInstance.style.display === 'flex') {
        console.log('✅ Modal is visible');
    } else {
        console.error('❌ Modal is not visible');
        return false;
    }

    // Close modal
    if (typeof window.closeModal === 'function') {
        window.closeModal();
        console.log('✅ Modal closed successfully');
    } else {
        console.error('❌ closeModal function not found');
        return false;
    }

    // Check if modal is hidden
    if (modalInstance.style.display === 'none') {
        console.log('✅ Modal is hidden');
    } else {
        console.error('❌ Modal is still visible after close');
        return false;
    }

    console.log('=== VERIFICATION COMPLETE ===');
    console.log('🎉 All modal system checks passed!');
    return true;
}

// Auto-run verification if this script is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', verifyModalSystem);
} else {
    verifyModalSystem();
}