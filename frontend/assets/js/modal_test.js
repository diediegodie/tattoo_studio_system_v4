// modal_test.js - Test functions for modal system

function testBasicModal() {
    console.log('=== TESTING BASIC MODAL ===');
    openModal({
        title: 'Basic Modal Test',
        body: '<p>This is a basic modal test. Click confirm to see the callback execute.</p>',
        onConfirm: function () {
            console.log('✅ Basic modal onConfirm executed');
            alert('Basic modal confirmed!');
        },
        onCancel: function () {
            console.log('✅ Basic modal onCancel executed');
        }
    });
}

function testModalWithoutCallback() {
    console.log('=== TESTING MODAL WITHOUT CALLBACK ===');
    openModal({
        title: 'Modal without Callback',
        body: '<p>This modal has no onConfirm callback. It should just close when confirmed.</p>',
        onConfirm: null
    });
}

function testCustomModal() {
    console.log('=== TESTING CUSTOM MODAL ===');
    openCustomModal({
        title: 'Custom Modal Test',
        content: '<div><p>This is custom modal content.</p><input type="text" placeholder="Test input"></div>',
        onConfirm: function () {
            console.log('✅ Custom modal onConfirm executed');
            alert('Custom modal confirmed!');
        }
    });
}

function testMultipleModals() {
    console.log('=== TESTING MULTIPLE MODALS ===');
    // Open first modal
    openModal({
        title: 'First Modal',
        body: '<p>This is the first modal. Opening second modal...</p>',
        onConfirm: function () {
            console.log('✅ First modal confirmed');
        }
    });

    // After a delay, try to open another modal
    setTimeout(function () {
        console.log('Attempting to open second modal...');
        openModal({
            title: 'Second Modal',
            body: '<p>This should replace the first modal.</p>',
            onConfirm: function () {
                console.log('✅ Second modal confirmed');
            }
        });
    }, 1000);
}

// Override console.log to also show in debug output
const originalLog = console.log;
console.log = function (...args) {
    originalLog.apply(console, args);
    const debugOutput = document.getElementById('debug-output');
    if (debugOutput) {
        const message = args.join(' ');
        debugOutput.innerHTML += '<div>' + new Date().toLocaleTimeString() + ': ' + message + '</div>';
        debugOutput.scrollTop = debugOutput.scrollHeight;
    }
};

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('test-basic-modal').addEventListener('click', testBasicModal);
    document.getElementById('test-modal-no-callback').addEventListener('click', testModalWithoutCallback);
    document.getElementById('test-custom-modal').addEventListener('click', testCustomModal);
    document.getElementById('test-multiple-modals').addEventListener('click', testMultipleModals);
});