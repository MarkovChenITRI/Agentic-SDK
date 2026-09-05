/**
 * Talking to a voice agent from the page: microphone in, answer out.
 *
 * The page never holds a credential. It opens one websocket to the Playground
 * and everything — the transcription service, the synthesis service — happens
 * on the other side of it.
 *
 * Interruption is handled here first and reported afterwards. Stopping the
 * playback is a local decision the browser can make in one frame; truncating
 * the conversation is the server's job and can take as long as it takes. Doing
 * them in the other order would leave the agent talking over the person for a
 * whole round trip, which is the thing being interrupted is meant to fix.
 */

const SERVICE_SAMPLE_RATE = 16000;
const FRAME_SAMPLES = 1024;

export function bindVoiceConversation(page, { onTranscript, onStatus }) {
	if (page?.dataset.voice !== "true") {
		return null;
	}
	const session = {
		id: `voice-${Date.now()}-${Math.random().toString(36).slice(1, 7)}`,
		socket: null,
		context: null,
		playing: [],
		playheadAt: 0,
		startedSpeakingAt: 0,
	};

	const say = (message) => onStatus?.(message);

	function open() {
		const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
		const socket = new WebSocket(`${scheme}//${window.location.host}/playground/voice/${session.id}`);
		socket.binaryType = "arraybuffer";
		socket.addEventListener("message", (event) => {
			if (typeof event.data !== "string") {
				play(event.data);
				return;
			}
			handle(JSON.parse(event.data));
		});
		socket.addEventListener("close", () => say("語音連線結束了。重新整理頁面可以再開始。"));
		session.socket = socket;
	}

	function handle(message) {
		if (message.type === "speech_started") {
			// The service heard someone begin, before it knows what they said.
			stopPlaying();
			return;
		}
		if (message.type === "transcript" && message.text) {
			onTranscript?.(message.text);
			return;
		}
		if (message.type === "unavailable" || message.type === "nothing_to_interrupt") {
			say(message.message);
		}
	}

	async function listen() {
		let microphone;
		try {
			microphone = await navigator.mediaDevices.getUserMedia({ audio: true });
		} catch (error) {
			// A refusal and a missing microphone look the same from here: in both
			// cases the page would otherwise just sit there being silent.
			say("這個 Agent 要用麥克風才能聽你說話。請在瀏覽器的網址列允許麥克風權限，然後重新整理頁面。你也可以直接打字。");
			return;
		}
		open();
		const context = new AudioContext();
		session.context = context;
		const source = context.createMediaStreamSource(microphone);
		const meter = context.createScriptProcessor(FRAME_SAMPLES, 1, 1);
		meter.addEventListener("audioprocess", (event) => {
			send(event.inputBuffer.getChannelData(0), context.sampleRate);
		});
		source.connect(meter);
		meter.connect(context.destination);
		say("可以開始說話了。");
	}

	function send(samples, sampleRate) {
		if (session.socket?.readyState !== WebSocket.OPEN) {
			return;
		}
		session.socket.send(toServiceAudio(samples, sampleRate));
	}

	function play(audio) {
		const context = session.context;
		if (!context) {
			return;
		}
		const samples = new Int16Array(audio);
		const buffer = context.createBuffer(1, samples.length, SERVICE_SAMPLE_RATE);
		const channel = buffer.getChannelData(0);
		for (let index = 0; index < samples.length; index += 1) {
			channel[index] = samples[index] / 32768;
		}
		const piece = context.createBufferSource();
		piece.buffer = buffer;
		piece.connect(context.destination);
		// Queued against the running clock rather than played on arrival, so the
		// pieces join up instead of overlapping each other.
		const startAt = Math.max(context.currentTime, session.playheadAt);
		if (!session.playing.length) {
			session.startedSpeakingAt = startAt;
		}
		piece.start(startAt);
		session.playheadAt = startAt + buffer.duration;
		session.playing.push(piece);
		piece.addEventListener("ended", () => {
			session.playing = session.playing.filter((item) => item !== piece);
		});
	}

	function stopPlaying() {
		if (!session.playing.length) {
			return;
		}
		// How much of the answer the person actually heard — which only the thing
		// playing it knows, because speech lags generation by seconds.
		const heard = Math.max(0, (session.context?.currentTime || 0) - session.startedSpeakingAt);
		for (const piece of session.playing) {
			piece.stop();
		}
		session.playing = [];
		session.playheadAt = 0;
		session.socket?.send(JSON.stringify({ type: "interject", heard_seconds: heard }));
	}

	function speak(text) {
		if (!text || session.socket?.readyState !== WebSocket.OPEN) {
			return;
		}
		session.socket.send(JSON.stringify({ type: "speak", text }));
	}

	// No button: a voice agent that has to be switched on is a form with a
	// microphone attached.
	listen();

	return { sessionId: session.id, speak, stopPlaying };
}

/** Resample to the rate the transcription service takes, as 16-bit mono. */
export function toServiceAudio(samples, sampleRate) {
	const ratio = sampleRate / SERVICE_SAMPLE_RATE;
	const length = Math.floor(samples.length / ratio);
	const out = new Int16Array(length);
	for (let index = 0; index < length; index += 1) {
		const value = samples[Math.floor(index * ratio)];
		// Clamped before scaling: a value outside ±1 wraps around when it is
		// truncated, and a loud word comes out as a crackle.
		const clamped = Math.max(-1, Math.min(1, value));
		out[index] = clamped < 0 ? clamped * 32768 : clamped * 32767;
	}
	return out.buffer;
}
