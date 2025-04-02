class DeviceFingerprinter {
    static async generate() {
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            
            const data = {
                // Hardware/OS
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                hardwareConcurrency: navigator.hardwareConcurrency || 'unknown',
                deviceMemory: navigator.deviceMemory || 'unknown',
                
                // Screen
                screenResolution: `${window.screen.width}x${window.screen.height}`,
                colorDepth: window.screen.colorDepth,
                pixelRatio: window.devicePixelRatio,
                
                // Timezone
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                
                // WebGL Fingerprint
                webglVendor: gl ? gl.getParameter(gl.VENDOR) : 'none',
                webglRenderer: gl ? gl.getParameter(gl.RENDERER) : 'none',
                
                // Audio Context (randomized)
                audioFingerprint: await this.getAudioFingerprint(),
                
                // Touch support
                touchSupport: 'ontouchstart' in window,
                
                // Cookies enabled
                cookiesEnabled: navigator.cookieEnabled,
                
                // Do Not Track
                doNotTrack: navigator.doNotTrack || 'unknown'
            };
            
            return {
                raw: data,
                hash: await this.hashData(data)
            };
        } catch (error) {
            console.error('Fingerprint generation failed:', error);
            return {
                raw: {error: 'fingerprint_failed'},
                hash: 'failed_' + Math.random().toString(36).substring(2)
            };
        }
    }
    
    static async hashData(data) {
        const str = JSON.stringify(data);
        const encoder = new TextEncoder();
        const dataBuffer = encoder.encode(str);
        
        try {
            const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        } catch (error) {
            console.error('Hashing failed:', error);
            return 'hash_failed_' + Math.random().toString(36).substring(2);
        }
    }
    
    static async getAudioFingerprint() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const analyser = audioContext.createAnalyser();
            
            oscillator.connect(analyser);
            analyser.connect(audioContext.destination);
            oscillator.start(0);
            
            const timeDomainData = new Float32Array(analyser.frequencyBinCount);
            analyser.getFloatTimeDomainData(timeDomainData);
            
            oscillator.disconnect();
            
            return Array.from(timeDomainData)
                .map(n => n.toFixed(2))
                .join('')
                .slice(0, 100); // Take first 100 chars
        } catch (error) {
            return 'audio_error';
        }
    }
}

// Usage in forms
document.addEventListener('DOMContentLoaded', async () => {
    const fingerprint = await DeviceFingerprinter.generate();
    
    // Add to all forms
    document.querySelectorAll('form').forEach(form => {
        const hashInput = document.createElement('input');
        hashInput.type = 'hidden';
        hashInput.name = 'device_hash';
        hashInput.value = fingerprint.hash;
        form.appendChild(hashInput);
        
        const rawInput = document.createElement('input');
        rawInput.type = 'hidden';
        rawInput.name = 'device_data';
        rawInput.value = JSON.stringify(fingerprint.raw);
        form.appendChild(rawInput);
    });
    
    // Add screen info
    const screenInput = document.createElement('input');
    screenInput.type = 'hidden';
    screenInput.name = 'screen_width';
    screenInput.value = window.screen.width;
    document.body.appendChild(screenInput);
    
    const screenHeightInput = document.createElement('input');
    screenHeightInput.type = 'hidden';
    screenHeightInput.name = 'screen_height';
    screenHeightInput.value = window.screen.height;
    document.body.appendChild(screenHeightInput);
});