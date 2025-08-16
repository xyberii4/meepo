window.audioCapture = {
  audioContext: null,
  recorder: null,
  audioChunks: [],
  isCapturing: false,

  log: function (msg) {
    console.log('[AudioCapture] ' + msg);
  },

  startCapture: async function () {
    this.log("Starting audio capture...");

    // Find active media elements with audio
    const findMediaElements = async (retries = 5, delay = 2000) => {
      for (let i = 0; i < retries; i++) {
        const mediaElements = Array.from(
          document.querySelectorAll("audio, video")
        ).filter((el) =>
          !el.paused &&
          el.srcObject instanceof MediaStream &&
          el.srcObject.getAudioTracks().length > 0
        );

        if (mediaElements.length > 0) {
          this.log(`Found ${mediaElements.length} active media elements`);
          return mediaElements;
        }
        this.log(`No active media elements found. Retrying... (${i + 1}/${retries})`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
      return [];
    };

    const mediaElements = await findMediaElements();
    if (mediaElements.length === 0) {
      throw new Error("No active media elements found");
    }

    // Create audio context and mix streams
    this.audioContext = new AudioContext();
    const destinationNode = this.audioContext.createMediaStreamDestination();
    let sourcesConnected = 0;

    mediaElements.forEach((element, index) => {
      try {
        const elementStream = element.srcObject ||
          (element.captureStream && element.captureStream()) ||
          (element.mozCaptureStream && element.mozCaptureStream());

        if (elementStream instanceof MediaStream && elementStream.getAudioTracks().length > 0) {
          const sourceNode = this.audioContext.createMediaStreamSource(elementStream);
          sourceNode.connect(destinationNode);
          sourcesConnected++;
          this.log(`Connected audio stream ${index + 1}/${mediaElements.length}`);
        }
      } catch (error) {
        this.log(`Could not connect element ${index + 1}: ${error.message}`);
      }
    });

    if (sourcesConnected === 0) {
      throw new Error("Could not connect any audio streams");
    }

    const combinedStream = destinationNode.stream;
    this.log(`Successfully combined ${sourcesConnected} audio streams`);

    // Setup audio processing to capture chunks
    const mediaSource = this.audioContext.createMediaStreamSource(combinedStream);
    this.recorder = this.audioContext.createScriptProcessor(4096, 1, 1);

    this.recorder.onaudioprocess = (event) => {
      if (!this.isCapturing) return;

      const inputData = event.inputBuffer.getChannelData(0);
      const audioData = new Float32Array(inputData);

      // Convert to base64 for easy transfer to Python
      const buffer = new ArrayBuffer(audioData.length * 4);
      const view = new Float32Array(buffer);
      view.set(audioData);
      const base64 = btoa(String.fromCharCode(...new Uint8Array(buffer)));

      // Store audio chunk with timestamp
      this.audioChunks.push({
        timestamp: Date.now(),
        data: base64,
        sampleRate: this.audioContext.sampleRate,
        length: audioData.length
      });

      // Limit buffer size to prevent memory issues (keep last 100 chunks ~4 seconds)
      if (this.audioChunks.length > 100) {
        this.audioChunks = this.audioChunks.slice(-100);
      }
    };

    // Connect the audio processing pipeline
    mediaSource.connect(this.recorder);
    const gainNode = this.audioContext.createGain();
    gainNode.gain.value = 0; // Silent output
    this.recorder.connect(gainNode);
    gainNode.connect(this.audioContext.destination);

    this.isCapturing = true;
    this.log("Audio capture started successfully");
    return true;
  },

  stopCapture: function () {
    this.isCapturing = false;
    if (this.recorder) {
      this.recorder.disconnect();
      this.recorder = null;
    }
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    this.log("Audio capture stopped");
  },

  getAudioChunks: function (clearAfterGet = true) {
    const chunks = [...this.audioChunks];
    if (clearAfterGet) {
      this.audioChunks = [];
    }
    return chunks;
  },

  isActive: function () {
    return this.isCapturing;
  }
};
