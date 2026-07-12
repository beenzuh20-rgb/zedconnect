/**
 * WebRTC Video/Audio Calling for zedconnect
 * Handles peer-to-peer video and audio calls between matched users
 */

class CallManager {
    constructor() {
        this.ws = null;
        this.peerConnection = null;
        this.localStream = null;
        this.remoteStream = null;
        this.currentCallType = null; // 'video' or 'audio'
        this.inCall = false;
        this.callInProgress = false;
        this.currentPartnerId = null;
        this.currentPartnerName = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.pendingCallTimeout = null;
        this.ringtoneAudio = null;

        // ICE servers for NAT traversal
        this.iceServers = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' },
            ]
        };

        // DOM elements - will be initialized when UI is created
        this.elements = {};
    }

    /**
     * Initialize the WebSocket connection for signaling
     */
    connect() {
        // Get the auth token from cookie
        const token = this.getCookie('access_token');
        if (!token) {
            console.error('No auth token found');
            return;
        }

        // Determine WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/signaling?token=${encodeURIComponent(token)}`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('Signaling WebSocket connected');
                this.reconnectAttempts = 0;
                // Start keepalive ping
                this.startKeepalive();
            };

            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleSignalingMessage(data);
            };

            this.ws.onclose = (event) => {
                console.log('Signaling WebSocket disconnected', event.code);
                this.stopKeepalive();
                // Attempt reconnection if not in a call
                if (!this.inCall && this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    setTimeout(() => this.connect(), 2000 * this.reconnectAttempts);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        } catch (e) {
            console.error('Failed to create WebSocket:', e);
        }
    }

    /**
     * Send keepalive pings every 30 seconds
     */
    startKeepalive() {
        this.keepaliveInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
    }

    stopKeepalive() {
        if (this.keepaliveInterval) {
            clearInterval(this.keepaliveInterval);
            this.keepaliveInterval = null;
        }
    }

    /**
     * Get cookie value by name
     */
    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    /**
     * Handle incoming signaling messages
     */
    handleSignalingMessage(data) {
        switch (data.type) {
            case 'incoming_call':
                this.handleIncomingCall(data);
                break;
            case 'call_accepted':
                this.handleCallAccepted(data);
                break;
            case 'call_rejected':
                this.handleCallRejected(data);
                break;
            case 'call_busy':
                this.handleCallBusy(data);
                break;
            case 'user_offline':
                this.handleUserOffline(data);
                break;
            case 'offer':
                this.handleOffer(data);
                break;
            case 'answer':
                this.handleAnswer(data);
                break;
            case 'ice_candidate':
                this.handleIceCandidate(data);
                break;
            case 'call_ended':
                this.handleRemoteEndCall(data);
                break;
            case 'pong':
                // Keepalive response, ignore
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    /**
     * Send a signaling message
     */
    sendMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
    }

    /**
     * Initiate a call to another user
     */
    async startCall(targetId, targetName, callType = 'video') {
        if (this.inCall) {
            this.showNotification('You are already in a call');
            return;
        }

        this.currentPartnerId = targetId;
        this.currentPartnerName = targetName;
        this.currentCallType = callType;
        this.callInProgress = true;

        // Show calling UI
        this.showCallingUI(targetName, callType);

        // Send call request
        this.sendMessage({
            type: 'call_request',
            target_id: targetId,
            call_type: callType
        });

        // Set timeout for unanswered call
        this.pendingCallTimeout = setTimeout(() => {
            if (this.callInProgress && !this.inCall) {
                this.endCall('No answer');
                this.showNotification('No one answered the call');
            }
        }, 30000);
    }

    /**
     * Handle incoming call from another user
     */
    handleIncomingCall(data) {
        if (this.inCall || this.callInProgress) {
            // Busy - send busy signal
            this.sendMessage({
                type: 'call_busy',
                target_id: data.from_id
            });
            return;
        }

        this.currentPartnerId = data.from_id;
        this.currentPartnerName = data.from_name;
        this.currentCallType = data.call_type;
        this.callInProgress = true;

        // Show incoming call UI
        this.showIncomingCallUI(data);
        this.playRingtone();
    }

    /**
     * Accept an incoming call
     */
    async acceptCall() {
        this.stopRingtone();
        this.hideIncomingCallUI();

        this.sendMessage({
            type: 'call_accepted',
            target_id: this.currentPartnerId
        });

        // Start local media and create peer connection
        await this.initializeMediaAndPeer();
    }

    /**
     * Reject an incoming call
     */
    rejectCall() {
        this.stopRingtone();
        this.hideIncomingCallUI();

        this.sendMessage({
            type: 'call_rejected',
            target_id: this.currentPartnerId
        });

        this.callInProgress = false;
        this.currentPartnerId = null;
        this.currentPartnerName = null;
    }

    /**
     * Handle call accepted by remote user
     */
    async handleCallAccepted(data) {
        if (this.pendingCallTimeout) {
            clearTimeout(this.pendingCallTimeout);
            this.pendingCallTimeout = null;
        }

        // Start local media and create peer connection (as offerer)
        await this.initializeMediaAndPeer(true);
    }

    /**
     * Handle call rejected by remote user
     */
    handleCallRejected(data) {
        if (this.pendingCallTimeout) {
            clearTimeout(this.pendingCallTimeout);
            this.pendingCallTimeout = null;
        }

        this.cleanupCall();
        this.hideCallUI();
        this.showNotification(`${this.currentPartnerName || 'User'} declined the call`);
    }

    /**
     * Handle busy signal
     */
    handleCallBusy(data) {
        if (this.pendingCallTimeout) {
            clearTimeout(this.pendingCallTimeout);
            this.pendingCallTimeout = null;
        }

        this.cleanupCall();
        this.hideCallUI();
        this.showNotification(`${this.currentPartnerName || 'User'} is currently in a call`);
    }

    /**
     * Handle user offline
     */
    handleUserOffline(data) {
        if (this.pendingCallTimeout) {
            clearTimeout(this.pendingCallTimeout);
            this.pendingCallTimeout = null;
        }

        this.cleanupCall();
        this.hideCallUI();
        this.showNotification('User is offline');
    }

    /**
     * Initialize local media stream and create peer connection
     */
    async initializeMediaAndPeer(asOfferer = false) {
        try {
            const constraints = {
                audio: true,
                video: this.currentCallType === 'video'
            };

            this.localStream = await navigator.mediaDevices.getUserMedia(constraints);
            this.createPeerConnection();

            // Add local stream to peer connection
            this.localStream.getTracks().forEach(track => {
                this.peerConnection.addTrack(track, this.localStream);
            });

            // Show the call UI with local video
            this.showCallUI(this.currentPartnerName, this.currentCallType);

            // Set local video stream
            if (this.elements.localVideo) {
                this.elements.localVideo.srcObject = this.localStream;
            }

            if (asOfferer) {
                // Create and send offer
                const offer = await this.peerConnection.createOffer();
                await this.peerConnection.setLocalDescription(offer);
                this.sendMessage({
                    type: 'offer',
                    target_id: this.currentPartnerId,
                    sdp: this.peerConnection.localDescription
                });
            }

            this.inCall = true;
        } catch (err) {
            console.error('Error accessing media devices:', err);
            this.showNotification('Could not access camera/microphone. Please check permissions.');
            this.cleanupCall();
            this.hideCallUI();
        }
    }

    /**
     * Create RTCPeerConnection
     */
    createPeerConnection() {
        this.peerConnection = new RTCPeerConnection(this.iceServers);

        // Handle ICE candidates
        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                this.sendMessage({
                    type: 'ice_candidate',
                    target_id: this.currentPartnerId,
                    candidate: event.candidate
                });
            }
        };

        // Handle connection state changes
        this.peerConnection.onconnectionstatechange = () => {
            console.log('Connection state:', this.peerConnection.connectionState);
            if (this.peerConnection.connectionState === 'disconnected' ||
                this.peerConnection.connectionState === 'failed') {
                this.handleRemoteEndCall({ from_id: this.currentPartnerId });
            }
        };

        // Handle remote stream
        this.peerConnection.ontrack = (event) => {
            this.remoteStream = event.streams[0];
            if (this.elements.remoteVideo) {
                this.elements.remoteVideo.srcObject = this.remoteStream;
            }
        };
    }

    /**
     * Handle incoming offer
     */
    async handleOffer(data) {
        if (!this.peerConnection) {
            await this.initializeMediaAndPeer(false);
        }

        try {
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp));
            const answer = await this.peerConnection.createAnswer();
            await this.peerConnection.setLocalDescription(answer);
            this.sendMessage({
                type: 'answer',
                target_id: this.currentPartnerId,
                sdp: this.peerConnection.localDescription
            });
        } catch (err) {
            console.error('Error handling offer:', err);
        }
    }

    /**
     * Handle incoming answer
     */
    async handleAnswer(data) {
        try {
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp));
        } catch (err) {
            console.error('Error handling answer:', err);
        }
    }

    /**
     * Handle incoming ICE candidate
     */
    async handleIceCandidate(data) {
        try {
            if (data.candidate) {
                await this.peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
            }
        } catch (err) {
            console.error('Error adding ICE candidate:', err);
        }
    }

    /**
     * End the current call
     */
    endCall(reason = '') {
        if (this.currentPartnerId) {
            this.sendMessage({
                type: 'end_call',
                target_id: this.currentPartnerId
            });
        }

        this.cleanupCall();
        this.hideCallUI();
        if (reason) {
            this.showNotification(reason);
        }
    }

    /**
     * Handle remote user ending the call
     */
    handleRemoteEndCall(data) {
        this.cleanupCall();
        this.hideCallUI();
        this.showNotification(`${this.currentPartnerName || 'User'} ended the call`);
    }

    /**
     * Clean up all call resources
     */
    cleanupCall() {
        // Stop local media tracks
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }

        // Close peer connection
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }

        // Clear timeouts
        if (this.pendingCallTimeout) {
            clearTimeout(this.pendingCallTimeout);
            this.pendingCallTimeout = null;
        }

        this.remoteStream = null;
        this.inCall = false;
        this.callInProgress = false;
        this.currentCallType = null;
        this.stopRingtone();
    }

    /**
     * Toggle local video on/off during a call
     */
    toggleVideo() {
        if (this.localStream) {
            const videoTrack = this.localStream.getVideoTracks()[0];
            if (videoTrack) {
                videoTrack.enabled = !videoTrack.enabled;
                const btn = document.getElementById('toggle-video-btn');
                if (btn) {
                    btn.textContent = videoTrack.enabled ? '📷 Video On' : '🚫 Video Off';
                    btn.classList.toggle('btn-danger', !videoTrack.enabled);
                }
            }
        }
    }

    /**
     * Toggle local audio on/off during a call
     */
    toggleAudio() {
        if (this.localStream) {
            const audioTrack = this.localStream.getAudioTracks()[0];
            if (audioTrack) {
                audioTrack.enabled = !audioTrack.enabled;
                const btn = document.getElementById('toggle-audio-btn');
                if (btn) {
                    btn.textContent = audioTrack.enabled ? '🎤 Mic On' : '🔇 Mic Off';
                    btn.classList.toggle('btn-danger', !audioTrack.enabled);
                }
            }
        }
    }

    // ==================== UI Methods ====================

    /**
     * Show incoming call notification
     */
    showIncomingCallUI(data) {
        const callTypeIcon = data.call_type === 'video' ? '📹' : '📞';
        const callTypeText = data.call_type === 'video' ? 'Video Call' : 'Audio Call';

        const overlay = document.createElement('div');
        overlay.id = 'incoming-call-overlay';
        overlay.className = 'call-overlay';
        overlay.innerHTML = `
            <div class="incoming-call-card">
                <div class="incoming-call-header">
                    <h3>${callTypeIcon} Incoming ${callTypeText}</h3>
                </div>
                <div class="incoming-call-body">
                    <img src="${data.from_picture || '/static/default_profile.png'}" alt="${data.from_name}" class="incoming-call-pic">
                    <h2>${data.from_name}</h2>
                    <p>is calling you...</p>
                </div>
                <div class="incoming-call-actions">
                    <button onclick="callManager.acceptCall()" class="btn btn-accept-call">✅ Accept</button>
                    <button onclick="callManager.rejectCall()" class="btn btn-reject-call">❌ Decline</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
    }

    /**
     * Hide incoming call UI
     */
    hideIncomingCallUI() {
        const overlay = document.getElementById('incoming-call-overlay');
        if (overlay) {
            overlay.remove();
        }
    }

    /**
     * Show calling UI (when initiating a call)
     */
    showCallingUI(targetName, callType) {
        const callTypeIcon = callType === 'video' ? '📹' : '📞';
        const callTypeText = callType === 'video' ? 'Video Call' : 'Audio Call';

        const overlay = document.createElement('div');
        overlay.id = 'calling-overlay';
        overlay.className = 'call-overlay';
        overlay.innerHTML = `
            <div class="calling-card">
                <div class="calling-spinner"></div>
                <h2>${callTypeIcon} ${callTypeText}</h2>
                <p>Calling <strong>${targetName}</strong>...</p>
                <button onclick="callManager.endCall('Cancelled')" class="btn btn-end-call">End Call</button>
            </div>
        `;
        document.body.appendChild(overlay);
    }

    /**
     * Show active call UI
     */
    showCallUI(partnerName, callType) {
        // Remove any existing call overlays
        this.hideCallUI();
        this.hideIncomingCallUI();
        const callingOverlay = document.getElementById('calling-overlay');
        if (callingOverlay) callingOverlay.remove();

        const isVideo = callType === 'video';

        const overlay = document.createElement('div');
        overlay.id = 'active-call-overlay';
        overlay.className = 'call-overlay';
        overlay.innerHTML = `
            <div class="active-call-container">
                <div class="call-header">
                    <h3>${isVideo ? '📹' : '📞'} Call with ${partnerName}</h3>
                    <span id="call-timer">00:00</span>
                </div>
                <div class="call-videos">
                    <div class="remote-video-container">
                        <video id="remote-video" autoplay playsinline ${isVideo ? '' : 'style="display:none"'}>
                        </video>
                        ${!isVideo ? '<div class="audio-only-avatar"><div class="avatar-icon">🎵</div><h2>' + partnerName + '</h2></div>' : ''}
                    </div>
                    <div class="local-video-container">
                        <video id="local-video" autoplay playsinline muted></video>
                    </div>
                </div>
                <div class="call-controls">
                    <button id="toggle-audio-btn" onclick="callManager.toggleAudio()" class="btn btn-call-control">🎤 Mic On</button>
                    ${isVideo ? '<button id="toggle-video-btn" onclick="callManager.toggleVideo()" class="btn btn-call-control">📷 Video On</button>' : ''}
                    <button onclick="callManager.endCall()" class="btn btn-end-call-red">End Call</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        // Store element references
        this.elements.remoteVideo = document.getElementById('remote-video');
        this.elements.localVideo = document.getElementById('local-video');

        // Start call timer
        this.startCallTimer();
    }

    /**
     * Hide all call UI elements
     */
    hideCallUI() {
        const overlays = [
            'active-call-overlay',
            'incoming-call-overlay',
            'calling-overlay'
        ];
        overlays.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.remove();
        });
        this.stopCallTimer();
    }

    /**
     * Play ringtone sound
     */
    playRingtone() {
        try {
            // Create a simple beep using AudioContext as ringtone
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            this.ringtoneAudio = audioCtx;

            function playBeep(ctx, frequency, duration, delay) {
                return new Promise((resolve) => {
                    setTimeout(() => {
                        const oscillator = ctx.createOscillator();
                        const gainNode = ctx.createGain();
                        oscillator.connect(gainNode);
                        gainNode.connect(ctx.destination);
                        oscillator.frequency.value = frequency;
                        oscillator.type = 'sine';
                        gainNode.gain.setValueAtTime(0.3, ctx.currentTime);
                        gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + duration);
                        oscillator.start(ctx.currentTime);
                        oscillator.stop(ctx.currentTime + duration);
                        resolve();
                    }, delay);
                });
            }

            // Play ring pattern
            const ringPattern = async () => {
                for (let i = 0; i < 10; i++) {
                    if (!this.ringtoneAudio) break;
                    await playBeep(audioCtx, 440, 0.3, 0);
                    await playBeep(audioCtx, 440, 0.3, 500);
                    await new Promise(r => setTimeout(r, 1000));
                }
            };
            ringPattern();
        } catch (e) {
            console.log('Ringtone not available:', e);
        }
    }

    /**
     * Stop ringtone
     */
    stopRingtone() {
        if (this.ringtoneAudio) {
            this.ringtoneAudio.close();
            this.ringtoneAudio = null;
        }
    }

    /**
     * Start call timer
     */
    startCallTimer() {
        this.callStartTime = Date.now();
        this.timerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.callStartTime) / 1000);
            const minutes = String(Math.floor(elapsed / 60)).padStart(2, '0');
            const seconds = String(elapsed % 60).padStart(2, '0');
            const timerEl = document.getElementById('call-timer');
            if (timerEl) {
                timerEl.textContent = `${minutes}:${seconds}`;
            }
        }, 1000);
    }

    /**
     * Stop call timer
     */
    stopCallTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    /**
     * Show a notification toast
     */
    showNotification(message) {
        const toast = document.createElement('div');
        toast.className = 'call-notification';
        toast.textContent = message;
        document.body.appendChild(toast);

        // Animate in
        setTimeout(() => toast.classList.add('show'), 10);

        // Remove after 3 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

// Global instance
const callManager = new CallManager();

// Auto-connect when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Check if user is logged in (has access_token cookie)
    if (callManager.getCookie('access_token')) {
        callManager.connect();
    }
});
</write_to_file>